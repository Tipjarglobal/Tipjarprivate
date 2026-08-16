
import React, { useState } from 'react';

const OPEN_JARS = [
  { id: 1, name: 'Common Glass Jar', short: 'COMMON GLASS', fill: 12, need: 40, state: 'OPEN', color: '#9ca3af', silverPerHour: 2 },
  { id: 2, name: null, short: null, fill: 0, need: 0, state: 'LEER', color: null },
  { id: 3, name: null, short: null, fill: 0, need: 0, state: 'LEER', color: null },
];

export default function OpenCase() {
  const [jars, setJars] = useState(OPEN_JARS);
  const [closing, setClosing] = useState(null);

  const closeAndSwap = (idx) => {
    setClosing(idx);
    setTimeout(() => {
      setJars(prev => {
        const n = [...prev];
        n[idx] = { ...n[idx], state: 'CLOSED', fill: n[idx].fill };
        return n;
      });
      setClosing(null);
    }, 500);
  };

  const openAgain = (idx) => {
    setJars(prev => {
      const n = [...prev];
      n[idx] = { ...n[idx], state: 'OPEN' };
      return n;
    });
  };

  return (
    <div className="min-h-screen bg-black text-white p-4 font-mono">
      <div className="flex justify-between items-center mb-6 border-b border-zinc-800 pb-4">
        <h1 className="text-xl font-black tracking-widest">OPEN CASE</h1>
        <span className="text-[10px] text-zinc-500">Max 3 Jars • Alle offen ohne Deckel • Deckel zu = tauschen</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {jars.map((jar, idx) => (
          <div key={idx} className="relative">
            <div className={`relative bg-zinc-900 rounded-2xl p-6 border h-72 flex flex-col items-center justify-center overflow-hidden transition-all ${jar.state==='LEER' ? 'border-dashed border-zinc-700' : 'border-zinc-800'}`} 
                 style={{boxShadow: jar.color ? `0 0 25px ${jar.color}30` : 'none'}}>
              
              {jar.state==='LEER' ? (
                <div className="flex flex-col items-center">
                  <div className="text-3xl text-zinc-700">+</div>
                  <div className="text-[11px] text-zinc-600 mt-2">LEER SLOT {idx+1}/3</div>
                  <div className="text-[9px] text-zinc-700 mt-1">Hier fällt Gold rein</div>
                </div>
              ) : (
                <>
                  {/* Deckel Animation */}
                  <div className={`absolute top-0 left-1/2 -translate-x-1/2 w-20 h-5 bg-zinc-600 rounded-b-lg border border-zinc-500 z-20 transition-all duration-500 ${closing===idx ? 'translate-y-0' : '-translate-y-10 opacity-0'}`} />

                  {/* Status Badge */}
                  <div className={`absolute top-3 left-3 text-[8px] px-2 py-1 rounded-full border ${jar.state==='OPEN' ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'}`}>
                    {jar.state}
                  </div>

                  {/* Jar Body offen = gestrichelter Rand oben */}
                  <div className="w-24 h-32 rounded-b-2xl border-2 flex flex-col items-center justify-center relative"
                       style={{background: `${jar.color}18`, borderColor: jar.color, borderTop: jar.state==='OPEN' ? '4px dashed #52525b' : `4px solid ${jar.color}`}}>
                    <span className="text-3xl">🏺</span>
                    <div className="mt-2 text-[8px] text-zinc-400">{jar.fill}/{jar.need} Coins</div>
                    <div className="w-16 h-1 bg-zinc-800 rounded-full mt-1 overflow-hidden">
                      <div className="h-full bg-yellow-500" style={{width: `${(jar.fill/jar.need)*100}%`}}/>
                    </div>
                  </div>

                  <div className="mt-4 text-center">
                    <div className="text-[10px] font-bold">{jar.short}</div>
                    <div className="text-[8px] text-zinc-500 mt-1">AFK Silver: {jar.silverPerHour}/h</div>
                    <div className="text-[8px] text-zinc-600">{jar.state==='OPEN' ? 'Verdient AFK • Gold fällt hier rein' : 'Versiegelt? Kein Verlust'}</div>
                  </div>
                </>
              )}
            </div>

            {jar.state!=='LEER' && (
              <button onClick={() => jar.state==='OPEN' ? closeAndSwap(idx) : openAgain(idx)}
                className="w-full mt-3 py-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 rounded-xl text-[10px] font-bold tracking-wider">
                {closing===idx ? 'SCHLIESST...' : jar.state==='OPEN' ? 'DECKEL ZU MACHEN • DANN TAUSCHEN' : 'WIEDER ÖFFNEN'}
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="mt-10 p-4 bg-zinc-900/50 rounded-xl border border-zinc-800 text-[10px] text-zinc-400 space-y-1">
        <div className="text-yellow-400 font-bold">MEMORY.md FINAL REGELN:</div>
        <div>• Start: 1x Common Glass Jar direkt im OPEN CASE (40 Coins)</div>
        <div>• Max 3 Jars gleichzeitig - alle OFFEN ohne Deckel = gestrichelte Linie oben</div>
        <div>• OPEN = Verdient AFK Silver automatisch + Gold Coins fallen rein (Click = 1 Gold)</div>
        <div>• CLOSED nicht versiegelt = -5% pro Tag wenn nicht 5 Calls gedrückt</div>
        <div>• SEALED = 5% vom vollen Wert (z.B. 40=2 Coins) - einmalig für immer - kein Verlust mehr</div>
        <div>• Wenn offen + versiegelt = perfekt: verdient AFK aber kein Verlust</div>
      </div>
    </div>
  );
}
