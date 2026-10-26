const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../learn/实践.js'), 'utf8');
const inputs = ['programmer', 'student', 'business', '__proto__'].map(value => ({value, checked: false, events: {}, addEventListener(kind, fn) {this.events[kind]=fn;}}));
const elements = Object.fromEntries(['track-title', 'track-task', 'track-outputs', 'track-article'].map(id => [id, {textContent: 'initial', replaceChildren(...children) {this.children=children;}}]));
const document = {querySelectorAll() {return inputs;}, getElementById(id) {return elements[id];}, createElement() {return {textContent: ''};}};
vm.runInNewContext(source, {document});
for (const [index, phrase] of [[0, '小工具'], [1, '小练习'], [2, '拆清楚']]) {
  inputs.forEach((item, i) => {item.checked=i===index;}); inputs[index].events.change();
  assert.ok(elements['track-title'].textContent.includes(phrase));
  assert.equal(elements['track-outputs'].children.length, 3);
  assert.ok(elements['track-task'].textContent.length > 50);
  assert.ok(elements['track-article'].href.startsWith('/') || elements['track-article'].href.startsWith('https://willeai.cn/'));
}
const prior = elements['track-title'].textContent;
inputs[3].checked=true; inputs[3].events.change(); assert.equal(elements['track-title'].textContent, prior);
inputs[0].checked=false; inputs[0].events.change(); assert.equal(elements['track-title'].textContent, prior);
console.log('Learning tracks passed: programmer, student, business, invalid and unchecked controls.');
