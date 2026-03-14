from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from scoring.risk_calculator import calculate_sri
from agents.orchestrator import query_agent

app = FastAPI(
    title="Shadow Fleet Detection API",
    description="Backend template for Maritime Navigator Hackathon Project.",
    version="1.0.0"
)

class VesselRequest(BaseModel):
    mmsi: str
    imo: str = None

class QueryRequest(BaseModel):
    query: str

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
