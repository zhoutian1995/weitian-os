import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import {fileURLToPath} from "node:url";

const code = fs.readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "../assets/geo-events.js"), "utf8");
function run({dnt = "0", privacy = false, query = "?utm_source=deepseek&geo_test=1&token=SECRET", image: options = null} = {}) {
  const calls = [], handlers = new Map();
  let intersect = null;
  const imageHandlers = new Map();
  let top = options?.top ?? 900;
  let cssVisible = options?.cssVisible ?? true;
  let mutate = null;
  const image = options ? {complete: options.complete ?? true, naturalWidth: options.loaded === false ? 0 : 200,
    getBoundingClientRect: () => ({left: 0, top, right: 200, bottom: top + 200, width: 200, height: 200}),
    addEventListener: (name, handler) => imageHandlers.set(name, handler), checkVisibility: () => cssVisible} : null;
  const storage = new Map();
  const context = {URL, URLSearchParams, WeakSet, Set, Map, JSON, innerWidth: 1000, innerHeight: 800,
    IntersectionObserver: class {constructor(callback) {intersect = callback;} observe() {}},
    location: new URL("https://willeai.com/topics/fde.html" + query),
    navigator: {doNotTrack: dnt, globalPrivacyControl: privacy, sendBeacon: (url, body) => {calls.push({url, body}); return true;}},
    sessionStorage: {getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value)},
    document: {referrer: "https://chat.deepseek.com/private?token=DO_NOT_KEEP", body: {},
      querySelectorAll: () => image ? [image] : [], addEventListener: (name, handler) => handlers.set(name, handler)},
    MutationObserver: class {constructor(callback) {mutate = callback;} observe() {}}, requestAnimationFrame: fn => fn(), fetch: () => Promise.resolve()};
  vm.runInNewContext(code, context);
  return {calls, handlers, image, moveImage: value => {top = value;}, showImage: () => {cssVisible = true;}, mutateImages: () => mutate?.(), loadImage: () => {
    image.complete = true; image.naturalWidth = 200; imageHandlers.get("load")?.();
  }, intersectImage: () => intersect?.([{isIntersecting: true, target: image}])};
}
assert.equal(run({dnt: "1"}).calls.length, 0);
assert.equal(run({privacy: true}).calls.length, 0);
const normal = run();
assert.equal(normal.calls.length, 1);
let parsed = new URL(normal.calls[0].url, "https://willeai.com");
assert.equal(parsed.searchParams.get("event"), "page_view");
assert.equal(parsed.searchParams.get("test"), "1");
assert.equal(parsed.searchParams.get("referrer_host"), "chat.deepseek.com");
assert.equal(parsed.searchParams.get("source"), "deepseek");
assert.equal(parsed.searchParams.get("path"), "/topics/fde.html");
assert(!normal.calls[0].url.includes("SECRET"));
assert(!normal.calls[0].url.includes("private"));
normal.handlers.get("click")({target: {closest: () => ({matches: selector => selector === ".claim-save"})}});
parsed = new URL(normal.calls.at(-1).url, "https://willeai.com");
assert.equal(parsed.searchParams.get("event"), "qr_download_click");
assert(!code.includes("wechat_added"));
assert(!code.includes("document.cookie"));
const hiddenImage = run({image: {top: 900}});
assert.equal(hiddenImage.calls.length, 1);
hiddenImage.loadImage();
assert.equal(hiddenImage.calls.length, 1);
hiddenImage.moveImage(790);
hiddenImage.intersectImage();
assert.equal(hiddenImage.calls.length, 1);
hiddenImage.moveImage(100);
hiddenImage.intersectImage();
hiddenImage.loadImage();
assert.equal(hiddenImage.calls.filter(call => new URL(call.url, "https://willeai.com").searchParams.get("event") === "wechat_qr_view").length, 1);
const unloaded = run({image: {top: 100, complete: false, loaded: false}});
unloaded.intersectImage();
assert.equal(unloaded.calls.length, 1);
unloaded.loadImage();
assert.equal(unloaded.calls.length, 2);
const animated = run({image: {top: 100, cssVisible: false}});
animated.intersectImage();
assert.equal(animated.calls.length, 1);
animated.showImage();
animated.handlers.get("transitionend")();
animated.handlers.get("animationend")();
assert.equal(animated.calls.length, 2);
const reducedMotion = run({image: {top: 100, cssVisible: false}});
reducedMotion.showImage();
reducedMotion.mutateImages();
assert.equal(reducedMotion.calls.length, 2);
console.log("geo-events client checks passed: privacy opt-out, bounded attribution, QA tagging, real loaded viewport exposure and deduplication");
