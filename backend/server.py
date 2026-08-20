from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import re
load_dotenv(Path(__file__).parent / '.env')
app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
def norm(s): return str(s).lower().replace("ueber","über").replace("over","über")
def parse(s):
    m=re.search(r'(.+?)\s*über\s*(\d+(?:\.\d+)?)',norm(s))
    return (m.group(1).strip(),float(m.group(2))) if m else None
@app.get("/")
def root(): return {"ok":True,"v":"6.4-standalone"}
@app.post("/api/predict")
def predict(p: dict):
    legs=p.get("legs",[])
    flat=[str(x) for x in legs if x]
    has_btts=any("btts" in norm(x) for x in flat)
    tmap={}; others=[]; btts=[]
    for l in flat:
        if "btts" in norm(l): btts.append(l); continue
        pp=parse(l)
        if pp: tmap.setdefault(pp[0],[]).append((pp[1],l))
        else: others.append(l)
    keep=[]; drop=[]
    for vals in tmap.values():
        vals=sorted(vals,key=lambda x:x[0])
        keep.append(vals[-1][1])
        drop.extend([o for _,o in vals[:-1]])
    if has_btts:
        keep=[k for k in keep if not (parse(k) and parse(k)[1]==0.5)]
        for k in flat:
            pp=parse(k)
            if pp and pp[1]==0.5:
                if k not in drop: drop.append(k)
    keep=list(dict.fromkeys(keep+btts+others))
    drop=[d for d in drop if d not in keep]
    return {"input":legs,"deduped":keep,"dropped":drop,"precise":True}
if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8001)
