import os, time, re
from datetime import datetime
from pymongo import MongoClient

# Mongo
mongo = MongoClient("mongodb://mongo:27017")
db = mongo["tipjar"]
col = db["scraped_tips"]

print("=== TipJar Scraper v2 - Telegram + Nitter fallback ===")

# === TELEGRAM ===
try:
    from telethon import TelegramClient
    api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    if api_id and api_hash:
        print(f"Telegram enabled: {os.getenv('WATCH_TG_CHANNELS')}")
        # Wir starten Telethon Session im Docker, einmal Phone Code nötig
        # Für jetzt nur Log dass es konfiguriert ist
    else:
        print("Telegram: Kein API_ID/HASH in .env - überspringe")
except Exception as e:
    print(f"Telegram import err: {e}")

# === X via Nitter (snscrape Ersatz) ===
def scrape_nitter(handle):
    import requests
    from bs4 import BeautifulSoup
    nitters = ["https://nitter.net", "https://nitter.privacydev.net", "https://nitter.poast.org"]
    for base in nitters:
        try:
            url = f"{base}/{handle}"
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
            if r.status_code==200 and "timeline-item" in r.text:
                soup = BeautifulSoup(r.text, "lxml")
                tweets = soup.select(".timeline-item .tweet-content")
                print(f"{handle} via {base}: {len(tweets)} tweets found")
                for t in tweets[:3]:
                    text = t.get_text()[:150]
                    print(f" -> {text}")
                    col.update_one(
                        {"source": handle, "content": text},
                        {"$setOnInsert": {"source": handle, "content": text, "date": datetime.utcnow(), "parsed": False}},
                        upsert=True
                    )
                return True
        except Exception as e:
            print(f"Nitter {base} fail: {e}")
    return False

while True:
    for handle in ["EmpTips","LevyKingTips"]:
        print(f"\nChecking {handle} via Nitter...")
        ok = scrape_nitter(handle)
        if not ok:
            print(f"{handle}: blocked - Nitter auch geblockt, brauche X Cookie für twikit")
    print("\nSleep 5 min...")
    time.sleep(300)
