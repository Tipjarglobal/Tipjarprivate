import React, { useEffect, useState } from "react";
import api from "../api";

// Sponsor feed banner (wazamba etc.). Fetches /api/sponsors/feed and rotates through sponsors.
export default function SponsorFeeder() {
  const [sponsors, setSponsors] = useState([]);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    let alive = true;
    api.get("/sponsors/feed")
      .then(({ data }) => { if (alive) setSponsors(data.sponsors || []); })
      .catch(() => { if (alive) setSponsors([]); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (sponsors.length < 2) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % sponsors.length), 6000);
    return () => clearInterval(t);
  }, [sponsors]);

  if (!sponsors.length) return null;
  const s = sponsors[idx];

  return (
    <a
      data-testid="sponsor-feeder"
      href={s.url || "#"}
      target="_blank"
      rel="noopener noreferrer nofollow sponsored"
      className="block mx-4 mt-3 rounded-xl border border-white/10 bg-gradient-to-r from-[#18181B] to-[#1f1710] hover:border-volt/40 transition-colors overflow-hidden"
    >
      <div className="flex items-center gap-3 px-4 py-2.5">
        {s.logo ? (
          <img src={s.logo} alt={s.name} className="h-7 w-auto object-contain rounded" />
        ) : (
          <span className="text-sm font-black uppercase tracking-wider text-[#FFB020]">{s.name}</span>
        )}
        <span className="text-sm text-zinc-200 font-semibold truncate">{s.tagline || s.bonus}</span>
        {s.bonus && s.tagline && (
          <span className="ml-auto text-xs font-bold text-[#00FF94] whitespace-nowrap">{s.bonus}</span>
        )}
        <span className="ml-auto shrink-0 text-[10px] uppercase tracking-widest text-zinc-500">Anzeige</span>
      </div>
    </a>
  );
}
