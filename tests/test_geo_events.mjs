import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import {fileURLToPath} from "node:url";

const code = fs.readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "../assets/geo-events.js"), "utf8");
function run({dnt = "0", privacy = false, query = "?utm_source=deepseek&geo_test=1&token=SECRET", image: options = null, previous = null} = {}) {
  const calls = [], handlers = new Map();
  let intersect = null;
  const imageHandlers = new Map();
  let top = options?.top ?? 900;
  let cssVisible = options?.cssVisible ?? true;
  let mutate = null;
  const image = options ? {complete: options.complete ?? true, naturalWidth: options.loaded === false ? 0 : 200,
    parentElement: options.parent || null,
    getBoundingClientRect: () => ({left: 0, top, right: 200, bottom: top + 200, width: 200, height: 200}),
    addEventListener: (name, handler) => imageHandlers.set(name, handler), checkVisibility: () => cssVisible} : null;
  const storage = new Map(previous ? [["geo-touch-v1", JSON.stringify(previous)]] : []);
  const context = {URL, URLSearchParams, WeakSet, Set, Map, JSON, innerWidth: 1000, innerHeight: 800,
    getComputedStyle: element => element.computedStyle || {},
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
  }, intersectImage: (ratio = 1) => intersect?.([{isIntersecting: true, intersectionRatio: ratio, target: image}])};
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
normal.handlers.get("click")({target: {closest: () => ({matches: selector => selector === ".claim-save,.qr-download"})}});
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
const previousQa = run({query: "?utm_source=new-source&utm_campaign=fresh", previous: {source: "old-source", test: "1"}});
const previousQaEvent = new URL(previousQa.calls[0].url, "https://willeai.com");
assert.equal(previousQaEvent.searchParams.get("test"), "1");
assert.equal(previousQaEvent.searchParams.get("source"), "new-source");
const parent = {parentElement: null, offsetWidth: 200, offsetHeight: 200, clientWidth: 200, clientHeight: 20,
  clientLeft: 0, clientTop: 0, computedStyle: {overflowY: "hidden", overflowX: "visible"},
  getBoundingClientRect: () => ({left: 0, top: 100, right: 200, bottom: 300, width: 200, height: 200})};
const clipped = run({image: {top: 100, parent}});
clipped.intersectImage(0.1);
clipped.mutateImages();
assert.equal(clipped.calls.length, 1);
parent.clientHeight = 200;
clipped.mutateImages();
assert.equal(clipped.calls.length, 2);
const intent = run({query: "?intent=fde"});
assert.equal(new URL(intent.calls[0].url, "https://willeai.com").searchParams.get("audience"), "fde");
intent.handlers.get("click")({target:{closest:()=>({dataset:{contactIntent:"enterprise"},matches:selector=>selector==="[data-contact-intent]"})}});
const selected = new URL(intent.calls.at(-1).url, "https://willeai.com");
assert.equal(selected.searchParams.get("event"), "contact_intent_select");
assert.equal(selected.searchParams.get("audience"), "enterprise");
const qaOwnedLink = {tagName: "A", href: "https://willeai.cn/contact/?intent=enterprise&utm_source=willeai.com", matches: () => false};
normal.handlers.get("click")({target: {closest: () => qaOwnedLink}});
assert.equal(new URL(qaOwnedLink.href).searchParams.get("geo_test"), "1");
assert.equal(new URL(qaOwnedLink.href).searchParams.get("intent"), "enterprise");
const external = {tagName: "A", href: "https://example.org/article", matches: () => false};
normal.handlers.get("click")({target: {closest: () => external}});
assert.equal(external.href, "https://example.org/article");
const production = run({query: "?utm_source=google"});
const productionLink = {tagName: "A", href: "https://willeai.cn/services/", matches: () => false};
production.handlers.get("click")({target: {closest: () => productionLink}});
assert.equal(productionLink.href, "https://willeai.cn/services/");
console.log("geo-events client checks passed: opt-out, attribution, sticky/cross-site QA, clipped exposure, intent and deduplication");
