import base64
import gc
import io
import threading
import uuid

import numpy as np
import torch
from aiohttp import web
from PIL import Image

import comfy.model_management
from server import PromptServer


_pending_image_gates = {}
_pending_image_gates_lock = threading.Lock()


def _image_tensor_to_pil(image_tensor):
    while image_tensor.ndim > 3 and image_tensor.shape[0] == 1:
        image_tensor = image_tensor[0]
    img_np = (image_tensor.detach().cpu().clamp(0, 1).numpy() * 255).astype(np.uint8)
    if img_np.ndim == 3 and img_np.shape[-1] == 1:
        img_np = img_np[:, :, 0]
    return Image.fromarray(img_np)


def _normalize_images(images):
    if not isinstance(images, torch.Tensor):
        raise TypeError(f"Expected IMAGE tensor, got {type(images).__name__}")

    if images.ndim == 3:
        images = images.unsqueeze(0)
    elif images.ndim == 4:
        pass
    elif images.ndim == 5:
        if images.shape[1] != 1:
            raise ValueError(
                "EU_图片筛选 only supports 5D IMAGE tensors with a single frame/time dimension; "
                f"got shape {tuple(images.shape)}"
            )
        images = images.reshape(images.shape[0], images.shape[-3], images.shape[-2], images.shape[-1])
    else:
        raise ValueError(f"EU_图片筛选 expected IMAGE shape [B,H,W,C], got {tuple(images.shape)}")

    if images.ndim != 4 or images.shape[-1] not in (1, 3, 4):
        raise ValueError(f"EU_图片筛选 expected IMAGE shape [B,H,W,C], got {tuple(images.shape)}")

    return images


def _first_value(value, default=None):
    if isinstance(value, list):
        return value[0] if len(value) > 0 else default
    return value


def _input_items(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item is not None]
    return [value]


def _merge_images(images):
    image_items = [_normalize_images(item) for item in _input_items(images)]
    if len(image_items) == 0:
        return None
    if len(image_items) == 1:
        return image_items[0]
    try:
        return torch.cat(image_items, dim=0)
    except RuntimeError as e:
        shapes = [tuple(item.shape) for item in image_items]
        raise ValueError(f"EU_图片筛选 cannot merge IMAGE list with different shapes: {shapes}") from e


def _merge_latents(latent):
    latent_items = _input_items(latent)
    if len(latent_items) == 0:
        return None
    if len(latent_items) == 1:
        return latent_items[0]

    samples_list = []
    for item in latent_items:
        if not isinstance(item, dict) or item.get("samples") is None:
            raise ValueError("EU_图片筛选 received a LATENT list item without samples")
        samples_list.append(item["samples"])

    try:
        merged_samples = torch.cat(samples_list, dim=0)
    except RuntimeError as e:
        shapes = [tuple(samples.shape) for samples in samples_list]
        raise ValueError(f"EU_图片筛选 cannot merge LATENT list with different shapes: {shapes}") from e

    merged = latent_items[0].copy()
    merged["samples"] = merged_samples

    noise_masks = []
    can_merge_noise_mask = True
    for item, samples in zip(latent_items, samples_list):
        noise_mask = item.get("noise_mask")
        if not isinstance(noise_mask, torch.Tensor) or noise_mask.shape[0] != samples.shape[0]:
            can_merge_noise_mask = False
            break
        noise_masks.append(noise_mask)
    if can_merge_noise_mask and len(noise_masks) == len(latent_items):
        merged["noise_mask"] = torch.cat(noise_masks, dim=0)
    else:
        merged.pop("noise_mask", None)

    batch_index_tensors = []
    batch_index_values = []
    batch_index_mode = None
    can_merge_batch_index = True
    for item, samples in zip(latent_items, samples_list):
        batch_index = item.get("batch_index")
        if isinstance(batch_index, torch.Tensor) and batch_index.shape[0] == samples.shape[0]:
            if batch_index_mode not in (None, "tensor"):
                can_merge_batch_index = False
                break
            batch_index_mode = "tensor"
            batch_index_tensors.append(batch_index)
        elif isinstance(batch_index, list) and len(batch_index) == samples.shape[0]:
            if batch_index_mode not in (None, "list"):
                can_merge_batch_index = False
                break
            batch_index_mode = "list"
            batch_index_values.extend(batch_index)
        elif batch_index is None:
            can_merge_batch_index = False
            break
        else:
            can_merge_batch_index = False
            break
    if can_merge_batch_index and batch_index_mode == "tensor":
        merged["batch_index"] = torch.cat(batch_index_tensors, dim=0)
    elif can_merge_batch_index and batch_index_mode == "list":
        merged["batch_index"] = batch_index_values
    else:
        merged.pop("batch_index", None)

    return merged


