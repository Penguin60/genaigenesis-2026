from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os
import pandas as pd
import time
import torch

load_dotenv()

from scoring.risk_calculator import calculate_sri
from agents.orchestrator import query_agent
from agents.info_agents import run_info_agents
from agents.chat_agent import run_chat
from ingestion.vessel_checks import check_retirement, get_ship_age
from models.trajectory_vae import calculate_reconstruction_error
from scoring.gap_check import analyze_ais_reporting_gaps

app = FastAPI(
    title="Shadow Fleet Detection API",
    description="Backend for Maritime Navigator Hackathon Project.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.sim_start = None
app.state.sim_csv_start = None
app.state.sim_speed = 300

class VesselRequest(BaseModel):
    mmsi: str
    imo: Optional[str] = None

class QueryRequest(BaseModel):
    query: str


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = ""

class AnalysisRequest(BaseModel):
    trajectory: List[Dict[str, Any]]
    ship_type: str = "tanker"

@app.get("/")
def read_root():
    return {"message": "Shadow Fleet Detection API"}

@app.post("/api/v1/simulation/start")
def start_simulation():
    data_path = os.path.join(os.path.dirname(__file__), "data", "test", "hackathon_test_data.csv")
    if not os.path.exists(data_path):
        raise HTTPException(status_code=404, detail="Hackathon data not found.")

    df = pd.read_csv(data_path)
    df = df[~df['TYPE'].str.lower().isin(['fishing', 'passenger'])]
    df = df[df['CRAFT_ID'] != 'END']
    df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])

    csv_start_time = df['TIMESTAMP'].min()
    csv_end_time = df['TIMESTAMP'].max()
    total_span_seconds = max((csv_end_time - csv_start_time).total_seconds(), 0.0)
    initial_offset_seconds = total_span_seconds * 0
    
    app.state.sim_csv_start = csv_start_time + pd.Timedelta(seconds=initial_offset_seconds)
    app.state.sim_start = time.time()
    
    return {
        "message": "Simulation started",
        "start_time": app.state.sim_start,
        "csv_start_reference": app.state.sim_csv_start.isoformat(),
        "initial_offset_seconds": initial_offset_seconds,
    }

@app.get("/api/v1/simulation")
def simulation():
    if app.state.sim_start is None:
        raise HTTPException(status_code=400, detail="Simulation not started")

    data_path = os.path.join(os.path.dirname(__file__), "data", "test", "hackathon_test_data.csv")
    if not os.path.exists(data_path):
        raise HTTPException(status_code=404, detail="Hackathon data not found.")

    df = pd.read_csv(data_path)
    df = df[~df['TYPE'].str.lower().isin(['fishing', 'passenger'])]
    df = df[df['CRAFT_ID'] != 'END']
    df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])
    
    real_elapsed = time.time() - app.state.sim_start
    sim_elapsed_seconds = real_elapsed * app.state.sim_speed
    current_sim_time = app.state.sim_csv_start + pd.Timedelta(seconds=sim_elapsed_seconds)

    # Only show pings that have occurred SINCE the simulation start point
    # df_visible = df[(df['TIMESTAMP'] >= app.state.sim_csv_start) & (df['TIMESTAMP'] <= current_sim_time)]
    df_visible = df[df['TIMESTAMP'] <= current_sim_time]
    
    vessels = {}
    for mmsi, group in df_visible.groupby('MMSI'):
        if (mmsi == 2000016):
            print(group)
            print(current_sim_time)
        group_sorted = group.sort_values('TIMESTAMP')
        pings = group_sorted.to_dict('records')
        
        ship_type = pings[0]['TYPE'].lower()
        score = calculate_reconstruction_error(pings, ship_type=ship_type)
        
        # Provide the latest point separately for easy frontend rendering
        latest = pings[-1]
        
        vessels[mmsi] = {
            "name": f"VESSEL_{mmsi}",
            "mmsi": str(mmsi),
            "imo": f"900{mmsi}" if mmsi < 10000000 else str(mmsi),
            "type": pings[0]['TYPE'],
            "status": "Anomaly Detected" if score > 0.05 else "Compliant",
            "score": round(score, 4),
            "latest_point": {
                "ts": latest['TIMESTAMP'].isoformat(),
                "lat": latest['LAT'],
                "lon": latest['LON'],
                "course": latest['COURSE'],
                "speed": latest['SPEED']
            },
            "track": [{"ts": p['TIMESTAMP'].isoformat(), "lat": p['LAT'], "lon": p['LON'], "course": p['COURSE'], "speed": p['SPEED']} for p in pings]
        }

    return {
        "current_sim_time": current_sim_time.isoformat(),
        "vessels": list(vessels.values())
    }

@app.post("/api/v1/analyze-vessel")
def analyze_vessel(request: VesselRequest) -> Dict[str, Any]:
    try:
        result = calculate_sri(request.mmsi, request.imo)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/agent-query")
def ask_agent(request: QueryRequest) -> Dict[str, Any]:
    try:
        response = query_agent(request.query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/info")
def vessel_info(request: VesselRequest) -> Dict[str, Any]:
    try:
        retirement = check_retirement(imo=request.imo, mmsi=request.mmsi)
        age = get_ship_age(imo=request.imo, mmsi=request.mmsi)
        agent_results = run_info_agents(imo=request.imo, mmsi=request.mmsi)
        return {
            "mmsi": request.mmsi,
            "imo": request.imo,
            "retirement": retirement,
            "age": age,
            "insurer": agent_results.get("insurer", {}),
            "registration": agent_results.get("registration", {}),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat")
def chat(request: ChatRequest) -> Dict[str, Any]:
    try:
        response = run_chat(request.message, request.context or "")
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analysis")
def run_analysis(request: AnalysisRequest) -> Dict[str, Any]:
    """
    Runs the heavier analysis pipeline over a trajectory using the trained ship-type VAE.
    Returns a normalized movement anomaly score in [0, 1].
    """
    try:
        if not request.trajectory:
            raise HTTPException(status_code=400, detail="trajectory must contain at least one point")

        ship_type = request.ship_type.lower().strip()
        score = calculate_reconstruction_error(request.trajectory, ship_type=ship_type)
        gap_check = analyze_ais_reporting_gaps(request.trajectory)
        movement_alert = score > 0.05
        gap_alert = bool(gap_check.get("suspicious", False))

        return {
            "ship_type": ship_type,
            "trajectory_points": len(request.trajectory),
            "movement_anomaly_score": round(score, 4),
            "movement_alert": movement_alert,
            "gap_check": gap_check,
            "alert": movement_alert or gap_alert,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
