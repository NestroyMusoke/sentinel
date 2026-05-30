

from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException

from backend.db.mongo import async_db
from backend.gemini_parser import parse_chw_report


def _calculate_risk_score(contact: dict, new_symptoms: list) -> int:
    score = contact.get("riskScore", 40)
    high_risk = {"fever", "rash", "vomiting", "abdominal_pain", "diarrhea", "bleeding"}

    score += len(new_symptoms) * 5
    score += sum(10 for s in new_symptoms if s in high_risk)

    day = contact.get("monitoringDay", 0)
    if 5 <= day <= 10:
        score += 15

    return min(score, 100)


def _risk_label(score: int) -> str:
    if score >= 85: return "CRITICAL"
    if score >= 70: return "HIGH"
    if score >= 50: return "MEDIUM"
    return "LOW"


async def log_field_report(
    raw_text: str,
    chw_id: Optional[str] = None
) -> dict:

    # ── 1. Parse with Gemini 3.5 Flash ──────────────────────
    try:
        parsed = parse_chw_report(raw_text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Parsing failed: {str(e)}")

    # ── 2. Match contact in MongoDB ──────────────────────────
    contact = await async_db["contacts"].find_one(
        {"name": {"$regex": parsed.contactName, "$options": "i"}}
    )
    if not contact:
        raise HTTPException(
            status_code=404,
            detail=f"No contact found matching: '{parsed.contactName}'"
        )

    # ── 3. Compute updated risk score ────────────────────────
    new_score = _calculate_risk_score(contact, parsed.symptoms)
    risk_label = _risk_label(new_score)

    # ── 4. Build update fields ───────────────────────────────
    update = {
        "riskScore": new_score,
        "lastVisited": datetime.utcnow(),
    }

    if parsed.symptoms:
        existing = set(contact.get("symptoms", []))
        update["symptoms"] = list(existing | set(parsed.symptoms))
        if not contact.get("symptomOnsetDate"):
            update["symptomOnsetDate"] = datetime.utcnow()

    if parsed.notes:
        update["notes"] = parsed.notes

    if parsed.monitoringDay:
        update["monitoringDay"] = parsed.monitoringDay

    await async_db["contacts"].update_one(
        {"_id": contact["_id"]},
        {"$set": update}
    )

    # ── 5. Update CHW heartbeat (reset to 90 on activity) ────
    chw_filter = None
    if chw_id:
        try:
            chw_filter = {"_id": ObjectId(chw_id)}
        except Exception:
            chw_filter = {"chwId": chw_id}
    elif parsed.chwName:
        chw_filter = {"name": {"$regex": parsed.chwName, "$options": "i"}}
    else:
        chw_filter = {"_id": contact.get("assignedCHW")}

    if chw_filter:
        await async_db["operational_topology"].update_one(
            chw_filter,
            {"$set": {
                "lastReport": datetime.utcnow(),
                "heartbeatScore": 90,
                "status": "active"
            }}
        )

    # ── 6. Log the event ─────────────────────────────────────
    alert_doc = {
        "alertType": "field_report",
        "contactId": contact["_id"],
        "contactRef": contact.get("contactRef"),
        "contactName": contact.get("name"),
        "district": contact.get("district"),
        "monitoringDay": update.get("monitoringDay", contact.get("monitoringDay")),
        "symptomsReported": parsed.symptoms,
        "riskScore": new_score,
        "riskLevel": risk_label,
        "rawReport": raw_text,
        "createdAt": datetime.utcnow()
    }
    result = await async_db["operational_alerts"].insert_one(alert_doc)

    return {
        "success": True,
        "contact_ref": contact.get("contactRef"),
        "contact_name": contact.get("name"),
        "district": contact.get("district"),
        "monitoring_day": update.get("monitoringDay", contact.get("monitoringDay")),
        "risk_score": new_score,
        "symptoms_detected": parsed.symptoms,
        "risk_level": risk_label,
        "event_id": str(result.inserted_id),
        "message": (
            f"Report logged — {contact.get('name')} ({contact.get('contactRef')}) | "
            f"Day {update.get('monitoringDay', contact.get('monitoringDay'))} | "
            f"Risk: {risk_label} ({new_score}/100)"
        )
    }