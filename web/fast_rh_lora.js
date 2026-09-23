import { app } from "/scripts/app.js";
import { chooseLora } from "./model_picker.js";

const DEFAULT_ROWS = () => Array.from({ length: 4 }, (_, i) => ({
  slot: `lora_${i + 1}`,
  model: "",
  enabled: false,
  strength_model: 1.0,
  strength_clip: 1.0,
}));

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
