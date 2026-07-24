// Share a TipJar slip image to Telegram / native share. Discreet, value-provider tone —
// no slogan/CTA in the visible text so it doesn't read like spam in third-party groups.
const TIPJAR_URL = "https://tipjarglobal.com";

export async function shareSlip({ imageUrl, username, odds }) {
  const text =
    `Kombi-Schein${odds ? ` · Gesamtquote ${odds}` : ""}${username ? ` · @${username}` : ""}`;
  try {
    if (imageUrl && typeof navigator !== "undefined" && navigator.canShare) {
      const resp = await fetch(imageUrl);
      const blob = await resp.blob();
      const file = new File([blob], "tipjar-slip.webp", { type: blob.type || "image/webp" });
      if (navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], text, title: "TipJar" });
        return true;
      }
    }
    if (typeof navigator !== "undefined" && navigator.share) {
      await navigator.share({ text, url: TIPJAR_URL });
      return true;
    }
  } catch (e) {
    if (e && e.name === "AbortError") return true;
  }
  // fallback: Telegram share (link to the image + text with the site URL)
  const tgUrl = encodeURIComponent(imageUrl || TIPJAR_URL);
  const tgText = encodeURIComponent(text);
  window.open(`https://t.me/share/url?url=${tgUrl}&text=${tgText}`, "_blank");
  return true;
}
