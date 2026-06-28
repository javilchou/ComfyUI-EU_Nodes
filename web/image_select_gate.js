import { api } from "../../../scripts/api.js";

let activeModal = null;

api.addEventListener("eu_image_select_gate_show", (event) => {
    showImageSelectGate(event.detail || {});
});

function ensureStyles() {
    if (document.getElementById("eu-image-select-gate-styles")) return;
    const style = document.createElement("style");
    style.id = "eu-image-select-gate-styles";
    style.textContent = `
        .eu-gate-overlay{position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.88);display:flex;align-items:center;justify-content:center}
        .eu-gate-panel{width:min(1800px,96vw);height:min(1000px,94vh);background:#252525;border:1px solid #444;border-radius:8px;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 16px 48px rgba(0,0,0,.55)}
        .eu-gate-header,.eu-gate-footer{padding:14px 18px;display:flex;align-items:center;justify-content:space-between;gap:12px;border-color:#3d3d3d}
        .eu-gate-header{border-bottom:1px solid #3d3d3d}.eu-gate-footer{border-top:1px solid #3d3d3d}
        .eu-gate-title{color:#fff;font-size:18px;font-weight:600}.eu-gate-subtitle{color:#aaa;font-size:12px;margin-top:4px}
        .eu-gate-stats{color:#79d7c5;font-size:14px;font-weight:600;white-space:nowrap}
        .eu-gate-grid{--eu-preview-size:180px;flex:1;overflow:auto;padding:16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--eu-preview-size),1fr));gap:12px;align-content:start}
        .eu-gate-card{position:relative;height:var(--eu-preview-size);border:3px solid transparent;border-radius:6px;overflow:hidden;background:#111;cursor:pointer;transition:border-color 120ms ease,transform 120ms ease}
        .eu-gate-card:hover{border-color:rgba(121,215,197,.5);transform:translateY(-1px)}.eu-gate-card.selected{border-color:#79d7c5}
        .eu-gate-card img{width:100%;height:100%;object-fit:contain;display:block}
        .eu-gate-badge,.eu-gate-dim{position:absolute;background:rgba(0,0,0,.72);color:#fff;border-radius:4px;padding:3px 7px;font-size:11px}
        .eu-gate-badge{top:6px;left:6px}.eu-gate-dim{right:6px;bottom:6px;color:#ccc}
        .eu-gate-check{position:absolute;inset:0;display:none;align-items:center;justify-content:center;background:rgba(121,215,197,.22);color:#79d7c5;font-size:52px;font-weight:700}
        .eu-gate-card.selected .eu-gate-check{display:flex}.eu-gate-actions{display:flex;gap:10px;flex-wrap:wrap}
        .eu-gate-zoom{display:flex;align-items:center;gap:8px;margin-right:2px;color:#bbb;font-size:12px;white-space:nowrap}
        .eu-gate-zoom-btn{width:30px;height:30px;padding:0;border:1px solid #666;border-radius:5px;background:transparent;color:#ddd;cursor:pointer;font-size:18px;line-height:1}
        .eu-gate-zoom-btn:hover{background:#333}.eu-gate-zoom input{width:150px;accent-color:#79d7c5;cursor:pointer}
        .eu-gate-btn{padding:8px 14px;border:1px solid #666;border-radius:5px;background:transparent;color:#ddd;cursor:pointer;font-size:13px}
        .eu-gate-btn:hover{background:#333}.eu-gate-btn.primary{background:#2f8f7f;border-color:#2f8f7f;color:#fff;font-weight:600}.eu-gate-btn.danger{border-color:#ad4d4d;color:#ff9a9a}
    `;
    document.head.appendChild(style);
}

