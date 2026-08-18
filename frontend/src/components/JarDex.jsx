import React, { useState, useEffect, useCallback, useRef } from 'react';
import api from '../api';
import { toast } from 'sonner';
import { useAuth } from '../auth';
import { JAR_DEFS } from './AnimatedJar';

// Graphik-Lookup: Katalog-ID -> vorhandene Jar-Grafik (Fallback: farbiger Block)
const GFX = {};
JAR_DEFS.forEach(j => { GFX[j.id] = j.graphic; });
GFX.glass = GFX.glass || GFX.common_glass;

const CAT_COLOR = { COMMON: '#9ca3af', UNCOMMON: '#34d399', RARE: '#60a5fa', LEGENDARY: '#fbbf24' };
const CATS = ['COMMON', 'UNCOMMON', 'RARE', 'LEGENDARY'];

const LANGS = ['DE', 'EN', 'ES', 'FR', 'IT', 'PT', 'TR', 'PL'];
const T = {
  DE: { shop: 'SHOP', buy: 'EINKAUFEN', sell: 'VERKAUFEN', balance: 'Guthaben', market: 'Marktübersicht', inv: 'Mein Inventar',
    kaufen: 'Kaufen', owned: 'In Besitz ✓', sellJar: 'Jar verkaufen', filling: 'füllt…', sellable: 'voll • verkaufbar',
    noOwn: 'Du besitzt noch keine Jars dieser Kategorie – kaufe zuerst im Tab EINKAUFEN.',
    tabBuyHelp: 'Hier kaufst du Jars. Kaufen kostet 25% weniger als der Verkaufswert – der Gewinn ist eingebaut. Alle Jars sind sofort verfügbar. Nach dem Kauf startet das Jar bei 0% und füllt sich ganz langsam von selbst wieder auf.',
    tabSellHelp: 'Hier verkaufst du deine Jars. Verkaufen geht NUR bei 100%. Beim Verkauf bekommst du den vollen Wert – das Jar bleibt in deinem Besitz und füllt sich danach wieder von 0% auf. So verdienst du immer wieder, aber gemächlich.',
    dropHelp: '🎁 Bonus: Je mehr du bewertest und Tipps postest, desto eher findest du zufällig ein GRATIS-Jar, das dir noch fehlt.',
    notEnough: 'Nicht genug Coins', bought: 'Gekauft', sold: 'Verkauft', drop: 'Gratis-Jar gefunden' },
  EN: { shop: 'SHOP', buy: 'BUY', sell: 'SELL', balance: 'Balance', market: 'Market', inv: 'My Inventory',
    kaufen: 'Buy', owned: 'Owned ✓', sellJar: 'Sell jar', filling: 'filling…', sellable: 'full • sellable',
    noOwn: 'You don\'t own any jars in this category yet – buy some in the BUY tab first.',
    tabBuyHelp: 'Buy jars here. Buying costs 25% less than the sell value – the profit is built in. All jars are available instantly. After buying, the jar starts at 0% and slowly refills by itself.',
    tabSellHelp: 'Sell your jars here. Selling only works at 100%. You get the full value and KEEP the jar – it refills from 0% again. Steady, repeatable income.',
    dropHelp: '🎁 Bonus: the more you rate and post tips, the sooner you randomly find a FREE jar you\'re missing.',
    notEnough: 'Not enough coins', bought: 'Bought', sold: 'Sold', drop: 'Free jar found' },
  ES: { shop: 'TIENDA', buy: 'COMPRAR', sell: 'VENDER', balance: 'Saldo', market: 'Mercado', inv: 'Mi inventario',
    kaufen: 'Comprar', owned: 'En posesión ✓', sellJar: 'Vender jar', filling: 'llenando…', sellable: 'lleno • vendible',
    noOwn: 'Aún no tienes jars de esta categoría – compra primero en COMPRAR.',
    tabBuyHelp: 'Compra jars aquí. Comprar cuesta 25% menos que el valor de venta – la ganancia está incluida. Todos disponibles al instante. Tras comprar, el jar empieza en 0% y se rellena solo muy despacio.',
    tabSellHelp: 'Vende tus jars aquí. Solo se puede vender al 100%. Recibes el valor completo y CONSERVAS el jar – se rellena desde 0% otra vez.',
    dropHelp: '🎁 Bonus: cuanto más valoras y publicas, antes encuentras al azar un jar GRATIS que te falta.',
    notEnough: 'Monedas insuficientes', bought: 'Comprado', sold: 'Vendido', drop: 'Jar gratis encontrado' },
  FR: { shop: 'BOUTIQUE', buy: 'ACHETER', sell: 'VENDRE', balance: 'Solde', market: 'Marché', inv: 'Mon inventaire',
    kaufen: 'Acheter', owned: 'Possédé ✓', sellJar: 'Vendre', filling: 'remplissage…', sellable: 'plein • vendable',
    noOwn: 'Aucun jar dans cette catégorie – achète d\'abord dans ACHETER.',
    tabBuyHelp: 'Achète des jars ici. L\'achat coûte 25% de moins que la valeur de vente – le profit est inclus. Tous disponibles. Après l\'achat, le jar part de 0% et se remplit lentement tout seul.',
    tabSellHelp: 'Vends tes jars ici. Vente uniquement à 100%. Tu reçois la valeur totale et GARDES le jar – il se remplit de nouveau depuis 0%.',
    dropHelp: '🎁 Bonus : plus tu notes et publies, plus vite tu trouves au hasard un jar GRATUIT qui te manque.',
    notEnough: 'Pas assez de pièces', bought: 'Acheté', sold: 'Vendu', drop: 'Jar gratuit trouvé' },
  IT: { shop: 'NEGOZIO', buy: 'COMPRA', sell: 'VENDI', balance: 'Saldo', market: 'Mercato', inv: 'Inventario',
    kaufen: 'Compra', owned: 'In possesso ✓', sellJar: 'Vendi', filling: 'riempimento…', sellable: 'pieno • vendibile',
    noOwn: 'Non possiedi jar in questa categoria – compra prima in COMPRA.',
    tabBuyHelp: 'Compra jar qui. Comprare costa il 25% in meno del valore di vendita – il profitto è incluso. Tutti disponibili subito. Dopo l\'acquisto il jar parte da 0% e si riempie lentamente da solo.',
    tabSellHelp: 'Vendi i tuoi jar qui. Vendita solo al 100%. Ricevi il valore pieno e MANTIENI il jar – si riempie di nuovo da 0%.',
    dropHelp: '🎁 Bonus: più valuti e pubblichi, prima trovi a caso un jar GRATIS che ti manca.',
    notEnough: 'Monete insufficienti', bought: 'Comprato', sold: 'Venduto', drop: 'Jar gratis trovato' },
  PT: { shop: 'LOJA', buy: 'COMPRAR', sell: 'VENDER', balance: 'Saldo', market: 'Mercado', inv: 'Meu inventário',
    kaufen: 'Comprar', owned: 'Em posse ✓', sellJar: 'Vender', filling: 'a encher…', sellable: 'cheio • vendível',
    noOwn: 'Ainda não tens jars desta categoria – compra primeiro em COMPRAR.',
    tabBuyHelp: 'Compra jars aqui. Comprar custa 25% menos que o valor de venda – o lucro está incluído. Todos disponíveis já. Após comprar, o jar começa em 0% e enche-se lentamente sozinho.',
    tabSellHelp: 'Vende os teus jars aqui. Venda só a 100%. Recebes o valor total e MANTÉNS o jar – enche de novo a partir de 0%.',
    dropHelp: '🎁 Bónus: quanto mais avalias e publicas, mais cedo encontras ao acaso um jar GRÁTIS que te falta.',
    notEnough: 'Moedas insuficientes', bought: 'Comprado', sold: 'Vendido', drop: 'Jar grátis encontrado' },
  TR: { shop: 'MAĞAZA', buy: 'SATIN AL', sell: 'SAT', balance: 'Bakiye', market: 'Piyasa', inv: 'Envanterim',
    kaufen: 'Al', owned: 'Sahipsin ✓', sellJar: 'Jar sat', filling: 'doluyor…', sellable: 'dolu • satılabilir',
    noOwn: 'Bu kategoride jar\'ın yok – önce SATIN AL sekmesinden al.',
    tabBuyHelp: 'Jarları buradan al. Almak, satış değerinden %25 daha ucuz – kâr baştan içinde. Hepsi anında hazır. Aldıktan sonra jar %0\'dan başlar ve kendiliğinden çok yavaş dolar.',
    tabSellHelp: 'Jarlarını buradan sat. Satış sadece %100\'de. Tam değeri alırsın ve jar SENDE kalır – tekrar %0\'dan dolar.',
    dropHelp: '🎁 Bonus: ne kadar çok puan verir ve tahmin paylaşırsan, eksik bir jar\'ı o kadar erken ÜCRETSİZ bulursun.',
    notEnough: 'Yetersiz jeton', bought: 'Alındı', sold: 'Satıldı', drop: 'Ücretsiz jar bulundu' },
  PL: { shop: 'SKLEP', buy: 'KUP', sell: 'SPRZEDAJ', balance: 'Saldo', market: 'Rynek', inv: 'Mój ekwipunek',
    kaufen: 'Kup', owned: 'Posiadane ✓', sellJar: 'Sprzedaj', filling: 'napełnia…', sellable: 'pełny • do sprzedaży',
    noOwn: 'Nie masz jeszcze jarów w tej kategorii – najpierw kup w zakładce KUP.',
    tabBuyHelp: 'Kupuj jary tutaj. Kupno kosztuje 25% mniej niż wartość sprzedaży – zysk jest wbudowany. Wszystkie dostępne od razu. Po zakupie jar startuje od 0% i powoli napełnia się sam.',
    tabSellHelp: 'Sprzedawaj jary tutaj. Sprzedaż tylko przy 100%. Dostajesz pełną wartość i ZACHOWUJESZ jar – napełnia się znów od 0%.',
    dropHelp: '🎁 Bonus: im więcej oceniasz i publikujesz, tym szybciej losowo znajdziesz DARMOWY jar, którego ci brakuje.',
    notEnough: 'Za mało monet', bought: 'Kupiono', sold: 'Sprzedano', drop: 'Znaleziono darmowy jar' },
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
  const [lang, setLang] = useState(() => localStorage.getItem('shop_lang') || 'DE');
  const [cat, setCat] = useState('COMMON');
  const [sub, setSub] = useState('BUY');   // BUY | SELL
  const [balance, setBalance] = useState(0);
  const [jars, setJars] = useState([]);
  const [busy, setBusy] = useState('');
  const t = T[lang] || T.DE;
  const seen = useRef(false);

  const load = useCallback(async (announce = false) => {
    try {
      const { data } = await api.get('/jars/shop');
      setBalance(data.balance);
      setJars(data.jars);
      if (announce && data.new_drops?.length) {
        data.new_drops.forEach(n => toast.success(`🎉 ${t.drop}: ${n}!`));
      }
    } catch (e) { /* silent */ }
  }, [t]);

  useEffect(() => { load(true); seen.current = true; }, [load]);
  useEffect(() => {
    const id = setInterval(() => load(true), 5000);   // Auto-Fill live aktualisieren
    return () => clearInterval(id);
  }, [load]);

  const setLng = (l) => { setLang(l); localStorage.setItem('shop_lang', l); };

  const buy = async (j) => {
    setBusy(j.id);
    try {
      const { data } = await api.post('/jars/shop/buy', { jar_id: j.id });
      if (data.user) setUser(data.user);
      toast.success(`${t.bought}: ${j.name} (−${j.buyPrice} 🪙)`);
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t.notEnough);
    } finally { setBusy(''); }
  };

  const sell = async (j) => {
    setBusy(j.id);
    try {
      const { data } = await api.post('/jars/shop/sell', { jar_id: j.id });
      if (data.user) setUser(data.user);
      toast.success(`${t.sold}: ${j.name} (+${data.reward} 🪙)`);
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Fehler');
    } finally { setBusy(''); }
  };

  const inCat = jars.filter(j => j.category === cat);
  const ownedInCat = inCat.filter(j => j.owned);

  return (
    <div className="bg-black text-white p-4 font-mono" data-testid="jar-shop">
      {/* HEADER */}
      <div className="flex justify-between items-center mb-4 border-b border-zinc-800 pb-4 gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-black tracking-[0.2em]">TIPJAR {t.shop}</h1>
          <p className="text-[10px] text-zinc-500">{jars.filter(j => j.owned).length}/30 Jars</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="bg-zinc-900 border border-yellow-500/30 px-4 py-2 rounded-full flex items-center gap-2"
            data-testid="shop-balance">
            <span>🪙</span><span className="font-bold">{balance.toLocaleString()}</span>
            <span className="text-[9px] text-zinc-500 uppercase">{t.balance}</span>
          </div>
          <div className="flex gap-1 flex-wrap">
            {LANGS.map(l => (
              <button key={l} onClick={() => setLng(l)} data-testid={`shop-lang-${l}`}
                className={`text-[9px] font-black px-2 py-1 rounded-full ${lang === l ? 'bg-[#d4ff00] text-black' : 'bg-zinc-900 text-zinc-500 border border-zinc-800'}`}>{l}</button>
            ))}
          </div>
        </div>
      </div>

      {/* SUB-TABS: EINKAUFEN / VERKAUFEN */}
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

      {/* CATEGORY TABS */}
      <div className="flex gap-2 mb-3 flex-wrap">
        {CATS.map(c => (
          <button key={c} onClick={() => setCat(c)} data-testid={`shop-cat-${c.toLowerCase()}`}
            className={`px-3 py-2 rounded-lg font-black text-[10px] tracking-widest border ${cat === c ? 'text-black' : 'bg-zinc-900 text-zinc-400 border-zinc-800'}`}
            style={cat === c ? { background: CAT_COLOR[c], borderColor: CAT_COLOR[c] } : {}}>
            {c}
          </button>
        ))}
      </div>

      {/* ERKLÄRUNGSTEXT pro Tab */}
      <div className="mb-3 rounded-xl border px-3 py-2.5 text-[11px] leading-relaxed"
        style={{ borderColor: `${sub === 'BUY' ? '#d4ff00' : '#00ff88'}40`, background: `${sub === 'BUY' ? '#d4ff00' : '#00ff88'}0d` }}
        data-testid="shop-help">
        <p className="text-zinc-300">{sub === 'BUY' ? t.tabBuyHelp : t.tabSellHelp}</p>
        <p className="text-zinc-500 mt-1.5">{t.dropHelp}</p>
      </div>

      {/* GRID */}
      {sub === 'BUY' ? (
        <>
          <p className="text-[11px] text-zinc-500 mb-2 uppercase tracking-widest">{t.market} · {cat}</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {inCat.map(j => (
              <div key={j.id} data-testid={`shop-card-${j.id}`}
                className="rounded-xl p-3 border bg-zinc-950 relative"
                style={{ borderColor: `${CAT_COLOR[cat]}40` }}>
                <div className="flex justify-between text-[8px] mb-1">
                  <span className="font-black" style={{ color: CAT_COLOR[cat] }}>{cat}</span>
                  <span className="text-[#FFD447] font-black">💰 {j.sellReward.toLocaleString()}</span>
                </div>
                <div className="h-16 my-1 flex items-center justify-center"><JarIcon jar={j} /></div>
                <div className="text-[11px] font-bold truncate">{j.name.toUpperCase()}</div>
                {j.owned ? (
                  <>
                    <div className="mt-1 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${j.fill}%`, background: j.fill >= 100 ? '#00ff88' : '#d4ff00' }} />
                    </div>
                    <div className="text-[8px] mt-0.5" style={{ color: j.fill >= 100 ? '#00ff88' : '#a1a1aa' }}>
                      {j.fill}% {j.fill >= 100 ? `• ${t.sellable}` : `• ${t.filling}`}
                    </div>
                    <button disabled className="mt-1.5 w-full text-[9px] font-black rounded-full py-2 bg-zinc-800 text-zinc-500" data-testid={`shop-owned-${j.id}`}>
                      {t.owned}
                    </button>
                  </>
                ) : (
                  <button onClick={() => buy(j)} disabled={busy === j.id || balance < j.buyPrice}
                    data-testid={`shop-buy-${j.id}`}
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
                <div key={j.id} data-testid={`shop-sellcard-${j.id}`}
                  className="rounded-xl p-3 border bg-zinc-900" style={{ borderColor: '#00ff8840' }}>
                  <div className="flex justify-between text-[8px] mb-1">
                    <span className="font-black" style={{ color: CAT_COLOR[cat] }}>{cat}</span>
                    <span className="text-[#FFD447] font-black">💰 {j.sellReward.toLocaleString()}</span>
                  </div>
                  <div className="h-14 my-1 flex items-center justify-center"><JarIcon jar={j} size="h-14" /></div>
                  <div className="text-[10px] font-bold truncate">{j.name.toUpperCase()}</div>
                  <div className="mt-1 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${j.fill}%`, background: j.fill >= 100 ? '#00ff88' : '#d4ff00' }} />
                  </div>
                  <div className="text-[8px] mt-0.5" style={{ color: j.fill >= 100 ? '#00ff88' : '#a1a1aa' }}>
                    {j.fill}% {j.fill >= 100 ? `• ${t.sellable}` : `• ${t.filling}`}
                  </div>
                  <button onClick={() => sell(j)} disabled={busy === j.id || j.fill < 100}
                    data-testid={`shop-sell-${j.id}`}
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
  );
}
