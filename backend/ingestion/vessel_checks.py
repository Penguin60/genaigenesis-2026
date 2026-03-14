from typing import Dict, Any, Optional
from datetime import datetime

from ingestion.vessel_registry import fetch_registry_data
from ingestion.watsonx_data import query_knowledge_lakehouse


# ──────────────────────────────────────────────
# Direct checks (no agent required)
# ──────────────────────────────────────────────

def check_retirement(imo: Optional[str] = None, mmsi: Optional[str] = None) -> Dict[str, Any]:
    """
    Checks whether the vessel is flagged as retired or scrapped
    based on registry data.
    """
    registry = fetch_registry_data(imo) if imo else {}
    status = registry.get("status", "Unknown")
    is_retired = status in ("Retired", "Scrapped")

    return {
        "is_retired": is_retired,
        "status": status,
        "imo": imo,
        "mmsi": mmsi,
    }


def get_ship_age(imo: Optional[str] = None, mmsi: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns the age of the vessel and an approximate build year.
    """
    registry = fetch_registry_data(imo) if imo else {}
    age_years = registry.get("age_years", None)
    build_year = (datetime.now().year - age_years) if age_years is not None else None

    return {
        "age_years": age_years,
        "build_year": build_year,
        "imo": imo,
        "mmsi": mmsi,
    }


# ──────────────────────────────────────────────
# Raw data fetchers for agent-dependent checks
# ──────────────────────────────────────────────

def get_insurer_data(imo: Optional[str] = None, mmsi: Optional[str] = None) -> Dict[str, Any]:
    """
    Gathers raw insurer-related data from the knowledge lakehouse.
    This data is passed to the insurer analysis agent.
    """
    lakehouse = query_knowledge_lakehouse(mmsi or imo or "")
    return {
        "imo": imo,
        "mmsi": mmsi,
        "insurer_known": lakehouse.get("insurer_known", False),
        "raw_lakehouse": lakehouse,
    }


def get_registration_data(imo: Optional[str] = None, mmsi: Optional[str] = None) -> Dict[str, Any]:
    """
    Gathers raw flag/registration data from the vessel registry.
    This data is passed to the registration analysis agent.
    """
    registry = fetch_registry_data(imo) if imo else {}
    flag = registry.get("flag", "Unknown")
    foc_flags = {"Comoros", "Gabon", "Cook Islands", "Palau", "Togo", "Cameroon"}

    return {
        "imo": imo,
        "mmsi": mmsi,
        "country": flag,
        "flag_of_convenience": flag in foc_flags,
        "raw_registry": registry,
    }
