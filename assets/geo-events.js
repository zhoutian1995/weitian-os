(() => {
  "use strict";
  if (navigator.doNotTrack === "1" || navigator.globalPrivacyControl === true) return;
  if (globalThis.__xiaotianGeoEventsLoaded) return;
  globalThis.__xiaotianGeoEventsLoaded = true;
  const params = new URLSearchParams(location.search);
  const fields = {source: "utm_source", medium: "utm_medium", campaign: "utm_campaign", content: "utm_content"};
  const ownHosts = new Set(["willeai.com", "www.willeai.com", location.hostname]);
  let referrer = "";
  try {
    const host = new URL(document.referrer).hostname;
    if (!ownHosts.has(host) && host !== "localhost" && !/^\d+(\.\d+){3}$/.test(host)) referrer = host;
  } catch {}
  let touch = {referrer_host: referrer, test: params.get("geo_test") === "1" || navigator.webdriver === true ? "1" : "0"};
  for (const [field, parameter] of Object.entries(fields)) touch[field] = (params.get(parameter) || "").slice(0, 96);
  try {
    const previous = JSON.parse(sessionStorage.getItem("geo-touch-v1") || "null");
    const explicitCampaign = Object.values(fields).some(key => params.has(key));
    if (previous && !explicitCampaign) touch = {...previous, test: touch.test === "1" ? "1" : previous.test || "0"};
    sessionStorage.setItem("geo-touch-v1", JSON.stringify(touch));
  } catch {}
  const sent = new Set();
  function track(kind, once = false) {
    if (once && sent.has(kind)) return;
    if (once) sent.add(kind);
    const query = new URLSearchParams({event: kind, path: location.pathname.slice(0, 240), ...touch});
    const url = "/_geo/event?" + query;
    try {
      if (navigator.sendBeacon && navigator.sendBeacon(url, "")) return;
      fetch(url, {method: "POST", credentials: "same-origin", keepalive: true, body: ""}).catch(() => {});
    } catch {}
  }
  track("page_view", true);
  document.addEventListener("click", event => {
    const target = event.target.closest?.("a,button,[data-win],[data-open-win]");
    if (!target) return;
    if (target.matches(".claim-save")) track("qr_download_click");
    else if (target.matches('[data-win="win-sayhi"],[data-open-win="win-sayhi"]')) track("resource_cta_click");
    else if (target.matches('a[href^="mailto:"]')) track("consult_click");
  }, {capture: true, passive: true});
  const observed = new WeakSet();
  const visible = element => {
    const rect = element.getBoundingClientRect();
    if (!element.complete || element.naturalWidth <= 0 || rect.width <= 0 || rect.height <= 0) return false;
    if (element.checkVisibility && !element.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})) return false;
    const width = typeof innerWidth === "number" ? innerWidth : document.documentElement.clientWidth;
    const height = typeof innerHeight === "number" ? innerHeight : document.documentElement.clientHeight;
    const area = Math.max(0, Math.min(rect.right, width) - Math.max(rect.left, 0))
      * Math.max(0, Math.min(rect.bottom, height) - Math.max(rect.top, 0));
    return area / (rect.width * rect.height) >= 0.25;
  };
  const intersection = typeof IntersectionObserver === "function" ? new IntersectionObserver(entries => {
    for (const entry of entries) if (entry.isIntersecting && visible(entry.target)) track("wechat_qr_view", true);
  }, {threshold: 0.25}) : null;
  function watchImages() {
    if (sent.has("wechat_qr_view")) return;
    for (const image of document.querySelectorAll(".claim-qr")) {
      if (observed.has(image)) {
        if (visible(image)) track("wechat_qr_view", true);
        continue;
      }
      observed.add(image);
      if (intersection) intersection.observe(image);
      image.addEventListener("load", () => { if (visible(image)) track("wechat_qr_view", true); }, {once: true});
      if (image.complete && image.naturalWidth > 0 && visible(image)) track("wechat_qr_view", true);
    }
  }
  watchImages();
  document.addEventListener("transitionend", watchImages, {capture: true, passive: true});
  document.addEventListener("animationend", watchImages, {capture: true, passive: true});
  let queued = false;
  new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; watchImages(); });
  }).observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ["class", "style", "hidden"]});
})();
