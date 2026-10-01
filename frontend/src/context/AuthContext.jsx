import React, { createContext, useContext, useState, useEffect } from 'react'
const AuthContext = createContext({user:null, login:()=>{}, logout:()=>{}, loading:false})
export const useAuth = () => useContext(AuthContext)
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  useEffect(()=>{
    try{
      const s=localStorage.getItem('tipjar_user')
      if(s) setUser(JSON.parse(s))
    }catch{}
  },[])
  const login=(u)=>{setUser(u); try{localStorage.setItem('tipjar_user',JSON.stringify(u))}catch{}}
  const logout=()=>{setUser(null); try{localStorage.removeItem('tipjar_user')}catch{}}
  return <AuthContext.Provider value={{user, login, logout, loading:false}}>{children}</AuthContext.Provider>
}
