/* Minimal app-shell cache for CDX Web Scan */

const CACHE_NAME = "cdx-web-scan-v7";
const APP_SHELL = [
  "/",
  "/static/styles.css",
  "/static/app.js",
  "/manifest.webmanifest",
  "/static/icon.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );

  // Activate updated SW ASAP.
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => (key === CACHE_NAME ? null : caches.delete(key)))
      )
    )
  );

  // Take control of uncontrolled clients immediately.
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;

  // Only handle GET requests.
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  const isHttp = url.protocol === "http:" || url.protocol === "https:";
  const isSameOrigin = url.origin === self.location.origin;

  // Ignore non-http(s) schemes (e.g., chrome-extension://) and cross-origin requests.
  // Extensions and browser internals can trigger these, and Cache.put will throw.
  if (!isHttp || !isSameOrigin) return;

  event.respondWith(
    fetch(req)
      .then((res) => {
        // Only cache successful, same-origin responses.
        if (res.ok && res.type === "basic") {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(req).then((cached) => cached || caches.match("/")))
  );
});
