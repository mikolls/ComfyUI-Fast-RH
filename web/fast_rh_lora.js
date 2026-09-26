import { app } from "/scripts/app.js";
import { chooseLora } from "./model_picker.js";

const newRow = index => ({
  slot: `lora_${index + 1}`, model: "", model_cover: "", nodeId: 0,
  enabled: false, strength_model: 1, strength_clip: 1,
});
const initialRows = () => [newRow(0)];
const MAX_ROWS = 16;

function hideWidget(widget) {
  widget.hidden = true;
  widget.type = "converted-widget";
  widget.computeSize = () => [0, -4];
  widget.serializeValue = () => widget.value;
}

function installStyle() {
  if (document.getElementById("fast-rh-stack-style")) return;
  const style = document.createElement("style");
  style.id = "fast-rh-stack-style";
  style.textContent = `
.fast-rh-stack{box-sizing:border-box;width:100%;height:100%;padding:8px;background:#18181b;color:#eee;font:12px Arial,sans-serif;display:flex;flex-direction:column;gap:8px;overflow:hidden}
.fast-rh-stack *{box-sizing:border-box}.fast-rh-stack button{font:inherit;color:inherit;cursor:pointer}
.fast-rh-stack-toolbar{height:30px;flex:none;display:flex;align-items:center;justify-content:flex-end;border-bottom:1px solid #303034;padding-bottom:5px}
.fast-rh-stack-toolbar button{border:0;background:transparent;font-size:19px;line-height:22px;width:28px}
.fast-rh-stack-list{flex:1;overflow:auto;min-height:0;padding:4px 5px}
.fast-rh-stack-row{margin:0 0 12px;border:1px solid #38383e;border-radius:5px;overflow:hidden;background:#29292b}
.fast-rh-stack-head{height:44px;background:#18181b;display:flex;align-items:center;gap:8px;padding:4px 9px}
.fast-rh-stack-thumb{width:36px;height:36px;flex:none;border:1px solid #414149;border-radius:3px;object-fit:cover;background:#333}
.fast-rh-stack-name{flex:1;min-width:0;border:0;background:transparent;text-align:left;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:bold}
.fast-rh-stack-icon{border:0;background:transparent;width:24px;height:26px;font-size:16px}
.fast-rh-stack-icon:disabled{opacity:.35;cursor:default}
.fast-rh-stack-fields{min-height:37px;display:flex;align-items:center;flex-wrap:wrap;gap:5px 10px;padding:5px 10px}
.fast-rh-stack-fields label{display:flex;align-items:center;gap:5px;white-space:nowrap}
.fast-rh-stack-fields input[type=number]{width:59px;height:24px;padding:2px 5px;background:#1d1d20;color:#eee;border:1px solid #38383e;border-radius:3px;font:inherit}
.fast-rh-stack-fields .fast-rh-node-id{width:64px}
.fast-rh-stack-toggle{margin-left:auto;appearance:none;width:38px;height:20px;background:#555;border-radius:12px;position:relative;cursor:pointer}
.fast-rh-stack-toggle:checked{background:#22c55e}
.fast-rh-stack-toggle:after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;background:white;border-radius:50%;transition:left .12s}
.fast-rh-stack-toggle:checked:after{left:20px}
.fast-rh-preview{border:0;padding:0;max-width:min(90vw,1100px);max-height:90vh;background:#151518;color:#fff}
.fast-rh-preview::backdrop{background:#000d}.fast-rh-preview img{display:block;max-width:90vw;max-height:82vh;object-fit:contain}
.fast-rh-preview button{position:absolute;right:8px;top:8px;background:#111c;color:#fff;border:1px solid #aaa;cursor:pointer}
`;
  document.head.append(style);
}

function previewImage(url, name) {
  if (!url) return;
  const dialog = document.createElement("dialog");
  dialog.className = "fast-rh-preview";
  const img = document.createElement("img");
  img.src = url;
  img.alt = name;
  const close = document.createElement("button");
  close.type = "button";
  close.textContent = "×";
  close.setAttribute("aria-label", "Close image preview");
  close.onclick = () => dialog.close();
  dialog.append(img, close);
  dialog.addEventListener("close", () => dialog.remove());
  dialog.onclick = event => { if (event.target === dialog) dialog.close(); };
  document.body.append(dialog);
  dialog.showModal();
}

function numberField(label, value, className, onChange, step = "0.01") {
  const field = document.createElement("label");
  field.textContent = label;
  const input = document.createElement("input");
  input.type = "number";
  input.step = step;
  input.value = String(value);
  if (className) input.className = className;
  input.onchange = () => onChange(Number(input.value));
  field.append(input);
  return field;
}

