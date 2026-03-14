from typing import Dict, Any

from ingestion.ais_stream import fetch_live_ais_data, fetch_ocean_currents
from ingestion.vessel_registry import fetch_registry_data
from ingestion.watsonx_data import query_knowledge_lakehouse

from models.trajectory_vae import calculate_reconstruction_error
from models.dark_agent import analyze_dark_period

def calculate_sri(mmsi: str, imo: str = None) -> Dict[str, Any]:
    """
    Computes the final Shadow-Risk Index (SRI) using:
    SRI = (W1 * MovementAnomaly) + (W2 * DarkLoitering) + (W3 * IdentityRisk) + (W4 * OwnershipRisk)
    
    Weights:
    - AIS Behavior (Movement Anomaly): 40%
    - Dark Loitering (Dark Gap): 25%
    - Vessel Identity: 20%
    - Financial/Owner: 15%
    """
    # 1. Ingestion Layer
    live_ais = fetch_live_ais_data(mmsi)
    currents = fetch_ocean_currents(live_ais["gps"]["lat"], live_ais["gps"]["lon"])
    
    registry = fetch_registry_data(imo) if imo else {}
    lakehouse = query_knowledge_lakehouse(mmsi)

    # 2. AI Processing Layer
    movement_anomaly_score = calculate_reconstruction_error([live_ais], currents["current_vector"])
    dark_loitering_score = analyze_dark_period([live_ais], "Fujairah") # Simulated zone

    # Identity Risk Logic (Flags of Convenience, Age, Status)
    identity_risk_score = 0.0
    if registry:
        if registry.get("age_years", 0) > 20:
            identity_risk_score += 0.4
        if registry.get("status") in ["Retired", "Scrapped"]:
            identity_risk_score += 0.4
        if registry.get("flag") in ["Comoros", "Gabon", "Cook Islands"]:
            identity_risk_score += 0.2
            
    # Ownership Risk Logic
    ownership_risk_score = 0.0
    if lakehouse.get("shell_company_risk"):
        ownership_risk_score += 0.6
    if not lakehouse.get("insurer_known"):
        ownership_risk_score += 0.4
        
    # 3. SRI Calculation
    W1, W2, W3, W4 = 0.40, 0.25, 0.20, 0.15
    
    sri = (
        (W1 * movement_anomaly_score) + 
        (W2 * dark_loitering_score) + 
        (W3 * min(1.0, identity_risk_score)) + 
        (W4 * min(1.0, ownership_risk_score))
    )
    
    return {
        "mmsi": mmsi,
        "imo": imo,
        "sri_score": round(sri, 4),
        "breakdown": {
            "movement_anomaly": W1 * movement_anomaly_score,
            "dark_loitering": W2 * dark_loitering_score,
            "identity_risk": W3 * min(1.0, identity_risk_score),
            "ownership_risk": W4 * min(1.0, ownership_risk_score)
        },
        "risk_level": "High" if sri > 0.7 else "Medium" if sri > 0.4 else "Low",
        "data_sources": {
            "live_ais": live_ais,
            "registry": registry,
            "lakehouse": lakehouse
        }
    }
