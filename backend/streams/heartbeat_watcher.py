

import asyncio
from datetime import datetime, timedelta
from backend.db.mongo import async_db
from backend.tools.detect_operational_collapse import detect_operational_collapse

COLLAPSE_THRESHOLD = 40

# In-memory cooldown: prevents re-firing for the same CHW within 5 minutes.
# Key: str(chw ObjectId), Value: datetime of last collapse trigger
_last_triggered: dict[str, datetime] = {}
_COOLDOWN_SECONDS = 300  # 5 minutes


async def run_change_stream_watcher():
    """
    Entry point called by FastAPI lifespan.
    Subscribes to operational_topology change stream.
    Reconnects automatically on network drops or cursor expiry.
    """
    print("[STREAM] Change stream watcher starting...")

    # Watch only update and replace operations (not inserts/deletes)
    pipeline = [
        {"$match": {
            "operationType": {"$in": ["update", "replace"]}
        }}
    ]

    while True:
        try:
            print("[STREAM] Subscribing to operational_topology...")

            async with async_db["operational_topology"].watch(
                pipeline,
                full_document="updateLookup"   # fetch the full doc after update
            ) as stream:

                print("[STREAM] ✅ Change stream active — "
                      "watching for heartbeat collapses")

                async for change in stream:
                    await _handle_change(change)

        except asyncio.CancelledError:
            print("[STREAM] Change stream watcher stopped cleanly")
            break
        except Exception as e:
            print(f"[STREAM] Stream error: {e!r} — reconnecting in 5s")
            await asyncio.sleep(5)


async def _handle_change(change: dict):
    """
    Called for every update to operational_topology.
    Filters for heartbeatScore drops below threshold, applies cooldown,
    then fires the autonomous collapse pipeline.
    """
    # ── Check if heartbeatScore was part of this update ───────
    updated_fields = (
        change.get("updateDescription", {}).get("updatedFields", {})
    )
    new_score = updated_fields.get("heartbeatScore")

    if new_score is None:
        return   # This update didn't touch heartbeatScore — ignore

    if new_score >= COLLAPSE_THRESHOLD:
        return   # Score is healthy — ignore

    # ── Get full document for logging ─────────────────────────
    doc       = change.get("fullDocument") or {}
    chw_id    = str(doc.get("_id", "unknown"))
    chw_name  = doc.get("name", "Unknown CHW")
    chw_ref   = doc.get("chwId", "")
    district  = doc.get("district", "")

    # ── Cooldown check ─────────────────────────────────────────
    now  = datetime.utcnow()
    last = _last_triggered.get(chw_id)
    if last and (now - last).total_seconds() < _COOLDOWN_SECONDS:
        remaining = int(_COOLDOWN_SECONDS - (now - last).total_seconds())
        print(
            f"[STREAM] Collapse cooldown active for {chw_name} "
            f"— {remaining}s remaining"
        )
        return

    _last_triggered[chw_id] = now

    # ── Log the event ──────────────────────────────────────────
    print(
        f"\n[STREAM] ⚡ HEARTBEAT COLLAPSE DETECTED\n"
        f"         CHW:      {chw_name} ({chw_ref})\n"
        f"         Score:    {new_score}/100  (threshold: {COLLAPSE_THRESHOLD})\n"
        f"         District: {district}\n"
        f"         Firing autonomous collapse pipeline...\n"
    )

    # ── Autonomous action ──────────────────────────────────────
    try:
        result = await detect_operational_collapse()

        if result.get("collapse_detected"):
            total_rerouted = result.get("total_contacts_rerouted", 0)
            reassignments  = result.get("reassignments_completed", 0)
            alerts         = len(result.get("alert_ids", []))

            print(
                f"[STREAM] ✅ AUTO-RESPONSE COMPLETE\n"
                f"         {result['message']}\n"
                f"         Contacts rerouted:      {total_rerouted}\n"
                f"         Reassignments done:     {reassignments}\n"
                f"         Alerts generated:       {alerts}\n"
            )

            # Log to operational_alerts so SSE stream picks it up
            await async_db["operational_alerts"].insert_one({
                "alertType":    "autonomous_action",
                "trigger":      "change_stream",
                "chwName":      chw_name,
                "chwId":        chw_ref,
                "triggerScore": new_score,
                "district":     district,
                "result":       result.get("message"),
                "createdAt":    now
            })

        else:
            print(
                f"[STREAM] ℹ️  Collapse pipeline ran — no dangerous gap found\n"
                f"         ({result['message']})\n"
            )

    except Exception as e:
        print(f"[STREAM] Error in collapse pipeline: {e!r}")