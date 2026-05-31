# SENTINEL

### Autonomous Outbreak Coordination Intelligence

---

> *"Outbreaks don't escape containment because the disease moves faster than expected.*
> *They escape because the system monitoring the disease degrades silently —*
> *and nobody notices until it is too late."*

---

## Built in Kampala. During the outbreak.

On May 15, 2026, Uganda and the Democratic Republic of Congo jointly declared
an Ebola outbreak caused by Bundibugyo virus. Two days later, WHO declared it
a Public Health Emergency of International Concern. Confirmed cases reached
Kampala the same week. As of submission, 1,262 suspected and confirmed cases
have been reported, with at least 241 deaths.

Bundibugyo virus has no licensed vaccine. No approved therapeutics. The case
fatality rate in previous outbreaks reached 50%. The only intervention
available is contact tracing — identifying who was exposed, monitoring them
through the 21-day incubation window, and catching transmission before it
chains.

That contact tracing system depends entirely on Community Health Workers
filing reports, supervisors maintaining oversight, and coordination chains
holding under pressure. Research consistently shows this is where outbreak
response fails — not from lack of medical knowledge, but from delayed
reporting, silent field workers, and coordination gaps that go unnoticed
until clusters have already formed.

I built Sentinel to detect those gaps before they become visible in
aggregated data.

---

## The Insight

Every AI system in this space monitors whether patients are getting better
or worse.

Sentinel monitors whether the system doing the monitoring is still
functioning.

That is not a product variation. It is a different problem entirely. And it
is the problem that costs lives.

---

##  What makes this an agent (not a chatbot)

Sentinel qualifies as an autonomous agent because it:

- Executes scheduled reasoning without prompts (Cloud Scheduler)
- Reacts to real-time database events (MongoDB Change Streams)
- Performs multi-step tool execution (Agent Builder orchestration)
- Makes autonomous operational decisions (reassignment + escalation)
- Maintains persistent system state (operational_topology memory layer)
  
---

## What Sentinel Does

**Sentinel is not a symptom tracker. It is not a patient dashboard. It is
an autonomous operational intelligence layer that watches the system
watching patients.**

**1 — Detects when field workers go silent**

Every CHW carries a rolling heartbeat score from 0 to 100, degrading in
real time based on hours since their last report. A CHW who filed a report
two hours ago scores 86. A CHW silent for eleven hours scores 22. When that
score drops below 40 and their assigned contacts are in the peak monitoring
window — days 5 through 10, when transmission risk is highest — Sentinel
detects an operational collapse signal.

**2 — Acts without being asked**

MongoDB change streams hold a live subscription to the operational topology
collection. The moment a heartbeat score update lands in the database, the
stream wakes, evaluates the coverage gap risk, and if the threshold is
crossed, fires the collapse detection pipeline. Contacts get reassigned to
the nearest active CHW. A supervisor alert is generated. A containment
protocol is written. All of this happens before any human knows there is a
problem.

**3 — Detects outbreak clusters with a single query**

A MongoDB aggregation pipeline cross-references contacts by exposure event,
joins follow-up completion history, calculates missed visits per contact,
and returns a cluster confidence score. If four people who attended the same
burial ceremony are all symptomatic in the same week, Sentinel flags it —
with evidence, not inference.

**4 — Generates autonomous operational briefs**

At 6 AM East Africa Time, Google Cloud Scheduler triggers the morning brief
without a human request. The brief includes a Gemini 3.5 Flash intelligence assessment which is a contextual
analysis of the highest-risk pattern visible in the current data and the
single most important supervisory action for the day. This is Gemini
reasoning about a real operational situation, not filling a template. Every CHW's priority visit list for the day is
assembled automatically. A CHW with reassigned contacts from a silent
colleague receives an updated list. They never know the system intervened.
They just see their day.

**5 — Renders the operational picture in real time**

