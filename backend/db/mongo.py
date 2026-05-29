import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentinel")

# Async client (used by FastAPI routes)
async_client = AsyncIOMotorClient(MONGO_URI)
async_db = async_client[MONGO_DB_NAME]

# Sync client (used by seed scripts and change stream workers)
sync_client = MongoClient(MONGO_URI)
sync_db = sync_client[MONGO_DB_NAME]

# Collection references (async)
contacts_col = async_db["contacts"]
exposure_events_col = async_db["exposure_events"]
follow_ups_col = async_db["follow_ups"]
operational_topology_col = async_db["operational_topology"]
operational_alerts_col = async_db["operational_alerts"]

# Collection references (sync)
contacts_col_sync = sync_db["contacts"]
exposure_events_col_sync = sync_db["exposure_events"]
follow_ups_col_sync = sync_db["follow_ups"]
operational_topology_col_sync = sync_db["operational_topology"]
operational_alerts_col_sync = sync_db["operational_alerts"]