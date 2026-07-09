import api from "./api";

export function anonId() {
  let id = localStorage.getItem("tj_anon");
  if (!id) {
    id = "anon-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("tj_anon", id);
  }
  return id;
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

export function supportsWebPush() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}
export function isStandalonePwa() {
  return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
}
export function isIos() {
  return /iPhone|iPad|iPod/.test(navigator.userAgent);
}

async function enableWebPush() {
  if (!supportsWebPush()) return { ok: false, reason: "unsupported" };
  if (isIos() && !isStandalonePwa()) return { ok: false, reason: "ios-install" };
  const reg = await navigator.serviceWorker.ready;
  const { data } = await api.get("/push/vapid-public-key");
  if (!data.publicKey) return { ok: false, reason: "no-key" };
  const existing = await reg.pushManager.getSubscription();
  const sub = existing || await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(data.publicKey),
  });
  const json = sub.toJSON();
  await api.post("/push/subscribe", { endpoint: json.endpoint, keys: json.keys });
  return { ok: true };
}

// Turn everything on in one go and let the bell sync via the "tj-push-enabled" event.
export async function enablePushFull() {
  if (window.Notification && Notification.permission !== "granted") {
    const perm = await Notification.requestPermission();
    if (perm !== "granted") return { ok: false, reason: "denied" };
  }
  try { await api.post("/notifications/subscribe", { anon_id: anonId() }); } catch { /* ignore */ }
  let res = { ok: true };
  try { res = await enableWebPush(); } catch { /* ignore */ }
  localStorage.setItem("tj_bell", "1");
  window.dispatchEvent(new Event("tj-push-enabled"));
  return res;
}
