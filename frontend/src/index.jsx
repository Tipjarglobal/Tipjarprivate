import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import App from "./App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

// Self-heal a stale/broken cached bundle after a deploy
function tjRecoverFromStaleBundle() {
  if (sessionStorage.getItem("tj-recovered-once")) return;
  window.addEventListener("error", (e) => {
    const msg = e?.message || "";
    if (msg.includes("Failed to fetch") || msg.includes("ChunkLoadError") || msg.includes("Loading chunk")) {
      sessionStorage.setItem("tj-recovered-once", "1");
      if ("caches" in window) caches.keys().then((ks) => ks.forEach((k) => caches.delete(k)));
      if (navigator.serviceWorker) navigator.serviceWorker.getRegistrations().then((rs) => rs.forEach((r) => r.unregister()));
      location.reload();
    }
  });
}
tjRecoverFromStaleBundle();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
