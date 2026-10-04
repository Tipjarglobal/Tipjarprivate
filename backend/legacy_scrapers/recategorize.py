"""One-off migration: recategorise all pending TipJarHQ single picks into the
new Banker / Value / Risk buckets (owner rule 2026-06):
  • RISK  = ONLY favourite -1.5 handicaps (realistic odds, capped at 2.75).
  • VALUE = the sweet-spot 1.40–2.60 tips + bet-builder combos (1.40–3.0).
  • BANKER = very safe low-odds picks (win-prob >= 0.85).
Junk (high-odds Über/Unter goals, 4-leg combos > 3.0, coin-flips) is deleted.
Removes the duplicate 'Handicap -1.5' (plain) variant, keeping '-1.5 (Handicap)'.
"""
import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()


def _float(v, d=0.0):
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return d


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    docs = await db.tips.find(
        {"source": "hq-auto", "status": "pending"}).to_list(2000)
    to_value = to_banker = to_risk = deleted = capped = 0
    for d in docs:
        ml = (d.get("market") or "").lower().strip()
        odd = _float(d.get("odds"))
        wp = _float(d.get("win_prob"))
        is_parlay = bool(d.get("is_parlay"))
        tid = d["id"]

        # drop the duplicate plain 'Handicap -1.5' variant (generator removed)
        if not is_parlay and ml.endswith("handicap -1.5"):
            await db.tips.delete_one({"id": tid})
            deleted += 1
            continue

        # RISK: favourite -1.5 handicaps only
        if not is_parlay and "-1.5" in ml and "handicap" in ml:
            upd = {"category": "risk", "pick_type": "risk"}
            if odd > 2.75:
                upd["odds"] = "2.60"
                upd["win_prob"] = 0.40
                capped += 1
            await db.tips.update_one({"id": tid}, {"$set": upd})
            to_risk += 1
            continue

        # VALUE: bet-builder combos in the nice range
        if is_parlay:
            if 1.40 <= odd <= 3.0:
                await db.tips.update_one(
                    {"id": tid}, {"$set": {"category": "value", "pick_type": "combo"}})
                to_value += 1
            else:
                await db.tips.delete_one({"id": tid})
                deleted += 1
            continue

        # VALUE: single picks in the sweet spot
        if 1.40 <= odd <= 2.60 and wp >= 0.42:
            await db.tips.update_one(
                {"id": tid}, {"$set": {"category": "value", "pick_type": "value"}})
            to_value += 1
            continue

        # BANKER: safe low-odds picks
        if wp >= 0.85 and odd >= 1.03:
            await db.tips.update_one(
                {"id": tid}, {"$set": {"category": "banker", "pick_type": "banker"}})
            to_banker += 1
            continue

        # everything else = junk
        await db.tips.delete_one({"id": tid})
        deleted += 1

    print(f"value={to_value} banker={to_banker} risk={to_risk} "
          f"capped_odds={capped} deleted={deleted} total={len(docs)}")


if __name__ == "__main__":
    asyncio.run(main())
