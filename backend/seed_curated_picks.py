"""Curated Single-Picks feed (owner, 2026-07-09) — exact bookmaker legs & odds.
Replaces ALL pending hq-auto single picks with this hand-picked list.
Categories: banker (extreme confidence) / value / risk (Astana -1.5).
Bet-builder combos carry deterministic `kind` per leg so auto-settlement works.
"""
import asyncio, os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# key = (home, away) exactly as stored in DB → we reuse the real kickoff + league.
SINGLES = [
    # (home, away, market, odds, category)
    ("CSKA-Sofia", "Derry City", "Über 0.5 Tore", "1.01", "banker"),
    ("Glentoran Belfast", "Rigas Futbola skola", "Unter 3.5 Tore", "1.40", "value"),
    ("OFK Petrovac", "Zalgiris", "Zalgiris Handicap +2.5", "1.002", "banker"),
    ("Pen-y-Bont FC", "FC Santa Coloma", "Unter 3.5 Tore", "1.30", "banker"),
    ("Dinamo Tirana", "Astana", "Astana Handicap -1.5", "5.50", "risk"),
    ("Dynamo Kyiv", "Univ Cluj-Napoca", "Univ Cluj-Napoca Handicap +3.5", "1.07", "banker"),
    ("Bohemians FC", "St Joseph's (GIB)", "St Joseph's (GIB) Handicap +3.5", "1.20", "banker"),
    ("Dinamo Minsk", "Sileks Kratovo", "Unter 2.5 Tore", "1.70", "value"),
    ("Velez Mostar", "FC Milsami", "Unter 3.5 Tore", "1.17", "banker"),
    ("Sheriff Tiraspol", "NK Aluminij", "Sheriff Tiraspol Handicap -1.5", "1.95", "value"),
    ("Marsaxlokk", "Pyunik", "Unter 2.5 Tore", "1.65", "value"),
    ("AC d'Escaldes", "Mornar", "Unter 2.5 Tore", "1.67", "value"),
    ("Hegelmann Litauen", "Paide", "Paide Handicap +2.5", "1.03", "banker"),
    ("Qarabag", "Vestri", "Qarabag Handicap -1.5", "1.19", "banker"),
    ("Dila Gori", "SS Virtus", "SS Virtus Handicap +3.5", "1.22", "banker"),
    ("Nomme Kalju", "Linfield Belfast", "Über 0.5 Tore", "1.04", "banker"),
    ("FK Liepaja", "Decic Tuzi", "Über 0.5 Tore", "1.03", "banker"),
    ("Alashkert", "Yelimay Semey", "Unter 2.5 Tore", "1.60", "value"),
]

# Bet-builder combos: (home, away, market_label, combined_odds, [ (leg_market, kind, leg_odds) ... ])
COMBOS = [
    ("Hajduk Split", "MSK Zilina",
     "Über 0.5 Tore je Halbzeit (Bet-Builder)", "1.40",
     [("Über 0.5 Tore (1. Halbzeit)", "ht_o05", "1.18"),
      ("Über 0.5 Tore (2. Halbzeit)", "sh_o05", "1.19")]),
    ("Vllaznia Shkodër", "KF Malisheva",
     "Über 2.5 Tore + Doppelte Chance 12 (Bet-Builder)", "2.14",
     [("Über 2.5 Tore", "o25", "1.62"),
      ("Doppelte Chance 12", "dc_12", "1.32")]),
    ("NSÍ Runavík", "Hamrun Spartans",
     "Über 0.5 Tore (1. HZ) + Über 1.5 Tore (Bet-Builder)", "1.43",
     [("Über 0.5 Tore (1. Halbzeit)", "ht_o05", "1.18"),
      ("Über 1.5 Tore", "o15", "1.21")]),
    ("FK Sarajevo", "Inter Turku",
     "Beide Teams treffen + Doppelte Chance 1X (Bet-Builder)", "2.09",
     [("Beide Teams treffen", "btts", "1.55"),
      ("Doppelte Chance 1X", "dc_1x", "1.35")]),
    ("Stjarnan FC", "Vikingur Gota",
     "Doppelte Chance 1X + Beide Teams treffen (Bet-Builder)", "1.73",
     [("Doppelte Chance 1X", "dc_1x", "1.30"),
      ("Beide Teams treffen", "btts", "1.33")]),
    ("Caernarfon Town", "Levadia Tallinn",
     "Über 2.5 Tore + Doppelte Chance 12 (Bet-Builder)", "1.58",
     [("Über 2.5 Tore", "o25", "1.20"),
      ("Doppelte Chance 12", "dc_12", "1.32")]),
    ("Europa F.C.", "Shkendija 79",
     "Über 2.5 Tore + Beide Teams treffen (Bet-Builder)", "2.16",
     [("Über 2.5 Tore", "o25", "1.36"),
      ("Beide Teams treffen", "btts", "1.59")]),
    ("US Mondorf", "Dinamo Tbilisi",
     "Über 2.5 Tore + Doppelte Chance 12 (Bet-Builder)", "1.95",
     [("Über 2.5 Tore", "o25", "1.48"),
      ("Doppelte Chance 12", "dc_12", "1.32")]),
]

