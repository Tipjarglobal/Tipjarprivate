"""One-off cleanup: keep only the single smartest hq-auto tip per match.
Groups pending hq-auto (forebet) tips by (home,away,match_time) and deletes all
but the one with the best rating × odds, matching the new one-pick-per-match rule."""
import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _score(t):
    try:
        return (round(float(t.get("ai_rating") or 0) * float(t.get("odds") or 0), 3),
                float(t.get("odds") or 0))
    except Exception:
        return (0.0, 0.0)


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    tips = await db.tips.find(
        {"source": "hq-auto", "status": "pending"}, {"_id": 0}).to_list(5000)
    groups = {}
    for t in tips:
        key = (t.get("home_team"), t.get("away_team"), t.get("match_time"))
        groups.setdefault(key, []).append(t)
    to_delete = []
    for key, grp in groups.items():
        if len(grp) < 2:
            continue
        grp.sort(key=_score, reverse=True)
        keep = grp[0]
        for t in grp[1:]:
            to_delete.append(t["id"])
        print(f"KEEP {keep['home_team']} v {keep['away_team']}: {keep['market']} "
              f"({keep['ai_rating']}) — removing {len(grp)-1} dup(s)")
    if to_delete:
        res = await db.tips.delete_many({"id": {"$in": to_delete}})
        print(f"Deleted {res.deleted_count} duplicate tips")
    else:
        print("No duplicates found")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
