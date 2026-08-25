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
import Raster6_BLang from "./components/Raster6_BLang.jsx";

class Err extends React.Component{
  state={e:null}
  static getDerivedStateFromError(e){return {e}}
  render(){
    if(this.state.e) return <div style={{background:'white', color:'red', padding:'20px', whiteSpace:'pre-wrap', fontSize:'14px', minHeight:'100vh'}}><b>CRASH in {this.props.name}:</b>{String(this.state.e)}<br/><br/>{this.state.e?.stack}</div>
    return this.props.children
  }
}

export default function App(){
  const [lang, setLang] = useState(()=> localStorage.getItem("tj_lang") || "de");
  useEffect(()=>{ localStorage.setItem("tj_lang", lang); }, [lang]);
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-black text-white">
        <Err name="Raster1_RentPills"><Raster1_RentPills lang={lang} setLang={setLang} /></Err>
        <Err name="Raster2_Header"><Raster2_Header lang={lang} setLang={setLang} /></Err>
        <Err name="Raster2_Supporter"><Raster2_Supporter lang={lang} setLang={setLang} /></Err>
        <Err name="Raster3_AiPicks"><Raster3_AiPicks lang={lang} setLang={setLang} /></Err>
        <Err name="Raster4_Money"><Raster4_Money lang={lang} setLang={setLang} /></Err>
        <Err name="Raster4b_CommunityLive"><Raster4b_CommunityLive lang={lang} setLang={setLang} /></Err>
        <Err name="Raster5_InputFeedback"><Raster5_InputFeedback lang={lang} setLang={setLang} /></Err>
        <Err name="Raster6_BLang"><Raster6_BLang lang={lang} setLang={setLang} /></Err>
      </div>
      <Toaster />
    </BrowserRouter>
  )
}
