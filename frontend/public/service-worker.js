const CACHE = "tipjar-shell-v5";
const SHELL = ["/", "/index.html", "/manifest.json", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.pathname.startsWith("/api/")) return;      // never cache API calls
  if (url.origin !== self.location.origin) return;

  // (1) NAVIGATIONS (the HTML shell): network-first so a fresh deploy loads immediately;
  //     fall back to the cached index.html ONLY when the network is truly unreachable (offline).
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put("/index.html", copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match("/index.html").then((c) => c || Response.error()))
    );
    return;
  }

  // (2) STATIC ASSETS (hashed JS/CSS/images — immutable): cache-first, else network.
  //     CRITICAL: never fall back to index.html here. Returning HTML for a .js/.css request
  //     throws "Unexpected token '<'" and black-screens the app (the old bug + reload loop).
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req)
        .then((res) => {
          if (res && res.status === 200 && res.type === "basic") {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => cached || Response.error());
    })
  );
});

// ── Web Push: show a notification even when the app/browser is closed ──────
self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch { data = {}; }
  const title = data.title || "TipJar";
  const options = {
    body: data.body || "",
    icon: data.icon || "/icon-192.png",
    badge: data.badge || "/icon-192.png",
    tag: data.tag || "tipjar",
    renotify: true,
    // LOUD + persistent (owner request): play the OS notification sound (not silent), keep the
    // banner on screen until the user acts, and vibrate strongly — works with the app closed.
    silent: false,
    requireInteraction: true,
    vibrate: data.vibrate || (data.kind === "live"
      ? [300, 120, 300, 120, 300, 120, 500]
      : [200, 100, 200, 100, 400]),
    data: { url: data.url || "/", kind: data.kind || "tip" },
    actions: (data.actions && data.actions.length)
      ? data.actions
      : [{ action: "open", title: "Zum Pick →" }],
  };
  event.waitUntil(self.registration.showNotification(title, options));
  // Best-effort: nudge any open tab to play the coin ding (SWs can't play audio).
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
      for (const c of cs) c.postMessage({ type: "tj-push-coin", sound: data.sound || "coin" });
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = new URL((event.notification.data && event.notification.data.url) || "/", self.location.origin).href;
  event.waitUntil(
    (async () => {
      const all = await clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const c of all) {
        if ("focus" in c) { c.navigate(target).catch(() => {}); return c.focus(); }
      }
      return clients.openWindow(target);
    })()
  );
});
