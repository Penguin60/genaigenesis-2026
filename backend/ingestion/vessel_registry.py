import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _extract_status(payload: Dict[str, Any]) -> str:
    # Datalastic field names can vary by plan/version; check common aliases.
    candidates = [
        payload.get("status"),
        payload.get("ship_status"),
        payload.get("vessel_status"),
        payload.get("navigation_status"),
    ]
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Unknown"


def fetch_registry_data(imo: Optional[str] = None, mmsi: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches vessel registry-like data by IMO or MMSI.

    API used: Datalastic vessel info endpoint (if DATALASTIC_API_KEY is set).
    Falls back to mock data when credentials are unavailable.
    """
    api_key = os.getenv("DATALASTIC_API_KEY")
    if api_key and (imo or mmsi):
        params = {"api-key": api_key}
        if imo:
            params["imo"] = imo
        elif mmsi:
            params["mmsi"] = mmsi

        try:
            response = requests.get(
                "https://api.datalastic.com/api/v0/vessel_info",
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json() if response.content else {}

            # Some responses nest vessel details under "data".
            payload = data.get("data") if isinstance(data.get("data"), dict) else data

            built_year = _safe_int(payload.get("built") or payload.get("year_built"))
            age_years = (
                datetime.now().year - built_year
                if built_year is not None and built_year > 1900
                else _safe_int(payload.get("age") or payload.get("age_years"))
            )

            return {
                "imo": str(payload.get("imo") or imo or ""),
                "mmsi": str(payload.get("mmsi") or mmsi or ""),
                "age_years": age_years,
                "flag": payload.get("flag") or payload.get("flag_name") or "Unknown",
                "status": _extract_status(payload),
                "source": "datalastic",
            }
        except requests.RequestException:
            # Soft-fail to fallback data so API remains usable in local dev.
            pass

    # Fallback mock values for local/demo runs.
    return {
        "imo": imo,
        "mmsi": mmsi,
        "age_years": 22,
        "flag": "Comoros",
        "status": "Active",  # or "Retired" / "Scrapped"
        "source": "mock",
    }
