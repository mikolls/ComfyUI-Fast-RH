import { app } from "/scripts/app.js";

const PRESETS = [
  "512 × 512",
  "768 × 768",
  "1024 × 1024",
  "768 × 1024", "1024 × 768",
  "832 × 1216", "1216 × 832",
  "720 × 1280", "1280 × 720",
  "1024 × 1536", "1536 × 1024",
  "1024 × 1792", "1792 × 1024",
  "1024 × 1920", "1920 × 1024",
];

function dimensions(preset) {
  const match = /^(\d+) × (\d+)$/.exec(preset);
  return match ? [Number(match[1]), Number(match[2])] : null;
}

function setVisible(widget, visible) {
  if (!widget) return;
  if (!widget._fastRhOriginalType) {
    widget._fastRhOriginalType = widget.type;
    widget._fastRhOriginalComputeSize = widget.computeSize;
  }
  widget.hidden = !visible;
  widget.type = visible ? widget._fastRhOriginalType : "hidden";
  widget.computeSize = visible ? widget._fastRhOriginalComputeSize : () => [0, -4];
}

app.registerExtension({
  name: "fast-rh.empty-latent",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "FastRHEmptyLatentImage") return;

    const originalCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalCreated?.apply(this, arguments);
      const find = name => this.widgets?.find(widget => widget.name === name);
      const width = find("width");
      const height = find("height");
      if (!width || !height) return;

      this.properties ||= {};
      const state = () => {
        this.properties.fastRhEmptyLatent ||= {
          customWidth: Number(width.value),
          customHeight: Number(height.value),
        };
        return this.properties.fastRhEmptyLatent;
      };

      const mode = this.addWidget(
        "combo", "resolution_mode", "自定义", value => {
          mode.value = value;
          if (value === "预设") {
            state().customWidth = Number(width.value);
            state().customHeight = Number(height.value);
            applyPreset();
          } else {
            width.value = state().customWidth;
            height.value = state().customHeight;
          }
          updateVisibility();
        },
        { values: ["预设", "自定义"] },
      );
      const preset = this.addWidget(
        "combo", "resolution_preset", "1024 × 1920", value => {
          preset.value = value;
          if (mode.value === "预设") applyPreset();
          app.graph.setDirtyCanvas(true, true);
        },
        { values: PRESETS },
      );

      const applyPreset = () => {
        const pair = dimensions(preset.value);
        if (!pair) return;
        [width.value, height.value] = pair;
      };
      const updateVisibility = () => {
        const isPreset = mode.value === "预设";
        setVisible(preset, isPreset);
        setVisible(width, !isPreset);
        setVisible(height, !isPreset);
        const computed = this.computeSize();
        this.setSize([Math.max(this.size?.[0] || 0, 340), computed[1]]);
        app.graph.setDirtyCanvas(true, true);
      };

      const swap = this.addWidget("button", "交换宽高 ↔", null, () => {
        if (mode.value === "预设") {
          const pair = dimensions(preset.value);
          if (!pair) return;
          const reversed = `${pair[1]} × ${pair[0]}`;
          if (!PRESETS.includes(reversed)) return;
          preset.value = reversed;
          applyPreset();
        } else {
          [width.value, height.value] = [height.value, width.value];
          state().customWidth = Number(width.value);
          state().customHeight = Number(height.value);
        }
        app.graph.setDirtyCanvas(true, true);
      });
      swap.serializeValue = () => undefined;

      state();
      updateVisibility();
      this._fastRhEmptyLatentRefresh = () => {
        state();
        if (mode.value === "预设") applyPreset();
        updateVisibility();
      };
    };

    const originalConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      originalConfigure?.apply(this, arguments);
      setTimeout(() => this._fastRhEmptyLatentRefresh?.(), 0);
    };
  },
});