# Corner (Ecken) bet-builders — goals + corners from ONE match. `corner_o` legs are
# settled deterministically from API-Football fixture statistics. Distinct id prefix
# (hqcur-cc-) so a match can carry both a normal single and a corner builder.
CORNER_COMBOS = [
    ("Dynamo Kyiv", "Univ Cluj-Napoca",
     "Über 1.5 Tore + Über 8.5 Ecken (Bet-Builder)", "1.98",
     [("Über 1.5 Tore", "o15", "1.28"),
      ("Über 8.5 Ecken", "corner_o", "1.55")]),
    ("Qarabag", "Vestri",
     "Über 1.5 Tore + Über 8.5 Ecken (Bet-Builder)", "1.98",
     [("Über 1.5 Tore", "o15", "1.28"),
      ("Über 8.5 Ecken", "corner_o", "1.55")]),
    ("Sheriff Tiraspol", "NK Aluminij",
     "Über 2.5 Tore + Über 9.5 Ecken (Bet-Builder)", "2.98",
     [("Über 2.5 Tore", "o25", "1.70"),
      ("Über 9.5 Ecken", "corner_o", "1.75")]),
]


def _rating(cat):
    return {"banker": 9.2, "value": 8.0, "risk": 6.5}[cat]


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        print("HQ account missing"); return

    # metadata (kickoff + league) from the existing auto tips, keyed by (home, away)
    meta = {}
    for d in await db.tips.find(
            {"source": "hq-auto"}, {"_id": 0, "home_team": 1, "away_team": 1,
             "match_time": 1, "league": 1, "league_code": 1, "country": 1}).to_list(1000):
        meta.setdefault((d["home_team"], d["away_team"]),
                        (d.get("match_time"), d.get("league"), d.get("league_code"), d.get("country")))

    # wipe all current pending hq-auto single picks
    removed = (await db.tips.delete_many({"source": "hq-auto", "status": "pending"})).deleted_count
    print(f"removed {removed} old pending hq-auto tips")

    now = datetime.now(timezone.utc).isoformat()
    posted = 0

    def base_tip(home, away, market, odds, category, is_parlay):
        mt, lg, lc, cc = meta.get((home, away), (None, "TipJarHQ Pick", "", ""))
        try:
            wp = round(min(0.98, 1.0 / float(odds)), 3)
        except Exception:
            wp = 0.5
        return {
            "user_id": hq["id"], "username": "TipJarHQ", "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away, "match_time": mt,
            "country": cc or "", "league": lg or "TipJarHQ Pick", "league_code": lc or "",
            "market": market, "odds": odds, "ai_rating": _rating(category),
            "win_prob": wp, "pick_type": ("combo" if is_parlay else category),
            "category": category, "is_parlay": is_parlay, "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "curated": True, "created_at": now,
        }

    for home, away, market, odds, cat in SINGLES:
        t = base_tip(home, away, market, odds, cat, False)
        t["id"] = f"hqcur-s-{home}-{away}".replace(" ", "_")
        t["legs"] = []
        t["combo_legs"] = []
        t["ai_analysis"] = (
            f"Kuratierter TipJarHQ-Pick: {market} @ {odds}. Echte Buchmacher-Quote, "
            f"1:1 übernommen. Kategorie: {cat.upper()}."
        )
        await db.tips.insert_one(t)
        posted += 1

    for home, away, label, odds, legs in COMBOS:
        t = base_tip(home, away, label, odds, "value", True)
        t["id"] = f"hqcur-c-{home}-{away}".replace(" ", "_")
        mt, lg, lc, cc = meta.get((home, away), (None, "TipJarHQ Pick", "", ""))
        combo_legs = [{"home": home, "away": away, "market": lm, "odds": float(lo),
                       "kind": lk, "team": ""} for (lm, lk, lo) in legs]
        t["combo_legs"] = combo_legs
        t["legs"] = [{
            "match": f"{home} – {away}", "league": lg or "", "kickoff": mt,
            "selections": [lm for (lm, _, _) in legs],
            "sel_odds": [lo for (_, _, lo) in legs],
        }]
        t["ai_analysis"] = (
            f"Kuratierter TipJarHQ-Bet-Builder: {label} @ {odds}. Echte Buchmacher-Quote, "
            f"1:1 übernommen. Kategorie: VALUE."
        )
        await db.tips.insert_one(t)
        posted += 1

    for home, away, label, odds, legs in CORNER_COMBOS:
        t = base_tip(home, away, label, odds, "value", True)
        t["id"] = f"hqcur-cc-{home}-{away}".replace(" ", "_")
        mt, lg, lc, cc = meta.get((home, away), (None, "TipJarHQ Pick", "", ""))
        combo_legs = [{"home": home, "away": away, "market": lm, "odds": float(lo),
                       "kind": lk, "team": ""} for (lm, lk, lo) in legs]
        t["combo_legs"] = combo_legs
        t["legs"] = [{
            "match": f"{home} – {away}", "league": lg or "", "kickoff": mt,
            "selections": [lm for (lm, _, _) in legs],
            "sel_odds": [lo for (_, _, lo) in legs],
        }]
        t["ai_analysis"] = (
            f"Kuratierter TipJarHQ-Bet-Builder mit Ecken-Markt: {label} @ {odds}. "
            f"Der Ecken-Leg wird automatisch aus den Spielstatistiken abgerechnet. Kategorie: VALUE."
        )
        await db.tips.insert_one(t)
        posted += 1

    print(f"posted {posted} curated tips ({len(SINGLES)} singles + {len(COMBOS)} combos "
          f"+ {len(CORNER_COMBOS)} corner-builders)")


if __name__ == "__main__":
    asyncio.run(main())
