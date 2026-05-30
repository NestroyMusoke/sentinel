

import os
import json
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from bson import ObjectId

from backend.db.mongo import async_db
from backend.tools.log_field_report            import log_field_report
from backend.tools.detect_cluster              import detect_cluster
from backend.tools.get_contact_risk_profile    import get_contact_risk_profile
from backend.tools.escalate_supervisor         import escalate_supervisor
from backend.tools.get_morning_brief           import get_morning_brief
from backend.tools.detect_operational_collapse import detect_operational_collapse
from backend.streams.heartbeat_degradation     import run_heartbeat_degradation
from backend.streams.heartbeat_watcher         import run_change_stream_watcher

load_dotenv()

SCHEDULER_SECRET = os.getenv("SCHEDULER_SECRET", "sentinel-scheduler-2026")


# ── Lifespan: start/stop background tasks ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Starts both autonomous background tasks on server boot.
    Cancels them cleanly on server shutdown.
    """
    print("\n" + "=" * 56)
    print("  SENTINEL — AUTONOMOUS SYSTEMS INITIALIZING")
    print("=" * 56)

    task_degradation = asyncio.create_task(
        run_heartbeat_degradation(),
        name="heartbeat_degradation"
    )
    task_stream = asyncio.create_task(
        run_change_stream_watcher(),
        name="change_stream_watcher"
    )

    print("[SENTINEL] Heartbeat degradation worker : ACTIVE")
    print("[SENTINEL] MongoDB change stream watcher: ACTIVE")
    print("[SENTINEL] Sentinel is fully autonomous.")
    print("=" * 56 + "\n")

    yield  # ← application runs here

    print("\n[SENTINEL] Shutting down background tasks...")
    task_degradation.cancel()
    task_stream.cancel()
    await asyncio.gather(task_degradation, task_stream, return_exceptions=True)
    print("[SENTINEL] Clean shutdown complete.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sentinel",
    description=(
        "Autonomous outbreak coordination intelligence. "
        "Detects when the system tracking outbreaks starts to fail."
    ),
    version="1.0.0",
    lifespan=lifespan
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
            "status":   "operational",
            "system":   "sentinel",
            "database": "connected",
            "model":    os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            "version":  "1.0.0",
            "autonomous_tasks": ["heartbeat_degradation", "change_stream_watcher"]
        }
    except Exception as e:
        return {"status": "degraded", "database": str(e)}


@app.get("/")
async def root():
    return {
        "system":   "SENTINEL",
        "tagline":  "Detects when the system tracking outbreaks starts to fail.",
        "stack":    "Gemini 3.5 Flash · Google Cloud Agent Builder · MongoDB Atlas",
        "version":  "1.0.0"
    }


# ── Request models ────────────────────────────────────────────────────────────
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
    task: str = "morning_brief"


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


# ── Demo endpoints (for hackathon demonstration) ──────────────────────────────
@app.post("/api/demo/force-degradation-cycle")
async def demo_force_degradation():
    """
    Demo tool: immediately runs one degradation cycle without waiting for the timer.
    Use this in your demo video to trigger the collapse cascade on demand
    instead of waiting 10 seconds.
    """
    from backend.streams.heartbeat_degradation import _score, _status

    chws = await async_db["operational_topology"].find(
        {},
        {"_id": 1, "name": 1, "chwId": 1, "lastReport": 1,
         "heartbeatScore": 1, "district": 1}
    ).to_list(length=50)

    updated = []
    for chw in chws:
        if not chw.get("lastReport"):
            continue
        old_score = chw.get("heartbeatScore", 100)
        new_score = _score(chw["lastReport"])
        new_status = _status(new_score)

        if new_score != old_score:
            await async_db["operational_topology"].update_one(
                {"_id": chw["_id"]},
                {"$set": {"heartbeatScore": new_score, "status": new_status}}
            )
            updated.append({
                "name":       chw["name"],
                "chwId":      chw.get("chwId"),
                "old_score":  old_score,
                "new_score":  new_score,
                "status":     new_status,
                "crossed_threshold": old_score >= 40 > new_score
            })

    crossed = [u for u in updated if u["crossed_threshold"]]

    return {
        "cycle_run": True,
        "chws_updated": len(updated),
        "threshold_crossings": len(crossed),
        "updates": updated,
        "message": (
            f"Degradation cycle complete — {len(updated)} score(s) updated, "
            f"{len(crossed)} crossed the collapse threshold"
        )
    }


@app.get("/api/demo/topology-snapshot")
async def demo_topology_snapshot():
    """
    Demo tool: returns current CHW heartbeat scores sorted by score ascending.
    Shows Namwanje at the bottom with score ~23.
    """
    chws = await async_db["operational_topology"].find(
        {},
        {"name": 1, "chwId": 1, "district": 1, "heartbeatScore": 1,
         "status": 1, "lastReport": 1, "coverageGapRisk": 1,
         "assignedContacts": 1}
    ).sort("heartbeatScore", 1).to_list(length=20)

    result = []
    now = datetime.utcnow()
    for c in chws:
        hours_silent = None
        if c.get("lastReport"):
            hours_silent = round(
                (now - c["lastReport"]).total_seconds() / 3600, 1
            )
        result.append({
            "name":           c.get("name"),
            "chwId":          c.get("chwId"),
            "district":       c.get("district"),
            "heartbeatScore": c.get("heartbeatScore"),
            "status":         c.get("status"),
            "hoursSilent":    hours_silent,
            "coverageGapRisk": c.get("coverageGapRisk", 0),
            "assignedContactCount": len(c.get("assignedContacts", []))
        })

    return {
        "chws": result,
        "at_risk": [c for c in result if c["heartbeatScore"] < 40],
        "active":  [c for c in result if c["heartbeatScore"] >= 70]
    }


# ── SSE real-time event feed (powers the terminal UI) ────────────────────────
def _serialize(doc: dict) -> dict:
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
    Frontend terminal connects here and receives every new operational event.
    Change stream autonomous actions appear here in real time.
    """
    async def generate():
        seen_id = None

        # Send the 10 most recent events immediately on connect
        recent = await async_db["operational_alerts"].find(
            {}
        ).sort("createdAt", -1).limit(10).to_list(length=10)

        for ev in reversed(recent):
            seen_id = ev["_id"]
            payload = {
                "type":      ev.get("alertType", "event"),
                "timestamp": ev.get("createdAt", datetime.utcnow()).isoformat(),
                "data":      _serialize(ev)
            }
            yield f"data: {json.dumps(payload)}\n\n"

        # Poll for new events every 2 seconds
        while True:
            query = {"_id": {"$gt": seen_id}} if seen_id else {}
            new_evs = await async_db["operational_alerts"].find(
                query
            ).sort("createdAt", 1).to_list(length=20)

            for ev in new_evs:
                seen_id = ev["_id"]
                payload = {
                    "type":      ev.get("alertType", "event"),
                    "timestamp": ev.get("createdAt", datetime.utcnow()).isoformat(),
                    "data":      _serialize(ev)
                }
                yield f"data: {json.dumps(payload)}\n\n"

            await asyncio.sleep(2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "Connection":       "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ── Read-only data endpoints ──────────────────────────────────────────────────
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