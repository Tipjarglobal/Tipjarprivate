import React, { useState, useEffect, useCallback, useRef } from 'react';
import api from '../api';
import { toast } from 'sonner';
import { useAuth } from '../auth';
import { JAR_DEFS } from './AnimatedJar';

// Grafik-Lookup: Katalog-ID -> vorhandene Jar-Grafik (Fallback: farbiger Block)
const GFX = {};
JAR_DEFS.forEach(j => { GFX[j.id] = j.graphic; });
GFX.glass = GFX.glass || GFX.common_glass;

const CAT_COLOR = { COMMON: '#9ca3af', UNCOMMON: '#34d399', RARE: '#60a5fa', LEGENDARY: '#fbbf24' };
const CATS = ['COMMON', 'UNCOMMON', 'RARE', 'LEGENDARY'];

// Sprache aus der App (kein Switcher mehr in Sub-Fenstern)
const T = {
  DE: {
    tabInv: 'INVENTORY', tabShop: 'SHOP', tabCase: 'OPEN CASE',
    buy: 'EINKAUFEN', sell: 'VERKAUFEN', balance: 'Guthaben', market: 'Marktübersicht', inv: 'Mein Inventar',
    kaufen: 'Kaufen', owned: 'In Besitz ✓', sellJar: 'Jar verkaufen', filling: 'füllt…', sellable: 'voll • verkaufbar',
    starterReady: 'Gratis-Starter • bereit', addCase: '+ Open Case', inCase: 'im Case ✓', maxCase: 'Max 3 Jars im Open Case!',
    empty: 'LEER', tapRemove: 'tippen zum Zurücklegen', activeSet: 'Dein aktives Set',
    invHelp: 'Hier siehst du alle Jars, die dir gehören. Ein volles Jar (100%) kannst du verkaufen 💰. Tippe „+ Open Case", um ein Jar in dein aktives 3er-Set zu legen. Das Glass-Jar bekommst du gratis.',
    caseHelp: 'Dein aktives 3er-Set. Jedes Jar füllt sich langsam von selbst. Ein volles Jar (100%) kannst du direkt verkaufen. Tippe ein Jar an, um es zurückzulegen.',
    buyHelp: 'Hier kaufst du Jars. Kaufen kostet 25% weniger als der Verkaufswert – der Gewinn ist eingebaut. Alle Jars sind sofort verfügbar. Nach dem Kauf startet das Jar bei 0% und füllt sich ganz langsam von selbst wieder auf.',
    sellHelp: 'Hier verkaufst du deine Jars. Verkaufen geht NUR bei 100%. Du bekommst den vollen Wert – das Jar bleibt in deinem Besitz und füllt sich danach wieder von 0% auf.',
    dropHelp: '🎁 Bonus: Je mehr du bewertest und Tipps postest, desto eher findest du zufällig ein GRATIS-Jar, das dir noch fehlt.',
    noOwn: 'Du besitzt noch keine Jars dieser Kategorie – kaufe zuerst im Tab EINKAUFEN.',
    noInv: 'Du besitzt noch keine Jars. Kaufe welche im SHOP.',
    notEnough: 'Nicht genug Coins', bought: 'Gekauft', sold: 'Verkauft', drop: 'Gratis-Jar gefunden', jars: 'Jars',
  },
  EN: {
    tabInv: 'INVENTORY', tabShop: 'SHOP', tabCase: 'OPEN CASE',
    buy: 'BUY', sell: 'SELL', balance: 'Balance', market: 'Market', inv: 'My Inventory',
    kaufen: 'Buy', owned: 'Owned ✓', sellJar: 'Sell jar', filling: 'filling…', sellable: 'full • sellable',
    starterReady: 'Free starter • ready', addCase: '+ Open Case', inCase: 'in case ✓', maxCase: 'Max 3 jars in Open Case!',
    empty: 'EMPTY', tapRemove: 'tap to put back', activeSet: 'Your active set',
    invHelp: 'All jars you own. A full jar (100%) can be sold 💰. Tap "+ Open Case" to add a jar to your active set of 3. The Glass jar is free.',
    caseHelp: 'Your active set of 3. Each jar slowly refills by itself. A full jar (100%) can be sold. Tap a jar to put it back.',
    buyHelp: 'Buy jars here. Buying costs 25% less than the sell value – the profit is built in. All jars are available instantly. After buying, the jar starts at 0% and slowly refills by itself.',
    sellHelp: 'Sell your jars here. Selling only works at 100%. You get the full value and KEEP the jar – it refills from 0% again.',
    dropHelp: '🎁 Bonus: the more you rate and post tips, the sooner you randomly find a FREE jar you\'re missing.',
    noOwn: 'You don\'t own any jars in this category yet – buy some in the BUY tab first.',
    noInv: 'You don\'t own any jars yet. Buy some in the SHOP.',
    notEnough: 'Not enough coins', bought: 'Bought', sold: 'Sold', drop: 'Free jar found', jars: 'Jars',
  },
};

