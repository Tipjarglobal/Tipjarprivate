import React, { createContext, useContext, useState } from "react";
const Ctx = createContext(null);
export function AuthProvider({children}){
  const [user,setUser]=useState(null);
  const logout=()=>{ setUser(null); try{localStorage.removeItem("token");}catch{} };
  const login=(u)=>setUser(u);
  return <Ctx.Provider value={{user,setUser,login,logout}}>{children}</Ctx.Provider>
}
export function useAuth(){
  const c=useContext(Ctx);
  if(!c) return {user:null, logout:()=>{}, login:()=>{}};
  return c;
}
