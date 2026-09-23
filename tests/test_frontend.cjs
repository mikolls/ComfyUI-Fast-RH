const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
let extension;
const context = {app: {registerExtension: value => extension = value, graph: {setDirtyCanvas(){}}}, chooseLora: async () => 'sub/test.safetensors', setTimeout: fn => fn()};
vm.runInNewContext(fs.readFileSync('web/fast_rh_lora.js','utf8').replace(/^import .*;\r?\n/gm,''), context);
class Node {
  constructor(){ this.widgets=[{name:'configs_json',value:'[{"slot":"a","model":"old.safetensors","enabled":true}]'}]; }
  addWidget(type,name,value,callback,options){const widget={type,name,value,callback,options};this.widgets.push(widget);return widget;}
  setSize(){} computeSize(){return [400,400];}
}
(async()=>{
  await extension.beforeRegisterNodeDef(Node,{name:'FastRHLoRA'});
  const node = new Node(); node.onNodeCreated();
  await node.widgets.find(w=>w.type==='button'&&w.name.includes('. model:')).callback();
  const saved=node._fastRhConfigWidget.value;
  assert.equal(JSON.parse(saved)[0].model,'sub/test.safetensors');
  const restored=new Node(); restored.onNodeCreated(); restored._fastRhConfigWidget.value=saved; restored.onConfigure();
  assert.equal(restored._fastRhState[0].model,'sub/test.safetensors');
  assert.ok(restored.widgets.some(w=>w.name.includes('sub/test.safetensors')));
  console.log('Node selection and workflow restoration: PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
