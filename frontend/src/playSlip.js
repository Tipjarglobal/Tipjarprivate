// Bet-slip handoff helpers. Real bookmakers offer no public bet-placement API, so we
// can't auto-load a parlay onto Wazamba. Instead we show an in-app checklist overlay
// (see PlaySlipOverlay) and copy a clean, ordered slip to the clipboard.
import { formatKickoff } from "./i18n";

export const BOOKMAKER = { name: "Wazamba", url: "https://www.wazamba.com" };

function legLine(leg, idx, t) {
  const head = `${idx}. ${leg.match || ""}`.trim();
  const sub = [leg.market, leg.odds ? `@${leg.odds}` : "", formatKickoff(leg.kickoff, t)]
    .filter(Boolean)
    .join("  ·  ");
  return sub ? `${head}\n   ${sub}` : head;
}

export function buildSlipText(legs, meta, t) {
  const title = meta.title ? ` — ${meta.title}` : "";
  const odds = meta.totalOdds ? `  ·  ${t("play.totalOdds")} ${meta.totalOdds}` : "";
  const body = (legs || []).map((l, i) => legLine(l, i + 1, t)).join("\n");
  const foot = [
    meta.stake ? `${t("play.stake")}: ${meta.stake}` : "",
    meta.winnings ? `${t("play.win")}: ${meta.winnings}` : "",
  ]
    .filter(Boolean)
    .join("  ·  ");
  return [`🎯 TipJar${title}${odds}`, "", body, foot, "tipjarglobal.com"]
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

// Copy synchronously first (document still focused), then async clipboard as fallback.
export async function copySlip(text) {
  let copied = false;
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "0";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    ta.setSelectionRange(0, text.length);
    copied = document.execCommand("copy");
    document.body.removeChild(ta);
  } catch (_) {
    /* ignore */
  }
  if (!copied && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
    } catch (_) {
      /* ignore */
    }
  }
  return copied;
}

export function openBookmaker() {
  try {
    window.open(BOOKMAKER.url, "_blank", "noopener,noreferrer");
  } catch (_) {
    /* ignore */
  }
}
