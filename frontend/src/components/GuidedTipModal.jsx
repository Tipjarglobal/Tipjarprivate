import React, { useState } from "react";
import Modal from "./Modal";
import api, { apiErr } from "../api";
import { useAuth } from "../auth";
import { toast } from "sonner";
import { Search, Plus, Star, X, Loader2, Zap, Clock, CalendarClock } from "lucide-react";

const L = {
  DE: {
    title: "Tipp abgeben", stepTeam: "Schritt 1 · Spiel finden", stepPick: "Schritt 2 · Dein Pick",
    stepMore: "Noch ein Spiel?", stepFinish: "Schritt 3 · Bewerten & posten",
    teamPh: "Mannschaft eingeben (z.B. PAOK)", search: "Suchen", searching: "suche…",
    found: "Okay, ich habe diese Spiele gefunden. Welches meinst du?",
    noGames: "Keine kommenden Spiele gefunden. Trage das Spiel unten frei ein oder poste nur mit Text/Bild.",
    freeGame: "Spiel frei eintragen (Heim vs Gast)", useFree: "Dieses Spiel nehmen",
    skip: "Ohne Spiel weiter (nur Text/Bild)",
    pickFor: "Was ist dein Pick für", pickPh: "z.B. Über 2.5 Tore, 1X, Beide treffen…",
    oddsPh: "Quote (optional, z.B. 1.85)", next: "Weiter",
    moreQ: "Möchtest du noch ein Spiel hinzufügen (Kombi)?", yes: "Ja, Spiel hinzufügen", no: "Nein, weiter",
    yourGames: "Deine Auswahl", stars: "Deine Sterne (1–10) – Pflicht", timing: "Wann geht's los?",
    live: "Live", today: "Heute", later: "Später",
    textPh: "Kurzer Text (OPTIONAL)", post: "Tipp posten", posting: "poste…",
    needStars: "Bitte vergib zuerst deine Sterne (1–10).",
    needSomething: "Trage mindestens ein Spiel + Pick, einen Text oder ein Bild ein.",
    published: "Tipp gepostet! 🎉", addImg: "Foto anhängen (optional, max 4)", remove: "entfernen",
  },
  EN: {
    title: "Post a tip", stepTeam: "Step 1 · Find match", stepPick: "Step 2 · Your pick",
    stepMore: "Another match?", stepFinish: "Step 3 · Rate & post",
    teamPh: "Enter a team (e.g. PAOK)", search: "Search", searching: "searching…",
    found: "Okay, I found these matches. Which one do you mean?",
    noGames: "No upcoming matches found. Enter the match freely below, or post with text/image only.",
    freeGame: "Enter match freely (Home vs Away)", useFree: "Use this match",
    skip: "Continue without a match (text/image only)",
    pickFor: "What is your pick for", pickPh: "e.g. Over 2.5 goals, 1X, Both teams to score…",
    oddsPh: "Odds (optional, e.g. 1.85)", next: "Next",
    moreQ: "Add another match (combo)?", yes: "Yes, add match", no: "No, continue",
    yourGames: "Your selection", stars: "Your stars (1–10) – required", timing: "When does it start?",
    live: "Live", today: "Today", later: "Later",
    textPh: "Short text (OPTIONAL)", post: "Post tip", posting: "posting…",
    needStars: "Please give your stars (1–10) first.",
    needSomething: "Add at least one match + pick, a text, or an image.",
    published: "Tip posted! 🎉", addImg: "Attach photo (optional, max 4)", remove: "remove",
  },
};

const PICK_PILLS = ["Über 0.5", "Über 1.5", "Über 2.5", "Beide treffen", "1", "X", "2", "1X", "X2", "Über 9.5 Ecken"];

