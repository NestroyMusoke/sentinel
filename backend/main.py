

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from bson import ObjectId

from backend.db.mongo import async_db
from backend.tools.log_field_report        import log_field_report
from backend.tools.detect_cluster          import detect_cluster
from backend.tools.get_contact_risk_profile import get_contact_risk_profile
from backend.tools.escalate_supervisor     import escalate_supervisor
from backend.tools.get_morning_brief       import get_morning_brief
from backend.tools.detect_operational_collapse import detect_operational_collapse

load_dotenv()

SCHEDULER_SECRET = os.getenv("SCHEDULER_SECRET", "sentinel-scheduler-2026")

app = FastAPI(
    title="Sentinel",
    description="Autonomous outbreak coordination intelligence — Gemini 3.5 Flash + MongoDB Atlas",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    try:
        await async_db.command("ping")
        return {
            "status": "operational",
            "system": "sentinel",
            "database": "connected",
            "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            "version": "1.0.0"
        }
    except Exception as e:
        return {"status": "degraded", "database": str(e)}


@app.get("/")
async def root():
    return {
        "system": "SENTINEL",
        "tagline": "Detects when the system tracking outbreaks starts to fail.",
        "stack": "Gemini 3.5 Flash · Google Cloud Agent Builder · MongoDB Atlas",
        "version": "1.0.0"
    }


# ── Tool request/response models ──────────────────────────────────────────────
class LogReportRequest(BaseModel):
    raw_text: str
    chw_id: Optional[str] = None

class DetectClusterRequest(BaseModel):
    exposure_event_id: Optional[str] = None
    district: Optional[str] = None

class RiskProfileRequest(BaseModel):
    contact_ref: Optional[str] = None
    contact_name: Optional[str] = None
    include_pii: bool = False

class EscalateRequest(BaseModel):
    contact_refs: List[str]
    reason: str
    district: str
    is_cluster: bool = False
    chw_id: Optional[str] = None
    override_level: Optional[int] = None

class MorningBriefRequest(BaseModel):
    target_date: Optional[str] = None

class SchedulerRequest(BaseModel):
    secret: str
    task: str = "morning_brief"  # morning_brief | collapse_check | cluster_scan


# ── Tool endpoints ────────────────────────────────────────────────────────────
@app.post("/api/tools/log-field-report")
async def route_log_report(req: LogReportRequest):
    return await log_field_report(req.raw_text, req.chw_id)


@app.post("/api/tools/detect-cluster")
async def route_detect_cluster(req: DetectClusterRequest):
    return await detect_cluster(req.exposure_event_id, req.district)


@app.post("/api/tools/get-contact-risk-profile")
async def route_risk_profile(req: RiskProfileRequest):
    return await get_contact_risk_profile(
        req.contact_ref, req.contact_name, req.include_pii
    )


@app.post("/api/tools/escalate-supervisor")
async def route_escalate(req: EscalateRequest):
    return await escalate_supervisor(
        req.contact_refs, req.reason, req.district,
        req.is_cluster, req.chw_id, req.override_level
    )


@app.post("/api/tools/get-morning-brief")
async def route_morning_brief(req: MorningBriefRequest):
    return await get_morning_brief(req.target_date)


@app.post("/api/tools/detect-operational-collapse")
async def route_collapse():
    return await detect_operational_collapse()


# ── Cloud Scheduler autonomous trigger ───────────────────────────────────────
@app.post("/api/scheduler/trigger")
async def scheduler_trigger(req: SchedulerRequest):
    """
    Called by Google Cloud Scheduler. Requires the SCHEDULER_SECRET header value.
    Enables truly autonomous behavior: Sentinel acts without a human request.
    """
    if req.secret != SCHEDULER_SECRET:
        raise HTTPException(status_code=403, detail="Invalid scheduler secret")

    if req.task == "morning_brief":
        result = await get_morning_brief()
        return {"triggered": "morning_brief", "status": "completed", "result": result}

    if req.task == "collapse_check":
        result = await detect_operational_collapse()
        return {"triggered": "collapse_check", "status": "completed", "result": result}

    if req.task == "cluster_scan":
        result = await detect_cluster()
        return {"triggered": "cluster_scan", "status": "completed", "result": result}

    raise HTTPException(status_code=400, detail=f"Unknown task: {req.task}")


# ── SSE real-time event feed (powers the terminal UI) ────────────────────────
def _serialize(doc: dict) -> dict:
    """Convert ObjectIds and datetimes to JSON-safe strings."""
    clean = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        elif isinstance(v, ObjectId):
            clean[k] = str(v)
        elif isinstance(v, datetime):
            clean[k] = v.isoformat()
        elif isinstance(v, list):
            clean[k] = [str(i) if isinstance(i, ObjectId) else i for i in v]
        else:
            clean[k] = v
    return clean


@app.get("/api/events/stream")
async def event_stream():
    """
    Server-Sent Events stream.
    The terminal UI connects here and receives live operational events.
    """
    async def generate():
        seen_id = None

        # Send the 10 most recent events on connect
        recent = await async_db["operational_alerts"].find(
            {}
        ).sort("createdAt", -1).limit(10).to_list(length=10)

        for ev in reversed(recent):
            seen_id = ev["_id"]
            payload = {
                "type": ev.get("alertType", "event"),
                "timestamp": ev.get("createdAt", datetime.utcnow()).isoformat(),
                "data": _serialize(ev)
            }
            yield f"data: {json.dumps(payload)}\n\n"

        # Then poll for new events every 2 seconds
        while True:
            query = {"_id": {"$gt": seen_id}} if seen_id else {}
            new_events = await async_db["operational_alerts"].find(
                query
            ).sort("createdAt", 1).to_list(length=20)

            for ev in new_events:
                seen_id = ev["_id"]
                payload = {
                    "type": ev.get("alertType", "event"),
                    "timestamp": ev.get("createdAt", datetime.utcnow()).isoformat(),
                    "data": _serialize(ev)
                }
                yield f"data: {json.dumps(payload)}\n\n"

            await asyncio.sleep(2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ── Read-only data endpoints (for frontend panels) ───────────────────────────
@app.get("/api/contacts")
async def api_contacts():
    docs = await async_db["contacts"].find(
        {}, {"phone": 0}
    ).sort("riskScore", -1).to_list(length=50)
    return [_serialize(d) for d in docs]


@app.get("/api/topology")
async def api_topology():
    docs = await async_db["operational_topology"].find(
        {}, {"phone": 0}
    ).sort("heartbeatScore", 1).to_list(length=20)
    return [_serialize(d) for d in docs]


@app.get("/api/alerts")
async def api_alerts():
    cutoff = datetime.utcnow() - timedelta(hours=48)
    docs = await async_db["operational_alerts"].find(
        {"createdAt": {"$gte": cutoff}}
    ).sort("createdAt", -1).to_list(length=100)
    return [_serialize(d) for d in docs]