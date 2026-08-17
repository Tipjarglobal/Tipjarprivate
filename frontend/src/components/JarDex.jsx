import React, { useState, useEffect } from 'react';
import api from '../api';
import { toast } from 'sonner';
import { useAuth } from '../auth';
import { JAR_DEFS } from './AnimatedJar';

const TIER_COLOR = {
  common: 'text-zinc-400',
  uncommon: 'text-green-400',
  rare: 'text-blue-400',
  epic: 'text-purple-400',
  legendary: 'text-yellow-400',
  mystic: 'text-pink-400',
};

const sellReward = (j) => (j.coins || 0);   // Verkaufswert = Jar-Wert (Refund; +einmaliger Bonus im Backend)
const RewardBadge = ({ jar }) => (
  <span className="absolute top-1.5 right-1.5 z-10 inline-flex items-center gap-0.5 rounded-full bg-[#FFD447] text-black text-[8px] font-black px-1.5 py-0.5 shadow"
    title="Verkaufswert">
    💰 +{sellReward(jar).toLocaleString()}
  </span>
);

// Bild mit Fallback-Kette: open→closed→farbiger Initial-Block (fixt broken image bei Wood/Bamboo etc.)
function JarImg({ jar, open = false, className = "" }) {
  const chain = (open ? [jar.graphicOpen, jar.graphic] : [jar.graphic, jar.graphicOpen]).filter(Boolean);
  const [idx, setIdx] = useState(0);
  const src = chain[idx];
  if (!src) {
    return (
      <div className={`flex items-center justify-center w-full h-full rounded-lg ${className}`} style={{ background: jar.color }}>
        <span className="text-lg font-black text-black/70">{(jar.name || "?")[0]}</span>
      </div>
    );
  }
  return <img src={src} alt={jar.name} className={className} onError={() => setIdx((i) => i + 1)} />;
}

