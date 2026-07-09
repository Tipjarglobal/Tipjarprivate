"""Curated Smart-Pick reports (owner, 2026-07-09). One report card per match from
the owner's WC analysis notebook — posted WITHOUT the 48h-fixture requirement
(player props / qualify markets have no auto-fixture). Protected via 'smart-' id
prefix so the startup cleanup never wipes them. Plus a re-written iShowSpeed note.
"""
import asyncio, os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

REPORTS = [
    {
        "id": "smart-rep-fra-mar",
        "home": "Frankreich", "away": "Marokko", "rating": 8.5,
        "market": "El Aynaoui 1+ Foul · Doué/Barcola 1+ Schuss · Über 1 Tor",
        "analysis": (
            "⚽ Frankreich – Marokko | 4er-Analyse\n"
            "① El Aynaoui 1+ Foul: Der Motor Marokkos vor der Abwehr foult bei jeder "
            "Gelegenheit – Ø 2,25 Fouls/Spiel, 11 bei dieser WM (5 vs. Niederlande, 4 vs. "
            "Brasilien). Gerade gegen große Teams gnadenlos.\n"
            "② Doué 1+ Schuss: Ø 3,83 Schüsse/Spiel, 2+ in seinen letzten 8 Startelf-Einsätzen.\n"
            "③ Barcola 1+ Schuss: Ø 3,67 Schüsse/Spiel, 1 Schuss in 30/30 Spielen.\n"
            "④ Über 1 Tor: Frankreich – außer dem 1:0 vs. Paraguay – davor 17 Spiele in Folge "
            "2+ Tore und seit 2024 immer ≥2 Tore im Spiel. Marokko in 10/11 Spielen über 1 Tor.\n"
            "ℹ️ Hinweis: Entweder Barcola oder Doué startet – beide sind aufgenommen, einer "
            "wird void, damit die Quote nicht fällt."
        ),
    },
    {
        "id": "smart-rep-esp-bel",
        "home": "Spanien", "away": "Belgien", "rating": 8.0,
        "market": "Spanien qualifiziert sich · Cucurella 1+ Foul",
        "analysis": (
            "⚽ Spanien – Belgien | Analyse\n"
            "① Spanien qualifiziert sich: In 2,5 Jahren nur 1 Pflichtspiel verloren (Portugal, "
            "Nations-League-Finale). Klarer Favorit – wir erwarten den Aufstieg.\n"
            "② Cucurella 1+ Foul: Foult am meisten im spanischen Team (Ø 1,29/Spiel) und trifft "
            "auf Doku, der Ø 4,46 Fouls zieht (2+ in 10/11 seiner letzten Spiele)."
        ),
    },
    {
        "id": "smart-rep-nor-eng",
        "home": "Norwegen", "away": "England", "rating": 8.0,
        "market": "Kane 1+ Schuss aufs Tor · Beide Teams treffen",
        "analysis": (
            "⚽ Norwegen – England | Analyse\n"
            "① Kane 1+ Schuss aufs Tor: 6 Tore bei dieser WM, in Topform neben Bellingham. "
            "SOT in 16/17 Länderspielen, Ø über 2 pro Spiel.\n"
            "② Beide Teams treffen: Haaland und Kane brandgefährlich. Norwegen BTTS in den "
            "letzten 7 Spielen. England kassierte schon gegen Kroatien, Kongo und Mexiko – "
            "Haaland 90 Minuten draußen zu halten, glauben wir nicht."
        ),
    },
    {
        "id": "smart-rep-arg-sui",
        "home": "Argentinien", "away": "Schweiz", "rating": 7.5,
        "market": "Schweiz Über 1,5 Schüsse aufs Tor · Argentinien qualifiziert sich",
        "analysis": (
            "⚽ Argentinien – Schweiz | Analyse\n"
            "① Schweiz Über 1,5 Schüsse aufs Tor: 2+ SOT in 28/30 Spielen. Argentinien geht "
            "wohl in Führung, die Schweiz muss aufmachen → Schüsse aufs Tor kommen.\n"
            "② Argentinien qualifiziert sich: Zuletzt ein paar Wackler und nicht überragend, "
            "aber mit Messi vorne trauen wir ihnen den souveränen Auftritt zu."
        ),
    },
    {
        "id": "smart-note-ishowspeed",
        "home": "Der iShowSpeed-Fluch", "away": "", "rating": 6.0,
        "market": "Fun-Fact: Tippe gegen das Team, das iShowSpeed unterstützt 🎽",
        "analysis": (
            "😅 Spaß-Tipp mit ernstem Kern – der 'iShowSpeed-Fluch':\n"
            "Immer dort, wo iShowSpeed das Trikot überstreift und lautstark mitfiebert, läuft "
            "es für sein Team am Ende schief. Der Fluch ist inzwischen fast Kult.\n"
            "👉 Unsere Lesart: Setz auf das Team, das er NICHT unterstützt – genau das "
            "qualifiziert sich meistens. Kein Datenmodell, nur Aberglaube mit Augenzwinkern. 🍀"
        ),
    },
]


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        print("HQ account missing"); return
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    for i, r in enumerate(REPORTS):
        tip = {
            "id": r["id"], "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": r["home"], "away_team": r["away"],
            "match_time": "", "country": "", "league": "TipJarHQ Smart Pick", "league_code": "",
            "market": r["market"], "odds": "", "ai_rating": r["rating"],
            "ai_analysis": r["analysis"], "legs": [], "is_parlay": False,
            "stake": "", "potential_return": "", "status": "pending",
            "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "smart", "smart_idea": True, "idea_by": "TipJarHQ",
            "curated": True, "created_at": now,
        }
        await db.tips.replace_one({"id": r["id"]}, tip, upsert=True)
        n += 1
    print(f"seeded {n} smart-pick reports")


if __name__ == "__main__":
    asyncio.run(main())
