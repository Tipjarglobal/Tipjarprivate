from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime,timedelta
import os
app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"],allow_credentials=True)
db=MongoClient(os.getenv("MONGO_URL","mongodb://mongo:27017/tipjar")).get_default_database()
JARS=[{"id":"GLASS","reward":40,"rarity":"COMMON"},{"id":"WOOD","reward":50,"rarity":"COMMON"},{"id":"STONE","reward":60,"rarity":"COMMON"},{"id":"CLAY","reward":70,"rarity":"COMMON"},{"id":"BAMBOO","reward":75,"rarity":"COMMON"},{"id":"CARTON BOX","reward":80,"rarity":"COMMON"},{"id":"PAPER","reward":85,"rarity":"COMMON"},{"id":"PLASTIC","reward":90,"rarity":"COMMON"},{"id":"CERAMIC","reward":95,"rarity":"COMMON"},{"id":"WICKER","reward":100,"rarity":"COMMON"},{"id":"BRONZE","reward":110,"rarity":"UNCOMMON"},{"id":"IRON","reward":120,"rarity":"UNCOMMON"},{"id":"TIN","reward":150,"rarity":"UNCOMMON"},{"id":"ZINC","reward":180,"rarity":"UNCOMMON"},{"id":"COPPER","reward":200,"rarity":"UNCOMMON"},{"id":"ALUMINUM","reward":220,"rarity":"UNCOMMON"},{"id":"STEEL","reward":250,"rarity":"UNCOMMON"},{"id":"LEAD","reward":280,"rarity":"UNCOMMON"},{"id":"SILVER","reward":350,"rarity":"RARE"},{"id":"GOLD","reward":500,"rarity":"RARE"},{"id":"CRYSTAL","reward":650,"rarity":"RARE"},{"id":"RUBY","reward":800,"rarity":"RARE"},{"id":"SAPPHIRE","reward":950,"rarity":"RARE"},{"id":"EMERALD","reward":1100,"rarity":"RARE"},{"id":"DIAMOND","reward":1500,"rarity":"RARE"},{"id":"VOID","reward":2000,"rarity":"LEGENDARY"},{"id":"COSMIC","reward":3000,"rarity":"LEGENDARY"},{"id":"QUANTUM","reward":5000,"rarity":"LEGENDARY"},{"id":"INFINITY","reward":8000,"rarity":"LEGENDARY"},{"id":"ORIGIN","reward":12000,"rarity":"LEGENDARY"}]
def seed():
 if db.tips.count_documents({})==0:
  now=datetime.utcnow()
  db.tips.insert_many([{"id":"SEED-QA-DANGER","source":"ai","status":"live","live_danger":True,"ai_rating":2.5,"category":"risk","home_team":"PAOK","away_team":"AEK","league":"Super League Greece","market":"Over 2.5","odds":1.95,"match_time":now.isoformat(),"avg_rating":4.2,"ratings_count":12,"live_category":"banger"},{"id":"SEED-QA-MASTER-LIVE","source":"master","status":"live","home_team":"Portugal","away_team":"Messi Team","market":"1","odds":2.0,"league":"Showcase","match_time":now.isoformat(),"master_tab":"live","avg_rating":4.8,"ratings_count":34},{"id":"SEED-AI-BANKER-1","source":"ai","status":"pending","category":"banker","live_category":"banker","home_team":"Bayern","away_team":"Dortmund","league":"Bundesliga","market":"1","odds":1.65,"ai_rating":4.5,"avg_rating":4.6,"ratings_count":89,"match_time":(now+timedelta(hours=5)).isoformat()},{"id":"SEED-AI-VALUE-1","source":"ai","status":"pending","category":"value","live_category":"value","home_team":"Liverpool","away_team":"Arsenal","league":"Premier League","market":"X2","odds":2.2,"ai_rating":4.0,"avg_rating":4.1,"ratings_count":45,"match_time":(now+timedelta(hours=26)).isoformat()}])
