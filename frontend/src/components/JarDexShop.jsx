import { useState } from "react"

const JARS = [
 {id:"GLASS",name:"GLASS",reward:40,rarity:"COMMON",color:"#e0e0e0",glow:"#ffffff"},
 {id:"WOOD",name:"WOOD",reward:50,rarity:"COMMON",color:"#8d6e63",glow:"#a1887f"},
 {id:"STONE",name:"STONE",reward:60,rarity:"COMMON",color:"#78909c",glow:"#b0bec5"},
 {id:"CLAY",name:"CLAY",reward:70,rarity:"COMMON",color:"#bf8a65",glow:"#d7b69f"},
 {id:"BAMBOO",name:"BAMBOO",reward:75,rarity:"COMMON",color:"#7cb342",glow:"#aed581"},
 {id:"CARTON BOX",name:"CARTON",reward:80,rarity:"COMMON",color:"#c49a6c",glow:"#dcc7a7"},
 {id:"PAPER",name:"PAPER",reward:85,rarity:"COMMON",color:"#fafafa",glow:"#eeeeee"},
 {id:"PLASTIC",name:"PLASTIC",reward:90,rarity:"COMMON",color:"#4fc3f7",glow:"#81d4fa"},
 {id:"CERAMIC",name:"CERAMIC",reward:95,rarity:"COMMON",color:"#f8f8ff",glow:"#ffffff"},
 {id:"WICKER",name:"WICKER",reward:100,rarity:"COMMON",color:"#a1887f",glow:"#bcaaa4"},
 {id:"BRONZE",name:"BRONZE",reward:110,rarity:"UNCOMMON",color:"#cd7f32",glow:"#e6a86a"},
 {id:"IRON",name:"IRON",reward:120,rarity:"UNCOMMON",color:"#6e7b8b",glow:"#90a4ae"},
 {id:"TIN",name:"TIN",reward:150,rarity:"UNCOMMON",color:"#b0b7b9",glow:"#cfd8dc"},
 {id:"ZINC",name:"ZINC",reward:180,rarity:"UNCOMMON",color:"#a8c0c6",glow:"#c5d6da"},
 {id:"COPPER",name:"COPPER",reward:200,rarity:"UNCOMMON",color:"#b87333",glow:"#d18a4a"},
 {id:"ALUMINUM",name:"ALUMINUM",reward:220,rarity:"UNCOMMON",color:"#d6d6d6",glow:"#eeeeee"},
 {id:"STEEL",name:"STE
cat > frontend/src/components/JarDexShop.jsx << 'JSX'
import { useState } from "react"

const JARS = [
 {id:"GLASS",name:"GLASS",reward:40,rarity:"COMMON",color:"#e0e0e0",glow:"#ffffff"},
 {id:"WOOD",name:"WOOD",reward:50,rarity:"COMMON",color:"#8d6e63",glow:"#a1887f"},
 {id:"STONE",name:"STONE",reward:60,rarity:"COMMON",color:"#78909c",glow:"#b0bec5"},
 {id:"CLAY",name:"CLAY",reward:70,rarity:"COMMON",color:"#bf8a65",glow:"#d7b69f"},
 {id:"BAMBOO",name:"BAMBOO",reward:75,rarity:"COMMON",color:"#7cb342",glow:"#aed581"},
 {id:"CARTON BOX",name:"CARTON",reward:80,rarity:"COMMON",color:"#c49a6c",glow:"#dcc7a7"},
 {id:"PAPER",name:"PAPER",reward:85,rarity:"COMMON",color:"#fafafa",glow:"#eeeeee"},
 {id:"PLASTIC",name:"PLASTIC",reward:90,rarity:"COMMON",color:"#4fc3f7",glow:"#81d4fa"},
 {id:"CERAMIC",name:"CERAMIC",reward:95,rarity:"COMMON",color:"#f8f8ff",glow:"#ffffff"},
 {id:"WICKER",name:"WICKER",reward:100,rarity:"COMMON",color:"#a1887f",glow:"#bcaaa4"},
 {id:"BRONZE",name:"BRONZE",reward:110,rarity:"UNCOMMON",color:"#cd7f32",glow:"#e6a86a"},
 {id:"IRON",name:"IRON",reward:120,rarity:"UNCOMMON",color:"#6e7b8b",glow:"#90a4ae"},
 {id:"TIN",name:"TIN",reward:150,rarity:"UNCOMMON",color:"#b0b7b9",glow:"#cfd8dc"},
 {id:"ZINC",name:"ZINC",reward:180,rarity:"UNCOMMON",color:"#a8c0c6",glow:"#c5d6da"},
 {id:"COPPER",name:"COPPER",reward:200,rarity:"UNCOMMON",color:"#b87333",glow:"#d18a4a"},
 {id:"ALUMINUM",name:"ALUMINUM",reward:220,rarity:"UNCOMMON",color:"#d6d6d6",glow:"#eeeeee"},
 {id:"STEEL",name:"STEEL",reward:250,rarity:"UNCOMMON",color:"#71797e",glow:"#9099a0"},
 {id:"LEAD",name:"LEAD",reward:280,rarity:"UNCOMMON",color:"#5a5a5a",glow:"#757575"},
 {id:"SILVER",name:"SILVER",reward:350,rarity:"RARE",color:"#c0c0c0",glow:"#e8e8e8"},
 {id:"GOLD",name:"GOLD",reward:500,rarity:"RARE",color:"#ffd700",glow:"#ffeb3b"},
 {id:"CRYSTAL",name:"CRYSTAL",reward:650,rarity:"RARE",color:"#e1f5fe",glow:"#b3e5fc"},
 {id:"RUBY",name:"RUBY",reward:800,rarity:"RARE",color:"#e0115f",glow:"#ff1744"},
 {id:"SAPPHIRE",name:"SAPPHIRE",reward:950,rarity:"RARE",color:"#0f52ba",glow:"#2979ff"},
 {id:"EMERALD",name:"EMERALD",reward:1100,rarity:"RARE",color:"#50c878",glow:"#69f0ae"},
 {id:"DIAMOND",name:"DIAMOND",reward:1500,rarity:"RARE",color:"#b9f2ff",glow:"#e0f7fa"},
 {id:"VOID",name:"VOID",reward:2000,rarity:"LEGENDARY",color:"#1a1a2e",glow:"#7c4dff"},
 {id:"COSMIC",name:"COSMIC",reward:3000,rarity:"LEGENDARY",color:"#4a148c",glow:"#e040fb"},
 {id:"QUANTUM",name:"QUANTUM",reward:5000,rarity:"LEGENDARY",color:"#00bcd4",glow:"#18ffff"},
 {id:"INFINITY",name:"INFINITY",reward:8000,rarity:"LEGENDARY",color:"#000000",glow:"#d4ff00"},
 {id:"ORIGIN",name:"ORIGIN",reward:12000,rarity:"LEGENDARY",color:"#d4ff00",glow:"#ffff00"},
]

export default function JarDexShop({balance=9999,setBalance=()=>{},userJars=[],setUserJars=()=>{}}){
 const [tab,setTab]=useState("COMMON")
 const [selected,setSelected]=useState(null)
 const filtered=JARS.filter(j=>j.rarity===tab)

 return(
 <div className="min-h-screen bg-[#050505] text-white p-4 pb-20">
  <h1 className="text-2xl font-black tracking-tighter mb-1">JARDEX</h1>
  <p className="text-[10px] text-[#666] mb-4 tracking-[0.3em]">30 COLLECTIBLES • {userJars.length}/30</p>

  <div className="flex gap-2 mb-6 overflow-x-auto scrollbar-none">
   {[
    {id:"COMMON",col:"bg-[#2a2a2a]"},
    {id:"UNCOMMON",col:"bg-[#1a3a2a]"},
    {id:"RARE",col:"bg-[#1a2a4a]"},
    {id:"LEGENDARY",col:"bg-[#3a2a1a]"},
   ].map(t=>(
    <button key={t.id} onClick={()=>setTab(t.id)} className={`px-5 py-2.5 rounded-full text-[11px] font-bold tracking-widest transition-all ${tab===t.id?"bg-[#d4ff00] text-black scale-105 shadow-[0_0_20px_#d4ff00]":"bg-[#151515] text-[#888] border border-[#222]"}`}>{t.id}</button>
   ))}
  </div>

  <div className="grid grid-cols-2 gap-4">
   {filtered.map(j=>{
    const owned=userJars.find(x=>x.jar_id===j.id||x.id===j.id)
    return(
     <div key={j.id} onClick={()=>setSelected(j)} className="group relative bg-gradient-to-b from-[#1c1c1c] to-[#111] rounded-[24px] p-[1px] cursor-pointer hover:scale-[1.02] transition-all duration-300">
      <div className="bg-[#111] rounded-[23px] p-4 h-full relative overflow-hidden">
       {j.rarity==="LEGENDARY"&&<div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-[#d4ff00]/10 opacity-0 group-hover:opacity-100 transition-opacity"/>}
       {/* JAR VISUAL */}
       <div className="relative h-[90px] flex items-center justify-center mb-3">
        <div className="absolute w-[60px] h-[70px] rounded-[12px_12px_20px_20px] blur-[12px] opacity-40" style={{background:j.color}}/>
        <div className="relative w-[56px] h-[68px] rounded-[14px_14px_22px_22px] border border-white/20 flex flex-col overflow-hidden" style={{background:`linear-gradient(180deg, ${j.glow}40, ${j.color})`, boxShadow:`inset 0 2px 10px white/30, 0 4px 20px ${j.color}60`}}>
         <div className="h-[12px] bg-black/40 border-b border-white/10 w-full"/>
         <div className="flex-1 relative">
          <div className="absolute left-[6px] top-[8px] w-[8px] h-[30px] bg-white/40 rounded-full blur-[0.5px]"/>
          {owned&&<div className="absolute bottom-0 w-full bg-[#d4ff00]/80 transition-all" style={{height:(owned.fill||40)+"%"}}/>}
         </div>
        </div>
        {owned&&<div className="absolute -top-1 -right-1 w-5 h-5 bg-[#00ff88] rounded-full flex items-center justify-center text-[10px] text-black font-bold">✓</div>}
       </div>

       <div className="font-black text-[13px] tracking-tight">{j.name}</div>
       <div className="flex items-center gap-1.5 mt-1">
        <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-bold ${j.rarity==="COMMON"?"bg-[#333] text-[#aaa]":j.rarity==="UNCOMMON"?"bg-[#00ff88]/20 text-[#00ff88]":j.rarity==="RARE"?"bg-[#2979ff]/20 text-[#82b1ff]":"bg-[#d4ff00]/20 text-[#d4ff00]"}`}>{j.rarity}</span>
        <span className="text-[10px] text-[#555]">{j.reward}¢</span>
       </div>

       {owned? (
        <div className="mt-3">
         <div className="h-1 bg-black rounded-full overflow-hidden"><div className="h-full bg-[#d4ff00]" style={{width:(owned.fill||0)+"%"}}/></div>
         <div className="text-[9px] text-[#666] mt-1">{owned.fill||0}% gefüllt</div>
        </div>
       ):(
        <button className="mt-3 w-full py-2 rounded-full bg-white text-black text-[11px] font-bold tracking-widest group-hover:bg-[#d4ff00] transition-colors">HOLEN • {Math.floor(j.reward*0.75)}¢</button>
       )}
      </div>
     </div>
    )
   })}
  </div>

  {selected&&(
   <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xl flex items-end sm:items-center justify-center p-4" onClick={()=>setSelected(null)}>
    <div className="bg-[#151515] rounded-[32px] p-6 w-full max-w-[340px] border border-[#222]" onClick={e=>e.stopPropagation()}>
     <div className="w-[100px] h-[120px] mx-auto rounded-[20px_20px_32px_32px] border border-white/20 mb-4" style={{background:`linear-gradient(180deg, ${selected.glow}, ${selected.color})`, boxShadow:`0 20px 60px ${selected.color}80`}}/>
     <h2 className="text-xl font-black text-center">{selected.name}</h2>
     <p className="text-center text-xs text-[#666] mt-1">{selected.rarity} • Reward {selected.reward} Credits</p>
     <button onClick={()=>setSelected(null)} className="mt-6 w-full py-3 rounded-full bg-[#d4ff00] text-black font-bold">SCHLIESSEN</button>
    </div>
   </div>
  )}
 </div>
 )
}
