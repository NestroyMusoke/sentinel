

from datetime import datetime, timedelta
from typing import Optional

from backend.db.mongo import async_db


async def get_morning_brief(target_date: Optional[str] = None) -> dict:

    NOW = datetime.utcnow()

    # 1. Active contacts
    total_active = await async_db["contacts"].count_documents(
        {"status": {"$in": ["active_monitoring", "escalated"]}}
    )

    # 2. Peak window contacts (days 5-10)
    peak_contacts = await async_db["contacts"].find(
        {"monitoringDay": {"$gte": 5, "$lte": 10}, "status": "active_monitoring"},
        {"phone": 0}
    ).sort("riskScore", -1).to_list(length=50)

    # 3. Escalated contacts
    escalated = await async_db["contacts"].find(
        {"status": "escalated"}, {"phone": 0}
    ).sort("riskScore", -1).to_list(length=20)

    # 4. Missed follow-ups
    missed_fu = await async_db["follow_ups"].find(
        {"completed": False, "dueDate": {"$lt": NOW}}
    ).sort("dueDate", 1).to_list(length=50)

    # 5. CHW topology
    all_chws = await async_db["operational_topology"].find(
        {}, {"phone": 0}
    ).sort("heartbeatScore", 1).to_list(length=20)

    at_risk_chws = [c for c in all_chws if c.get("heartbeatScore", 100) < 50]
    active_chws  = [c for c in all_chws if c.get("heartbeatScore", 0) >= 70]

    # 6. Priority visits: peak window + symptomatic or risk >= 70
    priority_visits = []
    for c in peak_contacts:
        if c.get("symptoms") or c.get("riskScore", 0) >= 70:
            chw_active = False
            chw_name = c.get("assignedCHWName", "Unassigned")
            if c.get("assignedCHW"):
                chw = await async_db["operational_topology"].find_one(
                    {"_id": c["assignedCHW"]},
                    {"heartbeatScore": 1, "name": 1}
                )
                if chw:
                    chw_active = chw.get("heartbeatScore", 0) >= 70
                    chw_name = chw.get("name", chw_name)

            priority_visits.append({
                "contactRef": c.get("contactRef"),
                "contactName": c.get("name"),
                "district": c.get("district"),
                "monitoringDay": c.get("monitoringDay"),
                "riskScore": c.get("riskScore"),
                "symptoms": c.get("symptoms", []),
                "assignedCHWName": chw_name,
                "chwActive": chw_active
            })

    priority_visits.sort(key=lambda x: x["riskScore"], reverse=True)

    # 7. Build brief text
    lines = [
        f"SENTINEL OPERATIONAL BRIEF — {NOW.strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 56,
        "",
        "SYSTEM STATUS",
        f"  Active contacts under monitoring : {total_active}",
        f"  In peak risk window (days 5-10)  : {len(peak_contacts)}",
        f"  Escalated cases                  : {len(escalated)}",
        f"  Overdue missed follow-ups        : {len(missed_fu)}",
        f"  CHWs with degraded score (< 50)  : {len(at_risk_chws)}",
        f"  Active CHWs (score >= 70)        : {len(active_chws)}",
        "",
        "PRIORITY VISITS"
    ]

    if priority_visits:
        for i, v in enumerate(priority_visits[:8], 1):
            syms    = ", ".join(v["symptoms"]) if v["symptoms"] else "asymptomatic"
            chw_tag = " [CHW COVERAGE GAP]" if not v["chwActive"] else ""
            lines.append(
                f"  {i}. {v['contactRef']} {v['contactName']} | "
                f"Day {v['monitoringDay']} | Risk {v['riskScore']} | "
                f"{syms} | {v['assignedCHWName']}{chw_tag}"
            )
    else:
        lines.append("  No priority visits flagged.")

    if at_risk_chws:
        lines += ["", "CHW OPERATIONAL WARNINGS"]
        for chw in at_risk_chws:
            hours = ""
            if chw.get("lastReport"):
                h = (NOW - chw["lastReport"]).total_seconds() / 3600
                hours = f" | silent: {h:.0f}h"
            lines.append(
                f"  {chw.get('name')} ({chw.get('chwId')}) — "
                f"score: {chw.get('heartbeatScore')}/100 | "
                f"status: {chw.get('status')}{hours}"
            )

    lines += ["", "— END OF BRIEF —"]
    brief_text = "\n".join(lines)

    # 8. Store brief
    await async_db["operational_alerts"].insert_one({
        "alertType": "morning_brief",
        "briefDate": NOW.strftime("%Y-%m-%d"),
        "totalActiveContacts": total_active,
        "peakWindowCount": len(peak_contacts),
        "escalatedCount": len(escalated),
        "missedFollowupCount": len(missed_fu),
        "atRiskCHWCount": len(at_risk_chws),
        "priorityVisitCount": len(priority_visits),
        "priorityVisits": priority_visits[:10],
        "briefText": brief_text,
        "createdAt": NOW
    })

    return {
        "brief_date": NOW.strftime("%Y-%m-%d"),
        "total_active_contacts": total_active,
        "peak_window_contacts": len(peak_contacts),
        "escalated_contacts": len(escalated),
        "missed_followups": len(missed_fu),
        "at_risk_chws": len(at_risk_chws),
        "priority_visit_count": len(priority_visits),
        "priority_visits": priority_visits[:10],
        "brief_text": brief_text,
        "message": (
            f"Morning brief generated — {NOW.strftime('%Y-%m-%d')} | "
            f"{len(priority_visits)} priority visits | "
            f"{len(at_risk_chws)} CHW warnings"
        )
    }