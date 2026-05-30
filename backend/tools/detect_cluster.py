

from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException

from backend.db.mongo import async_db


def _confidence(contacts: list) -> float:
    if not contacts:
        return 0.0
    total = len(contacts)
    in_peak   = sum(1 for c in contacts if 5 <= c.get("monitoringDay", 0) <= 10)
    symptomatic = sum(1 for c in contacts if c.get("symptoms"))
    missed    = sum(c.get("missedFollowups", 0) for c in contacts)

    base       = min(total * 0.15, 0.60)
    symp_bonus = (symptomatic / total) * 0.25 if total else 0
    peak_bonus = (in_peak / total) * 0.10 if total else 0
    miss_bonus = min(missed * 0.03, 0.10)

    return min(round(base + symp_bonus + peak_bonus + miss_bonus, 3), 0.99)


async def detect_cluster(
    exposure_event_id: Optional[str] = None,
    district: Optional[str] = None
) -> dict:

    NOW = datetime.utcnow()

    # ── Build match stage ────────────────────────────────────
    if exposure_event_id:
        try:
            oid = ObjectId(exposure_event_id)
        except Exception:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid exposure_event_id: {exposure_event_id}"
            )
        match = {"$match": {"exposureEvents": {"$in": [oid]}}}
        ev = await async_db["exposure_events"].find_one({"_id": oid})
        event_name = ev.get("name", "Unknown event") if ev else "Unknown event"

    elif district:
        match = {"$match": {"district": district, "riskScore": {"$gt": 60}}}
        event_name = f"District cluster: {district}"

    else:
        match = {"$match": {
            "monitoringDay": {"$gte": 5, "$lte": 10},
            "symptoms": {"$ne": []},
            "riskScore": {"$gt": 65}
        }}
        event_name = "Auto-detected symptomatic cluster"

    # ── The aggregation pipeline (shown to judges in README) ──
    pipeline = [
        match,
        {"$lookup": {
            "from": "follow_ups",
            "localField": "_id",
            "foreignField": "contactId",
            "as": "followups"
        }},
        {"$addFields": {
            "missedFollowups": {
                "$size": {"$filter": {
                    "input": "$followups",
                    "cond": {"$and": [
                        {"$eq": ["$$this.completed", False]},
                        {"$lt": ["$$this.dueDate", NOW]}
                    ]}
                }}
            },
            "completedFollowups": {
                "$size": {"$filter": {
                    "input": "$followups",
                    "cond": {"$eq": ["$$this.completed", True]}
                }}
            }
        }},
        {"$lookup": {
            "from": "operational_topology",
            "localField": "assignedCHW",
            "foreignField": "_id",
            "as": "chw_data"
        }},
        {"$addFields": {
            "chwHeartbeat": {
                "$ifNull": [{"$arrayElemAt": ["$chw_data.heartbeatScore", 0]}, 0]
            },
            "chwStatus": {
                "$ifNull": [{"$arrayElemAt": ["$chw_data.status", 0]}, "unknown"]
            }
        }},
        {"$sort": {"riskScore": -1}},
        {"$project": {
            "followups": 0,
            "chw_data": 0,
            "phone": 0  # PII isolation
        }}
    ]

    contacts = await async_db["contacts"].aggregate(pipeline).to_list(length=100)

    if not contacts:
        return {
            "cluster_detected": False,
            "contact_count": 0,
            "confidence": 0.0,
            "message": "No cluster contacts found for given criteria"
        }

    # ── Serialize ObjectIds and dates ────────────────────────
    serialized = []
    for c in contacts:
        sc = dict(c)
        sc["_id"] = str(sc["_id"])
        sc["assignedCHW"] = str(sc.get("assignedCHW", ""))
        sc["exposureEvents"] = [str(e) for e in sc.get("exposureEvents", [])]
        for df in ["monitoringStartDate", "monitoringEndDate",
                   "lastVisited", "symptomOnsetDate", "createdAt"]:
            if sc.get(df):
                sc[df] = sc[df].isoformat()
        serialized.append(sc)

    confidence   = _confidence(serialized)
    symptomatic  = sum(1 for c in serialized if c.get("symptoms"))
    missed_total = sum(c.get("missedFollowups", 0) for c in serialized)
    districts    = list(set(c.get("district") for c in serialized))

    # ── Store alert ──────────────────────────────────────────
    await async_db["operational_alerts"].insert_one({
        "alertType": "cluster_detected",
        "eventName": event_name,
        "contactCount": len(serialized),
        "symptomaticCount": symptomatic,
        "missedFollowups": missed_total,
        "confidence": confidence,
        "districts": districts,
        "contactRefs": [c.get("contactRef") for c in serialized],
        "createdAt": NOW
    })

    return {
        "cluster_detected": True,
        "event_name": event_name,
        "contact_count": len(serialized),
        "symptomatic_count": symptomatic,
        "missed_followups": missed_total,
        "confidence_score": confidence,
        "confidence_percent": f"{int(confidence * 100)}%",
        "districts_affected": districts,
        "contacts": serialized,
        "message": (
            f"CLUSTER ALERT — {len(serialized)} contacts | "
            f"Confidence: {int(confidence * 100)}% | "
            f"{symptomatic} symptomatic | "
            f"{missed_total} missed follow-ups"
        )
    }