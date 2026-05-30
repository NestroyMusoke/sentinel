

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime


class ParsedCHWReport(BaseModel):
    """Output from Gemini 3.5 Flash function calling parser."""
    contactName: str
    district: Optional[str] = None
    monitoringDay: Optional[int] = None
    symptoms: List[str] = Field(default_factory=list)
    exposureEventHint: Optional[str] = None
    notes: Optional[str] = None
    chwName: Optional[str] = None

    @field_validator("symptoms", mode="before")
    @classmethod
    def normalize_symptoms(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return list(v)

    @field_validator("monitoringDay", mode="before")
    @classmethod
    def coerce_day(cls, v: Any) -> Optional[int]:
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None


class ContactSummary(BaseModel):
    """Serializable contact summary for API responses (no PII by default)."""
    contactRef: str
    name: str
    district: str
    monitoringDay: int
    riskScore: int
    symptoms: List[str]
    assignedCHWName: str
    status: str
    missedFollowups: int = 0
    chwHeartbeat: Optional[int] = None


class CHWSummary(BaseModel):
    """Serializable CHW summary for API responses."""
    chwId: str
    name: str
    district: str
    heartbeatScore: int
    status: str
    coverageGapRisk: float
    totalContactsAssigned: int


class ClusterAlert(BaseModel):
    """Cluster detection result."""
    cluster_detected: bool
    event_name: Optional[str] = None
    contact_count: int = 0
    symptomatic_count: int = 0
    missed_followups: int = 0
    confidence_score: float = 0.0
    confidence_percent: str = "0%"
    districts_affected: List[str] = Field(default_factory=list)
    message: str


class CollapseAlert(BaseModel):
    """Operational collapse detection result."""
    collapse_detected: bool
    silent_chws: int = 0
    gaps_found: int = 0
    reassignments_completed: int = 0
    message: str


VALID_SYMPTOMS = {
    "fever", "headache", "fatigue", "vomiting", "rash",
    "diarrhea", "abdominal_pain", "myalgia", "cough",
    "bleeding", "jaundice", "mild_fever", "nausea"
}

VALID_DISTRICTS = {
    "Nakawa", "Kampala Central", "Kawempe",
    "Makindye", "Rubaga", "Wakiso"
}


def sanitize_symptoms(symptoms: List[str]) -> List[str]:
    """Keep only known symptom terms. Prevents hallucinated values."""
    return [s.lower().replace(" ", "_") for s in symptoms
            if s.lower().replace(" ", "_") in VALID_SYMPTOMS]