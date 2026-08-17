import React from "react";
import { Users, Wifi } from "lucide-react";

// RASTER 4b — Community Picks (GELB, links) + Live KI Picks (BLAU, rechts), getrennt nebeneinander.
const T = {
  de: { community: "Community Picks ansehen", live: "Live KI Picks", liveBtn: "Live" },
  en: { community: "See Community Picks", live: "Live AI Picks", liveBtn: "Live" },
  es: { community: "Ver Community Picks", live: "Live AI Picks", liveBtn: "Live" },
  el: { community: "Δες Community Picks", live: "Live KI Picks", liveBtn: "Live" },
  fr: { community: "Voir Community Picks", live: "Live AI Picks", liveBtn: "Live" },
  it: { community: "Vedi Community Picks", live: "Live AI Picks", liveBtn: "Live" },
  ar: { community: "عرض Community Picks", live: "Live AI Picks", liveBtn: "مباشر" },
  tr: { community: "Community Picks'e bak", live: "Canlı YZ Picks", liveBtn: "Canlı" },
};

export default function Raster4b_CommunityLive({ lang = "de", counts = {}, onViewMembers, onViewLiveCommunity, onViewLive }) {
  const t = T[lang] || T.de;
  const rtl = lang === "ar";
  return (
    <section className="px-4 py-4" dir={rtl ? "rtl" : "ltr"} data-testid="raster4b-community-live">
      <div className="max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* LINKS: Community Picks — GELB + LIVE Button blau */}
        <div className="flex items-center justify-between gap-1 rounded-full bg-[#E3A81B] text-black font-heading font-black p-1" data-testid="r4b-community-wrap">
          <button onClick={onViewMembers} data-testid="r4b-community"
            className="flex items-center gap-2 min-w-0 flex-1 justify-start pl-3 pr-1 py-2 rounded-full active:scale-[0.98] transition-transform">
            <Users size={16} strokeWidth={2.5} />
            <span className="truncate text-sm">{t.community}</span>
            {counts.members != null && (
              <span className="min-w-[18px] text-center text-[10px] font-mono font-black rounded-full bg-black/25 px-1.5 py-0.5">{counts.members}</span>
            )}
          </button>
          <button onClick={onViewLiveCommunity} data-testid="r4b-community-live"
            className="flex items-center gap-1.5 shrink-0 rounded-full bg-[#2563eb] text-white px-3.5 py-2 text-xs font-black uppercase tracking-wide hover:bg-[#1d4fd8] active:scale-95 shadow-[0_0_16px_rgba(37,99,235,0.6)] transition-all">
            <span className="w-2 h-2 rounded-full bg-white animate-pulse" /> {t.liveBtn}
            {counts.community_live > 0 && (
              <span className="min-w-[16px] text-center text-[10px] font-mono font-black rounded-full bg-black/25 px-1">{counts.community_live}</span>
            )}
          </button>
        </div>

        {/* RECHTS: Live KI Picks — BLAU + wifi */}
        <button onClick={onViewLive} data-testid="r4b-live"
          className="flex items-center gap-2 rounded-full bg-[#2563eb] text-white font-heading font-black px-4 py-3 active:scale-[0.98] transition-transform shadow-[0_0_18px_rgba(37,99,235,0.5)] animate-pulse">
          <Wifi size={16} strokeWidth={2.5} />
          <span className="truncate text-sm">{t.live}</span>
          {counts.live != null && (
            <span className="min-w-[18px] text-center text-[10px] font-mono font-black rounded-full bg-black/25 px-1.5 py-0.5">{counts.live}</span>
          )}
        </button>
      </div>
    </section>
  );
}