def _make_thumbnail_data_url(image_tensor, max_size=512):
    pil_img = _image_tensor_to_pil(image_tensor)
    width, height = pil_img.size
    thumb = pil_img.copy()
    thumb.thumbnail((max_size, max_size), Image.LANCZOS)

    buffered = io.BytesIO()
    thumb.save(buffered, format="JPEG", quality=85)
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return {
        "data": f"data:image/jpeg;base64,{img_base64}",
        "width": width,
        "height": height,
    }


def _select_latent_batch(latent, selected):
    if latent is None:
        return None

    selected_latent = latent.copy()
    samples = latent.get("samples")
    if samples is None:
        return selected_latent

    batch_size = int(samples.shape[0])
    selected_latent["samples"] = samples[selected]

    noise_mask = latent.get("noise_mask")
    if isinstance(noise_mask, torch.Tensor) and noise_mask.shape[0] == batch_size:
        selected_latent["noise_mask"] = noise_mask[selected]

    batch_index = latent.get("batch_index")
    if isinstance(batch_index, torch.Tensor) and batch_index.shape[0] == batch_size:
        selected_latent["batch_index"] = batch_index[selected]
    elif isinstance(batch_index, list) and len(batch_index) == batch_size:
        selected_latent["batch_index"] = [batch_index[i] for i in selected]

    return selected_latent


def _release_memory(reason):
    print(f"[EU_ImageSelectGate] releasing model/cache memory after {reason}")
    try:
        comfy.model_management.unload_all_models()
    except Exception as e:
        print(f"[EU_ImageSelectGate] unload_all_models failed: {e}")

    try:
        comfy.model_management.soft_empty_cache()
    except Exception as e:
        print(f"[EU_ImageSelectGate] soft_empty_cache failed: {e}")

    try:
        gc.collect()
    except Exception as e:
        print(f"[EU_ImageSelectGate] gc.collect failed: {e}")

    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception as e:
        print(f"[EU_ImageSelectGate] torch cuda cache cleanup failed: {e}")


@PromptServer.instance.routes.post("/eu_image_select_gate/continue")
async def eu_image_select_gate_continue(request):
    try:
        data = await request.json()
        session_id = data.get("session_id")
        selected = data.get("selected", [])
        cancelled = bool(data.get("cancelled", False))
        timed_out = bool(data.get("timed_out", False))

        with _pending_image_gates_lock:
            session = _pending_image_gates.get(session_id)

        if session is None:
            return web.json_response({"ok": False, "error": "session not found"}, status=404)

        session["selected"] = selected
        session["cancelled"] = cancelled
        session["timed_out"] = timed_out
        session["event"].set()
        return web.json_response({
            "ok": True,
            "selected": len(selected),
            "cancelled": cancelled,
            "timed_out": timed_out,
        })
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