export default function GuidedTipModal({ open, onClose, onPublished, requireLogin }) {
  const { user } = useAuth();
  const t = L[(typeof localStorage !== "undefined" && (localStorage.getItem("tj_lang") || "").toUpperCase())] || L.DE;

  const [phase, setPhase] = useState("TEAM");
  const [games, setGames] = useState([]);
  const [draft, setDraft] = useState(null); // {home,away,kickoff,league,country}
  const [q, setQ] = useState("");
  const [sugs, setSugs] = useState([]);
  const [searched, setSearched] = useState(false);
  const [searching, setSearching] = useState(false);
  const [freeHome, setFreeHome] = useState("");
  const [freeAway, setFreeAway] = useState("");
  const [pick, setPick] = useState("");
  const [odds, setOdds] = useState("");
  const [stars, setStars] = useState(0);
  const [timing, setTiming] = useState("today");
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const [publishing, setPublishing] = useState(false);

  const reset = () => {
    setPhase("TEAM"); setGames([]); setDraft(null); setQ(""); setSugs([]); setSearched(false);
    setFreeHome(""); setFreeAway(""); setPick(""); setOdds(""); setStars(0); setTiming("today");
    setText(""); setFiles([]);
  };
  const close = () => { reset(); onClose(); };

  const doSearch = async () => {
    if (q.trim().length < 2) return;
    setSearching(true); setSearched(false);
    try {
      const { data } = await api.get(`/tips/team-search`, { params: { q: q.trim() } });
      setSugs(data.suggestions || []);
    } catch { setSugs([]); }
    finally { setSearching(false); setSearched(true); }
  };

  const selectGame = (g) => { setDraft(g); setPick(""); setOdds(""); setPhase("PICK"); };
  const useFreeGame = () => {
    if (!freeHome.trim()) return;
    setDraft({ home: freeHome.trim(), away: freeAway.trim(), kickoff: "", league: "", country: "" });
    setPick(""); setOdds(""); setPhase("PICK");
  };

  const confirmPick = () => {
    if (!pick.trim()) { toast.error(t.pickPh); return; }
    setGames((g) => [...g, { ...draft, pick: pick.trim(), odds: odds.trim() }]);
    setDraft(null); setPick(""); setOdds(""); setPhase("MORE");
  };

  const removeGame = (i) => setGames((g) => g.filter((_, idx) => idx !== i));

  const publish = async () => {
    if (!user) { requireLogin && requireLogin(); return; }
    if (!(stars >= 1 && stars <= 10)) { toast.error(t.needStars); return; }
    if (games.length === 0 && !text.trim() && files.length === 0) { toast.error(t.needSomething); return; }
    setPublishing(true);
    try {
      // optionaler Bild-Upload (nicht blockierend, KI-frei falls Limit)
      let image_path = null, image_paths = [];
      if (files.length) {
        try {
          const fd = new FormData();
          files.slice(0, 4).forEach((f) => fd.append("files", f));
          fd.append("text", text);
          const { data } = await api.post("/tips/analyze", fd, { headers: { "Content-Type": "multipart/form-data" } });
          image_path = data.image_path || null; image_paths = data.image_paths || [];
        } catch { /* Bild optional – ohne weiter */ }
      }

      let payload = {
        raw_text: text, self_rating: stars, timing,
        image_path, image_paths,
      };
      if (games.length <= 1) {
        const g = games[0];
        payload = {
          ...payload,
          home_team: g?.home || "", away_team: g?.away || "",
          match_time: g?.kickoff || "", league: g?.league || "", country: g?.country || "",
          market: g?.pick || text.trim() || (files.length ? "Wettschein (Bild)" : ""),
          odds: g?.odds || "", legs: [],
        };
      } else {
        payload = {
          ...payload,
          is_parlay: true,
          market: games.map((g) => `${g.home} - ${g.away}: ${g.pick}`).join(" + "),
          legs: games.map((g) => ({
            match: `${g.home} vs ${g.away}`, league: g.league || "", kickoff: g.kickoff || "",
            selections: [g.pick], sel_odds: g.odds ? [g.odds] : [], combo_odds: g.odds || "", banker: false,
          })),
        };
      }
      const { data } = await api.post("/tips", payload);
      toast.success(t.published);
      onPublished && onPublished(data);
      close();
    } catch (err) {
      toast.error(apiErr(err));
    } finally { setPublishing(false); }
  };

  const kickoffLabel = (iso) => {
    if (!iso) return "";
    try { return new Date(iso).toLocaleString(undefined, { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }); }
    catch { return iso; }
  };

  return (
    <Modal open={open} onClose={close} title={t.title} testId="guided-tip-modal">
      <div className="space-y-4" data-testid="guided-body">

        {/* progress */}
        <div className="flex gap-1.5">
          {["TEAM", "PICK", "MORE", "FINISH"].map((p, i) => (
            <div key={p} className="flex-1 h-1 rounded-full" style={{ background: (["TEAM", "PICK", "MORE", "FINISH"].indexOf(phase) >= i) ? "#d4ff00" : "#27272a" }} />
          ))}
        </div>

        {/* ===== STEP 1: TEAM ===== */}
        {phase === "TEAM" && (
          <div className="space-y-3" data-testid="guided-team">
            <p className="text-[11px] font-black tracking-widest text-volt uppercase">{t.stepTeam}</p>
            <div className="flex gap-2">
              <input data-testid="guided-team-input" value={q} onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && doSearch()} placeholder={t.teamPh}
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2.5 text-sm text-white focus:border-volt outline-none" />
              <button data-testid="guided-team-search" onClick={doSearch} disabled={searching || q.trim().length < 2}
                className="rounded-xl bg-volt text-black font-black px-4 text-sm flex items-center gap-1 disabled:opacity-40">
                {searching ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />} {searching ? t.searching : t.search}
              </button>
            </div>

            {sugs.length > 0 && (
              <>
                <p className="text-xs text-zinc-400">{t.found}</p>
                <div className="space-y-2">
                  {sugs.map((g, i) => (
                    <button key={i} data-testid={`guided-sug-${i}`} onClick={() => selectGame(g)}
                      className="w-full text-left rounded-xl border border-zinc-700 bg-zinc-900 hover:border-volt px-3 py-2.5 transition-colors">
                      <div className="text-sm font-bold text-white">{g.home} <span className="text-zinc-500">vs</span> {g.away}</div>
                      <div className="text-[10px] text-zinc-500">{[kickoffLabel(g.kickoff), g.league, g.country].filter(Boolean).join(" · ")}</div>
                    </button>
                  ))}
                </div>
              </>
            )}
            {searched && sugs.length === 0 && <p className="text-xs text-amber-400">{t.noGames}</p>}

            {/* freies Spiel */}
            <div className="rounded-xl border border-dashed border-zinc-700 p-3 space-y-2">
              <p className="text-[10px] text-zinc-500 uppercase tracking-widest">{t.freeGame}</p>
              <div className="grid grid-cols-2 gap-2">
                <input data-testid="guided-free-home" value={freeHome} onChange={(e) => setFreeHome(e.target.value)} placeholder="Heim / Home"
                  className="bg-zinc-900 border border-zinc-700 rounded-lg px-2.5 py-2 text-sm text-white focus:border-volt outline-none" />
                <input data-testid="guided-free-away" value={freeAway} onChange={(e) => setFreeAway(e.target.value)} placeholder="Gast / Away"
                  className="bg-zinc-900 border border-zinc-700 rounded-lg px-2.5 py-2 text-sm text-white focus:border-volt outline-none" />
              </div>
              <button data-testid="guided-free-use" onClick={useFreeGame} disabled={!freeHome.trim()}
                className="w-full rounded-lg bg-zinc-800 text-white text-xs font-black py-2 disabled:opacity-40">{t.useFree}</button>
            </div>

            <button data-testid="guided-skip" onClick={() => setPhase("FINISH")} className="w-full text-[11px] text-zinc-500 underline">{t.skip}</button>
          </div>
        )}

        {/* ===== STEP 2: PICK ===== */}
        {phase === "PICK" && draft && (
          <div className="space-y-3" data-testid="guided-pick">
            <p className="text-[11px] font-black tracking-widest text-volt uppercase">{t.stepPick}</p>
            <div className="rounded-xl bg-zinc-900 border border-zinc-700 px-3 py-2">
              <div className="text-sm font-bold text-white">{draft.home} <span className="text-zinc-500">vs</span> {draft.away}</div>
              <div className="text-[10px] text-zinc-500">{[kickoffLabel(draft.kickoff), draft.league].filter(Boolean).join(" · ")}</div>
            </div>
            <p className="text-xs text-zinc-300">{t.pickFor} <b className="text-white">{draft.home} vs {draft.away}</b>?</p>
            <div className="flex flex-wrap gap-1.5">
              {PICK_PILLS.map((p) => (
                <button key={p} data-testid={`guided-pill-${p}`} onClick={() => setPick(p)}
                  className={`text-[11px] font-bold px-3 py-1.5 rounded-full border transition-colors ${pick === p ? "bg-volt text-black border-volt" : "bg-zinc-900 text-zinc-300 border-zinc-700"}`}>{p}</button>
              ))}
            </div>
            <input data-testid="guided-pick-input" value={pick} onChange={(e) => setPick(e.target.value)} placeholder={t.pickPh}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2.5 text-sm text-white focus:border-volt outline-none" />
            <input data-testid="guided-odds-input" value={odds} onChange={(e) => setOdds(e.target.value)} placeholder={t.oddsPh}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2.5 text-sm text-white focus:border-volt outline-none" />
            <button data-testid="guided-pick-next" onClick={confirmPick} disabled={!pick.trim()}
              className="w-full rounded-xl bg-volt text-black font-black py-2.5 text-sm disabled:opacity-40">{t.next}</button>
          </div>
        )}

        {/* ===== STEP 3: MORE ===== */}
        {phase === "MORE" && (
          <div className="space-y-3" data-testid="guided-more">
            <p className="text-sm text-white font-bold">{t.moreQ}</p>
            <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-2 space-y-1">
              {games.map((g, i) => (
                <div key={i} className="text-xs text-zinc-300 flex justify-between items-center">
                  <span>{g.home} - {g.away}: <b className="text-volt">{g.pick}</b>{g.odds ? ` @${g.odds}` : ""}</span>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button data-testid="guided-more-yes" onClick={() => { setQ(""); setSugs([]); setSearched(false); setFreeHome(""); setFreeAway(""); setPhase("TEAM"); }}
                className="rounded-xl bg-zinc-800 text-white font-black py-2.5 text-sm flex items-center justify-center gap-1"><Plus size={15} /> {t.yes}</button>
              <button data-testid="guided-more-no" onClick={() => setPhase("FINISH")}
                className="rounded-xl bg-volt text-black font-black py-2.5 text-sm">{t.no}</button>
            </div>
          </div>
        )}

        {/* ===== STEP 4: FINISH ===== */}
        {phase === "FINISH" && (
          <div className="space-y-4" data-testid="guided-finish">
            <p className="text-[11px] font-black tracking-widest text-volt uppercase">{t.stepFinish}</p>
            {games.length > 0 && (
              <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-2 space-y-1" data-testid="guided-summary">
                <p className="text-[10px] text-zinc-500 uppercase tracking-widest mb-1">{t.yourGames}</p>
                {games.map((g, i) => (
                  <div key={i} className="text-xs text-zinc-300 flex justify-between items-center">
                    <span>{g.home} - {g.away}: <b className="text-volt">{g.pick}</b>{g.odds ? ` @${g.odds}` : ""}</span>
                    <button data-testid={`guided-remove-${i}`} onClick={() => removeGame(i)} className="text-zinc-500 hover:text-red-400"><X size={13} /></button>
                  </div>
                ))}
              </div>
            )}

            {/* Sterne */}
            <div>
              <p className="text-xs text-zinc-400 mb-1.5">{t.stars}</p>
              <div className="flex flex-wrap gap-1">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                  <button key={n} data-testid={`guided-star-${n}`} onClick={() => setStars(n)}
                    className={`w-7 h-7 rounded-md flex items-center justify-center transition-colors ${n <= stars ? "bg-volt text-black" : "bg-zinc-800 text-zinc-500"}`}>
                    <Star size={13} fill={n <= stars ? "currentColor" : "none"} />
                  </button>
                ))}
              </div>
            </div>

            {/* Timing */}
            <div>
              <p className="text-xs text-zinc-400 mb-1.5">{t.timing}</p>
              <div className="grid grid-cols-3 gap-2">
                {[["live", t.live, Zap], ["today", t.today, Clock], ["later", t.later, CalendarClock]].map(([k, label, Icon]) => (
                  <button key={k} data-testid={`guided-timing-${k}`} onClick={() => setTiming(k)}
                    className={`rounded-xl py-2 text-xs font-black flex items-center justify-center gap-1 border transition-colors ${timing === k ? "bg-volt text-black border-volt" : "bg-zinc-900 text-zinc-400 border-zinc-700"}`}>
                    <Icon size={13} /> {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Text optional */}
            <textarea data-testid="guided-text" value={text} onChange={(e) => setText(e.target.value)} placeholder={t.textPh} rows={2}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2.5 text-sm text-white focus:border-volt outline-none resize-none" />

            {/* Bild optional */}
            <div>
              <label className="text-[11px] text-zinc-400 flex items-center gap-2 cursor-pointer">
                <input type="file" accept="image/*" multiple data-testid="guided-image" className="hidden"
                  onChange={(e) => setFiles(Array.from(e.target.files || []).slice(0, 4))} />
                <span className="rounded-lg bg-zinc-800 px-3 py-1.5 font-black">{t.addImg}</span>
                {files.length > 0 && <span className="text-zinc-500">{files.length} 📎 <button onClick={(e) => { e.preventDefault(); setFiles([]); }} className="underline">{t.remove}</button></span>}
              </label>
            </div>

            <button data-testid="guided-post" onClick={publish} disabled={publishing}
              className="w-full rounded-xl bg-volt text-black font-black py-3 text-sm disabled:opacity-50 flex items-center justify-center gap-2">
              {publishing ? <><Loader2 size={16} className="animate-spin" /> {t.posting}</> : t.post}
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}
