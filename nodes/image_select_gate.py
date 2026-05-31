import base64
import io
import threading
import uuid

import numpy as np
from aiohttp import web
from PIL import Image

import comfy.model_management
from server import PromptServer


_pending_image_gates = {}
_pending_image_gates_lock = threading.Lock()


def _image_tensor_to_pil(image_tensor):
    img_np = (image_tensor.detach().cpu().clamp(0, 1).numpy() * 255).astype(np.uint8)
    return Image.fromarray(img_np)


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
                "images": ("IMAGE",),
                "timeout_sec": ("INT", {"default": 600, "min": 30, "max": 86400, "step": 10}),
                "取消等待时间": ("BOOLEAN", {"default": False, "label_on": "开启", "label_off": "关闭"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    CATEGORY = "EU Nodes/Utils"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "selection_info")
    FUNCTION = "select_images"

    def select_images(self, images, timeout_sec: int, 取消等待时间=False, unique_id=None):
        batch_size = int(images.shape[0])
        if batch_size <= 0:
            raise ValueError("No upstream images found")

        session_id = f"{unique_id or 'eu_gate'}_{uuid.uuid4().hex[:8]}"
        thumbnails = []
        for i in range(batch_size):
            item = _make_thumbnail_data_url(images[i])
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
            raise comfy.model_management.InterruptProcessingException()

        if result.get("timed_out"):
            print(f"[EU_ImageSelectGate] selection timed out, interrupting workflow: {session_id}")
            raise comfy.model_management.InterruptProcessingException()

        if result.get("cancelled"):
            print(f"[EU_ImageSelectGate] selection cancelled, interrupting workflow: {session_id}")
            raise comfy.model_management.InterruptProcessingException()

        selected = result.get("selected") or []
        selected = sorted({int(i) for i in selected if 0 <= int(i) < batch_size})
        if len(selected) == 0:
            raise ValueError("No images selected")

        selected_images = images[selected]
        info = f"selected {len(selected)} of {batch_size}: {selected}"
        print(f"[EU_ImageSelectGate] {info}")
        return (selected_images, info)

    @classmethod
    def IS_CHANGED(cls, images, timeout_sec, 取消等待时间):
        return float("NaN")
