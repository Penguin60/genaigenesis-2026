import re

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
import requests
from google import genai

load_dotenv()

client = genai.Client()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

from scoring.risk_calculator import calculate_sri
from agents.orchestrator import query_agent
from agents.info_agents import run_info_agents
from agents.chat_agent import run_chat
from ingestion.vessel_checks import check_retirement, get_ship_age, get_insurer_data, get_registration_data
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
app.state.sim_speed = 600

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

    vessel_info_cache = {}
    vessel_prompt_result_cache = {}
    vessel_prompt_score_cache = {}
    vessel_flag_cache = {}

    prompt = """You are a maritime risk analysis assistant. For each vessel, you will receive structured data including retirement status, age, insurer information, and registration details. Please provide a holistic risk assessment for the vessel, considering:

If the registration country is a common flag-of-convenience or AIS spoofing country (e.g., Comoros, Panama, Liberia, Marshall Islands, Togo, Palau, Cook Islands, Gabon, Cameroon, Mongolia, Belize, St. Kitts and Nevis, Sierra Leone).
If the vessel is older than 15 years.
If the insurer is unknown or marked as high risk.
Any other relevant risk factors in the data.
Here is the vessel data:

"""
    # Collect all vessel infos
    all_vessel_infos = []
    mmsi_list = []
    for mmsi in df['MMSI'].unique():
        vessel_info = {
            "retirement": check_retirement(mmsi=mmsi),
            "age": get_ship_age(mmsi=mmsi),
            "insurer": get_insurer_data(mmsi=mmsi),
            "registration": get_registration_data(mmsi=mmsi),
        }
        vessel_info_cache[mmsi] = vessel_info
        mmsi_list.append(str(mmsi))
        print("running")
        all_vessel_infos.append(f"MMSI: {mmsi}\n{vessel_info}")
        print(vessel_info["registration"])
        vessel_flag_cache[str(mmsi)] = vessel_info["registration"].get("country", "Unknown")

    batch_prompt = prompt + "\n\n".join(all_vessel_infos) + """\n\nFor each vessel above, provide a concise risk summary and highlight any red flags or suspicious factors. Also provide a risk score from 0 to 1, be conservative in your estimates especially for insurance as the API has some issues. Your response should be limited to a maximum of 3 bullet points per vessel, in the same order as input, separated by \n---\n. Do not use emojis. Do not include a header at the beginning of your response like MMSI: xxxxxxx. Instead, here is a sample * Multiple red flags including an age of 22 years and status indicating it should be retired.
* High-risk registration in Comoros, frequently used to obscure vessel activity and origin.
* Lacks a known insurer and is linked to shell company risk and high-risk ownership structures.
Data Risk Score: 0.23"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview", contents=batch_prompt
    )
    if not response or not getattr(response, "text", None):
        for mmsi in mmsi_list:
            vessel_prompt_result_cache[str(mmsi)] = "AI summary not available"
    else:
        summaries = response.text.split("---")
        for idx, mmsi in enumerate(mmsi_list):
            vessel_prompt_result_cache[str(mmsi)] = summaries[idx].strip() if idx < len(summaries) else "No summary returned."
            match = re.search(r"Risk Score:\s*([0-1](?:\.\d+)?)", summaries[idx].strip() if idx < len(summaries) else "No summary returned.")
            if match:
                vessel_prompt_score_cache[str(mmsi)] = float(match.group(1))
            else:
                vessel_prompt_score_cache[str(mmsi)] = None
    print(response)

    print(vessel_prompt_result_cache)

    csv_start_time = df['TIMESTAMP'].min()
    csv_end_time = df['TIMESTAMP'].max()
    total_span_seconds = max((csv_end_time - csv_start_time).total_seconds(), 0.0)
    initial_offset_seconds = total_span_seconds * 0
    
    app.state.sim_csv_start = csv_start_time + pd.Timedelta(seconds=initial_offset_seconds)
    app.state.sim_start = time.time()

    app.state.vessel_prompt_result_cache = vessel_prompt_result_cache
    app.state.vessel_prompt_score_cache = vessel_prompt_score_cache

    app.state.vessel_flag_cache = vessel_flag_cache
    
    return {
        "message": "Simulation started",
        "start_time": app.state.sim_start,
        "csv_start_reference": app.state.sim_csv_start.isoformat(),
        "initial_offset_seconds": initial_offset_seconds,
        "vessel_prompt_results": vessel_prompt_result_cache,
        "vessel_prompt_scores": vessel_prompt_score_cache,
        "vessel_flags": vessel_flag_cache,
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
        group_sorted = group.sort_values('TIMESTAMP')
        pings = group_sorted.to_dict('records')
        
        ship_type = pings[0]['TYPE'].lower()
        score = calculate_reconstruction_error(pings, ship_type=ship_type)
        
        # Provide the latest point separately for easy frontend rendering
        latest = pings[-1]

        if not hasattr(app.state, "behavior_analysis_cache"):
            app.state.behavior_analysis_cache = {}

        behavior_analysis_cache = app.state.behavior_analysis_cache

        if score > 0.05:
            mmsi_str = str(mmsi)
            if mmsi_str not in behavior_analysis_cache:
                track = [{"ts": p['TIMESTAMP'].isoformat(), "lat": p['LAT'], "lon": p['LON'], "course": p['COURSE'], "speed": p['SPEED']} for p in pings]
                recent_track = track[-10:]
                gemini_prompt = (
                    f"Vessel MMSI: {mmsi_str}\n"
                    f"Recent Path: {recent_track}\n"
                    "Categorize the vessel's behavior as one of: going dark, heading error, speed error, or location jump. If there is a sudden change in heading, say it's a heading error not a jump. If a vessel fails to broadcast for over 30 minutes, set it as going dark."
                    "Return your answer in the format:\n"
                    "Category: <category>\nJustification: <brief explanation>"
                )
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview", contents=gemini_prompt
                )
                behavior_analysis_cache[mmsi_str] = response.text if response and getattr(response, "text", None) else "No analysis available"
            
        
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
        "vessels": list(vessels.values()),
        "behavior_analysis": app.state.behavior_analysis_cache
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