A live Leaflet.js map of Kampala renders every CHW and monitored contact as
a location marker. CHW markers pulse red when heartbeat scores drop below the
collapse threshold. Contact markers scale by risk score. When autonomous
reassignment fires, contact markers flash and resolve to their new CHW. The
map and the event feed update together — giving supervisors an instant
operational picture without navigating a dashboard.

---

## The Demonstration Scenario

This is not hypothetical. This is what the seeded demo data shows.

CHW Namwanje Aisha covers Nakawa Division. Her last report was eleven hours
ago. Her heartbeat score: 22 out of 100. Two of her assigned contacts —
James Ssemwogerere (Day 9, fever, risk score 87) and Rachael Nalwoga
(Day 9, three symptoms, risk score 82) — are both in the peak monitoring
window with no recent coverage.

The coverage gap risk formula:
coverageGapRisk = (1 − heartbeatScore / 100) × max(assignedContact.riskScore)
= (1 − 0.22) × 87
= 0.78 × 87
= 67.86

Threshold is 50. Sentinel detects the crossing.

The MongoDB change stream fires. `detect_operational_collapse()` runs. Both
contacts are reassigned to Grace Namutebi — who filed a report two hours
ago, heartbeat score 88, same district. Supervisor Muwanga Patrick receives
a Level 3 URGENT escalation. An operational collapse alert is written to
MongoDB. The SSE stream pushes the event to the terminal UI.

Nobody triggered any of this. The server watched the database. The database
changed. Sentinel acted.

---


##  Architecture Overview

```
                    ┌────────────────────────────┐
                    │  CHW Field Report (text)   │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │ Google Cloud Agent Builder │
                    │ Gemini 3.5 Flash (reason)  │
                    └─────────────┬──────────────┘
                                  │
          ┌───────────────────────┼────────────────────────┐
          │                       │                        │
          ▼                       ▼                        ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────────┐
│ log_field_report │   │ detect_cluster   │   │ detect_operational_      │
│ (Gemini parsing) │   │ (MongoDB agg)    │   │ collapse (core logic)    │
└──────────────────┘   └──────────────────┘   └──────────────────────────┘
          │                       │                        │
          └───────────────┬───────┴──────────────┬────────┘
                          ▼                      ▼
                ┌────────────────────────────────────┐
                │        MongoDB Atlas               │
                │------------------------------------│
                │ contacts                           │
                │ exposure_events                   │
                │ follow_ups                       │
                │ operational_topology ◄────────────┤
                └──────────────┬─────────────────────┘
                               │
               ┌───────────────┴────────────────┐
               ▼                                ▼
   Change Streams (real-time)        Cloud Scheduler (timed)
               │                                │
               ▼                                ▼
   detect_operational_collapse      morning_brief / scans
               │
               ▼
   ┌────────────────────────────┐
   │ SSE Terminal UI (live feed)│
   └────────────────────────────┘
```
---

## MongoDB Architecture

### Why document model

Each contact embeds their exposure event references, symptom history, and
assigned CHW directly in a single document. A cluster risk assessment —
joining contacts, their follow-up history, and their CHW's operational
status — is a single aggregation pipeline with two `$lookup` stages. No ORM.
No joins across normalized tables. The query structure mirrors the
operational structure of outbreak response.

### Collections

| Collection | Purpose | Key design decision |
|---|---|---|
| `contacts` | 12+ fields of monitoring data per person | `phone` projected out of all analytical queries — PII isolation by default |
| `exposure_events` | Burial ceremonies, market gatherings, health facility visits | Embedded coordinates for geographic clustering |
| `follow_ups` | Scheduled CHW visits with completion status | `completed: false` + `dueDate < now` = missed visit, computed at query time |
| `operational_topology` | CHW heartbeat scores, assignment lists, coverage gap risk | `heartbeatScore` field is the change stream trigger |
| `operational_alerts` | Every autonomous action logged here | SSE stream polls this collection — powers the terminal UI |

### The cluster detection pipeline

This is the complete cluster detection query. One aggregation. No
application-layer joins. Shown here exactly as it runs in production:

