import os
import json
from google import genai
from google.genai.types import GenerateContentConfig
from dotenv import load_dotenv

from backend.validators import ParsedCHWReport, sanitize_symptoms

load_dotenv()

_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# ── Lazy client initialization ────────────────────────────────────────────────
_client = None

def get_client():
    global _client
    if _client is None:
        if not _API_KEY:
            raise ValueError("GEMINI_API_KEY is required for deployment")
        _client = genai.Client(api_key=_API_KEY)
    return _client


# ── JSON extraction schema ────────────────────────────────────────────────────
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
You are a medical data extraction assistant for a disease outbreak monitoring program in Uganda.

Extract structured fields from this CHW (Community Health Worker) field report.

Strict rules:
- Extract ONLY values explicitly stated in the text
- Never infer, guess, or hallucinate values
- For symptoms, normalize to ONLY these exact terms: fever, headache, fatigue, vomiting, rash, diarrhea, abdominal_pain, myalgia, cough, bleeding, mild_fever
- Return an empty array for symptoms if none are mentioned
- contactName is always required

CHW Report:
"""
{report}
"""
"""


def parse_chw_report(raw_text: str) -> ParsedCHWReport:
    """
    Parse a free-text CHW field report into validated structured fields.

    Uses Gemini Flash JSON mode via the google-genai SDK.
    response_schema enforces structure. Pydantic validates output.
    sanitize_symptoms filters against known vocabulary as a final guardrail.

    Raises:
        ValueError: If the report is too short or contactName cannot be extracted.
    """
    if not raw_text or len(raw_text.strip()) < 10:
        raise ValueError("Report text is too short to parse meaningfully")

    prompt = _PROMPT_TEMPLATE.format(report=raw_text.strip())
    client = get_client()

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_SCHEMA,
                temperature=0.0,
            ),
        )
        extracted = json.loads(response.text)

    except TypeError:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        extracted = json.loads(response.text)

    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini returned non-JSON response for report: "
            f"'{raw_text[:80]}...' — {str(e)}"
        )

    if not extracted.get("contactName"):
        raise ValueError(
            f"Could not extract contactName from report: '{raw_text[:100]}'"
        )

    raw_symptoms = extracted.get("symptoms") or []
    if not isinstance(raw_symptoms, list):
        raw_symptoms = [raw_symptoms]
    extracted["symptoms"] = sanitize_symptoms(raw_symptoms)

    if extracted.get("monitoringDay") is not None:
        try:
            extracted["monitoringDay"] = int(extracted["monitoringDay"])
        except (TypeError, ValueError):
            extracted["monitoringDay"] = None

    return ParsedCHWReport(extracted)
