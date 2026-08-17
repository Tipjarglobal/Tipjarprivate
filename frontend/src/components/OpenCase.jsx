import React, { useState, useEffect } from "react";
import { JAR_DEFS, getJarForCredits } from "./AnimatedJar";
import { useAuth } from "../auth";

export default function OpenCase() {
  const { user } = useAuth();
  const credits = (user?.received_credits || 0) + (user?.credits || 0);
  const currentJar = getJarForCredits(credits);
  
  const [openJars, setOpenJars] = useState(() => {
    try {
      const saved = localStorage.getItem("tipjar_active_set");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length === 3) {
          const validIds = new Set(JAR_DEFS.map(j => j.id));
          const cleaned = parsed.map(s => {
            if (s?.jar && !validIds.has(s.jar.id)) return { id: s.id, jar: null, filled: 0 };
            return s;
          });
          return cleaned;
        }
      }
    } catch {}
    // Start: alle 3 Slots leer, User wählt selbst - oder Slot1 mit currentJar initial, aber danach frei
    return [
      { id: "slot1", jar: currentJar || null, filled: 0 },
      { id: "slot2", jar: null, filled: 0 },
      { id: "slot3", jar: null, filled: 0 },
    ];
  });

  // KEIN useEffect mehr der Slot 1 erzwingt! Alle Slots funktionieren gleich

  useEffect(() => {
    try { localStorage.setItem("tipjar_active_set", JSON.stringify(openJars)); } catch {}
  }, [openJars]);

  const handleSlotClick = (index) => {
    setOpenJars(prev => {
      const next = [...prev];
      next[index] = { ...next[index], jar: null, filled: 0 };
      return next;
    });
  };

  const getOpenImage = (jar) => jar ? (jar.graphicOpen || null) : null;
  const getClosedImage = (jar) => jar ? (jar.graphic || null) : null;

  return (
    <div className="w-full">
      <h3 className="text-[12px] font-black tracking-widest text-white mb-1">OPEN CASE • 3 SLOTS</h3>
      <p className="text-[9px] text-zinc-500 mb-3">Alle 3 Slots gleich • Tippe zum Zurücklegen</p>
      
      <div className="grid grid-cols-3 gap-3">
        {openJars.map((slot, i) => {
          const openImg = getOpenImage(slot.jar);
          const closedImg = getClosedImage(slot.jar);
          
          return (
          <div key={slot.id} onClick={() => slot.jar && handleSlotClick(i)}
            className={`relative aspect-[3/4] bg-zinc-900 rounded-[16px] border border-white/10 overflow-hidden flex flex-col ${slot.jar ? 'cursor-pointer active:scale-[0.98]' : ''}`}>
            {slot.jar ? (
              <>
                <div className="flex-1 relative min-h-0 w-full flex items-center justify-center bg-gradient-to-b from-white/[0.04] to-zinc-900 p-2">
                  {openImg ? (
                    <img src={openImg} alt={slot.jar.name} className="w-full h-full max-h-[96px] object-contain object-bottom drop-shadow-[0_6px_16px_rgba(0,0,0,0.6)]"
                      onError={(e)=>{ e.target.style.display='none'; e.target.nextElementSibling.style.display='flex'; }} />
                  ) : null}
                  {(!openImg && closedImg) ? (
                    <img src={closedImg} alt={slot.jar.name} className="w-full h-full max-h-[96px] object-contain object-bottom"
                      onError={(e)=>{ e.target.style.display='none'; e.target.nextElementSibling.style.display='flex'; }} />
                  ) : null}
                  <div className="fb absolute inset-0 hidden flex-col items-center justify-center rounded-[12px] border border-white/10" style={{ background: slot.jar.color, display: (!openImg && !closedImg) ? 'flex' : 'none' }}>
                    <span className="text-[26px] font-black text-black/70">{slot.jar.name[0]}</span>
                    <span className="text-[7px] font-bold text-black/50 mt-1 tracking-widest">{slot.jar.name.toUpperCase()}</span>
                  </div>
                  <div className="absolute bottom-[21%] left-[23%] right-[23%] h-[42%] rounded-b-[14px] overflow-hidden opacity-80 pointer-events-none">
                    <div className="absolute bottom-0 left-0 right-0 transition-all duration-700" style={{ height: `${Math.min(100, slot.filled)}%`, background: slot.jar.color }} />
                  </div>
                </div>
                <div className="p-2 bg-black/60 backdrop-blur border-t border-white/5">
                  <div className="text-[9px] font-black truncate leading-none" style={{ color: slot.jar.color }}>{slot.jar.name.toUpperCase()}</div>
                  <div className="text-[8px] text-zinc-500 mt-[2px]">{slot.filled.toFixed(0)}% • {slot.jar.coins} COINS • Seal {slot.jar.seal}</div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-3 text-center">
                <div className="relative w-[40px] h-[50px] mb-2">
                  <div className="absolute inset-0 rounded-b-[12px] border-2 border-dashed border-white/15 bg-white/[0.02]" />
                  <div className="absolute -top-[3px] left-[4px] right-[4px] h-[8px] rounded-[50%] border-2 border-dashed border-white/10 bg-zinc-900" />
                </div>
                <div className="text-[8px] text-zinc-600 font-bold tracking-widest">LEER</div>
                <div className="text-[7px] text-zinc-700 mt-1">Slot {i+1}</div>
              </div>
            )}
            <div className="absolute top-1.5 left-1.5 w-[16px] h-[16px] rounded-full bg-white/10 border border-white/10 flex items-center justify-center text-[7px] font-black text-white/70">{i+1}</div>
          </div>
          );
        })}
      </div>
    </div>
  );
}
