const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

class Element {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.style = {};
    this.className = "";
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute() {}
  removeAttribute() {}
  addEventListener() {}
  scrollIntoView() {}
}
const document = {
  head: new Element("head"),
  body: new Element("body"),
  createElement: tag => new Element(tag),
  getElementById: () => null,
};
let extension;
const context = {
  document,
  app: { registerExtension: value => extension = value, graph: { setDirtyCanvas() {} } },
  chooseLora: async () => ({ model: "sub/test.safetensors", cover: "https://example.com/cover.png" }),
  setTimeout: fn => fn(),
};
vm.runInNewContext(fs.readFileSync("web/fast_rh_lora.js", "utf8").replace(/^import .*;\r?\n/gm, ""), context);

class Node {
  constructor() {
    this.widgets = [{ name: "configs_json", value: '[{"slot":"a","model":"old.safetensors","enabled":true}]' }];
    this.size = [300, 200];
  }
  addDOMWidget(name, type, element, options) {
    const widget = { name, type, element, options };
    this.widgets.push(widget);
    return widget;
  }
  setSize(size) { this.size = size; }
}
function find(root, className) {
  if (root.className === className) return root;
  for (const child of root.children || []) {
    const match = find(child, className);
    if (match) return match;
  }
  return null;
}
(async () => {
  await extension.beforeRegisterNodeDef(Node, { name: "FastRHLoRA" });
  const node = new Node();
  node.onNodeCreated();
  assert.ok(node.widgets.some(w => w.type === "fast-rh-stack"));
  assert.equal(node._fastRhConfigWidget.hidden, true);
  assert.equal(node._fastRhDomWidget.options.getHeight(), "100%");
  assert.equal(find(node._fastRhDomWidget.element, "fast-rh-stack-open"), null);
  assert.ok(find(node._fastRhDomWidget.element, "fast-rh-stack-thumb"));
  await find(node._fastRhDomWidget.element, "fast-rh-stack-name").onclick();
  const saved = node._fastRhConfigWidget.value;
  assert.equal(JSON.parse(saved)[0].model, "sub/test.safetensors");
  assert.equal(JSON.parse(saved)[0].model_cover, "https://example.com/cover.png");
  const restored = new Node();
  restored.onNodeCreated();
  restored._fastRhConfigWidget.value = saved;
  restored.onConfigure();
  assert.equal(restored._fastRhState[0].model, "sub/test.safetensors");
  assert.equal(find(restored._fastRhDomWidget.element, "fast-rh-stack-icon").disabled, false);
  console.log("LoRA card selection, cover, and workflow restoration: PASS");
})().catch(error => { console.error(error); process.exitCode = 1; });