class EU_ImageSelectGate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "timeout_sec": ("INT", {"default": 600, "min": 30, "max": 86400, "step": 10}),
                "取消等待时间": ("BOOLEAN", {"default": False, "label_on": "开启", "label_off": "关闭"}),
                "取消或超时释放缓存": ("BOOLEAN", {"default": False, "label_on": "开启", "label_off": "关闭"}),
            },
            "optional": {
                "images": ("IMAGE",),
                "latent": ("LATENT",),
                "vae": ("VAE",),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    CATEGORY = "EU Nodes/Utils"
    RETURN_TYPES = ("IMAGE", "LATENT", "STRING")
    RETURN_NAMES = ("images", "latent", "selection_info")
    FUNCTION = "select_images"
    INPUT_IS_LIST = True

    def select_images(self, timeout_sec: int, 取消等待时间=False, 取消或超时释放缓存=False, images=None, latent=None, vae=None, unique_id=None):
        timeout_sec = _first_value(timeout_sec, 600)
        取消等待时间 = bool(_first_value(取消等待时间, False))
        取消或超时释放缓存 = bool(_first_value(取消或超时释放缓存, False))
        unique_id = _first_value(unique_id)
        vae = _first_value(vae)

        latent = _merge_latents(latent)
        preview_images = _merge_images(images)
        if preview_images is None:
            if latent is None or vae is None:
                raise ValueError("EU_图片筛选 needs images, or latent + vae for internal preview decode")
            samples = latent.get("samples")
            if samples is None:
                raise ValueError("latent input is missing samples")
            preview_images = vae.decode(samples)
        preview_images = _normalize_images(preview_images)

        batch_size = int(preview_images.shape[0])
        if batch_size <= 0:
            raise ValueError("No upstream images found")

        if latent is not None:
            latent_batch = int(latent["samples"].shape[0])
            if latent_batch != batch_size:
                raise ValueError(f"image batch ({batch_size}) and latent batch ({latent_batch}) must match")

        session_id = f"{unique_id or 'eu_gate'}_{uuid.uuid4().hex[:8]}"
        thumbnails = []
        for i in range(batch_size):
            item = _make_thumbnail_data_url(preview_images[i])
            item["index"] = i
            thumbnails.append(item)

        event = threading.Event()
        with _pending_image_gates_lock:
            _pending_image_gates[session_id] = {
                "event": event,
                "selected": None,
                "cancelled": False,
                "timed_out": False,
            }

        PromptServer.instance.send_sync("eu_image_select_gate_show", {
            "session_id": session_id,
            "node_id": unique_id,
            "images": thumbnails,
            "batch_size": batch_size,
            "timeout_sec": timeout_sec,
            "wait_forever": bool(取消等待时间),
        })

        wait_label = "no timeout" if 取消等待时间 else f"timeout={timeout_sec}s"
        print(f"[EU_ImageSelectGate] waiting for selection: {session_id}, images={batch_size}, {wait_label}")
        wait_timeout = None if 取消等待时间 else max(1, int(timeout_sec))
        event_set = event.wait(timeout=wait_timeout)

        with _pending_image_gates_lock:
            result = _pending_image_gates.pop(session_id, None)

        if not event_set or result is None:
            print(f"[EU_ImageSelectGate] selection timed out, interrupting workflow: {session_id}")
            if 取消或超时释放缓存:
                _release_memory("timeout")
            raise comfy.model_management.InterruptProcessingException()

        if result.get("timed_out"):
            print(f"[EU_ImageSelectGate] selection timed out, interrupting workflow: {session_id}")
            if 取消或超时释放缓存:
                _release_memory("timeout")
            raise comfy.model_management.InterruptProcessingException()

        if result.get("cancelled"):
            print(f"[EU_ImageSelectGate] selection cancelled, interrupting workflow: {session_id}")
            if 取消或超时释放缓存:
                _release_memory("cancel")
            raise comfy.model_management.InterruptProcessingException()

        selected = result.get("selected") or []
        selected = sorted({int(i) for i in selected if 0 <= int(i) < batch_size})
        if len(selected) == 0:
            raise ValueError("No images selected")

        selected_images = preview_images[selected]
        selected_latent = _select_latent_batch(latent, selected)
        info = f"selected {len(selected)} of {batch_size}: {selected}"
        print(f"[EU_ImageSelectGate] {info}")
        return (selected_images, selected_latent, info)

    @classmethod
    def IS_CHANGED(cls, timeout_sec, 取消等待时间, 取消或超时释放缓存, images=None, latent=None, vae=None, unique_id=None):
        return float("NaN")
