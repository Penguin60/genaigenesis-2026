from typing import Dict, Any, Optional

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
    registry = fetch_registry_data(imo=imo, mmsi=mmsi) if (imo or mmsi) else {}
    status = registry.get("status", "Unknown")
    normalized_status = str(status).strip().lower()
    is_retired = normalized_status in {"retired", "scrapped", "decommissioned"}
    age_years = registry.get("age_years")
    should_retire = bool(is_retired)

    if isinstance(age_years, int) and age_years > 15:
        should_retire = True

    return {
        "is_retired": is_retired,
        "should_retire": should_retire,
        "status": status,
        "age_years": age_years,
        "source": registry.get("source", "unknown"),
        "imo": imo,
        "mmsi": mmsi,
    }


def get_ship_age(imo: Optional[str] = None, mmsi: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns whether vessel age is above 15 years.
    """
    registry = fetch_registry_data(imo=imo, mmsi=mmsi) if (imo or mmsi) else {}
    age_years = registry.get("age_years")
    is_over_15_years = False

    if isinstance(age_years, int) and age_years > 15:
        is_over_15_years = True

    return {
        "age_years": age_years,
        "is_over_15_years": is_over_15_years,
        "source": registry.get("source", "unknown"),
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
    registry = fetch_registry_data(imo=imo, mmsi=mmsi) if (imo or mmsi) else {}
    flag = registry.get("flag", "Unknown")
    foc_flags = {"Comoros", "Gabon", "Cook Islands", "Palau", "Togo", "Cameroon"}

    return {
        "imo": imo,
        "mmsi": mmsi,
        "country": flag,
        "flag_of_convenience": flag in foc_flags,
        "raw_registry": registry,
    }
