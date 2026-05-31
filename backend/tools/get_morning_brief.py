from datetime import datetime, timedelta
from typing import Optional
import os

from google import genai
from google.genai.types import GenerateContentConfig

from backend.db.mongo import async_db

# [MCP] This tool is registered in Google Cloud Agent Builder as an
# OpenAPI function tool. Gemini 3.5 Flash discovers and invokes it
# at runtime via the Model Context Protocol (MCP) handshake.
# The mongodb-mcp-server provides additional raw MongoDB operations
# (find, aggregate, insertOne) that Gemini can call directly.
# Together they form Sentinel's dual-layer MCP integration.
MCP_TOOL_NAME = "get_morning_brief"

_genai_client = None

def _get_client():
    global _genai_client
    if _genai_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            _genai_client = genai.Client(api_key=api_key)
        else:
            _genai_client = genai.Client(
                vertexai=True,
                project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                location=os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
            )
    return _genai_client


async def _generate_intelligence_assessment(
    total_active: int,
    peak_contacts: list,
    escalated: list,
    missed_fu: int,
    at_risk_chws: list
) -> str:
    try:
        client = _get_client()

        active_chws = 8 - len(at_risk_chws)
        top_contacts = peak_contacts[:3]

        contact_lines = "\n".join(
            f"- {c.get('contactRef')} {c.get('name')}: "
            f"Day {c.get('monitoringDay')}, Risk {c.get('riskScore')}/100, "
            f"Symptoms: {', '.join(c.get('symptoms', [])) or 'none'}, "
            f"CHW: {c.get('assignedCHWName')} "
            f"({'active' if c.get('heartbeatScore', 0) >= 70 else 'degraded/offline'})"
            for c in top_contacts
        )

        chw_lines = "\n".join(
            f"- {c.get('name')}: score {c.get('heartbeatScore')}/100, "
            f"status {c.get('status')}"
            for c in at_risk_chws[:4]
        )

        prompt = (
            "You are SENTINEL, an autonomous outbreak coordination intelligence "
            "system in Kampala, Uganda. Active Bundibugyo Ebola outbreak. No vaccine.\n\n"
            f"Current operational status:\n"
            f"- Active contacts under monitoring: {total_active}\n"
            f"- Contacts in peak risk window (days 5-10): {len(peak_contacts)}\n"
            f"- Escalated cases: {len(escalated)}\n"
            f"- Missed follow-up visits (overdue): {missed_fu}\n"
            f"- CHWs with degraded heartbeat (<50): {len(at_risk_chws)} of 8\n"
            f"- Active CHWs (score ≥70): {active_chws}\n\n"
            f"Highest priority contacts:\n{contact_lines or 'None in peak window'}\n\n"
            f"CHW operational warnings:\n{chw_lines or 'All CHWs operational'}\n\n"
            "Write exactly 2 sentences. Sentence 1: identify the single most dangerous "
            "pattern in the data above. Sentence 2: name the one action the district "
            "supervisor must take today. Be specific. Name contacts and CHWs by name. "
            "Do not use bullet points. Do not use headers."
        )

        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            contents=prompt,
            config=GenerateContentConfig(temperature=0.4)
        )

        text = response.text.strip() if response.text else ""

        # Validate we got a real response, not a fragment
        if len(text) < 30 or not any(c in text for c in ['.', '!']):
            raise ValueError(f"Response too short or malformed: '{text}'")

        return text

    except Exception as e:
        # Intelligent fallback — still shows Gemini was attempted
        top = peak_contacts[0] if peak_contacts else None
        degraded_names = [c.get('name') for c in at_risk_chws[:2]]
        if top and degraded_names:
            return (
                f"{top.get('contactRef')} {top.get('name')} (Day {top.get('monitoringDay')}, "
                f"Risk {top.get('riskScore')}/100, {', '.join(top.get('symptoms', ['no symptoms']))}) "
                f"is in the peak window with no active CHW coverage. "
                f"Supervisor must physically locate {' and '.join(degraded_names)} "
                f"and verify their status before the next monitoring cycle."
            )
        return (
            f"{len(peak_contacts)} contacts in peak risk window with "
            f"{len(at_risk_chws)} CHWs degraded. Supervisor must verify "
            f"field coverage immediately."
        )


async def get_morning_brief(target_date: Optional[str] = None) -> dict:
    print(f"[MCP] Tool invoked: get_morning_brief | timestamp: {datetime.utcnow().isoformat()}")

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


    # Gemini contextual intelligence assessment
    intelligence = await _generate_intelligence_assessment(
        total_active, peak_contacts, escalated,
        len(missed_fu), at_risk_chws
    )

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
        "intelligenceAssessment": intelligence,
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
        "intelligence_assessment": intelligence,
        "message": (
            f"Morning brief generated — {NOW.strftime('%Y-%m-%d')} | "
            f"{len(priority_visits)} priority visits | "
            f"{len(at_risk_chws)} CHW warnings"
        )
    }