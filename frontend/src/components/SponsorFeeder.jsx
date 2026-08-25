import React from "react";
export default function SponsorFeeder(){
  return (
    <div className="flex flex-col gap-2">
      <button className="relative w-full h-[60px] rounded overflow-hidden bg-zinc-900">
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/40">
          <div className="text-[13px] text-[#D4FF32] tracking-widest">RENT 2 PILLS FOR YOUR LINK 300€/MONTH</div>
          <div className="text-[9px] text-pink-300 mt-1">CLICK -&gt; INSTAGRAM @tipjarglobal</div>
        </div>
      </button>
      <button className="relative w-full h-[60px] rounded overflow-hidden bg-zinc-900">
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/30">
          <div className="text-[12px] text-white tracking-widest">RENT A PILL FOR YOUR LINK 150€/MONTH</div>
          <div className="text-[8px] text-pink-300 mt-1">CLICK -&gt; INSTAGRAM @tipjarglobal</div>
        </div>
      </button>
    </div>
  )
}
