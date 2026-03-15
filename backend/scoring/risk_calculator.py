from typing import Dict, Any, Optional

from ingestion.ais_stream import fetch_live_ais_data, fetch_ocean_currents
from ingestion.vessel_registry import fetch_registry_data
from ingestion.watsonx_data import query_knowledge_lakehouse

from models.trajectory_vae import calculate_reconstruction_error
from models.dark_agent import analyze_dark_period
from agents.info_agents import run_info_agents
from ingestion.vessel_checks import check_retirement, get_ship_age

import pandas as pd
import os

def calculate_sri(mmsi: str, imo: str = None) -> Dict[str, Any]:
    # 1. Fetch historical track data for activity analysis
    mmsi_val = int(mmsi)
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test", "hackathon_test_data.csv")
    
    trajectory = []
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        df_vessel = df[df['MMSI'] == mmsi_val].sort_values('TIMESTAMP')
        trajectory = df_vessel.to_dict('records')
    
    # 2. Activity Signals (Movement & Gaps)
    live_ais = fetch_live_ais_data(mmsi)
    currents = fetch_ocean_currents(live_ais["gps"]["lat"], live_ais["gps"]["lon"])
    
    # Fallback to current point if no trajectory
    if not trajectory:
        trajectory = [{
            "LAT": live_ais["gps"]["lat"],
            "LON": live_ais["gps"]["lon"],
            "COURSE": live_ais.get("heading", 0.0),
            "SPEED": live_ais.get("speed", 10.0), # assumed speed
            "TIMESTAMP": live_ais.get("timestamp")
        }]
    
    movement_anomaly_score = calculate_reconstruction_error(trajectory, ship_type="tanker")
    
    # 2. Info Signals (Registry & Agents)
    retirement_data = check_retirement(imo=imo, mmsi=mmsi)
    age_data = get_ship_age(imo=imo, mmsi=mmsi)
    agent_results = run_info_agents(imo=imo, mmsi=mmsi)
    
    registry = fetch_registry_data(imo) if imo else {}
    lakehouse = query_knowledge_lakehouse(mmsi)

    # Identity Risk Calculation
    identity_risk_score = 0.0
    age = age_data.get("age_years", 0) or 0
    if age > 20:
        identity_risk_score += 0.4
    if retirement_data.get("is_retired"):
        identity_risk_score += 0.4
    
    reg_risk = agent_results.get("registration", {}).get("risk_level", "LOW")
    if reg_risk == "HIGH":
        identity_risk_score += 0.2
    elif reg_risk == "MEDIUM":
        identity_risk_score += 0.1
            
    # Ownership Risk Calculation
    ownership_risk_score = 0.0
    if lakehouse.get("shell_company_risk"):
        ownership_risk_score += 0.6
        
    ins_risk = agent_results.get("insurer", {}).get("risk_level", "LOW")
    if ins_risk == "HIGH" or not lakehouse.get("insurer_known"):
        ownership_risk_score += 0.4
    elif ins_risk == "MEDIUM":
        ownership_risk_score += 0.2
        
    # Dark Period / Loitering
    dark_loitering_score = analyze_dark_period([live_ais], "Fujairah")
        
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
        "risk_level": "High" if sri > 0.7 else "Medium" if sri > 0.4 else "Low",
        "breakdown": {
            "movement_anomaly": round(W1 * movement_anomaly_score, 4),
            "dark_loitering": round(W2 * dark_loitering_score, 4),
            "identity_risk": round(W3 * min(1.0, identity_risk_score), 4),
            "ownership_risk": round(W4 * min(1.0, ownership_risk_score), 4)
        },
        "details": {
            "age": age_data,
            "retirement": retirement_data,
            "agent_results": agent_results,
            "lakehouse": lakehouse
        }
    }
