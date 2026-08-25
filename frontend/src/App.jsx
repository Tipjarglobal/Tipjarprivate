import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";

import Raster1_RentPills from "./components/Raster1_RentPills.jsx";
import Raster2_Header from "./components/Raster2_Header.jsx";
import Raster2_Supporter from "./components/Raster2_Supporter.jsx";
import Raster3_AiPicks from "./components/Raster3_AiPicks.jsx";
import Raster4_Money from "./components/Raster4_Money.jsx";
import Raster4b_CommunityLive from "./components/Raster4b_CommunityLive.jsx";
import Raster5_InputFeedback from "./components/Raster5_InputFeedback.jsx";
import Raster6_8Lang from "./components/Raster6_8Lang.jsx";

export default function App(){
  const [lang, setLang] = useState(()=> localStorage.getItem("tj_lang") || "de");
  useEffect(()=>{ localStorage.setItem("tj_lang", lang); }, [lang]);
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-black text-white">
 <Raster1_RentPills lang={lang} setLang={setLang} />
 <Raster2_Header lang={lang} setLang={setLang} />
 <Raster2_Supporter lang={lang} setLang={setLang} />
 <Raster3_AiPicks lang={lang} setLang={setLang} />
 <Raster4_Money lang={lang} setLang={setLang} />
 <Raster4b_CommunityLive lang={lang} setLang={setLang} />
 <Raster5_InputFeedback lang={lang} setLang={setLang} />
 <Raster6_8Lang lang={lang} setLang={setLang} />
      </div>
      <Toaster />
    </BrowserRouter>
  )
}
