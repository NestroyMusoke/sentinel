

from datetime import datetime
from typing import Optional, List
from bson import ObjectId

from backend.db.mongo import async_db

# [MCP] This tool is registered in Google Cloud Agent Builder as an
# OpenAPI function tool. Gemini 3.5 Flash discovers and invokes it
# at runtime via the Model Context Protocol (MCP) handshake.
# The mongodb-mcp-server provides additional raw MongoDB operations
# (find, aggregate, insertOne) that Gemini can call directly.
# Together they form Sentinel's dual-layer MCP integration.
MCP_TOOL_NAME = "escalate_supervisor"

_LEVELS = {1: "WATCH", 2: "ALERT", 3: "URGENT", 4: "CRITICAL_RESPONSE_REQUIRED"}
_ACTIONS = {
    1: "Continue monitoring. No immediate action required.",
    2: "Review contact list. Verify CHW availability. Schedule check-in within 4 hours.",
    3: "Immediate response required. Reassign contacts if CHW unavailable.",
    4: "CRITICAL — Deploy emergency response team. Contact District Health Officer NOW."
}


def _level(risk: int, missed: int, heartbeat: int, cluster: bool) -> int:
    lvl = 1
    if risk >= 85: lvl = max(lvl, 3)
    elif risk >= 70: lvl = max(lvl, 2)
    if missed >= 2: lvl = max(lvl, 2)
    if heartbeat < 30: lvl = max(lvl, 3)
    if cluster: lvl = max(lvl, 3)
    if risk >= 90 and cluster: lvl = 4
    return lvl


async def escalate_supervisor(
    contact_refs: List[str],
    reason: str,
    district: str,
    is_cluster: bool = False,
    chw_id: Optional[str] = None,
    override_level: Optional[int] = None
) -> dict:
    print(f"[MCP] Tool invoked: escalate_supervisor | timestamp: {datetime.utcnow().isoformat()}")

    NOW = datetime.utcnow()

    # Fetch contacts (no PII projection)
    contacts, max_risk, total_missed = [], 0, 0
    for ref in contact_refs:
        c = await async_db["contacts"].find_one({"contactRef": ref}, {"phone": 0})
        if c:
            contacts.append(c)
            max_risk = max(max_risk, c.get("riskScore", 0))
            missed_count = await async_db["follow_ups"].count_documents({
                "contactId": c["_id"],
                "completed": False,
                "dueDate": {"$lt": NOW}
            })
            total_missed += missed_count

    # Fetch CHW
    chw_heartbeat, chw_name = 100, "Unassigned"
    supervisor_name, supervisor_phone = "Supervisor", ""

    if chw_id:
        try:
            chw = await async_db["operational_topology"].find_one(
                {"_id": ObjectId(chw_id)}
            )
        except Exception:
            chw = await async_db["operational_topology"].find_one(
                {"chwId": chw_id}
            )
        if chw:
            chw_heartbeat  = chw.get("heartbeatScore", 100)
            chw_name       = chw.get("name", "Unknown")
            supervisor_name  = chw.get("supervisorName", "Supervisor")
            supervisor_phone = chw.get("supervisorPhone", "")

    level = override_level or _level(max_risk, total_missed, chw_heartbeat, is_cluster)
    label = _LEVELS.get(level, "ALERT")

    contact_lines = " | ".join(
        f"{c.get('contactRef')} {c.get('name')} (Day {c.get('monitoringDay')}, "
        f"Risk {c.get('riskScore')})"
        for c in contacts
    ) or ", ".join(contact_refs)

    alert_text = (
        f"[{label}] SENTINEL ESCALATION — {district}\n"
        f"Reason: {reason}\n"
        f"Contacts: {contact_lines}\n"
        f"Missed follow-ups: {total_missed}\n"
        f"CHW: {chw_name} (heartbeat: {chw_heartbeat}/100)\n"
        f"Required action: {_ACTIONS[level]}\n"
        f"Supervisor: {supervisor_name} {supervisor_phone}\n"
        f"Generated: {NOW.strftime('%Y-%m-%d %H:%M UTC')}"
    )

    doc = {
        "alertType": "supervisor_escalation",
        "escalationLevel": level,
        "escalationLabel": label,
        "district": district,
        "reason": reason,
        "contactRefs": contact_refs,
        "contactCount": len(contacts),
        "isCluster": is_cluster,
        "chwName": chw_name,
        "supervisorName": supervisor_name,
        "supervisorPhone": supervisor_phone,
        "alertText": alert_text,
        "acknowledged": False,
        "createdAt": NOW
    }
    result = await async_db["operational_alerts"].insert_one(doc)

    return {
        "alert_id": str(result.inserted_id),
        "escalation_level": level,
        "escalation_label": label,
        "district": district,
        "contacts_affected": len(contacts),
        "supervisor": supervisor_name,
        "alert_text": alert_text,
        "message": f"Escalation generated — Level {level}: {label}"
    }