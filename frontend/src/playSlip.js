// One-tap "play this parlay" helper: copies the whole slip (sorted, clean) to the
// clipboard and opens the bookmaker so the user just ticks the markets — no more
// searching game-by-game. NOTE: real bookmakers offer no public bet-placement API,
// so this is a legal copy+handoff, never an automatic real-money placement.
import { toast } from "sonner";
import { formatSelection, formatKickoff } from "./i18n";

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
    .filter((x) => x !== "" || true)
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export async function playSlip(legs, meta, t) {
  const text = buildSlipText(legs, meta, t);
  // Copy FIRST, while the document still has focus (opening the bookmaker steals
  // focus and would make navigator.clipboard fail with "document not focused").
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
  // Modern async clipboard as an enhancement (only if the sync path didn't work).
  if (!copied && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
    } catch (_) {
      /* ignore */
    }
  }
  // Then open the bookmaker in a new tab.
  try {
    window.open(BOOKMAKER.url, "_blank", "noopener,noreferrer");
  } catch (_) {
    /* ignore */
  }
  if (copied) toast.success(t("play.copied"));
  else toast.message(t("play.manual"));
}