@app.on_event("startup")
def startup(): seed()
@app.get("/api/health")
def health(): return {"ok":True}
@app.get("/api/tips")
def get_tips(source:str=None,status:str=None,window:str=None,category:str=None,sort:str="new"):
 seed()
 q={}
 if source: q["source"]=source
 if status: q["status"]=status
 if category: q["$or"]=[{"category":category},{"live_category":category}]
 now=datetime.utcnow()
 if window=="24": q["match_time"]={"$gte":now.isoformat(),"$lte":(now+timedelta(hours=24)).isoformat()}
 elif window=="48": q["match_time"]={"$gte":(now+timedelta(hours=24)).isoformat(),"$lte":(now+timedelta(hours=48)).isoformat()}
 elif window=="48plus": q["match_time"]={"$gte":(now+timedelta(hours=48)).isoformat()}
 tips=list(db.tips.find(q,{"_id":0}).sort("match_time",1).limit(100))
 if sort=="hype": tips=sorted(tips,key=lambda x:x.get("ratings_count",0),reverse=True)
 if sort=="top": tips=sorted(tips,key=lambda x:x.get("avg_rating",0),reverse=True)
 return tips
@app.get("/api/tips/counts")
def counts(category:str=None):
 seed()
 now=datetime.utcnow()
 def cnt(q): return db.tips.count_documents(q)
 base={}
 if category: base["$or"]=[{"category":category},{"live_category":category}]
 return {"community_live":cnt({"source":"community","status":"live"}),"ai_now":cnt({**base,"source":"ai","match_time":{"$gte":now.isoformat(),"$lte":(now+timedelta(hours=24)).isoformat()}}),"ai_24_48":cnt({**base,"source":"ai","match_time":{"$gte":(now+timedelta(hours=24)).isoformat(),"$lte":(now+timedelta(hours=48)).isoformat()}}),"ai_48plus":cnt({**base,"source":"ai","match_time":{"$gte":(now+timedelta(hours=48)).isoformat()}}),"ai_total":cnt({**base,"source":"ai"}),"banker":cnt({"live_category":"banker","status":"live"}),"value":cnt({"live_category":"value","status":"live"}),"banger":cnt({"live_category":"banger","status":"live"}),"won":cnt({"status":"won"}),"lost":cnt({"status":"lost"}),"cashed":0,"bestwon":0,"void":0}
@app.post("/api/tips/{tip_id}/rate")
def rate(tip_id:str,p:dict):
 tip=db.tips.find_one({"id":tip_id})
 if not tip: raise HTTPException(404)
 s=p.get("stars",5)
 c=tip.get("ratings_count",0)+1
 avg=(tip.get("avg_rating",0)*tip.get("ratings_count",0)+s)/c
 db.tips.update_one({"id":tip_id},{"$set":{"avg_rating":round(avg,2),"ratings_count":c}})
 return {"ok":True}
@app.post("/api/tips/{tip_id}/settle")
def settle(tip_id:str,p:dict):
 db.tips.update_one({"id":tip_id},{"$set":{"status":p.get("status")}})
 return {"ok":True}
@app.post("/api/tips/blacklist")
def bl(p:dict):
 db.blacklist.insert_one({**p,"at":datetime.utcnow().isoformat()})
 return {"ok":True}
@app.get("/api/jars/list")
def jl(): return JARS
@app.get("/api/battery/status")
@app.get("/api/jars/mine")
def mine(user_id:str="demo"):
 u=db.users.find_one({"id":user_id}) or {"id":user_id,"balance":9999,"jars":[]}
 return {"coins":u["balance"],"balance":u["balance"],"jars":u["jars"],"user_jars":u["jars"]}
@app.post("/api/jars/buy")
def buy(p:dict):
 uid=p.get("user_id","demo"); jid=p.get("jar_id")
 jar=next((j for j in JARS if j["id"]==jid),None)
 if not jar: raise HTTPException(404)
 cost=int(jar["reward"]*0.75)
 u=db.users.find_one({"id":uid}) or {"id":uid,"balance":9999,"jars":[]}
 if u["balance"]<cost: raise HTTPException(400,"no coins")
 if any(x["jar_id"]==jid for x in u["jars"]): raise HTTPException(400,"owned")
 u["balance"]-=cost; u["jars"].append({"jar_id":jid,"fill":0})
 db.users.update_one({"id":uid},{"$set":u},upsert=True)
 return {"ok":True,"balance":u["balance"],"jars":u["jars"]}
@app.get("/api/pills/list")
def pills(): return [{"id":"RENT","price":100},{"id":"BOOST","price":250}]
@app.get("/api/tips/active")
def active(): return list(db.tips.find({},{"_id":0}).limit(10))
@app.get("/api/tips/mine")
def mine_tips(): return []
