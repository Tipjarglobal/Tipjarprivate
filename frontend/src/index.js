import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import App from "@/App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

// Self-heal a stale/broken cached bundle after a deploy: if a code chunk fails to load (an old
// service worker served a build whose hashed chunks no longer exist), clear caches + unregister
// the SW and hard-reload ONCE. Guarded via sessionStorage so it can never loop.
function tjRecoverFromStaleBundle() {
  if (sessionStorage.getItem("tj-recovered-once")) return;
  sessionStorage.setItem("tj-recovered-once", "1");
  Promise.resolve()
    .then(() => ("caches" in window ? caches.keys().then((ks) => Promise.all(ks.map((k) => caches.delete(k)))) : null))
    .then(() => ("serviceWorker" in navigator ? navigator.serviceWorker.getRegistrations().then((rs) => Promise.all(rs.map((r) => r.unregister()))) : null))
    .catch(() => {})
    .finally(() => window.location.reload());
}
function tjIsChunkError(msg) {
  return /ChunkLoadError|Loading chunk|Loading CSS chunk|Unexpected token '<'|module script failed|dynamically imported module/i.test(String(msg || ""));
}
window.addEventListener("error", (e) => {
  if (tjIsChunkError(e && (e.message || (e.error && e.error.message)))) tjRecoverFromStaleBundle();
});
window.addEventListener("unhandledrejection", (e) => {
  if (tjIsChunkError(e && e.reason && (e.reason.message || e.reason))) tjRecoverFromStaleBundle();
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  });
  // Foreground pushes ask us to play the matching notification sound.
  navigator.serviceWorker.addEventListener("message", (e) => {
    if (e.data && e.data.type === "tj-push-coin") {
      import("@/coinSound").then((m) => m.playCoin(e.data.sound || "coin")).catch(() => {});
    }
  });
}
