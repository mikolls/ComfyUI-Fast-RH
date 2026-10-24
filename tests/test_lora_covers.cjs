const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

class Element {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.style = {};
    this.dataset = {};
    this.attributes = {};
    this.value = '';
  }
  append(...children) {
    if (this.tagName === 'select' && !this.children.length && children.length) this.value = String(children[0].value);
    this.children.push(...children);
  }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this[name]; delete this.attributes[name]; }
  addEventListener() {}
  // Parse the card template so selectors exercise its actual markup.
  set innerHTML(html) {
    this.children = [];
    const stack = [this];
    for (const token of html.matchAll(/<\/(\w+)>|<(\w+)([^>]*)>/g)) {
      if (token[1]) { stack.pop(); continue; }
      const element = new Element(token[2]);
      for (const attribute of token[3].matchAll(/([\w-]+)(?:="([^"]*)")?/g)) {
        element.attributes[attribute[1]] = attribute[2] || '';
        if (attribute[1] === 'class') element.className = attribute[2];
      }
      stack.at(-1).append(element);
      if (!['input', 'img'].includes(element.tagName)) stack.push(element);
    }
  }
  querySelector(selector) {
    for (const child of this.children) {
      const matches = selector.startsWith('.') ? child.className === selector.slice(1)
        : selector.startsWith('[') ? selector.slice(1, -1) in child.attributes : child.tagName === selector;
      if (matches) return child;
      const match = child.querySelector(selector);
      if (match) return match;
    }
    return null;
  }
}

const status = new Element('div');
const credential = new Element('input');
const document = {
  head: new Element('head'), body: new Element('body'),
  createElement: tag => new Element(tag), getElementById: () => null,
};
let extension, selection, failUpload = false;
const uploads = [];
const context = vm.createContext({
  document, URLSearchParams,
  // Force uploads to happen at the same timestamp to check revision uniqueness.
  Date: { now: () => 12345 },
  FormData: class { constructor() { this.fields = new Map(); } append(key, value) { this.fields.set(key, value); } },
  app: { registerExtension: value => extension = value, graph: { setDirtyCanvas() {} } },
  api: { fetchApi: async (url, options) => {
    if (options.method === 'POST') uploads.push(options.body.fields);
    return { ok: !failUpload, status: failUpload ? 500 : 200,
      json: async () => failUpload ? { ok: false, error: 'Upload failed' } : { ok: true, url: '/fast-rh/covers/test' } };
  } },
  testDialog: { querySelector: selector => selector === '[data-credential]' ? credential : status, close() {} },
  selected: value => { selection = value; },
});
const load = path => fs.readFileSync(path, 'utf8').replace(/^import .*;\r?\n/gm, '').replace(/^export /gm, '');
vm.runInContext(load('web/model_picker.js'), context);
vm.runInContext('dialog = testDialog;', context);
vm.runInContext(load('web/fast_rh_lora.js'), context);

class Node {
  constructor() {
    this.widgets = [{ name: 'configs_json', value: JSON.stringify([
      { model: 'face.safetensors', model_cover: 'https://example.com/old.png', enabled: false, nodeId: 93, strength_model: 0.8 },
      { model: 'face.safetensors', model_cover: '', enabled: true },
      { model: 'other.safetensors', model_cover: 'https://example.com/other.png' },
    ]) }];
    this.size = [800, 600];
  }
  addDOMWidget(name, type, element) { return { name, type, element }; }
  setSize(size) { this.size = size; }
  onRemoved() { this.removed = true; }
}

(async () => {
  await extension.beforeRegisterNodeDef(Node, { name: 'FastRHLoRA' });
  const nodes = [new Node(), new Node()];
  nodes.forEach(node => node.onNodeCreated());
  const size = Array.from(nodes[0].size);
  const item = { title: 'Face', image: 'https://example.com/item.png', versions: [
    { model: 'face.safetensors', version: 'V1', image: 'https://example.com/remote.png' },
  ] };
  context.testItem = item;
  const card = vm.runInContext('renderCard(testItem)', context);
  const input = card.querySelector('[data-cover-file]');
  const button = card.querySelector('[data-cover]');
  const reset = card.querySelector('[data-cover-reset]');
  const image = card.querySelector('img');
  const file = { type: 'image/png', size: 100 };
  async function upload() { input.files = [file]; input.value = 'cover.png'; await input.onchange(); }
  function assertCover(url) {
    for (const node of nodes) {
      const saved = JSON.parse(node._fastRhConfigWidget.value);
      assert.equal(saved[0].model_cover, url);
      assert.equal(saved[1].model_cover, url);
      assert.equal(saved[2].model_cover, 'https://example.com/other.png');
      assert.equal(saved[0].enabled, false);
      assert.equal(saved[0].nodeId, 93);
      assert.equal(saved[0].strength_model, 0.8);
      assert.equal(node._fastRhDomWidget.element.querySelector('.fast-rh-stack-thumb').src || '', url);
    }
    assert.deepEqual(Array.from(nodes[0].size), size);
  }

  await upload();
  const first = image.src;
  assert.match(first, /^\/fast-rh\/covers\/test\?v=/);
  assertCover(first); // Updates without selecting a model or closing the picker.
  await upload();
  assert.notEqual(image.src, first);
  assertCover(image.src);
  assert.equal(uploads.length, 2);
  assert.equal(uploads[1].get('model'), 'face.safetensors');
  assert.equal(input.value, '');
  assert.equal(button.disabled, false);
  vm.runInContext('resolveSelection = selected;', context);
  card.querySelector('.fast-rh-pick').onclick();
  assert.equal(selection.cover, image.src); // Selection preserves the cache revision.

  failUpload = true;
  await upload();
  assertCover(image.src);
  assert.equal(button.disabled, false);
  assert.equal(input.value, '');
  failUpload = false;
  await reset.onclick({ currentTarget: reset });
  assertCover('https://example.com/remote.png');
  assert.equal(reset.disabled, true);
  await upload();
  assertCover(image.src);

  // Reset also clears covers when the remote model has no image.
  item.image = item.versions[0].image = '';
  await reset.onclick({ currentTarget: reset });
  assertCover('');
  assert.equal(nodes[0]._fastRhDomWidget.element.querySelector('.fast-rh-stack-icon').disabled, true);

  const removed = nodes.pop();
  removed.onRemoved();
  assert.equal(removed.removed, true);
  const removedState = removed._fastRhConfigWidget.value;
  await upload();
  assertCover(image.src);
  assert.equal(removed._fastRhConfigWidget.value, removedState);

  context.testItem = { title: 'Existing', versions: [{ model: 'face.safetensors', local_cover: '/fast-rh/covers/test?v=old' }] };
  const reopened = vm.runInContext('renderCard(testItem)', context);
  assert.notEqual(reopened.querySelector('img').src, '/fast-rh/covers/test?v=old');
  assert.equal((reopened.querySelector('img').src.match(/\?/g) || []).length, 1);
  console.log('LoRA repeated cover replacement, live node updates, reset, selection, and cleanup: PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