async function submitSelection(sessionId, selected, cancelled = false, timedOut = false) {
    const resp = await api.fetchApi("/eu_image_select_gate/continue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, selected, cancelled, timed_out: timedOut }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    return await resp.json();
}

function showImageSelectGate({ session_id, images = [], batch_size = 0, timeout_sec = 600, wait_forever = false }) {
    ensureStyles();
    if (activeModal) activeModal.remove();

    const selected = new Set();
    let remaining = Number(timeout_sec) || 600;
    let timer = null;

    const overlay = document.createElement("div");
    overlay.className = "eu-gate-overlay";
    const panel = document.createElement("div");
    panel.className = "eu-gate-panel";

    const header = document.createElement("div");
    header.className = "eu-gate-header";
    const titleWrap = document.createElement("div");
    titleWrap.innerHTML = `<div class="eu-gate-title">选择要继续处理的图片</div><div class="eu-gate-subtitle">点击图片选择/取消选择，点击继续后后面的工作流才会开始。</div>`;
    const stats = document.createElement("div");
    stats.className = "eu-gate-stats";
    const updateStats = () => {
        const waitText = wait_forever ? "不限时等待" : `剩余 ${remaining}s`;
        stats.textContent = `已选 ${selected.size} / ${batch_size}，${waitText}`;
    };
    updateStats();
    header.append(titleWrap, stats);

    const grid = document.createElement("div");
    grid.className = "eu-gate-grid";
    const setCardSelected = (card, index, on) => {
        if (on) selected.add(index);
        else selected.delete(index);
        card.classList.toggle("selected", selected.has(index));
        updateStats();
    };

    images.forEach((item, i) => {
        const index = Number(item.index ?? i);
        const card = document.createElement("div");
        card.className = "eu-gate-card";
        card.dataset.index = String(index);
        card.innerHTML = `<img src="${item.data}"><div class="eu-gate-badge">#${index + 1}</div><div class="eu-gate-dim">${item.width}x${item.height}</div><div class="eu-gate-check">✓</div>`;
        card.onclick = () => setCardSelected(card, index, !selected.has(index));
        grid.appendChild(card);
    });

    const footer = document.createElement("div");
    footer.className = "eu-gate-footer";
    const quick = document.createElement("div");
    quick.className = "eu-gate-actions";
    const main = document.createElement("div");
    main.className = "eu-gate-actions";

    const btn = (text, cls, onClick) => {
        const b = document.createElement("button");
        b.className = `eu-gate-btn ${cls || ""}`;
        b.textContent = text;
        b.onclick = onClick;
        return b;
    };
    const eachCard = (fn) => grid.querySelectorAll(".eu-gate-card").forEach((card) => fn(card, Number(card.dataset.index)));
    const zoomWrap = document.createElement("div");
    zoomWrap.className = "eu-gate-zoom";
    const zoomOut = document.createElement("button");
    zoomOut.className = "eu-gate-zoom-btn";
    zoomOut.type = "button";
    zoomOut.title = "缩小预览";
    zoomOut.textContent = "-";
    const zoomSlider = document.createElement("input");
    zoomSlider.type = "range";
    zoomSlider.min = "120";
    zoomSlider.max = "420";
    zoomSlider.step = "20";
    zoomSlider.value = "180";
    zoomSlider.title = "预览大小";
    const zoomIn = document.createElement("button");
    zoomIn.className = "eu-gate-zoom-btn";
    zoomIn.type = "button";
    zoomIn.title = "放大预览";
    zoomIn.textContent = "+";

    const setPreviewSize = (value) => {
        const min = Number(zoomSlider.min);
        const max = Number(zoomSlider.max);
        const size = Math.min(max, Math.max(min, Number(value) || Number(zoomSlider.value)));
        zoomSlider.value = String(size);
        grid.style.setProperty("--eu-preview-size", `${size}px`);
    };
    zoomSlider.oninput = () => setPreviewSize(zoomSlider.value);
    zoomOut.onclick = () => setPreviewSize(Number(zoomSlider.value) - Number(zoomSlider.step));
    zoomIn.onclick = () => setPreviewSize(Number(zoomSlider.value) + Number(zoomSlider.step));
    setPreviewSize(zoomSlider.value);
    zoomWrap.append(zoomOut, zoomSlider, zoomIn);

    quick.append(
        btn("全选", "", () => eachCard((card, index) => setCardSelected(card, index, true))),
        btn("全不选", "", () => eachCard((card, index) => setCardSelected(card, index, false))),
        btn("反选", "", () => eachCard((card, index) => setCardSelected(card, index, !selected.has(index))))
    );

    const close = () => {
        if (timer) clearInterval(timer);
        overlay.remove();
        activeModal = null;
    };
    main.append(
        zoomWrap,
        btn("取消筛选", "danger", async () => {
            if (!confirm("确定要取消筛选并中止当前工作流吗？")) return;
            try {
                await submitSelection(session_id, [], true);
                alert("已取消操作，工作流已中止。");
            } catch (e) { console.error(e); }
            close();
        }),
        btn("继续所选", "primary", async () => {
            const indices = Array.from(selected).sort((a, b) => a - b);
            if (indices.length === 0) return alert("请至少选择一张图片。");
            try { await submitSelection(session_id, indices, false); } catch (e) {
                console.error(e);
                return alert("提交选择失败，请看浏览器控制台。");
            }
            close();
        })
    );

    footer.append(quick, main);
    panel.append(header, grid, footer);
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    activeModal = overlay;

    if (!wait_forever) {
        timer = setInterval(async () => {
            remaining -= 1;
            updateStats();
            if (remaining <= 0) {
                try {
                    await submitSelection(session_id, [], true, true);
                    close();
                    alert("等待选择超时，工作流已中止。");
                } catch (e) {
                    console.error(e);
                    close();
                }
            }
        }, 1000);
    }
}
