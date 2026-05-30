
import os
import json
from google import genai
from google.genai.types import GenerateContentConfig
from dotenv import load_dotenv

from backend.validators import ParsedCHWReport, sanitize_symptoms

load_dotenv()

_API_KEY  = os.getenv("GEMINI_API_KEY")
_PROJECT  = os.getenv("GOOGLE_CLOUD_PROJECT")
_LOCATION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
MODEL_ID  = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# ── Client initialization ────────────────────────────────────────────────────
# API key path:    fast, development-safe, no billing required
# Vertex AI path: production, Agent Platform, Cloud Run deployment
if _API_KEY:
    _client = genai.Client(api_key=_API_KEY)
else:
    # Production path — requires: gcloud auth application-default login
    _client = genai.Client(
        vertexai=True,
        project=_PROJECT,
        location=_LOCATION
    )

# ── JSON extraction schema ────────────────────────────────────────────────────
# Passed to Gemini as response_schema to guarantee structured output.
# Eliminates hallucination risk on the extraction step.
_SCHEMA = {
    "type": "object",
    "properties": {
        "contactName": {
            "type": "string",
            "description": "Full name of the person being visited"
        },
        "district": {
            "type": "string",
            "description": "District or division name if explicitly stated"
        },
        "monitoringDay": {
            "type": "integer",
            "description": "Monitoring day number if explicitly stated (e.g. Day 6 → 6)"
        },
        "symptoms": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Symptoms explicitly mentioned. Use ONLY: fever, headache, fatigue, "
                "vomiting, rash, diarrhea, abdominal_pain, myalgia, cough, "
                "bleeding, mild_fever. Empty array if none."
            )
        },
        "exposureEventHint": {
            "type": "string",
            "description": "Any mention of a burial, gathering, market, or health facility"
        },
        "notes": {
            "type": "string",
            "description": "Any other clinically or operationally relevant information"
        },
        "chwName": {
            "type": "string",
            "description": "Name of the CHW submitting the report if mentioned"
        }
    },
    "required": ["contactName"]
}

_PROMPT_TEMPLATE = """\
You are a medical data extraction assistant for a disease outbreak \
monitoring program in Uganda.

Extract structured fields from this CHW (Community Health Worker) field report.

Strict rules:
- Extract ONLY values explicitly stated in the text
- Never infer, guess, or hallucinate values
- For symptoms, normalize to ONLY these exact terms: fever, headache, fatigue, \
vomiting, rash, diarrhea, abdominal_pain, myalgia, cough, bleeding, mild_fever
- Return an empty array for symptoms if none are mentioned
- contactName is always required

CHW Report:
\"\"\"
{report}
\"\"\"\
"""


def parse_chw_report(raw_text: str) -> ParsedCHWReport:
    """
    Parse a free-text CHW field report into validated structured fields.

    Uses Gemini 3.5 Flash JSON mode via google-genai SDK.
    response_schema enforces structure. Pydantic validates output.
    sanitize_symptoms filters against known vocabulary as final guardrail.

    Args:
        raw_text: The CHW report exactly as submitted

    Returns:
        ParsedCHWReport: Validated structured data

    Raises:
        ValueError: If report is too short or contactName cannot be extracted
    """
    if not raw_text or len(raw_text.strip()) < 10:
        raise ValueError("Report text is too short to parse meaningfully")

    prompt = _PROMPT_TEMPLATE.format(report=raw_text.strip())

    # ── Primary: JSON mode with schema constraint ────────────
    try:
        response = _client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_SCHEMA,
                temperature=0.0
            )
        )
        extracted = json.loads(response.text)

    except TypeError:
        # Older google-genai versions may not support response_schema in config.
        # Fall back to JSON mode without schema — prompt still constrains output.
        response = _client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        extracted = json.loads(response.text)

    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini returned non-JSON response for report: "
            f"'{raw_text[:80]}...' — {str(e)}"
        )

    # ── Validate required field ───────────────────────────────
    if not extracted.get("contactName"):
        raise ValueError(
            f"Could not extract contactName from report: '{raw_text[:100]}'"
        )

    # ── Normalize symptoms ────────────────────────────────────
    raw_symptoms = extracted.get("symptoms") or []
    if not isinstance(raw_symptoms, list):
        raw_symptoms = [raw_symptoms]
    extracted["symptoms"] = sanitize_symptoms(raw_symptoms)

    # ── Coerce monitoringDay to int ───────────────────────────
    if "monitoringDay" in extracted and extracted["monitoringDay"] is not None:
        try:
            extracted["monitoringDay"] = int(extracted["monitoringDay"])
        except (TypeError, ValueError):
            extracted["monitoringDay"] = None

    # ── Pydantic validation ───────────────────────────────────
    return ParsedCHWReport(**extracted)