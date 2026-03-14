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


def _pick_latest_record(records: Any) -> Dict[str, Any]:
    """
    Pick the best identity record from a list returned by GFW.

    Preference order:
    1) Record marked latestVesselInfo=true
    2) Most recent transmissionDateTo
    3) First available record
    """
    if not isinstance(records, list) or not records:
        return {}

    latest_records = [r for r in records if isinstance(r, dict) and r.get("latestVesselInfo") is True]
    if latest_records:
        return latest_records[0]

    def _sort_key(record: Dict[str, Any]) -> str:
        value = record.get("transmissionDateTo")
        return str(value) if value is not None else ""

    valid_records = [r for r in records if isinstance(r, dict)]
    if not valid_records:
        return {}

    return max(valid_records, key=_sort_key)


def _extract_built_year(record: Dict[str, Any]) -> Optional[int]:
    if not isinstance(record, dict):
        return None

    # GFW registry payloads can expose built year in different keys over time.
    direct_candidates = [
        record.get("builtYear"),
        record.get("yearBuilt"),
        record.get("built"),
    ]

    extra_fields = record.get("extraFields")
    if isinstance(extra_fields, dict):
        direct_candidates.extend(
            [
                extra_fields.get("builtYear"),
                extra_fields.get("yearBuilt"),
                extra_fields.get("built"),
            ]
        )

    for candidate in direct_candidates:
        year = _safe_int(candidate)
        if year is not None and 1900 <= year <= datetime.now().year:
            return year

    return None


def _extract_year_from_timestamp(value: Any) -> Optional[int]:
    if not isinstance(value, str) or len(value) < 4:
        return None

    year = _safe_int(value[:4])
    if year is None:
        return None

    current_year = datetime.now().year
    if 1900 <= year <= current_year:
        return year
    return None


def _extract_first_ais_year(
    registry_record: Dict[str, Any],
    self_reported_record: Dict[str, Any],
) -> Optional[int]:
    # Prefer AIS self-reported history, then registry history if available.
    candidates = [
        self_reported_record.get("transmissionDateFrom"),
        self_reported_record.get("firstTransmissionDate"),
        registry_record.get("transmissionDateFrom"),
        registry_record.get("firstTransmissionDate"),
    ]

    years = [_extract_year_from_timestamp(candidate) for candidate in candidates]
    valid_years = [year for year in years if year is not None]
    return min(valid_years) if valid_years else None


def fetch_registry_data(imo: Optional[str] = None, mmsi: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches vessel registry-like data by IMO or MMSI.

    Provider order:
    1) Global Fishing Watch Vessel API (if GFW_API_TOKEN is set)
    2) Local mock fallback
    """
    gfw_token = os.getenv("GFW_API_TOKEN")
    gfw_dataset = os.getenv("GFW_DATASET", "public-global-vessel-identity:latest")

    if gfw_token and (imo or mmsi):
        query_value = str(imo or mmsi or "").strip()

        try:
            response = requests.get(
                "https://gateway.api.globalfishingwatch.org/v3/vessels/search",
                headers={"Authorization": f"Bearer {gfw_token}"},
                params={
                    "query": query_value,
                    "datasets[0]": gfw_dataset,
                    "limit": 1,
                },
                timeout=12,
            )
            response.raise_for_status()
            data = response.json() if response.content else {}

            entries = data.get("entries") if isinstance(data, dict) else None
            if isinstance(entries, list) and entries:
                entry = entries[0] if isinstance(entries[0], dict) else {}
                registry_record = _pick_latest_record(entry.get("registryInfo"))
                self_reported_record = _pick_latest_record(entry.get("selfReportedInfo"))

                built_year = _extract_built_year(registry_record)
                first_ais_year = _extract_first_ais_year(registry_record, self_reported_record)

                if built_year is not None:
                    age_years = datetime.now().year - built_year
                elif first_ais_year is not None:
                    age_years = datetime.now().year - first_ais_year
                else:
                    age_years = None

                resolved_imo = (
                    registry_record.get("imo")
                    or self_reported_record.get("imo")
                    or imo
                    or ""
                )
                resolved_mmsi = (
                    registry_record.get("ssvid")
                    or self_reported_record.get("ssvid")
                    or mmsi
                    or ""
                )
                resolved_flag = (
                    registry_record.get("flag")
                    or self_reported_record.get("flag")
                    or "Unknown"
                )

                status = _extract_status(registry_record)

                return {
                    "imo": str(resolved_imo),
                    "mmsi": str(resolved_mmsi),
                    "age_years": age_years,
                    "flag": resolved_flag,
                    "status": status,
                    "source": "global_fishing_watch",
                }
        except requests.RequestException:
            # Soft-fail to mock so endpoint stays available.
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