```javascript
db.contacts.aggregate([
  // Match contacts linked to the target exposure event
  { $match: { exposureEvents: { $in: [targetEventId] } } },

  // Join follow-up records per contact
  { $lookup: {
      from: "follow_ups",
      localField: "_id",
      foreignField: "contactId",
      as: "followups"
  }},

  // Calculate missed follow-ups inline
  { $addFields: {
      missedFollowups: {
        $size: { $filter: {
          input: "$followups",
          cond: { $and: [
            { $eq: ["$$this.completed", false] },
            { $lt: ["$$this.dueDate", "$$NOW"] }
          ]}
        }}
      }
  }},

  // Join CHW operational status
  { $lookup: {
      from: "operational_topology",
      localField: "assignedCHW",
      foreignField: "_id",
      as: "chw_data"
  }},

  // Embed CHW heartbeat score directly on each contact
  { $addFields: {
      chwHeartbeat: {
        "$ifNull": [{ "$arrayElemAt": ["$chw_data.heartbeatScore", 0] }, 0]
      }
  }},

  // Sort by risk, highest first
  { $sort: { riskScore: -1 } },

  // Strip PII from output
  { $project: { followups: 0, chw_data: 0, phone: 0 } }
])
```

That is the entire cluster detection. Fifteen lines of MongoDB. The
intelligence is in the reasoning, not the code complexity.

### MongoDB Change Streams — the event-driven core

Sentinel does not poll. It subscribes.

```python
async with db["operational_topology"].watch(
    pipeline,
    full_document="updateLookup"
) as stream:
    async for change in stream:
        updated_score = (
            change["updateDescription"]["updatedFields"]
            .get("heartbeatScore")
        )
        if updated_score is not None and updated_score < COLLAPSE_THRESHOLD:
            await detect_operational_collapse()
```

When the heartbeat degradation worker writes a new score to
`operational_topology`, the change stream wakes immediately — no interval,
no cron, no polling. If the new score crosses the collapse threshold,
`detect_operational_collapse()` runs. This is MongoDB Atlas functioning as
an event bus, not a data store. It is the architectural decision that makes
Sentinel genuinely autonomous rather than scheduled-autonomous.

### PII Isolation

In Uganda's outbreak response context, protecting contact identity prevents
social stigma, reduces symptom concealment, and keeps the tracing system
trusted by the communities it depends on. This is operationally critical for
Bundibugyo containment.

Sentinel implements PII isolation through MongoDB projection. The `phone`
field is excluded from all analytical queries — cluster detection, risk
profiling, CHW assignment analysis, operational collapse detection. Phone
numbers are retrieved only when generating final supervisor notifications,
with `include_pii=true` set explicitly. This is document-model-native privacy
architecture: no separate table, no join penalty, no application-layer
filtering — just a projection that means the agent never sees PII unless the
operation specifically requires it.

---

## Research Foundation

Sentinel is built on documented failure modes in outbreak surveillance
systems, not on theoretical assumptions.

