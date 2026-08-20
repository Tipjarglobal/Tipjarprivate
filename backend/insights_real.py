from fastapi import APIRouter
router = APIRouter()
EXPERTS = ["Orion","Vega","Nova","Sirius","Polaris","TipJarAdmin","tipjarlogic","admin"]

@router.get("/api/insights/real")
async def real_insights():
    real_filter = {"username": {"$nin": EXPERTS}, "email": {"$exists": True, "$ne": None}}
    total_real = await db.users.count_documents(real_filter)
    total_views = await db.tips.aggregate([{"$group":{"_id":None,"sum":{"$sum":"$views"}}}]).to_list(1)
    return {
        "registered_real": total_real,
        "views_total": total_views[0]["sum"] if total_views else 0,
        "experts_excluded": EXPERTS
    }
