

import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from backend.db.mongo import async_db

load_dotenv()

INTERVAL    = int(os.getenv("DEGRADATION_INTERVAL_SECONDS", "60"))
HOURLY_DECAY = 7.0   # points lost per hour of silence


def _score(last_report: datetime) -> int:
    hours = (datetime.utcnow() - last_report).total_seconds() / 3600
    return max(0, int(100 - hours * HOURLY_DECAY))


def _status(score: int) -> str:
    if score >= 70: return "active"
    if score >= 40: return "degraded"
    if score > 0:   return "unresponsive"
    return "offline"


async def run_heartbeat_degradation():
    """
    Entry point called by FastAPI lifespan.
    Loops forever, updating CHW heartbeat scores every INTERVAL seconds.
    Logs whenever a score crosses the collapse threshold (100→40, 40→39, etc.)
    """
    print(f"[HEARTBEAT] Degradation worker started  (interval: {INTERVAL}s, "
          f"decay: {HOURLY_DECAY} pts/hr)")

    while True:
        try:
            await asyncio.sleep(INTERVAL)

            chws = await async_db["operational_topology"].find(
                {},
                {"_id": 1, "name": 1, "chwId": 1, "lastReport": 1,
                 "heartbeatScore": 1, "district": 1}
            ).to_list(length=50)

            cycle_updates = 0

            for chw in chws:
                if not chw.get("lastReport"):
                    continue

                old_score  = chw.get("heartbeatScore", 100)
                new_score  = _score(chw["lastReport"])
                new_status = _status(new_score)

                if new_score == old_score:
                    continue

                await async_db["operational_topology"].update_one(
                    {"_id": chw["_id"]},
                    {"$set": {
                        "heartbeatScore": new_score,
                        "status":         new_status
                    }}
                )
                cycle_updates += 1

                # Log threshold crossings prominently
                crossed_down = old_score >= 40 > new_score
                crossed_up   = old_score < 40 <= new_score

                if crossed_down:
                    print(
                        f"[HEARTBEAT] ⚠️  THRESHOLD CROSSED (down): "
                        f"{chw['name']} ({chw.get('chwId', '')}) | "
                        f"score {old_score} → {new_score} | "
                        f"status: {new_status} | district: {chw.get('district', '')}"
                    )
                elif crossed_up:
                    print(
                        f"[HEARTBEAT] ✅ CHW RECOVERED: "
                        f"{chw['name']} | score {old_score} → {new_score}"
                    )

            if cycle_updates > 0:
                print(f"[HEARTBEAT] Cycle complete — {cycle_updates} score(s) updated")

        except asyncio.CancelledError:
            print("[HEARTBEAT] Degradation worker stopped cleanly")
            break
        except Exception as e:
            print(f"[HEARTBEAT] Worker error: {e!r} — retrying in 10s")
            await asyncio.sleep(10)