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
        if (Array.isArray(parsed) && parsed.length === 3) return parsed;
      }
    } catch {}
    return [
      { id: "slot1", jar: currentJar || null, filled: 0 },
      { id: "slot2", jar: null, filled: 0 },
      { id: "slot3", jar: null, filled: 0 },
    ];
  });

  useEffect(() => {
    if (!currentJar) return;
    setOpenJars(prev => {
      if (!prev[0]?.jar) {
        const next = [...prev];
        next[0] = { ...next[0], jar: currentJar };
        return next;
      }
      return prev;
    });
  }, [currentJar]);

  useEffect(() => {
    try {
      localStorage.setItem("tipjar_active_set", JSON.stringify(openJars));
    } catch {}
  }, [openJars]);

  const handleSlotClick = (index) => {
    setOpenJars(prev => {
      const next = [...prev];
      next[index] = { ...next[index], jar: null, filled: 0 };
      return next;
    });
  };

  // IMMER offenes Top POV ohne Deckel
  const getOpenImage = (jar) => {
    if (!jar) return null;
    // Reihenfolge: explizites Open Top, dann High POV, dann Alt
    return jar.graphicOpen || jar.graphicOpenTop || jar.graphicHighPov || jar.graphicTop || jar.topView || jar.open || null;
  };

  const getClosedImageForCrop = (jar) => {
    if (!jar) return null;
    return jar.graphic || jar.image || jar.src || null;
  };

  return (
    <div className="w-full">
      <h3 className="text-[12px] font-black tracking-widest text-white mb-1">OPEN CASE • 3 SLOTS</h3>
      <p className="text-[9px] text-zinc-500 mb-3">Dein aktives Set • Bis zu 3 Jars sammeln gleichzeitig Coins • Tippe zum Zurücklegen</p>
      
      <div className="grid grid-cols-3 gap-3">
        {openJars.map((slot, i) => {
          const openImg = getOpenImage(slot.jar);
          const closedImg = getClosedImageForCrop(slot.jar);
          const hasOpenGraphic = !!openImg;
          
          return (
          <div 
            key={slot.id} 
            onClick={() => slot.jar && handleSlotClick(i)}
            className={`relative aspect-[3/4] bg-zinc-900 rounded-[16px] border border-white/10 overflow-hidden flex flex-col ${slot.jar ? 'cursor-pointer active:scale-[0.98] transition-transform' : ''}`}
          >
            {slot.jar ? (
              <>
                {/* VISUELL IMMER OBEN POV OHNE DECKEL */}
                <div className="flex-1 relative min-h-0 w-full flex items-center justify-center bg-gradient-to-b from-white/[0.04] to-zinc-900 p-2">
                  {hasOpenGraphic ? (
                    // Fall 1: Hat echtes Open Top Bild - direkt nehmen
                    <img 
                      src={openImg}
                      alt={slot.jar.name}
                      className="w-full h-full max-h-[96px] object-contain object-bottom drop-shadow-[0_6px_16px_rgba(0,0,0,0.6)]"
                    />
                  ) : (
                    // Fall 2: Kein Open Bild vorhanden -> Erzwinge offenen Look aus normalem Graphic
                    <div className="relative w-full h-full max-h-[96px] flex items-end justify-center overflow-hidden">
                      {/* Das normale Jar - aber oben abgeschnitten damit Deckel weg ist */}
                      <img 
                        src={closedImg}
                        alt={slot.jar.name}
                        className="w-full h-[115%] object-contain object-bottom translate-y-[8%]"
                        style={{ clipPath: "inset(0% 0% 0% 0%)" }}
                      />
                      {/* Fake Öffnung oben - Ellipse die Deckel überdeckt */}
                      <div 
                        className="absolute top-[8%] left-[18%] right-[18%] h-[18%] rounded-[50%] border-[2px] border-white/10 pointer-events-none"
                        style={{ 
                          background: `radial-gradient(ellipse at center, #0a0a0a 0%, #1a1a1a 60%, ${slot.jar.color || '#222'} 100%)`,
                          boxShadow: "inset 0 2px 6px rgba(0,0,0,0.9), inset 0 -1px 2px rgba(255,255,255,0.1)"
                        }}
                      />
                    </div>
                  )}

                  {/* Fill - immer innen, passend für offene Ansicht */}
                  <div className="absolute bottom-[21%] left-[23%] right-[23%] h-[42%] rounded-b-[14px] overflow-hidden opacity-80 pointer-events-none">
                    <div 
                      className="absolute bottom-0 left-0 right-0 transition-all duration-700"
                      style={{ 
                        height: `${Math.min(100, slot.filled)}%`,
                        background: slot.jar.color || "#facc15",
                        boxShadow: "inset 0 2px 8px rgba(0,0,0,0.4)"
                      }}
                    />
                    {/* Oberfläche des Fills für Top POV */}
                    <div 
                      className="absolute w-full h-[10%] rounded-[50%] -top-[5%]"
                      style={{ 
                        background: slot.jar.color || "#facc15",
                        opacity: 0.9,
                        filter: "brightness(1.2)"
                      }}
                    />
                  </div>
                </div>
                <div className="p-2 bg-black/60 backdrop-blur border-t border-white/5">
                  <div className="text-[9px] font-black truncate leading-none" style={{ color: slot.jar.color || "#fff" }}>{(slot.jar.name || "TIPJAR").toUpperCase()}</div>
                  <div className="text-[8px] text-zinc-500 mt-[2px] flex items-center gap-1">
                    <span>{slot.filled.toFixed(0)}% • {slot.jar.coins || 0} COINS</span>
                    {!hasOpenGraphic && <span className="text-[6px] bg-white/10 px-1 rounded">AUTO-OPEN</span>}
                  </div>
                </div>
              </>
            ) : (
              // LEER Slot - gleiche Größe wie Jar Slots
              <div className="flex-1 flex flex-col items-center justify-center p-3 text-center min-h-0">
                <div className="relative w-[40px] h-[50px] mb-2">
                  {/* Leerer offener Jar Umriss ohne Deckel */}
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
