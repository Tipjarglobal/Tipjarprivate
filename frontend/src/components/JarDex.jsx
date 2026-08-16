
import React, { useState } from 'react';

// FINAL 30 Jars nach MEMORY.md 15.08.2026 - Carton Box statt Cork
const JARS_FINAL = [
  // TIER 1 COMMON 6 Jars 40-80
  { id: 1, name: 'Common Glass Jar', short: 'COMMON GLASS', need: 40, seal: 2, rarity: 'COMMON', owned: true, color: '#9ca3af', desc: 'START' },
  { id: 2, name: 'Wood Jar', short: 'WOOD', need: 50, seal: 3, rarity: 'COMMON', owned: false, color: '#92400e' },
  { id: 3, name: 'Stone Jar', short: 'STONE', need: 60, seal: 3, rarity: 'COMMON', owned: false, color: '#6b7280' },
  { id: 4, name: 'Clay Jar', short: 'CLAY', need: 70, seal: 4, rarity: 'COMMON', owned: false, color: '#b45309' },
  { id: 5, name: 'Bamboo Jar', short: 'BAMBOO', need: 75, seal: 4, rarity: 'COMMON', owned: false, color: '#65a30d' },
  { id: 6, name: 'Carton Box Jar', short: 'CARTON BOX', need: 80, seal: 4, rarity: 'COMMON', owned: false, color: '#d6c7a1' },
  // TIER 2 UNCOMMON 90-170
  { id: 7, name: 'Bronze Jar', short: 'BRONZE', need: 90, seal: 5, rarity: 'UNCOMMON', owned: false, color: '#b45309' },
  { id: 8, name: 'Iron Jar', short: 'IRON', need: 110, seal: 6, rarity: 'UNCOMMON', owned: false, color: '#4b5563' },
  { id: 9, name: 'Tin Jar', short: 'TIN', need: 130, seal: 7, rarity: 'UNCOMMON', owned: false, color: '#9ca3af' },
  { id: 10, name: 'Copper Jar', short: 'COPPER', need: 150, seal: 8, rarity: 'UNCOMMON', owned: false, color: '#c2410c' },
  { id: 11, name: 'Aluminum Jar', short: 'ALUMINUM', need: 160, seal: 8, rarity: 'UNCOMMON', owned: false, color: '#e5e7eb' },
  { id: 12, name: 'Brass Jar', short: 'BRASS', need: 170, seal: 9, rarity: 'UNCOMMON', owned: false, color: '#eab308' },
  // TIER 3 RARE 180-280
  { id: 13, name: 'Steel Jar', short: 'STEEL', need: 180, seal: 9, rarity: 'RARE', owned: false, color: '#6b7280' },
  { id: 14, name: 'Silver Jar', short: 'SILVER', need: 200, seal: 10, rarity: 'RARE', owned: false, color: '#d1d5db' },
  { id: 15, name: 'Nickel Jar', short: 'NICKEL', need: 220, seal: 11, rarity: 'RARE', owned: false, color: '#9ca3af' },
  { id: 16, name: 'Chrome Jar', short: 'CHROME', need: 240, seal: 12, rarity: 'RARE', owned: false, color: '#e5e7eb' },
  { id: 17, name: 'Carbon Jar', short: 'CARBON', need: 260, seal: 13, rarity: 'RARE', owned: false, color: '#111827' },
  { id: 18, name: 'Crystal Jar', short: 'CRYSTAL', need: 280, seal: 14, rarity: 'RARE', owned: false, color: '#06b6d4' },
  // TIER 4 EPIC 300-420
  { id: 19, name: 'Gold Jar', short: 'GOLD', need: 300, seal: 15, rarity: 'EPIC', owned: false, color: '#f59e0b' },
  { id: 20, name: 'Platinum Jar', short: 'PLATINUM', need: 350, seal: 18, rarity: 'EPIC', owned: false, color: '#e5e7eb' },
  { id: 21, name: 'Titanium Jar', short: 'TITANIUM', need: 380, seal: 19, rarity: 'EPIC', owned: false, color: '#6b7280' },
  { id: 22, name: 'Ruby Jar', short: 'RUBY', need: 400, seal: 20, rarity: 'EPIC', owned: false, color: '#dc2626' },
  { id: 23, name: 'Sapphire Jar', short: 'SAPPHIRE', need: 410, seal: 21, rarity: 'EPIC', owned: false, color: '#2563eb' },
  { id: 24, name: 'Emerald Jar', short: 'EMERALD', need: 420, seal: 21, rarity: 'EPIC', owned: false, color: '#16a34a' },
  // TIER 5 LEGENDARY 450-500
  { id: 25, name: 'Diamond Jar', short: 'DIAMOND', need: 450, seal: 23, rarity: 'LEGENDARY', owned: false, color: '#06b6d4' },
  { id: 26, name: 'Obsidian Jar', short: 'OBSIDIAN', need: 475, seal: 24, rarity: 'LEGENDARY', owned: false, color: '#000000' },
  { id: 27, name: 'Galaxy Jar', short: 'GALAXY', need: 500, seal: 25, rarity: 'LEGENDARY', owned: false, color: '#a855f7' },
  { id: 28, name: 'Void Jar', short: 'VOID', need: 500, seal: 25, rarity: 'LEGENDARY', owned: false, color: '#111827' },
  // TIER 6 MYTHIC 2 Jars 500 Endgame
  { id: 29, name: 'Nebula Jar', short: 'NEBULA', need: 500, seal: 25, rarity: 'MYTHIC', owned: false, color: '#ec4899', isEnd: true },
  { id: 30, name: 'Infinity Jar', short: 'INFINITY', need: 500, seal: 25, rarity: 'MYTHIC', owned: false, color: '#ffffff', isEnd: true },
];

