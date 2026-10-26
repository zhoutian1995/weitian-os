(() => {
  "use strict";
  if (navigator.doNotTrack === "1" || navigator.globalPrivacyControl === true) return;
  if (globalThis.__xiaotianGeoEventsLoaded) return;
  globalThis.__xiaotianGeoEventsLoaded = true;
  const params = new URLSearchParams(location.search);
  const fields = {source: "utm_source", medium: "utm_medium", campaign: "utm_campaign", content: "utm_content"};
  const ownHosts = new Set(["willeai.com", "www.willeai.com", "willeai.cn", "www.willeai.cn", location.hostname]);
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
    if (previous && !explicitCampaign) touch = {...previous};
    if (previous?.test === "1") touch.test = "1";
    if (params.get("geo_test") === "1" || navigator.webdriver === true) touch.test = "1";
    sessionStorage.setItem("geo-touch-v1", JSON.stringify(touch));
  } catch {}
  const sent = new Set();
  function track(kind, once = false, audienceOverride = "") {
    if (once && sent.has(kind)) return;
    if (once) sent.add(kind);
    const candidate = audienceOverride || new URLSearchParams(location.search).get("intent") || document.body?.dataset?.geoAudience || "";
    const audience = ["fde", "enterprise", "talent"].includes(candidate) ? candidate : "";
    const query = new URLSearchParams({event: kind, path: location.pathname.slice(0, 240), audience, ...touch});
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
    if (touch.test === "1" && target.tagName === "A" && target.href) {
      try {
        const destination = new URL(target.href, location.href);
        if (ownHosts.has(destination.hostname) && ["http:", "https:"].includes(destination.protocol)) {
          destination.searchParams.set("geo_test", "1");
          target.href = destination.toString();
        }
      } catch {}
    }
    if (target.matches(".claim-save,.qr-download")) track("qr_download_click");
    else if (target.matches("[data-copy-outline]")) track("outline_copy_click");
    else if (target.matches("[data-contact-intent]")) track("contact_intent_select", false, target.dataset?.contactIntent || "");
    else if (target.matches('[data-win="win-sayhi"],[data-open-win="win-sayhi"],[data-geo-workflow]')) track("resource_cta_click");
    else if (target.matches('a[href^="mailto:"],[data-geo-consult]')) track("consult_click");
  }, {capture: true, passive: true});
  const observed = new WeakSet();
  const visible = element => {
    const rect = element.getBoundingClientRect();
    if (!element.complete || element.naturalWidth <= 0 || rect.width <= 0 || rect.height <= 0) return false;
    if (element.checkVisibility && !element.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})) return false;
    const width = typeof innerWidth === "number" ? innerWidth : document.documentElement.clientWidth;
    const height = typeof innerHeight === "number" ? innerHeight : document.documentElement.clientHeight;
    let left = Math.max(rect.left, 0), right = Math.min(rect.right, width);
    let top = Math.max(rect.top, 0), bottom = Math.min(rect.bottom, height);
    for (let parent = element.parentElement; parent; parent = parent.parentElement) {
      const style = getComputedStyle(parent);
      const box = parent.getBoundingClientRect();
      const scaleX = parent.offsetWidth ? box.width / parent.offsetWidth : 1;
      const scaleY = parent.offsetHeight ? box.height / parent.offsetHeight : 1;
      if (/(hidden|clip|scroll|auto)/.test(style.overflowX || style.overflow || "")) {
        const start = box.left + (parent.clientLeft || 0) * scaleX;
        left = Math.max(left, start);
        right = Math.min(right, start + parent.clientWidth * scaleX);
      }
      if (/(hidden|clip|scroll|auto)/.test(style.overflowY || style.overflow || "")) {
        const start = box.top + (parent.clientTop || 0) * scaleY;
        top = Math.max(top, start);
        bottom = Math.min(bottom, start + parent.clientHeight * scaleY);
      }
    }
    const area = Math.max(0, right - left) * Math.max(0, bottom - top);
    return area / (rect.width * rect.height) >= 0.25;
  };
  const intersection = typeof IntersectionObserver === "function" ? new IntersectionObserver(entries => {
    for (const entry of entries) if (entry.isIntersecting && entry.intersectionRatio >= 0.25 && visible(entry.target)) track("wechat_qr_view", true);
  }, {threshold: 0.25}) : null;
  function watchImages() {
    if (sent.has("wechat_qr_view")) return;
    for (const image of document.querySelectorAll(".claim-qr,.owner-qr,[data-geo-qr]")) {
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
