from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

from scoring.risk_calculator import calculate_sri
from agents.orchestrator import query_agent
from agents.info_agents import run_info_agents
from ingestion.vessel_checks import check_retirement, get_ship_age
from models.trajectory_vae import calculate_reconstruction_error
from scoring.gap_check import analyze_ais_reporting_gaps

app = FastAPI(
    title="Shadow Fleet Detection API",
    description="Backend template for Maritime Navigator Hackathon Project.",
    version="1.0.0"
)

class VesselRequest(BaseModel):
    mmsi: str
    imo: Optional[str] = None

class QueryRequest(BaseModel):
    query: str

class AnalysisRequest(BaseModel):
    trajectory: List[Dict[str, Any]]
    ship_type: str = "tanker"

@app.get("/")
def read_root():
    return {"message": "Welcome to the Shadow Fleet Detection API"}

@app.post("/api/v1/analyze-vessel")
def analyze_vessel(request: VesselRequest) -> Dict[str, Any]:
    """
    Analyzes a given vessel using multi-signal ingestion, trajectory models,
    and dark period agents to compute a final Shadow-Risk Index (SRI).
    """
    try:
        # In a real scenario, this would orchestrate calls to ingestion layers and models.
        # Here we just call our SRI calculator stub:
        result = calculate_sri(request.mmsi, request.imo)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/agent-query")
def ask_agent(request: QueryRequest) -> Dict[str, Any]:
    """
    Query existing AI agents through LangGraph for more complex or basic queries.
    """
    try:
        response = query_agent(request.query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/info")
def vessel_info(request: VesselRequest) -> Dict[str, Any]:
    """
    Aggregated vessel intelligence endpoint.
    Queries retirement status, ship age, and runs two parallel AI agent
    checks (insurer reliability, flag-of-convenience analysis) via LangGraph + watsonx.
    """
    try:
        # Direct checks (no agent needed)
        retirement = check_retirement(imo=request.imo, mmsi=request.mmsi)
        age = get_ship_age(imo=request.imo, mmsi=request.mmsi)

        # Parallel agent checks via LangGraph fan-out/fan-in
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
