import React, { useState } from "react";
import { JAR_DEFS, getJarForCredits } from "./AnimatedJar";
import { useAuth } from "../auth";

export default function OpenCase() {
  const { user } = useAuth();
  const credits = (user?.received_credits || 0) + (user?.credits || 0);
  const currentJar = getJarForCredits(credits);
  
  // 3 Open Slots - max 3 offene Gläser
  const [openJars, setOpenJars] = useState([
    { id: "slot1", jar: currentJar, filled: 0 },
    { id: "slot2", jar: null, filled: 0 },
    { id: "slot3", jar: null, filled: 0 },
  ]);

  return (
    <div className="w-full">
      <h3 className="text-[12px] font-black tracking-widest text-white mb-1">OPEN CASE • 3 SLOTS</h3>
      <p className="text-[9px] text-zinc-500 mb-3">Dein aktives Set • Bis zu 3 Jars sammeln gleichzeitig Coins • Tippe zum Zurücklegen</p>
      
      <div className="grid grid-cols-3 gap-3">
        {openJars.map((slot, i) => (
          <div key={slot.id} className="relative aspect-[3/4] bg-zinc-900 rounded-[16px] border border-white/10 overflow-hidden flex flex-col">
            {slot.jar ? (
              <>
                {/* Top POV Graphic - offen ohne Deckel */}
                <div className="flex-1 relative p-2">
                  <img 
                    src={slot.jar.graphicOpen || slot.jar.graphic} 
                    alt={slot.jar.name}
                    className="w-full h-full object-contain"
                  />
                  {/* Fill indicator inside open jar */}
                  <div className="absolute bottom-[30%] left-[25%] right-[25%] h-[40%] rounded-b-[12px] overflow-hidden opacity-60">
                    <div 
                      className="absolute bottom-0 left-0 right-0 transition-all duration-700"
                      style={{ 
                        height: `${Math.min(100, slot.filled)}%`,
                        background: slot.jar.color,
                      }}
                    />
                  </div>
                </div>
                <div className="p-2 bg-black/50 backdrop-blur">
                  <div className="text-[9px] font-black truncate" style={{ color: slot.jar.color }}>{slot.jar.name.toUpperCase()}</div>
                  <div className="text-[8px] text-zinc-500">{slot.filled.toFixed(0)}% • {slot.jar.coins} COINS</div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-3 text-center">
                <div className="w-[40px] h-[50px] rounded-b-[12px] border-2 border-dashed border-white/20 mb-2" />
                <div className="text-[8px] text-zinc-600 font-bold">LEER</div>
                <div className="text-[7px] text-zinc-700 mt-1">Slot {i+1}</div>
              </div>
            )}
            {/* Slot number */}
            <div className="absolute top-1 left-1 w-[14px] h-[14px] rounded-full bg-white/10 flex items-center justify-center text-[7px] font-black text-white/60">{i+1}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
