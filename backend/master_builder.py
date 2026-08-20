import re
from collections import defaultdict
from datetime import datetime, timedelta
from pymongo import MongoClient
import os

MONGO_URL=os.getenv("MONGO_URL","mongodb://mongo:27017")
DB_NAME=os.getenv("DB_NAME","tipjar")
db=MongoClient(MONGO_URL)[DB_NAME]

MARKETS=[
  ("1-3_goals","{team} trifft 1-3 Tore", 1.85),
  ("dc_u45","{team} verliert nicht + Unter 4.5", 1.72),
  ("score_dc","{team} trifft + verliert nicht", 1.65)
]

def norm(s): return re.sub(r'\s+',' ',str(s).upper().strip()) if s else ""

def parse_match_time(doc):
    for key in ["match_time","kickoff","date","datetime","start_time","commence_time"]:
        val=doc.get(key)
        if not val: continue
        if isinstance(val, datetime):
            return val.replace(tzinfo=None) if val.tzinfo else val
        try:
            return datetime.fromisoformat(str(val).replace("Z","+00:00")).replace(tzinfo=None)
        except: pass
    return None

def calc_odds(base, conf, mid):
    conf=int(conf or 60)
    adj=(75-conf)*0.015
    odds=base+adj
    mn,mx={"1-3_goals":(1.62,2.25),"dc_u45":(1.50,2.05),"score_dc":(1.48,1.95)}.get(mid,(1.5,2.2))
    return round(max(mn,min(mx,odds)),2)

def run_master_builder():
    grouped=defaultdict(list)
    for doc in db.match_predictions.find().sort("created_at",-1).limit(800):
        h=norm(doc.get("home") or doc.get("home_team") or doc.get("team1"))
        a=norm(doc.get("away") or doc.get("away_team") or doc.get("team2"))
        if not h or not a:
            m=doc.get("match") or ""
            if "-" in m: p=m.split("-"); h=norm(p[0]); a=norm(p[1]) if len(p)>1 else ""
        if not h or not a: continue
        grouped[f"{h} vs {a}"].append(doc)

    scored=[]
    for k,docs in grouped.items():
        h,a=k.split(" vs ")
        fav=str(docs[0].get("fav") or docs[0].get("pred") or "home").lower()
        team=h if "home" in fav or fav==h.lower() else a
        if not team: team=h

        real_time=None
        for d in docs:
            real_time=parse_match_time(d)
            if real_time: break
        if not real_time: continue
        if real_time < datetime.utcnow() + timedelta(hours=1): continue

        score=len(docs)*20 + int(docs[0].get("p",50) or 50)
        scored.append((score,k,h,a,team,docs,real_time))

    scored=sorted(scored,key=lambda x:x[0],reverse=True)
    unique=[]
    seen=set()
    for score,k,h,a,team,docs,real_time in scored:
        if k in seen: continue
        seen.add(k)
        unique.append((k,h,a,team,docs,real_time))
        if len(unique)>=8: break

    unique=sorted(unique,key=lambda x:x[5]) # nach echter Zeit sortieren

    now=datetime.utcnow()
    result=[]
    for i,(k,h,a,team,docs,real_time) in enumerate(unique):
        mid,tmpl,base=MARKETS[i % len(MARKETS)]
        conf=docs[0].get("p",65)
        diff=(real_time.date()-now.date()).days
        day="today" if diff<=0 else "tomorrow" if diff==1 else "overmorrow"
        result.append({"match":k,"home":h,"away":a,"team":team,"market":mid,"tmpl":tmpl,"day":day,"real_time":real_time,"odds":calc_odds(base,conf,mid),"conf":conf})

    db.tips.delete_many({"consensus":True})
    c=0
    for p in result:
        db.tips.insert_one({
          "id": f"consensus-{now.timestamp()}-{p['match']}-{p['market']}",
          "home_team":p["home"],"away_team":p["away"],"league":"Consensus Master",
          "market":p["market"],"pick":p["tmpl"].format(team=p["team"].title()),
          "odds":p["odds"],"ai_rating":8 if p["conf"]<70 else 9,
          "analysis": f"🔥 MASTER {len(grouped)} Gruppen | {p['match']} - {p['team'].title()} | {p['real_time'].strftime('%d.%m %H:%M')} | {p['conf']}%",
          "status":"pending","match_time":p["real_time"],"created_at":now,
          "expiry":p["real_time"]-timedelta(minutes=15),"consensus":True,"day":p["day"]
        })
        c+=1
    print({"posted":c,"groups":len(grouped),"unique":len(unique)})
    return {"posted":c}

if __name__=="__main__":
    run_master_builder()
