

from datetime import datetime
from typing import Optional
from fastapi import HTTPException

from backend.db.mongo import async_db


async def get_contact_risk_profile(
    contact_ref: Optional[str] = None,
    contact_name: Optional[str] = None,
    include_pii: bool = False
) -> dict:

    if not contact_ref and not contact_name:
        raise HTTPException(
            status_code=422,
            detail="Provide contact_ref (e.g. R-027) or contact_name"
        )

    query = {"contactRef": contact_ref} if contact_ref else \
            {"name": {"$regex": contact_name, "$options": "i"}}

    # PII isolation: strip phone unless explicitly requested
    projection = {} if include_pii else {"phone": 0}

    contact = await async_db["contacts"].find_one(query, projection)
    if not contact:
        raise HTTPException(
            status_code=404,
            detail=f"Contact not found: {contact_ref or contact_name}"
        )

    # CHW status
    chw_summary = None
    if contact.get("assignedCHW"):
        chw = await async_db["operational_topology"].find_one(
            {"_id": contact["assignedCHW"]},
            {"phone": 0}
        )
        if chw:
            chw_summary = {
                "name": chw.get("name"),
                "chwId": chw.get("chwId"),
                "heartbeatScore": chw.get("heartbeatScore"),
                "status": chw.get("status"),
                "lastReport": chw["lastReport"].isoformat() if chw.get("lastReport") else None,
                "supervisorName": chw.get("supervisorName"),
                "coverageGapRisk": chw.get("coverageGapRisk", 0)
            }

    # Follow-up history
    NOW = datetime.utcnow()
    followups = await async_db["follow_ups"].find(
        {"contactId": contact["_id"]},
    ).sort("dueDate", -1).to_list(length=10)

    missed    = [f for f in followups if not f["completed"] and f["dueDate"] < NOW]
    completed = [f for f in followups if f["completed"]]

    # Exposure events
    exposure_events = []
    for eid in contact.get("exposureEvents", []):
        ev = await async_db["exposure_events"].find_one({"_id": eid})
        if ev:
            exposure_events.append({
                "name": ev.get("name"),
                "eventType": ev.get("eventType"),
                "date": ev["date"].isoformat() if ev.get("date") else None,
                "riskLevel": ev.get("riskLevel")
            })

    # Serialize
    c = dict(contact)
    c["_id"] = str(c["_id"])
    c["assignedCHW"] = str(c.get("assignedCHW", ""))
    c["exposureEvents"] = [str(e) for e in c.get("exposureEvents", [])]
    for df in ["monitoringStartDate", "monitoringEndDate",
               "lastVisited", "symptomOnsetDate", "createdAt"]:
        if c.get(df):
            c[df] = c[df].isoformat()

    score = c.get("riskScore", 0)
    risk_level = ("CRITICAL" if score >= 85 else "HIGH" if score >= 70
                  else "MEDIUM" if score >= 50 else "LOW")

    return {
        "contact": c,
        "chw_status": chw_summary,
        "exposure_events": exposure_events,
        "follow_up_summary": {
            "total": len(followups),
            "missed": len(missed),
            "completed": len(completed),
            "missed_details": [
                {
                    "dueDate": f["dueDate"].isoformat(),
                    "priority": f["priority"],
                    "hoursOverdue": round((NOW - f["dueDate"]).total_seconds() / 3600, 1)
                }
                for f in missed
            ]
        },
        "risk_assessment": {
            "score": score,
            "level": risk_level,
            "monitoring_day": c.get("monitoringDay"),
            "in_peak_window": 5 <= (c.get("monitoringDay") or 0) <= 10,
            "chw_coverage_active": (
                chw_summary is not None and
                chw_summary.get("heartbeatScore", 0) >= 50
            )
        }
    }