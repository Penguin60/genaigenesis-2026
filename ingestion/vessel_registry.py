from typing import Dict, Any

def fetch_registry_data(imo: str) -> Dict[str, Any]:
    """
    Simulates fetching Vessel Registry data (Ship Age, Status, Flag) via Datalastic or ShipsDNA.
    """
    # TODO: Implement API logic
    # Flag of Convenience e.g. Comoros, Gabon, Cook Islands
    # Identity Theft e.g. Retired / Scrapped
    return {
        "imo": imo,
        "age_years": 22,
        "flag": "Comoros",
        "status": "Active" # or "Retired" / "Scrapped"
    }
