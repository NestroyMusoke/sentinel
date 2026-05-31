

from datetime import datetime
from backend.db.mongo import async_db

# [MCP] This tool is registered in Google Cloud Agent Builder as an
# OpenAPI function tool. Gemini 3.5 Flash discovers and invokes it
# at runtime via the Model Context Protocol (MCP) handshake.
# The mongodb-mcp-server provides additional raw MongoDB operations
# (find, aggregate, insertOne) that Gemini can call directly.
# Together they form Sentinel's dual-layer MCP integration.
MCP_TOOL_NAME = "detect_operational_collapse"

COLLAPSE_THRESHOLD   = 40     # heartbeatScore below this = CHW silent
GAP_RISK_THRESHOLD   = 50.0   # coverageGapRisk above this = dangerous
PEAK_MIN, PEAK_MAX   = 5, 10  # days 5-10 peak window
HIGH_RISK_MIN        = 70     # riskScore minimum to qualify


async def detect_operational_collapse() -> dict:
    print(f"[MCP] Tool invoked: detect_operational_collapse | timestamp: {datetime.utcnow().isoformat()}")

    NOW = datetime.utcnow()
    collapse_detected  = False
    gaps_found         = []
    reassignments      = []
    alert_ids          = []

    # ── Step 1: Find all silent CHWs ────────────────────────
    silent_chws = await async_db["operational_topology"].find(
        {"heartbeatScore": {"$lt": COLLAPSE_THRESHOLD}}
    ).to_list(length=20)

    if not silent_chws:
        return {
            "collapse_detected": False,
            "silent_chws": 0,
            "message": "All CHWs operational. No collapse signals."
        }

    # ── Step 2-6: Process each silent CHW ───────────────────
    for chw in silent_chws:
        hours_silent = (NOW - chw["lastReport"]).total_seconds() / 3600

        # High-risk contacts assigned to this CHW in peak window
        at_risk = await async_db["contacts"].find(
            {
                "assignedCHW": chw["_id"],
                "monitoringDay": {"$gte": PEAK_MIN, "$lte": PEAK_MAX},
                "riskScore": {"$gte": HIGH_RISK_MIN}
            }
        ).to_list(length=20)

        if not at_risk:
            continue

        # coverageGapRisk formula
        max_risk = max(c.get("riskScore", 0) for c in at_risk)
        gap_risk = round((1 - chw["heartbeatScore"] / 100) * max_risk, 2)

        await async_db["operational_topology"].update_one(
            {"_id": chw["_id"]},
            {"$set": {"coverageGapRisk": gap_risk}}
        )

        if gap_risk < GAP_RISK_THRESHOLD:
            continue

        collapse_detected = True

        # ── Find replacement CHW (same district, score > 70) ──
        replacement = await async_db["operational_topology"].find_one(
            {
                "_id": {"$ne": chw["_id"]},
                "heartbeatScore": {"$gt": 70},
                "district": chw.get("district"),
                "status": "active"
            },
            sort=[("heartbeatScore", -1)]
        )
        if not replacement:
            # Fallback: any active CHW anywhere
            replacement = await async_db["operational_topology"].find_one(
                {
                    "_id": {"$ne": chw["_id"]},
                    "heartbeatScore": {"$gt": 70},
                    "status": "active"
                },
                sort=[("heartbeatScore", -1)]
            )

        if not replacement:
            gaps_found.append({
                "chw_name": chw.get("name"),
                "gap_risk": gap_risk,
                "contacts_unmonitored": [c.get("contactRef") for c in at_risk],
                "reassignment_status": "NO_ACTIVE_CHW_AVAILABLE"
            })
            continue

        # ── Reassign contacts ────────────────────────────────
        contact_ids   = [c["_id"] for c in at_risk]
        contact_refs  = [c.get("contactRef") for c in at_risk]

        await async_db["contacts"].update_many(
            {"_id": {"$in": contact_ids}},
            {"$set": {
                "assignedCHW":       replacement["_id"],
                "assignedCHWName":   replacement.get("name"),
                "reassignedFrom":    chw.get("name"),
                "reassignedAt":      NOW,
                "reassignmentReason": (
                    f"Operational collapse: {chw.get('name')} silent "
                    f"{round(hours_silent):.0f}h, score {chw.get('heartbeatScore')}/100"
                )
            }}
        )

        await async_db["operational_topology"].update_one(
            {"_id": replacement["_id"]},
            {"$push": {"assignedContacts": {"$each": contact_ids}}}
        )

        # ── Build escalation text ────────────────────────────
        contact_lines = "\n".join(
            f"    • {c.get('contactRef')} {c.get('name')} — "
            f"Day {c.get('monitoringDay')}, Risk {c.get('riskScore')}/100, "
            f"Symptoms: {', '.join(c.get('symptoms', [])) or 'none'}"
            for c in at_risk
        )

        escalation_text = (
            f"SENTINEL OPERATIONAL COLLAPSE ALERT\n"
            f"{'='*50}\n"
            f"CHW:          {chw.get('name')} ({chw.get('chwId')})\n"
            f"Status:       UNRESPONSIVE — {round(hours_silent):.0f}h since last report\n"
            f"Score:        {chw.get('heartbeatScore')}/100 (threshold: {COLLAPSE_THRESHOLD})\n"
            f"District:     {chw.get('district')}\n"
            f"Gap Risk:     {gap_risk} (threshold: {GAP_RISK_THRESHOLD})\n\n"
            f"UNMONITORED CONTACTS ({len(at_risk)}):\n{contact_lines}\n\n"
            f"ACTION TAKEN:\n"
            f"    {len(at_risk)} contact(s) auto-reassigned to:\n"
            f"    {replacement.get('name')} "
            f"(heartbeat: {replacement.get('heartbeatScore')}/100)\n\n"
            f"SUPERVISOR:\n"
            f"    {chw.get('supervisorName')} — {chw.get('supervisorPhone')}\n\n"
            f"Generated: {NOW.strftime('%Y-%m-%d %H:%M UTC')} | SENTINEL v1.0"
        )

        # ── Write alert ──────────────────────────────────────
        alert_doc = {
            "alertType":            "operational_collapse",
            "chwName":              chw.get("name"),
            "chwId":                chw.get("chwId"),
            "chwHeartbeatScore":    chw.get("heartbeatScore"),
            "hoursSilent":          round(hours_silent, 1),
            "district":             chw.get("district"),
            "contactsAffected":     contact_refs,
            "contactCount":         len(contact_refs),
            "gapRiskScore":         gap_risk,
            "reassignedTo":         replacement.get("name"),
            "supervisorName":       chw.get("supervisorName"),
            "supervisorPhone":      chw.get("supervisorPhone"),
            "actionTaken":          "auto_reassignment_completed",
            "escalationText":       escalation_text,
            "createdAt":            NOW
        }
        result = await async_db["operational_alerts"].insert_one(alert_doc)
        alert_ids.append(str(result.inserted_id))

        reassignments.append({
            "contacts_reassigned": contact_refs,
            "from_chw": chw.get("name"),
            "to_chw": replacement.get("name"),
            "to_chw_heartbeat": replacement.get("heartbeatScore")
        })
        gaps_found.append({
            "chw_name": chw.get("name"),
            "hours_silent": round(hours_silent, 1),
            "heartbeat_score": chw.get("heartbeatScore"),
            "gap_risk_score": gap_risk,
            "contacts_reassigned": contact_refs,
            "reassigned_to": replacement.get("name"),
            "reassignment_status": "COMPLETED",
            "escalation_text": escalation_text
        })

    if not collapse_detected:
        return {
            "collapse_detected": False,
            "silent_chws_below_threshold": len(silent_chws),
            "message": (
                f"{len(silent_chws)} CHW(s) below score threshold "
                f"but gap risk did not exceed {GAP_RISK_THRESHOLD}."
            )
        }

    total_contacts = sum(len(r["contacts_reassigned"]) for r in reassignments)

    return {
        "collapse_detected": True,
        "gaps_found": len(gaps_found),
        "reassignments_completed": len(reassignments),
        "total_contacts_rerouted": total_contacts,
        "alert_ids": alert_ids,
        "gaps": gaps_found,
        "reassignments": reassignments,
        "message": (
            f"OPERATIONAL COLLAPSE DETECTED — "
            f"{len(gaps_found)} gap(s) | "
            f"{len(reassignments)} reassignment(s) | "
            f"{total_contacts} contacts rerouted"
        )
    }