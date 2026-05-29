

import os
import sys
from datetime import datetime, timedelta
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db.mongo import sync_db


def seed():
    print("\n" + "=" * 55)
    print("  SENTINEL — DATABASE SEED SCRIPT")
    print("=" * 55 + "\n")

    NOW = datetime.utcnow()

    # ----------------------------------------------------------
    # 1. CLEAR ALL EXISTING DATA
    # ----------------------------------------------------------
    print("[1/8] Clearing existing collections...")
    collections = [
        "contacts", "exposure_events", "follow_ups",
        "operational_topology", "operational_alerts"
    ]
    for col in collections:
        result = sync_db[col].delete_many({})
        print(f"      Cleared '{col}': {result.deleted_count} documents removed")

    # ----------------------------------------------------------
    # 2. EXPOSURE EVENTS
    # ----------------------------------------------------------
    print("\n[2/8] Seeding exposure events...")

    kiwatule_id  = ObjectId()
    kalerwe_id   = ObjectId()
    bwaise_id    = ObjectId()

    exposure_events = [
        {
            "_id": kiwatule_id,
            "eventType": "burial_ceremony",
            "name": "Kiwatule Burial Ceremony",
            "location": {
                "name": "Kiwatule, Nakawa Division",
                "district": "Nakawa",
                "coordinates": {"lat": 0.3476, "lng": 32.6466}
            },
            "date": NOW - timedelta(days=9),
            "attendeeCount": 47,
            "districtsAffected": ["Nakawa", "Kampala Central", "Kawempe"],
            "riskLevel": "critical",
            "notes": "Burial of confirmed index case. High-density gathering. 47 attendees traced.",
            "createdAt": NOW - timedelta(days=9)
        },
        {
            "_id": kalerwe_id,
            "eventType": "market_gathering",
            "name": "Kalerwe Market Contact",
            "location": {
                "name": "Kalerwe Market, Kawempe Division",
                "district": "Kawempe",
                "coordinates": {"lat": 0.3394, "lng": 32.5729}
            },
            "date": NOW - timedelta(days=7),
            "attendeeCount": 12,
            "districtsAffected": ["Kawempe", "Kampala Central"],
            "riskLevel": "medium",
            "notes": "Secondary contact cluster at market. Linked to Kiwatule attendee.",
            "createdAt": NOW - timedelta(days=7)
        },
        {
            "_id": bwaise_id,
            "eventType": "health_facility_visit",
            "name": "Bwaise Health Center III",
            "location": {
                "name": "Bwaise Health Center III, Kawempe",
                "district": "Kawempe",
                "coordinates": {"lat": 0.3542, "lng": 32.5664}
            },
            "date": NOW - timedelta(days=5),
            "attendeeCount": 6,
            "districtsAffected": ["Kawempe", "Kampala Central"],
            "riskLevel": "medium",
            "notes": "Waiting room exposure. Patient later confirmed positive.",
            "createdAt": NOW - timedelta(days=5)
        }
    ]

    sync_db["exposure_events"].insert_many(exposure_events)
    print(f"      Inserted 3 exposure events")
    print(f"      ANCHOR: Kiwatule burial ID = {kiwatule_id}")

    # ----------------------------------------------------------
    # 3. OPERATIONAL TOPOLOGY (CHWs)
    # ----------------------------------------------------------
    print("\n[3/8] Seeding CHW operational topology...")

    grace_id     = ObjectId()
    namwanje_id  = ObjectId()
    kato_id      = ObjectId()
    nakato_id    = ObjectId()
    ssali_id     = ObjectId()
    nabirye_id   = ObjectId()
    musoke_id    = ObjectId()
    nansubuga_id = ObjectId()

    nakawa_sup_id  = ObjectId()
    central_sup_id = ObjectId()
    kawempe_sup_id = ObjectId()

    chws = [
        {
            "_id": grace_id,
            "chwId": "CHW-NKW-001",
            "name": "Grace Namutebi",
            "phone": "+256-772-100-001",
            "district": "Nakawa",
            "zone": "Kiwatule-Naguru Zone",
            "supervisorId": nakawa_sup_id,
            "supervisorName": "Muwanga Patrick",
            "supervisorPhone": "+256-772-200-001",
            "assignedContacts": [],
            "heartbeatScore": 88,
            "lastReport": NOW - timedelta(hours=2),
            "lastLocation": "Kiwatule, Nakawa",
            "totalContactsAssigned": 0,
            "activeContacts": 0,
            "coverageGapRisk": 0.0,
            "status": "active",
            "createdAt": NOW - timedelta(days=30)
        },
        {
            "_id": namwanje_id,
            "chwId": "CHW-NKW-002",
            "name": "Namwanje Aisha",
            "phone": "+256-772-100-002",
            "district": "Nakawa",
            "zone": "Nakawa-Luzira Zone",
            "supervisorId": nakawa_sup_id,
            "supervisorName": "Muwanga Patrick",
            "supervisorPhone": "+256-772-200-001",
            "assignedContacts": [],
            "heartbeatScore": 22,                        # ← SILENT
            "lastReport": NOW - timedelta(hours=11),     # ← 11 hours ago
            "lastLocation": "Nakawa Division",
            "totalContactsAssigned": 0,
            "activeContacts": 0,
            "coverageGapRisk": 0.0,
            "status": "unresponsive",
            "createdAt": NOW - timedelta(days=30)
        },
        {
            "_id": kato_id,
            "chwId": "CHW-KCA-001",
            "name": "Kato David",
            "phone": "+256-772-100-003",
            "district": "Kampala Central",
            "zone": "Kampala Central Zone A",
            "supervisorId": central_sup_id,
            "supervisorName": "Nakazibwe Ruth",
            "supervisorPhone": "+256-772-200-002",
            "assignedContacts": [],
            "heartbeatScore": 75,
            "lastReport": NOW - timedelta(hours=3),
            "lastLocation": "Kampala Central",
            "totalContactsAssigned": 0,
            "activeContacts": 0,
            "coverageGapRisk": 0.0,
            "status": "active",
            "createdAt": NOW - timedelta(days=30)
        },
        {
            "_id": nakato_id,
            "chwId": "CHW-KCA-002",
            "name": "Nakato Sarah",
            "phone": "+256-772-100-004",
            "district": "Kampala Central",
            "zone": "Kampala Central Zone B",
            "supervisorId": central_sup_id,
            "supervisorName": "Nakazibwe Ruth",
            "supervisorPhone": "+256-772-200-002",
            "assignedContacts": [],
            "heartbeatScore": 62,
            "lastReport": NOW - timedelta(hours=5),
            "lastLocation": "Kampala Central",
            "totalContactsAssigned": 0,
            "activeContacts": 0,
            "coverageGapRisk": 0.0,
            "status": "active",
            "createdAt": NOW - timedelta(days=30)
        },
        {
            "_id": ssali_id,
            "chwId": "CHW-KWP-001",
            "name": "Ssali Robert",
            "phone": "+256-772-100-005",
            "district": "Kawempe",
            "zone": "Kawempe-Kalerwe Zone",
            "supervisorId": kawempe_sup_id,
            "supervisorName": "Kayiira James",
            "supervisorPhone": "+256-772-200-003",
            "assignedContacts": [],
            "heartbeatScore": 80,
            "lastReport": NOW - timedelta(hours=1, minutes=30),
            "lastLocation": "Kawempe Division",
            "totalContactsAssigned": 0,
            "activeContacts": 0,
            "coverageGapRisk": 0.0,
            "status": "active",
            "createdAt": NOW - timedelta(days=30)
        },
        {
            "_id": nabirye_id,
            "chwId": "CHW-KWP-002",
            "name": "Nabirye Hope",
            "phone": "+256-772-100-006",
            "district": "Kawempe",
            "zone": "Kawempe-Bwaise Zone",
            "supervisorId": kawempe_sup_id,
            "supervisorName": "Kayiira James",
            "supervisorPhone": "+256-772-200-003",
            "assignedContacts": [],
            "heartbeatScore": 55,
            "lastReport": NOW - timedelta(hours=6),
            "lastLocation": "Bwaise, Kawempe",
            "totalContactsAssigned": 0,
            "activeContacts": 0,
            "coverageGapRisk": 0.0,
            "status": "active",
            "createdAt": NOW - timedelta(days=30)
        },
        {
            "_id": musoke_id,
            "chwId": "CHW-NKW-003",
            "name": "Musoke John",
            "phone": "+256-772-100-007",
            "district": "Nakawa",
            "zone": "Nakawa-Mbuya Zone",
            "supervisorId": nakawa_sup_id,
            "supervisorName": "Muwanga Patrick",
            "supervisorPhone": "+256-772-200-001",
            "assignedContacts": [],
            "heartbeatScore": 70,
            "lastReport": NOW - timedelta(hours=4),
            "lastLocation": "Mbuya, Nakawa",
            "totalContactsAssigned": 0,
            "activeContacts": 0,
            "coverageGapRisk": 0.0,
            "status": "active",
            "createdAt": NOW - timedelta(days=30)
        },
        {
            "_id": nansubuga_id,
            "chwId": "CHW-KCA-003",
            "name": "Nansubuga Fatuma",
            "phone": "+256-772-100-008",
            "district": "Kampala Central",
            "zone": "Kampala Central Zone C",
            "supervisorId": central_sup_id,
            "supervisorName": "Nakazibwe Ruth",
            "supervisorPhone": "+256-772-200-002",
            "assignedContacts": [],
            "heartbeatScore": 45,
            "lastReport": NOW - timedelta(hours=8),
            "lastLocation": "Kampala Central",
            "totalContactsAssigned": 0,
            "activeContacts": 0,
            "coverageGapRisk": 0.0,
            "status": "degraded",
            "createdAt": NOW - timedelta(days=30)
        }
    ]

    sync_db["operational_topology"].insert_many(chws)
    print(f"      Inserted 8 CHW records")
    print(f"      Grace  (ACTIVE,      score 88, last report  2h ago) — {grace_id}")
    print(f"      Namwanje (UNRESPONSIVE, score 22, last report 11h ago) — {namwanje_id}")

    # ----------------------------------------------------------
    # 4. CONTACTS
    # ----------------------------------------------------------
    print("\n[4/8] Seeding 12 contacts...")

    james_id     = ObjectId()
    rachael_id   = ObjectId()
    peter_id     = ObjectId()
    mary_id      = ObjectId()
    john_k_id    = ObjectId()
    agnes_id     = ObjectId()
    samuel_id    = ObjectId()
    lydia_id     = ObjectId()
    denis_id     = ObjectId()
    josephine_id = ObjectId()
    emmanuel_id  = ObjectId()
    christine_id = ObjectId()

    contacts = [
        # ── KIWATULE CLUSTER ─────────────────────────────────
        {
            "_id": james_id,
            "contactRef": "R-027",
            "name": "James Ssemwogerere",
            "age": 34, "sex": "M",
            "phone": "+256-701-234-001",
            "district": "Nakawa",
            "subCounty": "Nakawa", "village": "Kiwatule",
            "exposureEvents": [kiwatule_id],
            "monitoringDay": 9,
            "monitoringStartDate": NOW - timedelta(days=9),
            "monitoringEndDate":   NOW + timedelta(days=12),
            "symptoms": ["fever", "headache"],
            "symptomOnsetDate": NOW - timedelta(days=2),
            "riskScore": 87,
            "riskFactors": ["attended_index_case_burial", "symptomatic_day_9", "cluster_zone"],
            "status": "active_monitoring",
            "assignedCHW": namwanje_id,
            "assignedCHWName": "Namwanje Aisha",
            "lastVisited": NOW - timedelta(hours=28),
            "missedCheckins": 1,
            "notes": "Was at burial. Fever since yesterday evening. Wife also attending.",
            "createdAt": NOW - timedelta(days=9)
        },
        {
            "_id": rachael_id,
            "contactRef": "R-031",
            "name": "Rachael Nalwoga",
            "age": 28, "sex": "F",
            "phone": "+256-701-234-002",
            "district": "Nakawa",
            "subCounty": "Nakawa", "village": "Naguru",
            "exposureEvents": [kiwatule_id],
            "monitoringDay": 9,
            "monitoringStartDate": NOW - timedelta(days=9),
            "monitoringEndDate":   NOW + timedelta(days=12),
            "symptoms": ["headache", "fatigue", "myalgia"],
            "symptomOnsetDate": NOW - timedelta(days=1),
            "riskScore": 82,
            "riskFactors": ["attended_index_case_burial", "multi_symptom", "household_contact"],
            "status": "active_monitoring",
            "assignedCHW": namwanje_id,
            "assignedCHWName": "Namwanje Aisha",
            "lastVisited": NOW - timedelta(hours=30),
            "missedCheckins": 1,
            "notes": "Direct contact at burial. Three symptoms now. Husband also monitored.",
            "createdAt": NOW - timedelta(days=9)
        },
        {
            "_id": peter_id,
            "contactRef": "R-019",
            "name": "Peter Mulondo",
            "age": 52, "sex": "M",
            "phone": "+256-701-234-003",
            "district": "Kampala Central",
            "subCounty": "Central", "village": "Kamwokya",
            "exposureEvents": [kiwatule_id],
            "monitoringDay": 8,
            "monitoringStartDate": NOW - timedelta(days=9),
            "monitoringEndDate":   NOW + timedelta(days=13),
            "symptoms": ["fever", "vomiting", "abdominal_pain"],
            "symptomOnsetDate": NOW - timedelta(days=3),
            "riskScore": 93,
            "riskFactors": ["attended_index_case_burial", "multi_symptom", "age_over_50", "vomiting"],
            "status": "escalated",
            "assignedCHW": nakato_id,
            "assignedCHWName": "Nakato Sarah",
            "lastVisited": NOW - timedelta(hours=6),
            "missedCheckins": 0,
            "notes": "URGENT. Fever + vomiting + abdominal pain. Referral to Mulago under review.",
            "createdAt": NOW - timedelta(days=9)
        },
        {
            "_id": mary_id,
            "contactRef": "R-033",
            "name": "Mary Auma",
            "age": 41, "sex": "F",
            "phone": "+256-701-234-004",
            "district": "Kawempe",
            "subCounty": "Kawempe", "village": "Kalerwe",
            "exposureEvents": [kiwatule_id],
            "monitoringDay": 5,
            "monitoringStartDate": NOW - timedelta(days=9),
            "monitoringEndDate":   NOW + timedelta(days=16),
            "symptoms": [],
            "symptomOnsetDate": None,
            "riskScore": 68,
            "riskFactors": ["attended_index_case_burial", "entering_peak_window"],
            "status": "active_monitoring",
            "assignedCHW": ssali_id,
            "assignedCHWName": "Ssali Robert",
            "lastVisited": NOW - timedelta(hours=10),
            "missedCheckins": 0,
            "notes": "Asymptomatic. Entering peak risk window day 5. Monitor closely.",
            "createdAt": NOW - timedelta(days=9)
        },
        # ── KALERWE MARKET ───────────────────────────────────
        {
            "_id": john_k_id,
            "contactRef": "R-038",
            "name": "John Kiggundu",
            "age": 29, "sex": "M",
            "phone": "+256-701-234-005",
            "district": "Kampala Central",
            "subCounty": "Central", "village": "Wandegeya",
            "exposureEvents": [kalerwe_id],
            "monitoringDay": 7,
            "monitoringStartDate": NOW - timedelta(days=7),
            "monitoringEndDate":   NOW + timedelta(days=14),
            "symptoms": ["mild_fever"],
            "symptomOnsetDate": NOW - timedelta(days=1),
            "riskScore": 71,
            "riskFactors": ["market_exposure", "symptomatic"],
            "status": "active_monitoring",
            "assignedCHW": kato_id,
            "assignedCHWName": "Kato David",
            "lastVisited": NOW - timedelta(hours=4),
            "missedCheckins": 0,
            "notes": "Mild fever. Market contact. Kato visited this morning.",
            "createdAt": NOW - timedelta(days=7)
        },
        {
            "_id": agnes_id,
            "contactRef": "R-041",
            "name": "Agnes Nankya",
            "age": 35, "sex": "F",
            "phone": "+256-701-234-006",
            "district": "Kawempe",
            "subCounty": "Kawempe", "village": "Kalerwe",
            "exposureEvents": [kalerwe_id],
            "monitoringDay": 3,
            "monitoringStartDate": NOW - timedelta(days=7),
            "monitoringEndDate":   NOW + timedelta(days=18),
            "symptoms": [],
            "symptomOnsetDate": None,
            "riskScore": 42,
            "riskFactors": ["market_exposure"],
            "status": "active_monitoring",
            "assignedCHW": nabirye_id,
            "assignedCHWName": "Nabirye Hope",
            "lastVisited": NOW - timedelta(hours=18),
            "missedCheckins": 0,
            "notes": "Asymptomatic. Low risk currently.",
            "createdAt": NOW - timedelta(days=7)
        },
        # ── BWAISE HEALTH CENTER ─────────────────────────────
        {
            "_id": samuel_id,
            "contactRef": "R-045",
            "name": "Samuel Opolot",
            "age": 44, "sex": "M",
            "phone": "+256-701-234-007",
            "district": "Kawempe",
            "subCounty": "Kawempe", "village": "Bwaise",
            "exposureEvents": [bwaise_id],
            "monitoringDay": 5,
            "monitoringStartDate": NOW - timedelta(days=5),
            "monitoringEndDate":   NOW + timedelta(days=16),
            "symptoms": [],
            "symptomOnsetDate": None,
            "riskScore": 48,
            "riskFactors": ["health_facility_exposure", "entering_peak_window"],
            "status": "active_monitoring",
            "assignedCHW": nabirye_id,
            "assignedCHWName": "Nabirye Hope",
            "lastVisited": NOW - timedelta(hours=20),
            "missedCheckins": 0,
            "notes": "Waiting room exposure. Asymptomatic day 5. Monitor.",
            "createdAt": NOW - timedelta(days=5)
        },
        {
            "_id": lydia_id,
            "contactRef": "R-046",
            "name": "Lydia Nassimbwa",
            "age": 26, "sex": "F",
            "phone": "+256-701-234-008",
            "district": "Kampala Central",
            "subCounty": "Central", "village": "Mulago",
            "exposureEvents": [bwaise_id],
            "monitoringDay": 1,
            "monitoringStartDate": NOW - timedelta(days=5),
            "monitoringEndDate":   NOW + timedelta(days=20),
            "symptoms": [],
            "symptomOnsetDate": None,
            "riskScore": 30,
            "riskFactors": ["health_facility_exposure"],
            "status": "active_monitoring",
            "assignedCHW": kato_id,
            "assignedCHWName": "Kato David",
            "lastVisited": NOW - timedelta(hours=22),
            "missedCheckins": 0,
            "notes": "Early monitoring. Asymptomatic.",
            "createdAt": NOW - timedelta(days=5)
        },
        # ── ADDITIONAL ───────────────────────────────────────
        {
            "_id": denis_id,
            "contactRef": "R-022",
            "name": "Denis Waiswa",
            "age": 38, "sex": "M",
            "phone": "+256-701-234-009",
            "district": "Nakawa",
            "subCounty": "Nakawa", "village": "Naguru",
            "exposureEvents": [kiwatule_id],
            "monitoringDay": 10,
            "monitoringStartDate": NOW - timedelta(days=10),
            "monitoringEndDate":   NOW + timedelta(days=11),
            "symptoms": ["fever", "rash"],
            "symptomOnsetDate": NOW - timedelta(days=4),
            "riskScore": 91,
            "riskFactors": ["attended_index_case_burial", "day_10_peak", "rash_flagged", "fever"],
            "status": "escalated",
            "assignedCHW": grace_id,
            "assignedCHWName": "Grace Namutebi",
            "lastVisited": NOW - timedelta(hours=2),
            "missedCheckins": 0,
            "notes": "Day 10 — FINAL PEAK. Fever + rash. Grace on-site. Isolation initiated.",
            "createdAt": NOW - timedelta(days=10)
        },
        {
            "_id": josephine_id,
            "contactRef": "R-050",
            "name": "Josephine Katusiime",
            "age": 31, "sex": "F",
            "phone": "+256-701-234-010",
            "district": "Nakawa",
            "subCounty": "Nakawa", "village": "Mbuya",
            "exposureEvents": [kalerwe_id],
            "monitoringDay": 3,
            "monitoringStartDate": NOW - timedelta(days=7),
            "monitoringEndDate":   NOW + timedelta(days=18),
            "symptoms": ["mild_fever"],
            "symptomOnsetDate": NOW - timedelta(hours=12),
            "riskScore": 55,
            "riskFactors": ["market_exposure", "mild_symptoms"],
            "status": "active_monitoring",
            "assignedCHW": musoke_id,
            "assignedCHWName": "Musoke John",
            "lastVisited": NOW - timedelta(hours=7),
            "missedCheckins": 0,
            "notes": "Mild fever onset last 12 hours. Musoke scheduled PM visit.",
            "createdAt": NOW - timedelta(days=7)
        },
        {
            "_id": emmanuel_id,
            "contactRef": "R-015",
            "name": "Emmanuel Ssebunya",
            "age": 60, "sex": "M",
            "phone": "+256-701-234-011",
            "district": "Kawempe",
            "subCounty": "Kawempe", "village": "Bwaise",
            "exposureEvents": [kiwatule_id],
            "monitoringDay": 10,
            "monitoringStartDate": NOW - timedelta(days=10),
            "monitoringEndDate":   NOW + timedelta(days=11),
            "symptoms": ["fever"],
            "symptomOnsetDate": NOW - timedelta(days=5),
            "riskScore": 85,
            "riskFactors": ["attended_index_case_burial", "day_10_peak", "age_over_60", "fever"],
            "status": "active_monitoring",
            "assignedCHW": ssali_id,
            "assignedCHWName": "Ssali Robert",
            "lastVisited": NOW - timedelta(hours=3),
            "missedCheckins": 0,
            "notes": "Day 10. Age 60. Fever. Ssali monitoring closely.",
            "createdAt": NOW - timedelta(days=10)
        },
        {
            "_id": christine_id,
            "contactRef": "R-052",
            "name": "Christine Nakabugo",
            "age": 22, "sex": "F",
            "phone": "+256-701-234-012",
            "district": "Kampala Central",
            "subCounty": "Central", "village": "Wandegeya",
            "exposureEvents": [bwaise_id],
            "monitoringDay": 2,
            "monitoringStartDate": NOW - timedelta(days=5),
            "monitoringEndDate":   NOW + timedelta(days=19),
            "symptoms": [],
            "symptomOnsetDate": None,
            "riskScore": 25,
            "riskFactors": ["health_facility_exposure"],
            "status": "active_monitoring",
            "assignedCHW": nansubuga_id,
            "assignedCHWName": "Nansubuga Fatuma",
            "lastVisited": NOW - timedelta(hours=26),
            "missedCheckins": 0,
            "notes": "Asymptomatic. Low risk. Routine monitoring.",
            "createdAt": NOW - timedelta(days=5)
        }
    ]

    sync_db["contacts"].insert_many(contacts)
    print(f"      Inserted 12 contacts")
    print(f"      Kiwatule cluster: R-027, R-031, R-019, R-033")
    print(f"      DEMO CRITICAL: R-027 + R-031 assigned to SILENT Namwanje")

    # ----------------------------------------------------------
    # 5. UPDATE CHW assignedContacts ARRAYS
    # ----------------------------------------------------------
    print("\n[5/8] Linking contacts to CHWs...")

    chw_assignments = {
        grace_id:     [denis_id],
        namwanje_id:  [james_id, rachael_id],  # ← the gap
        kato_id:      [john_k_id, lydia_id],
        nakato_id:    [peter_id],
        ssali_id:     [mary_id, emmanuel_id],
        nabirye_id:   [agnes_id, samuel_id],
        musoke_id:    [josephine_id],
        nansubuga_id: [christine_id]
    }

    for chw_id, contact_ids in chw_assignments.items():
        sync_db["operational_topology"].update_one(
            {"_id": chw_id},
            {"$set": {
                "assignedContacts": contact_ids,
                "totalContactsAssigned": len(contact_ids),
                "activeContacts": len(contact_ids)
            }}
        )

    # coverageGapRisk = (1 - heartbeatScore/100) * max(assigned riskScores)
    # Namwanje: (1 - 22/100) * 87 = 0.78 * 87 = 67.86
    namwanje_gap_risk = round((1 - 22 / 100) * 87, 2)
    sync_db["operational_topology"].update_one(
        {"_id": namwanje_id},
        {"$set": {"coverageGapRisk": namwanje_gap_risk}}
    )
    print(f"      CHW-contact assignments linked")
    print(f"      Namwanje coverageGapRisk = {namwanje_gap_risk} (danger threshold: 50.0)")

    # ----------------------------------------------------------
    # 6. FOLLOW-UPS
    # ----------------------------------------------------------
    print("\n[6/8] Seeding follow-ups...")

    follow_ups = [
        # James — MISSED (Namwanje silent)
        {
            "contactId": james_id, "contactRef": "R-027",
            "contactName": "James Ssemwogerere",
            "dueDate": NOW - timedelta(hours=20),
            "priority": "high",
            "symptoms": ["fever", "headache"],
            "assignedCHW": namwanje_id, "assignedCHWName": "Namwanje Aisha",
            "completed": False, "completedAt": None,
            "notes": "Day 9 check-in. Fever worsening. OVERDUE — NOT COMPLETED.",
            "createdAt": NOW - timedelta(days=1)
        },
        {
            "contactId": james_id, "contactRef": "R-027",
            "contactName": "James Ssemwogerere",
            "dueDate": NOW - timedelta(days=1, hours=20),
            "priority": "high",
            "symptoms": ["fever"],
            "assignedCHW": namwanje_id, "assignedCHWName": "Namwanje Aisha",
            "completed": True, "completedAt": NOW - timedelta(days=1, hours=19),
            "notes": "Day 8 check-in completed. Fever reported.",
            "createdAt": NOW - timedelta(days=2)
        },
        # Rachael — MISSED (Namwanje silent)
        {
            "contactId": rachael_id, "contactRef": "R-031",
            "contactName": "Rachael Nalwoga",
            "dueDate": NOW - timedelta(hours=18),
            "priority": "high",
            "symptoms": ["headache", "fatigue"],
            "assignedCHW": namwanje_id, "assignedCHWName": "Namwanje Aisha",
            "completed": False, "completedAt": None,
            "notes": "Day 9 check-in. Multiple symptoms. OVERDUE — NOT COMPLETED.",
            "createdAt": NOW - timedelta(days=1)
        },
        {
            "contactId": rachael_id, "contactRef": "R-031",
            "contactName": "Rachael Nalwoga",
            "dueDate": NOW - timedelta(days=1, hours=18),
            "priority": "medium",
            "symptoms": [],
            "assignedCHW": namwanje_id, "assignedCHWName": "Namwanje Aisha",
            "completed": True, "completedAt": NOW - timedelta(days=1, hours=17),
            "notes": "Day 8. Asymptomatic at visit. Symptoms now developing.",
            "createdAt": NOW - timedelta(days=2)
        },
        # Peter — COMPLETED (escalated case, Nakato active)
        {
            "contactId": peter_id, "contactRef": "R-019",
            "contactName": "Peter Mulondo",
            "dueDate": NOW - timedelta(hours=6),
            "priority": "critical",
            "symptoms": ["fever", "vomiting", "abdominal_pain"],
            "assignedCHW": nakato_id, "assignedCHWName": "Nakato Sarah",
            "completed": True, "completedAt": NOW - timedelta(hours=5, minutes=45),
            "notes": "ESCALATED. Nakato on-site. Referral paperwork initiated.",
            "createdAt": NOW - timedelta(hours=7)
        },
        # Denis — COMPLETED (Grace active)
        {
            "contactId": denis_id, "contactRef": "R-022",
            "contactName": "Denis Waiswa",
            "dueDate": NOW - timedelta(hours=2),
            "priority": "critical",
            "symptoms": ["fever", "rash"],
            "assignedCHW": grace_id, "assignedCHWName": "Grace Namutebi",
            "completed": True, "completedAt": NOW - timedelta(hours=2),
            "notes": "Day 10. Grace on-site. Isolation protocol. Rash confirmed.",
            "createdAt": NOW - timedelta(hours=3)
        },
        # Mary — UPCOMING (Ssali scheduled)
        {
            "contactId": mary_id, "contactRef": "R-033",
            "contactName": "Mary Auma",
            "dueDate": NOW + timedelta(hours=2),
            "priority": "high",
            "symptoms": [],
            "assignedCHW": ssali_id, "assignedCHWName": "Ssali Robert",
            "completed": False, "completedAt": None,
            "notes": "Day 5 afternoon check. Entering peak window.",
            "createdAt": NOW - timedelta(hours=2)
        },
        # John K — COMPLETED (Kato active)
        {
            "contactId": john_k_id, "contactRef": "R-038",
            "contactName": "John Kiggundu",
            "dueDate": NOW - timedelta(hours=4),
            "priority": "medium",
            "symptoms": ["mild_fever"],
            "assignedCHW": kato_id, "assignedCHWName": "Kato David",
            "completed": True, "completedAt": NOW - timedelta(hours=3, minutes=50),
            "notes": "Morning visit complete. Mild fever persisting.",
            "createdAt": NOW - timedelta(hours=5)
        },
        # Emmanuel — COMPLETED (Ssali active, day 10)
        {
            "contactId": emmanuel_id, "contactRef": "R-015",
            "contactName": "Emmanuel Ssebunya",
            "dueDate": NOW - timedelta(hours=3),
            "priority": "high",
            "symptoms": ["fever"],
            "assignedCHW": ssali_id, "assignedCHWName": "Ssali Robert",
            "completed": True, "completedAt": NOW - timedelta(hours=3),
            "notes": "Day 10. Age 60. Ssali monitoring closely. Fever stable.",
            "createdAt": NOW - timedelta(hours=4)
        }
    ]

    sync_db["follow_ups"].insert_many(follow_ups)
    overdue = sum(
        1 for f in follow_ups
        if not f["completed"] and f["dueDate"] < NOW
    )
    print(f"      Inserted {len(follow_ups)} follow-up records")
    print(f"      Overdue + incomplete: {overdue} (both belong to Namwanje's contacts)")

    # ----------------------------------------------------------
    # 7. INDEXES
    # ----------------------------------------------------------
    print("\n[7/8] Creating indexes...")

    sync_db["contacts"].create_index([("assignedCHW", 1)])
    sync_db["contacts"].create_index([("riskScore", -1)])
    sync_db["contacts"].create_index([("district", 1)])
    sync_db["contacts"].create_index([("monitoringDay", 1)])
    sync_db["contacts"].create_index([("status", 1)])
    sync_db["contacts"].create_index([("exposureEvents", 1)])
    sync_db["contacts"].create_index(
        [("monitoringDay", 1), ("riskScore", -1)]
    )

    sync_db["operational_topology"].create_index([("heartbeatScore", 1)])
    sync_db["operational_topology"].create_index([("district", 1)])
    sync_db["operational_topology"].create_index([("coverageGapRisk", -1)])
    sync_db["operational_topology"].create_index([("status", 1)])

    sync_db["follow_ups"].create_index([("contactId", 1)])
    sync_db["follow_ups"].create_index([("assignedCHW", 1)])
    sync_db["follow_ups"].create_index([("completed", 1), ("dueDate", 1)])

    sync_db["operational_alerts"].create_index([("createdAt", -1)])
    sync_db["operational_alerts"].create_index([("alertType", 1)])
    sync_db["operational_alerts"].create_index([("district", 1)])

    print("      All indexes created")

    # ----------------------------------------------------------
    # 8. VERIFICATION QUERIES
    # ----------------------------------------------------------
    print("\n[8/8] Running verification queries...\n")

    print("  Collection document counts:")
    for col in ["contacts", "exposure_events", "follow_ups",
                "operational_topology", "operational_alerts"]:
        count = sync_db[col].count_documents({})
        print(f"    {col:<30} {count} documents")

    print("\n  Cluster detection — Kiwatule contacts (sorted by risk):")
    pipeline = [
        {"$match": {"exposureEvents": {"$in": [kiwatule_id]}}},
        {"$lookup": {
            "from": "follow_ups",
            "localField": "_id",
            "foreignField": "contactId",
            "as": "followups"
        }},
        {"$addFields": {
            "missedFollowups": {
                "$size": {"$filter": {
                    "input": "$followups",
                    "cond": {"$and": [
                        {"$eq": ["$$this.completed", False]},
                        {"$lt": ["$$this.dueDate", NOW]}
                    ]}
                }}
            }
        }},
        {"$sort": {"riskScore": -1}},
        {"$project": {
            "name": 1, "contactRef": 1, "monitoringDay": 1,
            "riskScore": 1, "missedFollowups": 1,
            "assignedCHWName": 1, "symptoms": 1
        }}
    ]

    cluster_results = list(sync_db["contacts"].aggregate(pipeline))
    for c in cluster_results:
        syms = ", ".join(c["symptoms"]) if c["symptoms"] else "asymptomatic"
        flag = " ← COVERAGE GAP" if c["missedFollowups"] > 0 else ""
        print(
            f"    {c['contactRef']} {c['name']:<25} "
            f"Day {c['monitoringDay']:>2} | Risk {c['riskScore']:>3} | "
            f"CHW: {c['assignedCHWName']:<18} | "
            f"Missed: {c['missedFollowups']} | {syms}{flag}"
        )

    print("\n  Operational collapse check — CHWs with heartbeatScore < 40:")
    silent = list(sync_db["operational_topology"].find(
        {"heartbeatScore": {"$lt": 40}},
        {"name": 1, "heartbeatScore": 1,
         "coverageGapRisk": 1, "lastReport": 1,
         "assignedContacts": 1, "status": 1}
    ))
    for chw in silent:
        hours_silent = (NOW - chw["lastReport"]).total_seconds() / 3600
        contacts_count = len(chw.get("assignedContacts", []))
        print(
            f"    {chw['name']:<20} score: {chw['heartbeatScore']:>3}/100 | "
            f"silent: {hours_silent:.0f}h | "
            f"gapRisk: {chw['coverageGapRisk']:>5} | "
            f"contacts: {contacts_count} | status: {chw['status']}"
        )

    print("\n  High-risk contacts assigned to silent CHWs:")
    if silent:
        silent_chw_ids = [c["_id"] for c in silent]
        gap_contacts = list(sync_db["contacts"].find(
            {
                "assignedCHW": {"$in": silent_chw_ids},
                "monitoringDay": {"$gte": 5, "$lte": 10},
                "riskScore": {"$gt": 70}
            },
            {"name": 1, "contactRef": 1, "monitoringDay": 1,
             "riskScore": 1, "assignedCHWName": 1}
        ).sort("riskScore", -1))

        for c in gap_contacts:
            print(
                f"    {c['contactRef']} {c['name']:<25} "
                f"Day {c['monitoringDay']:>2} | Risk {c['riskScore']:>3} | "
                f"UNMONITORED — CHW: {c['assignedCHWName']}"
            )

    print("\n" + "=" * 55)
    print("  SEED COMPLETE — MongoDB ready for Sentinel demo")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    seed()