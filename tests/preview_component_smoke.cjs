// Exercise the component message protocol without a browser or external packages.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../highlightminer/preview_component/index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const events = {}, messages = [], mediaEvents = {};
const player = {readyState: 1, duration: 30.04, currentTime: 5.25, error: null,
  pauseCount: 0, loadCount: 0, pause() {this.pauseCount++;}, load() {
    this.loadCount++;
    this.loadedSrc = this.src;
    // Model the HTMLMediaElement reset; actual decoding requires a browser.
    this.currentTime = 0;
    this.readyState = 0;
    this.duration = NaN;
  },
  addEventListener(type, fn) {mediaEvents[type] = fn;}};
const buttons = Object.fromEntries(['in', 'out'].map(id => [id, {id, disabled: true,
  addEventListener(type, fn) {this[type] = fn;}}]));
const parent = {postMessage(value) {messages.push(value);}};
vm.runInNewContext(script, {parent, console, Math, Number,
  document: {body: {scrollHeight: 400, style: {}}, getElementById(id) {
    return id === 'player' ? player : id === 'status' ? {} : buttons[id];
  }}, window: {addEventListener(type, fn) {events[type] = fn;}},
  ResizeObserver: class {observe() {}}});
function render(args) {events.message({source: parent, data: {type: 'streamlit:render', args}});}
const args = {token: 'candidate:100:130', src: 'data:video/mp4;base64,test', duration: 30};
render(args);
assert.equal(player.loadCount, 1);
assert.equal(player.loadedSrc, args.src);
assert.equal(buttons.in.disabled, true);
player.duration = 30.04; player.readyState = 1;
mediaEvents.loadedmetadata();
assert.equal(buttons.in.disabled, false);
player.currentTime = 5.25;
buttons.in.click();
const mark = messages.findLast(m => m.type === 'streamlit:setComponentValue').value;
assert.equal(mark.action, 'in');
assert.equal(mark.position, 5.25);
assert.equal(mark.token, args.token);
assert.equal(buttons.out.disabled, true); // Do not race the server with a second mark.
const count = messages.filter(m => m.type === 'streamlit:setComponentValue').length;
buttons.out.click();
assert.equal(messages.filter(m => m.type === 'streamlit:setComponentValue').length, count);
render({...args, ack: mark.id});
assert.equal(buttons.out.disabled, false);
assert.equal(player.loadCount, 1); // Reruns preserve the displayed media and playhead.
assert.equal(player.currentTime, 5.25);
player.currentTime = 30.04;
buttons.out.click();
const end = messages.findLast(m => m.type === 'streamlit:setComponentValue').value;
assert.equal(end.position, 30); // Encoded frame padding is not outside the VOD range.
assert.notEqual(end.id, mark.id);
// Execute the real component render handler with a replacement trimmed source.
const trimmed = {token: 'candidate:104.25:122.5',
  src: 'data:video/mp4;base64,trimmed', duration: 18.25};
const pauses = player.pauseCount;
render(trimmed);
assert.equal(player.pauseCount, pauses + 1);
assert.equal(player.loadCount, 2);
assert.equal(player.loadedSrc, trimmed.src);
assert.equal(player.currentTime, 0);
assert.equal(buttons.in.disabled, true); // Await metadata for replacement media.
player.duration = 18.29; player.readyState = 1;
mediaEvents.loadedmetadata();
assert.equal(buttons.in.disabled, false);
buttons.in.click();
const freshStart = messages.findLast(m => m.type === 'streamlit:setComponentValue').value;
assert.equal(freshStart.token, trimmed.token);
assert.equal(freshStart.position, 0);
render({...trimmed, ack: freshStart.id});
player.currentTime = 18.29;
buttons.out.click();
const freshEnd = messages.findLast(m => m.type === 'streamlit:setComponentValue').value;
assert.equal(freshEnd.position, 18.25); // Use the new duration, not the old 30s range.
render({...trimmed, ack: freshEnd.id});
assert.equal(player.loadCount, 2);
assert.equal(player.currentTime, 18.29); // Do not reset on an ordinary rerun.
render({...args, token: 'next-candidate', disabled: true});
assert.equal(player.loadCount, 3);
assert.equal(buttons.in.disabled, true);
assert.equal(buttons.out.disabled, true);
console.log('Component handshake, marks, acknowledgement, playhead preservation, source replacement, new duration, and candidate reset passed.');
