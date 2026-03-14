from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
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
from ingestion.vessel_checks import check_retirement, get_ship_age
from models.trajectory_vae import calculate_reconstruction_error

app = FastAPI(
    title="Shadow Fleet Detection API",
    description="Backend template for Maritime Navigator Hackathon Project.",
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
app.state.sim_speed = 300

class VesselRequest(BaseModel):
    mmsi: str
    imo: str = None

class QueryRequest(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"message": "Shadow Fleet Detection API"}

@app.post("/api/v1/simulation/start")
def start_simulation():
    app.state.sim_start = time.time()
    return {"message": "Simulation started", "start_time": app.state.sim_start}

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
    
    csv_start_time = df['TIMESTAMP'].min()
    real_elapsed = time.time() - app.state.sim_start
    sim_elapsed_seconds = real_elapsed * app.state.sim_speed
    current_sim_time = csv_start_time + pd.Timedelta(seconds=sim_elapsed_seconds)

    df_visible = df[df['TIMESTAMP'] <= current_sim_time]
    
    vessels = {}
    for mmsi, group in df_visible.groupby('MMSI'):
        group_sorted = group.sort_values('TIMESTAMP')
        pings = group_sorted.to_dict('records')
        
        ship_type = pings[0]['TYPE'].lower()
        score = calculate_reconstruction_error(pings, ship_type=ship_type)
        
        vessels[mmsi] = {
            "name": f"VESSEL_{mmsi}",
            "mmsi": str(mmsi),
            "imo": f"900{mmsi}" if mmsi < 10000000 else str(mmsi),
            "type": pings[0]['TYPE'],
            "status": "Anomaly Detected" if score > 0.1 else "Compliant",
            "score": round(score, 4),
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
