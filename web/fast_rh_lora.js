import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const DEFAULT_ROWS = () => Array.from({ length: 4 }, (_, i) => ({
  slot: `lora_${i + 1}`,
  model: "",
  enabled: false,
  strength_model: 1.0,
  strength_clip: 1.0,
}));

let picker;
let pickerResolve;
let allLoras = [];

function ensurePicker() {
  if (picker) return picker;
  const style = document.createElement("style");
  style.textContent = `
    .fast-rh-backdrop{position:fixed;inset:0;background:#0009;z-index:10000;display:flex;align-items:center;justify-content:center}
    .fast-rh-picker{width:min(720px,85vw);height:min(680px,80vh);background:#242424;color:#eee;border:1px solid #555;border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:10px;box-shadow:0 15px 50px #000}
    .fast-rh-toolbar{display:flex;gap:8px}.fast-rh-toolbar input{flex:1;padding:8px;background:#151515;color:#fff;border:1px solid #555;border-radius:5px}
    .fast-rh-toolbar button,.fast-rh-close{padding:7px 12px}.fast-rh-status{font-size:12px;color:#aaa;min-height:18px}
    .fast-rh-list{overflow:auto;flex:1;border:1px solid #444;border-radius:5px}.fast-rh-item{padding:8px 10px;border-bottom:1px solid #383838;cursor:pointer;word-break:break-all}.fast-rh-item:hover{background:#3d5268}
  `;
  document.head.appendChild(style);
  picker = document.createElement("div");
  picker.className = "fast-rh-backdrop";
  picker.style.display = "none";
  picker.innerHTML = `<div class="fast-rh-picker"><div class="fast-rh-toolbar"><input placeholder="搜索 LoRA 文件名…"><button data-refresh>刷新 RunningHub</button><button data-close>关闭</button></div><div class="fast-rh-status"></div><div class="fast-rh-list"></div></div>`;
  document.body.appendChild(picker);
  picker.querySelector("[data-close]").onclick = () => closePicker(null);
  picker.addEventListener("click", (event) => { if (event.target === picker) closePicker(null); });
  picker.querySelector("input").addEventListener("input", renderList);
  picker.querySelector("[data-refresh]").onclick = () => loadLoras(true);
  return picker;
}

function closePicker(value) {
  picker.style.display = "none";
  const resolve = pickerResolve;
  pickerResolve = null;
  if (resolve) resolve(value);
}

function renderList() {
  const query = picker.querySelector("input").value.trim().toLocaleLowerCase();
  const list = picker.querySelector(".fast-rh-list");
  list.replaceChildren();
  for (const name of allLoras.filter(x => x.toLocaleLowerCase().includes(query))) {
    const item = document.createElement("div");
    item.className = "fast-rh-item";
    item.textContent = name;
    item.onclick = () => closePicker(name);
    list.appendChild(item);
  }
  if (!list.childElementCount) list.textContent = "没有匹配的 LoRA";
}

async function loadLoras(refresh = false) {
  ensurePicker();
  const status = picker.querySelector(".fast-rh-status");
  status.textContent = refresh ? "正在从 RunningHub 刷新完整 object_info…" : "正在读取本地缓存…";
  try {
    const response = await api.fetchApi(refresh ? "/fast-rh/loras/refresh" : "/fast-rh/loras", { method: refresh ? "POST" : "GET" });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
    allLoras = data.loras;
    status.textContent = `${data.loras.length} 个 LoRA · 缓存时间 ${new Date(data.fetched_at).toLocaleString()} · ${data.source === "remote" ? "已从远程更新" : "本地缓存"}`;
    renderList();
  } catch (error) {
    status.textContent = `加载失败：${error.message}`;
    renderList();
  }
}

function chooseLora() {
  ensurePicker();
  picker.style.display = "flex";
  picker.querySelector("input").value = "";
  loadLoras(false);
  picker.querySelector("input").focus();
  return new Promise(resolve => { pickerResolve = resolve; });
}

function hideWidget(widget) {
  widget.type = "converted-widget";
  widget.computeSize = () => [0, -4];
  widget.serializeValue = () => widget.value;
}

app.registerExtension({
  name: "fast-rh.lora",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "FastRHLoRA") return;
    const originalCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalCreated?.apply(this, arguments);
      this._fastRhState = DEFAULT_ROWS();
      this._fastRhConfigWidget = this.widgets?.find(w => w.name === "configs_json");
      if (this._fastRhConfigWidget) {
        hideWidget(this._fastRhConfigWidget);
        try {
          const parsed = JSON.parse(this._fastRhConfigWidget.value);
          if (Array.isArray(parsed) && parsed.length) this._fastRhState = parsed.slice(0, 16);
        } catch (_) {}
      }
      this._fastRhWidgets = [];
      this._fastRhRebuild = () => {
        for (const widget of this._fastRhWidgets) {
          const index = this.widgets.indexOf(widget);
          if (index >= 0) this.widgets.splice(index, 1);
        }
        this._fastRhWidgets = [];
        const add = (type, name, value, callback, options) => {
          const widget = this.addWidget(type, name, value, callback, options);
          this._fastRhWidgets.push(widget);
          return widget;
        };
        this._fastRhState.forEach((row, index) => {
          add("text", `${index + 1}. slot`, row.slot, v => { row.slot = String(v); this._fastRhSync(); });
          add("toggle", `${index + 1}. enabled`, !!row.enabled, v => { row.enabled = !!v; this._fastRhSync(); });
          add("button", `${index + 1}. model: ${row.model || "选择模型…"}`, null, async () => {
            const selected = await chooseLora();
            if (selected) { row.model = selected; this._fastRhSync(); this._fastRhRebuild(); }
          });
          add("number", `${index + 1}. model strength`, Number(row.strength_model ?? 1), v => { row.strength_model = Number(v); this._fastRhSync(); }, { min: -100, max: 100, step: 0.01, precision: 2 });
          add("number", `${index + 1}. clip strength`, Number(row.strength_clip ?? 1), v => { row.strength_clip = Number(v); this._fastRhSync(); }, { min: -100, max: 100, step: 0.01, precision: 2 });
          add("button", `${index + 1}. 删除`, null, () => {
            if (this._fastRhState.length <= 1) return;
            this._fastRhState.splice(index, 1); this._fastRhSync(); this._fastRhRebuild();
          });
        });
        add("button", this._fastRhState.length >= 16 ? "已达到 16 条上限" : "＋ 添加 LoRA", null, () => {
          if (this._fastRhState.length >= 16) return;
          this._fastRhState.push({ slot: `lora_${this._fastRhState.length + 1}`, model: "", enabled: false, strength_model: 1, strength_clip: 1 });
          this._fastRhSync(); this._fastRhRebuild();
        });
        this.setSize(this.computeSize());
        app.graph.setDirtyCanvas(true, true);
      };
      this._fastRhSync = () => {
        if (this._fastRhConfigWidget) this._fastRhConfigWidget.value = JSON.stringify(this._fastRhState);
      };
      this._fastRhSync();
      this._fastRhRebuild();
    };
    const originalConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      originalConfigure?.apply(this, arguments);
      setTimeout(() => {
        if (!this._fastRhConfigWidget) return;
        try {
          const rows = JSON.parse(this._fastRhConfigWidget.value);
          if (Array.isArray(rows) && rows.length) this._fastRhState = rows.slice(0, 16);
        } catch (_) {}
        this._fastRhRebuild?.();
      }, 0);
    };
  },
});