function JarIcon({ jar, size = 'h-16' }) {
  const [broken, setBroken] = useState(false);
  const src = GFX[jar.id];
  if (!src || broken) {
    return (
      <div className={`${size} w-full rounded-lg flex items-center justify-center`}
        style={{ background: `${CAT_COLOR[jar.category]}22` }}>
        <span className="text-lg font-black" style={{ color: CAT_COLOR[jar.category] }}>{jar.name[0]}</span>
      </div>
    );
  }
  return <img src={src} alt={jar.name} className={`${size} w-full object-contain`} onError={() => setBroken(true)} />;
}

export default function Jardex() {
  const { setUser } = useAuth();
  const langCode = (typeof localStorage !== 'undefined' && (localStorage.getItem('tj_lang') || '').toUpperCase()) || 'DE';
  const t = T[langCode] || T.DE;

  const [tab, setTab] = useState('INVENTORY');   // INVENTORY | SHOP | OPEN CASE
  const [sub, setSub] = useState('BUY');          // Shop: BUY | SELL
  const [cat, setCat] = useState('COMMON');
  const [balance, setBalance] = useState(0);
  const [jars, setJars] = useState([]);
  const [openCase, setOpenCase] = useState([]);
  const [busy, setBusy] = useState('');
  const [note, setNote] = useState('');

  const byId = useCallback((id) => jars.find(j => j.id === id), [jars]);

  const load = useCallback(async (announce = false) => {
    try {
      const { data } = await api.get('/jars/shop');
      setBalance(data.balance);
      setJars(data.jars);
      if (announce && data.new_drops?.length) data.new_drops.forEach(n => toast.success(`🎉 ${t.drop}: ${n}!`));
    } catch (e) { /* silent */ }
  }, [t]);

  useEffect(() => { load(true); }, [load]);
  useEffect(() => {
    const validRef = new Set();
    api.get('/jars/opencase').then(r => {
      const raw = r.data?.jar_ids || [];
      setOpenCase(raw);
    }).catch(() => {});
    const id = setInterval(() => load(true), 5000);
    return () => clearInterval(id);
  }, [load]);

  // veraltete Open-Case-IDs (aus altem Jar-Set) rausfiltern, sobald jars geladen sind
  useEffect(() => {
    if (!jars.length || !openCase.length) return;
    const valid = new Set(jars.map(j => j.id));
    const cleaned = openCase.filter(id => valid.has(id));
    if (cleaned.length !== openCase.length) {
      setOpenCase(cleaned);
      api.put('/jars/opencase', { jar_ids: cleaned }).catch(() => {});
    }
  }, [jars]); // eslint-disable-line

  const saveCase = (ids) => { setOpenCase(ids); api.put('/jars/opencase', { jar_ids: ids }).catch(() => {}); };
  const addToCase = (j) => {
    if (openCase.includes(j.id)) return;
    if (openCase.length >= 3) { setNote(t.maxCase); setTimeout(() => setNote(''), 2200); return; }
    saveCase([...openCase, j.id]);
  };
  const removeFromCase = (id) => saveCase(openCase.filter(x => x !== id));

  const buy = async (j) => {
    setBusy(j.id);
    try {
      const { data } = await api.post('/jars/shop/buy', { jar_id: j.id });
      if (data.user) setUser(data.user);
      toast.success(`${t.bought}: ${j.name} (−${data.price} 🪙)`);
      await load();
    } catch (err) { toast.error(err?.response?.data?.detail || t.notEnough); }
    finally { setBusy(''); }
  };
  const sell = async (j) => {
    setBusy(j.id);
    try {
      const { data } = await api.post('/jars/shop/sell', { jar_id: j.id });
      if (data.user) setUser(data.user);
      toast.success(`${t.sold}: ${j.name} (+${data.reward} 🪙)`);
      await load();
    } catch (err) { toast.error(err?.response?.data?.detail || 'Fehler'); }
    finally { setBusy(''); }
  };

  const ownedAll = jars.filter(j => j.owned);
  const inCat = jars.filter(j => j.category === cat);
  const ownedInCat = inCat.filter(j => j.owned);
  const showcase = [0, 1, 2].map(i => (openCase[i] != null ? byId(openCase[i]) : null));

  const FillBar = ({ j }) => (
    <>
      <div className="mt-1 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${j.fill}%`, background: j.fill >= 100 ? '#00ff88' : '#d4ff00' }} />
      </div>
      <div className="text-[8px] mt-0.5" style={{ color: j.fill >= 100 ? '#00ff88' : '#a1a1aa' }}>
        {j.starter && j.fill >= 100 ? t.starterReady : `${j.fill}% ${j.fill >= 100 ? `• ${t.sellable}` : `• ${t.filling}`}`}
      </div>
    </>
  );

  return (
    <div className="bg-black text-white p-4 font-mono" data-testid="jardex">
      {/* HEADER */}
      <div className="flex justify-between items-center mb-4 border-b border-zinc-800 pb-4 gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-black tracking-[0.2em]">TIPJAR</h1>
          <p className="text-[10px] text-zinc-500">{ownedAll.length}/30 {t.jars}</p>
        </div>
        <div className="bg-zinc-900 border border-yellow-500/30 px-4 py-2 rounded-full flex items-center gap-2" data-testid="shop-balance">
          <span>🪙</span><span className="font-bold">{balance.toLocaleString()}</span>
          <span className="text-[9px] text-zinc-500 uppercase">{t.balance}</span>
        </div>
      </div>

      {/* 3 TOP TABS: INVENTORY | SHOP | OPEN CASE */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {[['INVENTORY', t.tabInv], ['SHOP', t.tabShop], ['OPEN CASE', t.tabCase]].map(([k, label]) => (
          <button key={k} data-testid={`jardex-tab-${k.replace(' ', '-').toLowerCase()}`} onClick={() => setTab(k)}
            className={`py-3 rounded-lg font-black text-[11px] tracking-widest transition-all ${tab === k ? 'bg-yellow-400 text-black shadow-[0_0_15px_rgba(250,204,21,0.6)]' : 'bg-zinc-900 text-zinc-500 border border-zinc-800'}`}>
            {label}
          </button>
        ))}
      </div>

      {/* ===================== INVENTORY ===================== */}
      {tab === 'INVENTORY' && (
        <div>
          <div className="mb-3 rounded-xl border border-[#D4FF32]/25 bg-[#D4FF32]/5 px-3 py-2.5 text-[11px] leading-relaxed text-zinc-300" data-testid="inv-help">
            {t.invHelp}
          </div>
          {note && <div className="text-[10px] text-red-400 mb-2 font-bold">{note}</div>}
          {ownedAll.length === 0 ? (
            <div className="text-[11px] text-zinc-500 py-8 text-center border border-dashed border-zinc-800 rounded-xl">{t.noInv}</div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {ownedAll.map(j => {
                const inCaseAlready = openCase.includes(j.id);
                return (
                  <div key={j.id} data-testid={`inv-jar-${j.id}`} className="rounded-xl p-3 border bg-zinc-900" style={{ borderColor: `${CAT_COLOR[j.category]}40` }}>
                    <div className="flex justify-between text-[8px] mb-1">
                      <span className="font-black" style={{ color: CAT_COLOR[j.category] }}>{j.category}</span>
                      <span className="text-[#FFD447] font-black">💰 {j.sellReward.toLocaleString()}</span>
                    </div>
                    <div className="h-16 my-1 flex items-center justify-center"><JarIcon jar={j} /></div>
                    <div className="text-[10px] font-bold truncate">{j.name.toUpperCase()}</div>
                    <FillBar j={j} />
                    <button onClick={() => addToCase(j)} disabled={inCaseAlready} data-testid={`inv-addcase-${j.id}`}
                      className="mt-1.5 w-full text-[9px] font-black rounded-full py-1.5 bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-40 transition-all">
                      {inCaseAlready ? t.inCase : t.addCase}
                    </button>
                    {j.fill >= 100 && (
                      <button onClick={() => sell(j)} disabled={busy === j.id} data-testid={`inv-sell-${j.id}`}
                        className="mt-1 w-full text-[9px] font-black rounded-full py-1.5 bg-[#00ff88] text-black hover:brightness-110 active:scale-95 transition-all">
                        {t.sellJar} 💰
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ===================== SHOP ===================== */}
      {tab === 'SHOP' && (
        <div>
          {/* Sub-Tabs EINKAUFEN / VERKAUFEN */}
          <div className="grid grid-cols-2 gap-2 mb-3">
            <button onClick={() => setSub('BUY')} data-testid="shop-subtab-buy"
              className={`py-3 rounded-xl font-black text-xs tracking-widest transition-all ${sub === 'BUY' ? 'bg-[#d4ff00] text-black shadow-[0_0_15px_rgba(212,255,0,0.5)]' : 'bg-zinc-900 text-zinc-500 border border-zinc-800'}`}>
              🛒 {t.buy}
            </button>
            <button onClick={() => setSub('SELL')} data-testid="shop-subtab-sell"
              className={`py-3 rounded-xl font-black text-xs tracking-widest transition-all ${sub === 'SELL' ? 'bg-[#00ff88] text-black shadow-[0_0_15px_rgba(0,255,136,0.5)]' : 'bg-zinc-900 text-zinc-500 border border-zinc-800'}`}>
              💰 {t.sell}
            </button>
          </div>
          {/* Kategorien */}
          <div className="flex gap-2 mb-3 flex-wrap">
            {CATS.map(c => (
              <button key={c} onClick={() => setCat(c)} data-testid={`shop-cat-${c.toLowerCase()}`}
                className={`px-3 py-2 rounded-lg font-black text-[10px] tracking-widest border ${cat === c ? 'text-black' : 'bg-zinc-900 text-zinc-400 border-zinc-800'}`}
                style={cat === c ? { background: CAT_COLOR[c], borderColor: CAT_COLOR[c] } : {}}>
                {c}
              </button>
            ))}
          </div>
          {/* Erklärungstext */}
          <div className="mb-3 rounded-xl border px-3 py-2.5 text-[11px] leading-relaxed" data-testid="shop-help"
            style={{ borderColor: `${sub === 'BUY' ? '#d4ff00' : '#00ff88'}40`, background: `${sub === 'BUY' ? '#d4ff00' : '#00ff88'}0d` }}>
            <p className="text-zinc-300">{sub === 'BUY' ? t.buyHelp : t.sellHelp}</p>
            <p className="text-zinc-500 mt-1.5">{t.dropHelp}</p>
          </div>

          {sub === 'BUY' ? (
            <>
              <p className="text-[11px] text-zinc-500 mb-2 uppercase tracking-widest">{t.market} · {cat}</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {inCat.map(j => (
                  <div key={j.id} data-testid={`shop-card-${j.id}`} className="rounded-xl p-3 border bg-zinc-950" style={{ borderColor: `${CAT_COLOR[cat]}40` }}>
                    <div className="flex justify-between text-[8px] mb-1">
                      <span className="font-black" style={{ color: CAT_COLOR[cat] }}>{cat}</span>
                      <span className="text-[#FFD447] font-black">💰 {j.sellReward.toLocaleString()}</span>
                    </div>
                    <div className="h-16 my-1 flex items-center justify-center"><JarIcon jar={j} /></div>
                    <div className="text-[11px] font-bold truncate">{j.name.toUpperCase()}</div>
                    {j.owned ? (
                      <>
                        <FillBar j={j} />
                        <button disabled className="mt-1.5 w-full text-[9px] font-black rounded-full py-2 bg-zinc-800 text-zinc-500" data-testid={`shop-owned-${j.id}`}>
                          {t.owned}
                        </button>
                      </>
                    ) : (
                      <button onClick={() => buy(j)} disabled={busy === j.id || balance < j.buyPrice} data-testid={`shop-buy-${j.id}`}
                        className="mt-2 w-full text-[10px] font-black rounded-full py-2.5 bg-[#d4ff00] text-black hover:brightness-110 active:scale-95 transition-all disabled:opacity-40">
                        {t.kaufen} ({j.buyPrice.toLocaleString()} 🪙)
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              <p className="text-[11px] text-zinc-500 mb-2 uppercase tracking-widest">{t.inv} · {cat}</p>
              {ownedInCat.length === 0 ? (
                <div className="text-[11px] text-zinc-500 py-8 text-center border border-dashed border-zinc-800 rounded-xl" data-testid="shop-empty">{t.noOwn}</div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {ownedInCat.map(j => (
                    <div key={j.id} data-testid={`shop-sellcard-${j.id}`} className="rounded-xl p-3 border bg-zinc-900" style={{ borderColor: '#00ff8840' }}>
                      <div className="flex justify-between text-[8px] mb-1">
                        <span className="font-black" style={{ color: CAT_COLOR[cat] }}>{cat}</span>
                        <span className="text-[#FFD447] font-black">💰 {j.sellReward.toLocaleString()}</span>
                      </div>
                      <div className="h-14 my-1 flex items-center justify-center"><JarIcon jar={j} size="h-14" /></div>
                      <div className="text-[10px] font-bold truncate">{j.name.toUpperCase()}</div>
                      <FillBar j={j} />
                      <button onClick={() => sell(j)} disabled={busy === j.id || j.fill < 100} data-testid={`shop-sell-${j.id}`}
                        className="mt-1.5 w-full text-[10px] font-black rounded-full py-2.5 transition-all disabled:opacity-40 disabled:bg-zinc-800 disabled:text-zinc-500"
                        style={j.fill >= 100 ? { background: '#00ff88', color: '#000' } : {}}>
                        {j.fill >= 100 ? `${t.sellJar} 💰 +${j.sellReward.toLocaleString()}` : `${t.filling} ${j.fill}%`}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ===================== OPEN CASE ===================== */}
      {tab === 'OPEN CASE' && (
        <div>
          <div className="mb-3 rounded-xl border border-[#D4FF32]/25 bg-[#D4FF32]/5 px-3 py-2.5 text-[11px] leading-relaxed text-zinc-300" data-testid="case-help">
            {t.caseHelp}
          </div>
          <p className="text-[11px] text-zinc-500 mb-3">{t.activeSet} • {openCase.length}/3</p>
          {note && <div className="text-[10px] text-red-400 mb-2 font-bold">{note}</div>}
          <div className="grid grid-cols-3 gap-3">
            {showcase.map((j, i) => (
              <div key={i} className="bg-zinc-900 rounded-xl p-3 border border-zinc-800 h-44 flex flex-col">
                {j ? (
                  <button data-testid={`case-slot-${i}`} onClick={() => removeFromCase(j.id)} className="text-left flex-1 flex flex-col w-full">
                    <div className="text-[8px] text-zinc-500">{j.category}</div>
                    <div className="flex-1 flex items-center justify-center"><JarIcon jar={j} size="h-full" /></div>
                    <div className="text-[9px] font-bold truncate">{j.name.toUpperCase()}</div>
                    <div className="w-full">
                      <FillBar j={j} />
                      {j.fill >= 100 && (
                        <div onClick={(e) => { e.stopPropagation(); sell(j); }} data-testid={`case-sell-${i}`}
                          className="mt-1 text-center text-[9px] font-black text-black bg-[#00ff88] rounded-full py-1 hover:brightness-110 active:scale-95 transition-all cursor-pointer">
                          {t.sellJar} 💰
                        </div>
                      )}
                    </div>
                    <div className="text-[7px] text-zinc-500 mt-0.5">{t.tapRemove}</div>
                  </button>
                ) : (
                  <div className="flex-1 border-2 border-dashed border-zinc-700 rounded-lg flex flex-col items-center justify-center">
                    <span className="text-zinc-600">+</span><span className="text-[9px] text-zinc-600">{t.empty}</span>
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
