import React, { createContext, useContext, useState } from "react";
export const LANGUAGES = [{code:"de",flag:"🇩🇪",label:"Deutsch"},{code:"en",flag:"🇬🇧",label:"English"},{code:"es",flag:"🇪🇸",label:"Español"},{code:"fr",flag:"🇫🇷",label:"Français"},{code:"it",flag:"🇮🇹",label:"Italiano"},{code:"pt",flag:"🇵🇹",label:"Português"},{code:"tr",flag:"🇹🇷",label:"Türkçe"},{code:"ru",flag:"🇷🇺",label:"Русский"}];
export const TIMEZONES = [{tz:"Europe/Berlin",label:"Berlin / CET"},{tz:"UTC",label:"UTC"}];
const Ctx = createContext(null);
export function I18nProvider({children}){
  const [lang,setLangState]=useState(()=>{try{return localStorage.getItem("tj_lang")||"de"}catch{return "de"}});
  const [tz,setTzState]=useState(()=>{try{return localStorage.getItem("tj_tz")||"Europe/Berlin"}catch{return "Europe/Berlin"}});
  const setLang=(l)=>{try{localStorage.setItem("tj_lang",l)}catch{}; setLangState(l);};
  const setTz=(t)=>{try{localStorage.setItem("tj_tz",t)}catch{}; setTzState(t);};
  const t=(k)=>k;
  return <Ctx.Provider value={{t,lang,setLang,tz,setTz}}>{children}</Ctx.Provider>
}
export function useI18n(){ const c=useContext(Ctx); if(!c) return {t:(k)=>k, lang:"de", setLang:()=>{}, tz:"Europe/Berlin", setTz:()=>{}}; return c; }