export default function Jardex({ userCoins = 12340, userCredits = 42 }) {
  const [tab, setTab] = useState('INVENTORY');
  const owned = JARS_FINAL.filter(j => j.owned);
  const showcase = [JARS_FINAL[0], null, null, null, null, null]; // Starter Common Glass + 5 LEER für Homepage Pille

  const getRarityColor = (r) => {
    if (r==='COMMON') return 'text-zinc-400';
    if (r==='UNCOMMON') return 'text-green-400';
    if (r==='RARE') return 'text-blue-400';
    if (r==='EPIC') return 'text-purple-400';
    if (r==='LEGENDARY') return 'text-yellow-400';
    if (r==='MYTHIC') return 'text-pink-400';
    return 'text-white';
  };

  return (
    <div className="min-h-screen bg-black text-white p-4 font-mono">
      {/* HEADER TIPJAR + Coins - KEINE DIAMANTEN */}
      <div className="flex justify-between items-center mb-6 border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-2xl font-black tracking-[0.2em]">TIPJAR</h1>
          <p className="text-[10px] text-zinc-500">{userCredits} / 2500 COIN BATTERY</p>
        </div>
        <div className="bg-zinc-900 border border-yellow-500/30 px-4 py-2 rounded-full flex items-center gap-2">
          <span>🪙</span><span className="font-bold">{userCoins.toLocaleString()} Coins</span>
        </div>
      </div>

      {/* 3 TABS */}
      <div className="flex gap-2 mb-6">
        {['INVENTORY','JARDEX','SHOWCASE'].map(t => (
          <button key={t} onClick={()=>setTab(t)}
            className={`px-5 py-3 rounded-lg font-black text-xs tracking-widest ${tab===t ? 'bg-yellow-400 text-black shadow-[0_0_15px_rgba(250,204,21,0.6)]' : 'bg-zinc-900 text-zinc-500 border border-zinc-800'}`}>
            {t}
          </button>
        ))}
      </div>

      {tab==='INVENTORY' && (
        <div>
          <p className="text-[11px] text-zinc-500 mb-3">Owned Lager - {owned.length}/30 - Nur im Besitz - mit Glow</p>
          <div className="grid grid-cols-3 gap-3">
            {JARS_FINAL.filter(j=>j.owned).map(j => (
              <div key={j.id} className="bg-zinc-900 rounded-xl p-3 border border-zinc-800 relative" style={{boxShadow: `0 0 20px ${j.color}40`}}>
                <div className="flex justify-between text-[8px]"><span className={getRarityColor(j.rarity)}>{j.rarity}</span><span className="text-zinc-600">{j.need} Coins</span></div>
                <div className="h-20 my-2 rounded-lg flex items-center justify-center text-3xl" style={{background: `${j.color}20`}}>🏺</div>
                <div className="text-[10px] font-bold truncate">{j.short}</div>
                <div className="text-[8px] text-zinc-500">Seal {j.seal} Coins</div>
                <div className="absolute top-2 right-2 w-2 h-2 rounded-full animate-pulse" style={{background:j.color}}/>
              </div>
            ))}
            {owned.length===0 && <div className="col-span-3 text-center py-10 text-zinc-600 text-xs">Noch keine Jars - Start mit Common Glass 40</div>}
          </div>
        </div>
      )}

      {tab==='JARDEX' && (
        <div>
          <p className="text-[11px] text-zinc-500 mb-3">Alle 30 Jars - Ghost Infos immer sichtbar - Wie Pokedex - Schatten für unentdeckte - MYSTIC = Nebula/Infinity Schatten-Silhouette</p>
          <div className="grid grid-cols-3 gap-2">
            {JARS_FINAL.map(j => (
              <div key={j.id} className={`rounded-xl p-2 border ${j.owned ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-950 border-zinc-900'}`}>
                <div className="flex justify-between text-[7px]"><span className={getRarityColor(j.rarity)}>{j.rarity}</span><span className="text-zinc-600">{j.need}</span></div>
                <div className="h-16 my-1 rounded-lg flex items-center justify-center relative" style={{background: j.owned ? `${j.color}15` : '#000'}}>
                  {j.owned ? <span className="text-2xl">🏺</span> : j.rarity==='MYTHIC' ? 
                    <div className="w-10 h-10 bg-zinc-800 rounded-full blur-[0.5px] opacity-40 flex items-center justify-center"><span className="text-[10px] text-zinc-600">?</span></div> :
                    <span className="text-xl opacity-10">🏺</span>}
                </div>
                <div className="text-[8px] font-bold truncate">{j.owned ? j.short : '???'}</div>
                <div className="flex justify-between text-[7px] mt-1"><span className="text-zinc-600">Seal {j.seal}</span><span className="text-yellow-600">+{j.need>=500 ? '∞' : j.need}</span></div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab==='SHOWCASE' && (
        <div>
          <p className="text-[11px] text-zinc-500 mb-3">6 für Homepage Pille - 2 gefüllt 4 LEER - Diese erscheinen auf Startseite als Pille</p>
          <div className="grid grid-cols-3 gap-3">
            {showcase.map((j,i) => (
              <div key={i} className="bg-zinc-900 rounded-xl p-3 border border-zinc-800 h-32 flex flex-col">
                {j ? (
                  <>
                    <div className="text-[8px] text-zinc-500">{j.rarity} • {j.need} Coins</div>
                    <div className="flex-1 flex items-center justify-center text-3xl">🏺</div>
                    <div className="text-[9px] font-bold">{j.short}</div>
                    <div className="text-[7px] text-zinc-500">{i+1}/6 Homepage</div>
                  </>
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

      <div className="mt-8 p-3 bg-zinc-900/50 rounded-lg border border-zinc-800 text-[10px] text-zinc-500">
        <div>Carton Box statt Cork • Starter Common Glass 40 im OPEN CASE • fill = received_credits + credits • Seal 5% einmalig für immer</div>
        <div className="mt-1">Member Jars Wall komplett raus - nur noch diese 3 Tabs Seite</div>
      </div>
    </div>
  );
}
