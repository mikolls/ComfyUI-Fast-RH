const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

let extension;
const context = {
  app: {
    registerExtension: value => extension = value,
    graph: { setDirtyCanvas() {} },
  },
  setTimeout: fn => fn(),
};
vm.runInNewContext(
  fs.readFileSync("web/fast_rh_empty_latent.js", "utf8").replace(/^import .*;\r?\n/gm, ""),
  context,
);

class Node {
  constructor() {
    this.widgets = [
      { name: "nodeId", type: "number", value: 8 },
      { name: "width", type: "number", value: 1024 },
      { name: "height", type: "number", value: 1920 },
      { name: "batch_size", type: "number", value: 1 },
    ];
    this.properties = {};
    this.size = [300, 220];
  }
  addWidget(type, name, value, callback, options) {
    const widget = { type, name, value, callback, options };
    this.widgets.push(widget);
    return widget;
  }
  computeSize() { return [300, 200]; }
  setSize(size) { this.size = size; }
}

(async () => {
  await extension.beforeRegisterNodeDef(Node, { name: "FastRHEmptyLatentImage" });
  const node = new Node();
  node.onNodeCreated();
  const get = name => node.widgets.find(w => w.name === name);
  const mode = get("resolution_mode");
  const preset = get("resolution_preset");
  const width = get("width");
  const height = get("height");
  const swap = get("Swap Width / Height ↔");

  assert.equal(preset.hidden, true);
  mode.callback("Preset");
  assert.equal(width.hidden, true);
  assert.equal(height.hidden, true);
  assert.equal(preset.hidden, false);
  preset.callback("1280 × 720");
  assert.deepEqual([width.value, height.value], [1280, 720]);
  swap.callback();
  assert.equal(preset.value, "720 × 1280");
  assert.deepEqual([width.value, height.value], [720, 1280]);

  mode.callback("Custom");
  assert.deepEqual([width.value, height.value], [1024, 1920]);
  width.value = 1536;
  height.value = 1024;
  mode.callback("Preset");
  mode.callback("Custom");
  assert.deepEqual([width.value, height.value], [1536, 1024]);
  swap.callback();
  assert.deepEqual([width.value, height.value], [1024, 1536]);

  mode.callback("Preset");
  const restored = new Node();
  restored.onNodeCreated();
  restored.properties = JSON.parse(JSON.stringify(node.properties));
  restored.widgets.find(w => w.name === "resolution_mode").value = "\u9884\u8bbe";
  restored.widgets.find(w => w.name === "resolution_preset").value = "720 × 1280";
  restored.onConfigure();
  assert.equal(restored.widgets.find(w => w.name === "resolution_mode").value, "Preset");
  assert.deepEqual([
    restored.widgets.find(w => w.name === "width").value,
    restored.widgets.find(w => w.name === "height").value,
  ], [720, 1280]);
  restored.widgets.find(w => w.name === "resolution_mode").callback("Custom");
  assert.deepEqual([
    restored.widgets.find(w => w.name === "width").value,
    restored.widgets.find(w => w.name === "height").value,
  ], [1024, 1536]);
  console.log("Empty Latent preset, custom, swap, and restore: PASS");
})().catch(error => { console.error(error); process.exitCode = 1; });
