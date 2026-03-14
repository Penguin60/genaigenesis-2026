from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

from scoring.risk_calculator import calculate_sri
from agents.orchestrator import query_agent
from agents.info_agents import run_info_agents
from agents.chat_agent import run_chat
from ingestion.vessel_checks import check_retirement, get_ship_age

app = FastAPI(
    title="Shadow Fleet Detection API",
    description="Backend for Maritime Navigator Hackathon Project.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VesselRequest(BaseModel):
    mmsi: str
    imo: str = None

class QueryRequest(BaseModel):
    query: str

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = ""

@app.get("/")
def read_root():
    return {"message": "Welcome to the Shadow Fleet Detection API"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