app.registerExtension({
  name: "fast-rh.lora",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "FastRHLoRA") return;
    const originalCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalCreated?.apply(this, arguments);
      installStyle();
      this._fastRhConfigWidget = this.widgets?.find(w => w.name === "configs_json");
      this._fastRhState = initialRows();
      if (this._fastRhConfigWidget) {
        try {
          const rows = JSON.parse(this._fastRhConfigWidget.value);
          if (Array.isArray(rows) && rows.length) this._fastRhState = rows.slice(0, MAX_ROWS);
        } catch (_) {}
        hideWidget(this._fastRhConfigWidget);
      }
      const root = document.createElement("div");
      root.className = "fast-rh-stack";
      const toolbar = document.createElement("div");
      toolbar.className = "fast-rh-stack-toolbar";
      const add = document.createElement("button");
      add.type = "button";
      add.title = "Add LoRA";
      add.textContent = "+";
      toolbar.append(add);
      const list = document.createElement("div");
      list.className = "fast-rh-stack-list";
      root.append(toolbar, list);
      this._fastRhSync = () => {
        if (this._fastRhConfigWidget) this._fastRhConfigWidget.value = JSON.stringify(this._fastRhState);
        app.graph.setDirtyCanvas(true, true);
      };
      this._fastRhRender = () => {
        list.replaceChildren();
        this._fastRhState.forEach((row, index) => {
          const card = document.createElement("div");
          card.className = "fast-rh-stack-row";
          const head = document.createElement("div");
          head.className = "fast-rh-stack-head";
          const img = document.createElement("img");
          img.className = "fast-rh-stack-thumb";
          img.alt = row.model ? `${row.model} cover` : "No model selected";
          if (row.model_cover) img.src = row.model_cover;
          img.onerror = () => { img.removeAttribute("src"); img.alt = "Cover unavailable"; };
          const name = document.createElement("button");
          name.className = "fast-rh-stack-name";
          name.type = "button";
          name.textContent = row.model || "Click to choose a LoRA model…";
          name.title = row.model || "Choose model";
          name.onclick = async () => {
            const selected = await chooseLora();
            if (selected) {
              row.model = typeof selected === "string" ? selected : selected.model;
              row.model_cover = typeof selected === "string" ? "" : selected.cover || "";
              row.enabled = true;
              this._fastRhSync();
              this._fastRhRender();
            }
          };
          const preview = document.createElement("button");
          preview.className = "fast-rh-stack-icon";
          preview.type = "button";
          preview.textContent = "▣";
          preview.title = "Enlarge cover preview";
          preview.disabled = !row.model_cover;
          preview.onclick = () => previewImage(row.model_cover, row.model);
          img.onclick = () => previewImage(row.model_cover, row.model);
          img.style.cursor = row.model_cover ? "zoom-in" : "default";
          const remove = document.createElement("button");
          remove.className = "fast-rh-stack-icon";
          remove.type = "button";
          remove.textContent = "×";
          remove.title = "Remove this row";
          remove.onclick = () => {
            this._fastRhState.splice(index, 1);
            if (!this._fastRhState.length) this._fastRhState.push(newRow(0));
            this._fastRhSync();
            this._fastRhRender();
          };
          head.append(img, name, preview, remove);
          const fields = document.createElement("div");
          fields.className = "fast-rh-stack-fields";
          fields.append(
            numberField("Model strength", row.strength_model ?? 1, "", v => { row.strength_model = v; this._fastRhSync(); }),
            numberField("CLIP strength", row.strength_clip ?? 1, "", v => { row.strength_clip = v; this._fastRhSync(); }),
            numberField("Remote node ID", row.nodeId ?? 0, "fast-rh-node-id", v => { row.nodeId = Math.trunc(v); this._fastRhSync(); }, "1"),
          );
          const enabled = document.createElement("input");
          enabled.type = "checkbox";
          enabled.className = "fast-rh-stack-toggle";
          enabled.title = "Enabled";
          enabled.checked = !!row.enabled;
          enabled.onchange = () => { row.enabled = enabled.checked; this._fastRhSync(); };
          fields.append(enabled);
          card.append(head, fields);
          list.append(card);
        });
        add.disabled = this._fastRhState.length >= MAX_ROWS;
        const height = Math.max(180, 47 + this._fastRhState.length * 94);
        this.setSize([Math.max(this.size?.[0] || 0, 680), Math.max(this.size?.[1] || 0, height + 100)]);
        app.graph.setDirtyCanvas(true, true);
      };
      add.onclick = () => {
        if (this._fastRhState.length >= MAX_ROWS) return;
        this._fastRhState.push(newRow(this._fastRhState.length));
        this._fastRhSync();
        this._fastRhRender();
      };
      this._fastRhDomWidget = this.addDOMWidget("LoRA", "fast-rh-stack", root, { serialize: false, hideOnZoom: false, getMinHeight: () => Math.max(180, 47 + this._fastRhState.length * 94), getHeight: () => "100%" });
      this._fastRhSync();
      this._fastRhRender();
    };
    const originalConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      originalConfigure?.apply(this, arguments);
      setTimeout(() => {
        if (!this._fastRhConfigWidget) return;
        try {
          const rows = JSON.parse(this._fastRhConfigWidget.value);
          if (Array.isArray(rows) && rows.length) this._fastRhState = rows.slice(0, MAX_ROWS);
        } catch (_) {}
        this._fastRhRender?.();
      }, 0);
    };
  },
});