**Delayed and incomplete field reporting degrades outbreak detection.**
Studies on Uganda's Integrated Disease Surveillance and Response system show
that untimely reporting is a persistent structural challenge, independent of
disease type. The mechanism Sentinel detects — CHWs going silent — is the
same mechanism that produces these reporting gaps at scale.
([BMC Public Health, 2023](https://link.springer.com/article/10.1186/s12889-023-15534-w))

**The first mile problem: community-level detection is the weakest point.**
Research on Ebola response in Uganda shows outbreaks are hardest to detect
at the community level, where the first signals appear. Coordination
breakdowns at the CHW layer allow clusters to grow before escalation
occurs — precisely the window Sentinel is designed to close.
([BMC Public Health — The first mile](https://bmcpublichealth.biomedcentral.com/articles/10.1186/s12889-016-2852-0))

**Surveillance gaps directly caused the delay in Uganda's 2022 Sudan Virus
outbreak.** A study on that specific response documents how gaps in
integrated disease surveillance and community-based reporting delayed
detection of viral hemorrhagic fever — the same failure mode Sentinel's
operational collapse detection is engineered to catch.
([BMC Infectious Diseases, 2024](https://bmcinfectdis.biomedcentral.com/articles/10.1186/s12879-024-09659-5))

**Response timeliness is the strongest predictor of outbreak severity.**
A systematic review of Ebola outbreaks in Uganda from 2000 to 2023 found
that diagnostic and response delays directly increase case fatality ratios.
The speed of the coordination system is not a secondary consideration — it
is the primary determinant of outcomes when no vaccine exists.
([DOAJ Systematic Review](https://doaj.org/article/7483c16bc49d42a9a9ae406da02f0763))

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Agent reasoning | Gemini 3.5 Flash via google-genai SDK | Multi-step tool orchestration; JSON-mode parsing with response_schema guardrails against hallucination |
| Agent orchestration | Google Cloud Agent Builder | Runtime tool registration; MCP-compatible tool discovery; agent memory across reasoning steps |
| MCP integration | Official mongodb-mcp-server | Gemini discovers MongoDB operations at runtime via Model Context Protocol handshake |
| Database | MongoDB Atlas M0 (replica set) | Change streams enabled; aggregation pipelines; document-native operational topology |
| Async driver | Motor 3.6 | Non-blocking MongoDB operations inside FastAPI async routes |
| CHW report parsing | Gemini 3.5 Flash function calling | Structured extraction from free-text field reports; function declaration enforces output schema |
| Backend | FastAPI + Python 3.12 | Async-native; SSE streaming; OpenAPI schema auto-generated for Agent Builder tool registration |
| Deployment | Google Cloud Run (min-instances=1) | Persistent background tasks; SSL/TLS handled; public HTTPS endpoint for Cloud Scheduler |
| Autonomous scheduling | Google Cloud Scheduler | Three jobs: morning brief (6 AM EAT), collapse check (every 2h), cluster scan (every 4h) |
| Terminal UI | Vanilla HTML/CSS/JS | SSE event stream; dark operations console aesthetic; no frameworks |
| Operational map | Leaflet.js + CartoDB dark tiles | Real-time CHW/contact location rendering; marker color reflects live heartbeat score and risk score; collapse events trigger map animations |
---

## Autonomous Scheduling

Three Cloud Scheduler jobs run without any human request:

| Job | Schedule | Purpose |
|---|---|---|
| `sentinel-morning-brief` | `0 3 * * *` (6 AM EAT) | Assembles priority visit list for every CHW; flags CHW warnings |
| `sentinel-collapse-check` | `0 */2 * * *` (every 2h) | Scans CHW heartbeat scores; triggers reassignment if gap risk exceeded |
| `sentinel-cluster-scan` | `0 */4 * * *` (every 4h) | Runs cluster detection across all active exposure events |

The agent does not wait to be called. It checks the system on its own
schedule, acts when it detects danger, and logs every autonomous action to
MongoDB — where the change stream picks it up and the terminal UI displays
it in real time.

---

## Setup

### Prerequisites

- Python 3.11+
- MongoDB Atlas account (free M0 cluster)
- Google Cloud project with billing enabled
- Google AI Studio API key (free): https://aistudio.google.com/apikey

### Local development

```bash
git clone https://github.com/YOUR_USERNAME/sentinel.git
cd sentinel

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r backend/requirements.txt

cp .env.example .env
# Edit .env — add MONGO_URI and GEMINI_API_KEY

# Seed the database with demo outbreak scenario
PYTHONPATH=. python seed/seed_data.py

# Start the server
PYTHONPATH=. uvicorn backend.main:app --reload --port 8080

# Open the terminal UI
# http://localhost:8080/ui
```

### Cloud Run deployment

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/sentinel

gcloud run deploy sentinel \
  --image gcr.io/YOUR_PROJECT/sentinel \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --timeout 3600 \
  --env-vars-file deployment/cloud_run.env
```

`--min-instances 1` keeps the change stream watcher and heartbeat
degradation worker permanently alive. Without it, the autonomous behavior
stops when Cloud Run scales to zero.

### MongoDB Atlas network access

Cloud Run uses dynamic IP addresses. In MongoDB Atlas → Network Access,
add `0.0.0.0/0` to allow connections from Cloud Run. Your Atlas cluster
must be a replica set for change streams — Atlas M0 qualifies.

---

## The Six Tools

All tools are registered in Google Cloud Agent Builder. Gemini 3.5 Flash
discovers them at runtime via the MCP protocol handshake and decides which
to call based on the agent system prompt and conversation context.

| Tool | What it does | When Gemini calls it |
|---|---|---|
| `log_field_report` | Parses CHW free-text via Gemini function calling; validates; writes to MongoDB; updates CHW heartbeat | Every CHW field report |
| `detect_cluster` | Runs aggregation pipeline across contacts by exposure event; returns confidence score | Automatically after any symptomatic report |
| `get_contact_risk_profile` | Returns full risk profile: score, follow-up history, CHW status. PII excluded by default | When asked about a specific contact |
| `escalate_supervisor` | Generates tiered supervisor alert (Level 1–4); writes to MongoDB; returns alert text | When cluster confirmed or CHW silence detected |
| `get_morning_brief` | Assembles full operational brief: priority visits, CHW warnings, missed follow-ups | 6 AM via Cloud Scheduler, or on demand |
| `detect_operational_collapse` | **The differentiator.** Finds silent CHWs → calculates gap risk → auto-reassigns contacts → generates alerts | Triggered by change stream AND every 2h by Cloud Scheduler |

---

## Demo

**Live system:** https://sentinel-509723815347.us-central1.run.app/ui

**Demo video:** [Link]

The operational map shows all 8 CHWs and 12 monitored contacts across
Kampala. CHW Namwanje Aisha's marker pulses red — 11 hours silent, score
22/100. The change stream fires within 10 seconds of server start. Watch
contacts R-027 and R-031 reassign to Grace in real time, both on the map
and in the event feed simultaneously.

---

## Potential Impact

This system was designed for a specific failure mode that is documented
in academic literature and visible in real outbreaks happening now.

Uganda has experienced Ebola in 2000, 2007, 2011, 2012, and 2022.
The 2026 Bundibugyo outbreak — active at the time of this submission —
has reached Kampala. There is no vaccine for this strain. The only
intervention is contact tracing coordination.

The architecture generalises to any country, any disease, any CHW-based
contact tracing program. The MongoDB schema adapts to any outbreak context.
The Agent Builder orchestration is reconfigurable. The change stream
architecture is the same whether the outbreak is Ebola in Uganda or Mpox
in the DRC or cholera in Somalia.

What does not change: CHWs go silent. Contacts go unmonitored. Clusters
form in the gap. Sentinel watches for that gap across all of them.

---

##  Repository Structure

```bash
sentinel/
├── backend/
│   ├── main.py
│   ├── gemini_parser.py
│   ├── validators.py
│   ├── db/
│   │   └── mongo.py
│   ├── tools/
│   │   ├── log_field_report.py
│   │   ├── detect_cluster.py
│   │   ├── get_contact_risk_profile.py
│   │   ├── escalate_supervisor.py
│   │   ├── get_morning_brief.py
│   │   └── detect_operational_collapse.py
│   └── streams/
│       ├── heartbeat_degradation.py
│       └── heartbeat_watcher.py

├── frontend/
│   └── index.html

├── mcp/
│   └── mcp_config.json

├── agent_config/
│   ├── system_prompt.txt
│   └── tool_definitions.json

├── seed/
│   └── seed_data.py

├── deployment/
│   ├── scheduler_setup.sh
│   └── cloud_run.env

├── Dockerfile
├── .env.example
├── requirements.txt
└── README.md
```


---

## License

MIT — see [LICENSE](LICENSE)

---

*Built in Kampala, Uganda.*
*Submitted to the Google Cloud Rapid Agent Hackathon 2026 — MongoDB Track.*
*The outbreak is real. The failure mode is documented. The system works.*