export default function Jardex({ userCoins = 0, userCredits = 0 }) {
  const { setUser } = useAuth();
  const [tab, setTab] = useState('INVENTORY');
  const [openCase, setOpenCase] = useState([]);
  const [note, setNote] = useState('');
  const [ownedIds, setOwnedIds] = useState(['common_glass']);
  const [soldJars, setSoldJars] = useState([]);
  const [nextJar, setNextJar] = useState(null);
  const coins = userCoins;
  const ownedSet = new Set(ownedIds);
  const owned = JAR_DEFS.filter(j => ownedSet.has(j.id));
  const byId = (id) => JAR_DEFS.find(j => j.id === id);
  const tierCls = (t) => TIER_COLOR[t] || 'text-white';
  const isOwned = (j) => ownedSet.has(j.id);
  const jarFill = (j) => (ownedSet.has(j.id) ? 100 : 0);   // besitzt = 100% voll, sonst gesperrt

  const loadState = () => api.get('/jars/state').then(r => {
    setOwnedIds(r.data?.owned_jars || ['common_glass']);
    setSoldJars(r.data?.sold_jars || []);
    setNextJar(r.data?.next_jar || null);
  }).catch(() => {});

  const acquireJar = async (e, j) => {
    e.stopPropagation();
    try {
      const { data } = await api.post('/jars/acquire', { jar_id: j.id });
      if (data.user) setUser(data.user);
      toast.success(`${j.name.toUpperCase()} freigeschaltet! (−${data.cost} 🪙)`);
      loadState();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Freischalten nicht möglich');
    }
  };

  const sellJar = async (e, j) => {
    e.stopPropagation();
    try {
      const { data } = await api.post('/jars/sell', { jar_id: j.id });
      if (data.user) setUser(data.user);
      toast.success(data.prestige > 0
        ? `Jar verkauft: +${data.reward} 🪙 (inkl. +${data.prestige} Bonus)`
        : `Jar verkauft: +${data.reward} 🪙`);
      loadState();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Verkauf nicht möglich');
    }
  };

  useEffect(() => { loadState(); }, []);
  useEffect(() => {
    const valid = new Set(JAR_DEFS.map(j => j.id));
    api.get('/jars/opencase').then(r => {
      const raw = r.data?.jar_ids || [];
      const ids = raw.filter(id => valid.has(id));   // veraltete IDs (frosted/cosmic) raus → kein leerer Slot
      setOpenCase(ids);
      if (ids.length !== raw.length) api.put('/jars/opencase', { jar_ids: ids }).catch(() => {});
    }).catch(() => {});
  }, []);

  const saveCase = (ids) => {
    setOpenCase(ids);
    api.put('/jars/opencase', { jar_ids: ids }).catch(() => {});
  };
  const addToCase = (j) => {
    if (openCase.includes(j.id)) return;
    if (openCase.length >= 3) { setNote('Max 3 offene Jars im Open Case!'); setTimeout(() => setNote(''), 2200); return; }
    saveCase([...openCase, j.id]);
  };
  const removeFromCase = (id) => saveCase(openCase.filter(x => x !== id));
  const showcase = [0, 1, 2].map(i => (openCase[i] != null ? byId(openCase[i]) : null));

  return (
    <div className="bg-black text-white p-4 font-mono" data-testid="jardex">
      {/* HEADER */}
      <div className="flex justify-between items-center mb-6 border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-2xl font-black tracking-[0.2em]">TIPJAR</h1>
          <p className="text-[10px] text-zinc-500">{owned.length}/30 Jars freigeschaltet</p>
        </div>
        <div className="bg-zinc-900 border border-yellow-500/30 px-4 py-2 rounded-full flex items-center gap-2">
          <span>🪙</span><span className="font-bold">{coins.toLocaleString()} Coins</span>
        </div>
      </div>

      {/* 3 TABS */}
      <div className="flex gap-2 mb-6">
        {['INVENTORY', 'JARDEX', 'OPEN CASE'].map(tk => (
          <button key={tk} data-testid={`jardex-tab-${tk.replace(' ', '-').toLowerCase()}`} onClick={() => setTab(tk)}
            className={`px-5 py-3 rounded-lg font-black text-xs tracking-widest ${tab === tk ? 'bg-yellow-400 text-black shadow-[0_0_15px_rgba(250,204,21,0.6)]' : 'bg-zinc-900 text-zinc-500 border border-zinc-800'}`}>
            {tk}
          </button>
        ))}
      </div>

      {/* INVENTORY — geschlossen mit Deckel, Front View */}
      {tab === 'INVENTORY' && (
        <div>
          <div className="mb-3 rounded-xl border border-[#D4FF32]/25 bg-[#D4FF32]/5 px-3 py-2.5 text-[11px] leading-relaxed text-zinc-300">
            <span className="text-[#D4FF32] font-black">🎮 So funktioniert die Sammlung:</span> Jeder Jar wird <b>der Reihe nach freigeschaltet</b> und kostet Coins (je seltener, desto teurer). Ein freigeschalteter Jar ist voll und du kannst ihn <b>verkaufen</b> – du bekommst die Coins zurück <b>plus einmaligen Bonus</b>. Coins verdienst du AFK, durch Sponsor-Klicks, ⭐ Bewertungen und Gewinne.
          </div>
          <p className="text-[11px] text-zinc-500 mb-3">Deine Jars • {owned.length}/30</p>
          {note && <div className="text-[10px] text-red-400 mb-2 font-bold">{note}</div>}
          <div className="grid grid-cols-3 gap-3">
            {[...JAR_DEFS].sort((a, b) => a.coins - b.coins).map(j => {
              const mine = isOwned(j);
              const inCase = openCase.includes(j.id);
              const canUnlock = !mine && j.id === nextJar;
              const affordable = coins >= (j.coins || 0);
              return (
                <div key={j.id} data-testid={`inv-jar-${j.id}`}
                  className={`text-left rounded-xl p-3 border relative transition-colors ${mine ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-950 border-zinc-900 opacity-80'}`}
                  style={mine ? { boxShadow: `0 0 20px ${j.color}40` } : {}}>
                  {mine && <RewardBadge jar={j} />}
                  {!mine && <span className="absolute top-1.5 right-1.5 z-10 text-[9px]">🔒</span>}
                  <div className="flex justify-between text-[8px] pr-14"><span className={tierCls(j.tier)}>{j.tier.toUpperCase()}</span><span className="text-zinc-600">{j.coins} 🪙</span></div>
                  <button onClick={() => mine && addToCase(j)} disabled={!mine || inCase} className="w-full h-20 my-2 rounded-lg flex items-center justify-center disabled:cursor-default" style={{ background: `${j.color}20` }}>
                    <JarImg jar={j} className={`h-full object-contain ${mine ? '' : 'opacity-30 grayscale'}`} />
                  </button>
                  <div className="text-[10px] font-bold truncate">{j.name.toUpperCase()}{mine && (inCase ? <span className="text-[#D4FF32]"> · IM CASE ✓</span> : <span className="text-zinc-500"> · + Open Case</span>)}</div>
                  {mine ? (
                    <div className="mt-1.5">
                      <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden"><div className="h-full rounded-full bg-[#22c55e]" style={{ width: '100%' }} /></div>
                      <div className="text-[8px] text-zinc-400 mt-0.5">100% voll • verkaufbar 💰</div>
                      <div onClick={(e) => sellJar(e, j)} data-testid={`sell-jar-${j.id}`}
                        className="mt-1 text-center text-[9px] font-black text-black bg-[#22c55e] rounded-full py-1 hover:brightness-110 active:scale-95 transition-all cursor-pointer">
                        Jar verkaufen 💰
                      </div>
                    </div>
                  ) : canUnlock ? (
                    <div onClick={(e) => acquireJar(e, j)} data-testid={`unlock-jar-${j.id}`}
                      className={`mt-1.5 text-center text-[9px] font-black rounded-full py-1.5 transition-all cursor-pointer ${affordable ? 'bg-[#D4FF32] text-black hover:brightness-110 active:scale-95' : 'bg-zinc-800 text-zinc-500'}`}>
                      🔓 Freischalten ({j.coins} 🪙)
                    </div>
                  ) : (
                    <div className="mt-1.5 text-center text-[8px] text-zinc-600 py-1.5">🔒 gesperrt</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* JARDEX — alle 30, immer sichtbar, locked = opacity-40 */}
      {tab === 'JARDEX' && (
        <div>
          <p className="text-[11px] text-zinc-500 mb-3">Sammle alle 30 Jars • Alle Grafiken immer sichtbar • Je mehr Coins desto seltener</p>
          <div className="grid grid-cols-3 gap-2">
            {JAR_DEFS.map(j => {
              const unlocked = isOwned(j);
              return (
                <div key={j.id} data-testid={`dex-jar-${j.id}`} className={`relative rounded-xl p-2 border ${unlocked ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-950 border-zinc-900'}`}>
                  {unlocked && <RewardBadge jar={j} />}
                  <div className="flex justify-between text-[7px] pr-12"><span className={tierCls(j.tier)}>{j.tier.toUpperCase()}</span><span className="text-zinc-600">{j.coins}</span></div>
                  <div className="h-16 my-1 rounded-lg flex items-center justify-center" style={{ background: unlocked ? `${j.color}15` : '#000' }}>
                    <JarImg jar={j} className={`h-full object-contain ${unlocked ? '' : 'opacity-40'}`} />
                  </div>
                  <div className="text-[8px] font-bold truncate">{j.name.toUpperCase()}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* OPEN CASE — offen ohne Deckel, Top View */}
      {tab === 'OPEN CASE' && (
        <div>
          <div className="mb-3 rounded-xl border border-[#D4FF32]/25 bg-[#D4FF32]/5 px-3 py-2.5 text-[11px] leading-relaxed text-zinc-300">
            <span className="text-[#D4FF32] font-black">💰 So funktioniert's:</span> Du verdienst automatisch <b>AFK Silver Coins</b> – und <b>Gold Coins</b>, sobald du auf einen Sponsor klickst. Deine Coins füllen dein aktives Jar. Der Balken zeigt, <b>wie voll</b> jedes Jar ist. Ein <b>volles Jar (100%)</b> kannst du <b>verkaufen</b>. Tippe ein Jar an, um es zurückzulegen.
          </div>
          <p className="text-[11px] text-zinc-500 mb-3">Dein aktives Set • {openCase.length}/3</p>
          {note && <div className="text-[10px] text-red-400 mb-2 font-bold">{note}</div>}
          <div className="grid grid-cols-3 gap-3">
            {showcase.map((j, i) => (
              <div key={i} className="bg-zinc-900 rounded-xl p-3 border border-zinc-800 h-44 flex flex-col">
                {j ? (
                  <button data-testid={`case-slot-${i}`} onClick={() => removeFromCase(j.id)} className="text-left flex-1 flex flex-col w-full">
                    <div className="text-[8px] text-zinc-500">{j.tier.toUpperCase()} • offen</div>
                    <div className="flex-1 flex items-center justify-center"><JarImg jar={j} open className="h-full object-contain" /></div>
                    <div className="text-[9px] font-bold truncate">{j.name.toUpperCase()}</div>
                    {/* %-Füllstand */}
                    <div className="mt-1 w-full">
                      <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${jarFill(j)}%`, background: jarFill(j) >= 100 ? '#22c55e' : '#D4FF32' }} />
                      </div>
                      <div className="text-[8px] mt-0.5" style={{ color: jarFill(j) >= 100 ? '#22c55e' : '#a1a1aa' }} data-testid={`case-fill-${i}`}>
                        {jarFill(j)}% voll{jarFill(j) >= 100 ? ' • verkaufbar 💰' : ''}
                      </div>
                      {jarFill(j) >= 100 && !soldJars.includes(j.id) && (
                        <div onClick={(e) => sellJar(e, j)} data-testid={`case-sell-${i}`}
                          className="mt-1 text-center text-[9px] font-black text-black bg-[#22c55e] rounded-full py-1 hover:brightness-110 active:scale-95 transition-all cursor-pointer">
                          Jar verkaufen 💰
                        </div>
                      )}
                    </div>
                    <div className="text-[7px] text-zinc-500 mt-0.5">tippen zum Zurücklegen</div>
                  </button>
                ) : (
                  <div className="flex-1 border-2 border-dashed border-zinc-700 rounded-lg flex flex-col items-center justify-center">
                    <span className="text-zinc-600">+</span><span className="text-[9px] text-zinc-600">LEER</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
