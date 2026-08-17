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
  const [soldJars, setSoldJars] = useState([]);
  const coins = userCoins;
  const owned = JAR_DEFS.filter(j => coins >= j.coins);
  const byId = (id) => JAR_DEFS.find(j => j.id === id);
  const tierCls = (t) => TIER_COLOR[t] || 'text-white';
  const sortedJars = [...JAR_DEFS].sort((a, b) => a.coins - b.coins);
  const jarFill = (j) => {
    const idx = sortedJars.findIndex(x => x.id === j.id);
    const next = sortedJars[idx + 1];
    if (!next) return 100;
    const span = next.coins - j.coins;
    if (span <= 0) return 100;
    return Math.max(0, Math.min(100, Math.round(((coins - j.coins) / span) * 100)));
  };
  const sellJar = async (e, j) => {
    e.stopPropagation();
    try {
      const { data } = await api.post('/jars/sell', { jar_id: j.id });
      setSoldJars((s) => [...s, j.id]);
      if (data.user) setUser(data.user);
      toast.success(`Jar verkauft: +${data.reward} Coins 💰`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Verkauf nicht möglich');
    }
  };

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
            <span className="text-[#D4FF32] font-black">✨ Neue Jars finden:</span> Du schaltest neue Jars durch <b>Coins</b> frei – je mehr Coins, desto seltener der Jar. Extra-Jars findest du durch <b>zufällige Besuche</b> der App und besonders durch <b>⭐ Sterne-Bewertungen</b>, die du bekommst. Tippe einen Jar an, um ihn ins Open Case zu legen.
          </div>
          <p className="text-[11px] text-zinc-500 mb-3">Deine Jars • {owned.length}/30</p>
          {note && <div className="text-[10px] text-red-400 mb-2 font-bold">{note}</div>}
          <div className="grid grid-cols-3 gap-3">
            {owned.map(j => {
              const inCase = openCase.includes(j.id);
              return (
                <button key={j.id} data-testid={`inv-jar-${j.id}`} onClick={() => addToCase(j)} disabled={inCase}
                  className="text-left bg-zinc-900 rounded-xl p-3 border border-zinc-800 relative hover:border-yellow-400/50 transition-colors disabled:cursor-default" style={{ boxShadow: `0 0 20px ${j.color}40` }}>
                  <div className="flex justify-between text-[8px]"><span className={tierCls(j.tier)}>{j.tier.toUpperCase()}</span><span className="text-zinc-600">{j.coins} Coins</span></div>
                  <div className="h-20 my-2 rounded-lg flex items-center justify-center" style={{ background: `${j.color}20` }}>
                    <JarImg jar={j} className="h-full object-contain" />
                  </div>
                  <div className="text-[10px] font-bold truncate">{j.name.toUpperCase()}</div>
                  {/* %-Füllstand */}
                  <div className="mt-1.5">
                    <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${jarFill(j)}%`, background: jarFill(j) >= 100 ? '#22c55e' : '#D4FF32' }} />
                    </div>
                    <div className="text-[8px] text-zinc-400 mt-0.5">{jarFill(j)}% voll{jarFill(j) >= 100 ? ' • verkaufbar 💰' : ''}</div>
                    {jarFill(j) >= 100 && (
                      soldJars.includes(j.id)
                        ? <div className="mt-1 text-[8px] text-zinc-500 font-bold">verkauft ✓</div>
                        : <div onClick={(e) => sellJar(e, j)} data-testid={`sell-jar-${j.id}`}
                            className="mt-1 text-center text-[9px] font-black text-black bg-[#22c55e] rounded-full py-1 hover:brightness-110 active:scale-95 transition-all cursor-pointer">
                            Jar verkaufen 💰
                          </div>
                    )}
                  </div>
                  {inCase
                    ? <div className="absolute top-2 right-2 text-[8px] font-black text-[#D4FF32]">IM CASE ✓</div>
                    : <div className="absolute top-2 right-2 text-[8px] text-zinc-500">+ Open Case</div>}
                </button>
              );
            })}
            {owned.length === 0 && <div className="col-span-3 text-center py-10 text-zinc-600 text-xs">Noch keine Jars – Start mit Common Glass (40 Coins)</div>}
          </div>
        </div>
      )}

      {/* JARDEX — alle 30, immer sichtbar, locked = opacity-40 */}
      {tab === 'JARDEX' && (
        <div>
          <p className="text-[11px] text-zinc-500 mb-3">Sammle alle 30 Jars • Alle Grafiken immer sichtbar • Je mehr Coins desto seltener</p>
          <div className="grid grid-cols-3 gap-2">
            {JAR_DEFS.map(j => {
              const unlocked = coins >= j.coins;
              return (
                <div key={j.id} data-testid={`dex-jar-${j.id}`} className={`rounded-xl p-2 border ${unlocked ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-950 border-zinc-900'}`}>
                  <div className="flex justify-between text-[7px]"><span className={tierCls(j.tier)}>{j.tier.toUpperCase()}</span><span className="text-zinc-600">{j.coins}</span></div>
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
