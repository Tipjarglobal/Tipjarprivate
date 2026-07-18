const CACHE = "tipjar-shell-v3";
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

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // Never cache API calls
  if (url.pathname.startsWith("/api/")) return;
  if (url.origin !== self.location.origin) return;
  // Network-first everywhere (fresh code when online, cached shell when offline)
  event.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(req).then((cached) => cached || caches.match("/index.html")))
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
    vibrate: data.vibrate || (data.kind === "live" ? [80, 40, 80, 40, 120] : [60, 30, 60]),
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
