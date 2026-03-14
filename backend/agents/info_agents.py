from typing import TypedDict, Any, Dict, Optional
from langgraph.graph import StateGraph, START, END

from ingestion.vessel_checks import (
    get_insurer_data,
    get_registration_data,
    get_ownership_data,
)


# ──────────────────────────────────────────────
# State
# ──────────────────────────────────────────────

class InfoAgentState(TypedDict):
    imo: str
    mmsi: str
    # Raw data populated by fetch_raw_data node
    raw_insurer: Dict[str, Any]
    raw_registration: Dict[str, Any]
    raw_ownership: Dict[str, Any]
    # Agent results populated by parallel agent nodes
    insurer_result: Dict[str, Any]
    registration_result: Dict[str, Any]
    ownership_result: Dict[str, Any]
    # Final aggregated output
    aggregated: Dict[str, Any]


# ──────────────────────────────────────────────
# Nodes
# ──────────────────────────────────────────────

def fetch_raw_data(state: InfoAgentState) -> dict:
    """Fetch raw data for all three agent-dependent checks."""
    imo = state["imo"]
    mmsi = state["mmsi"]
    return {
        "raw_insurer": get_insurer_data(imo, mmsi),
        "raw_registration": get_registration_data(imo, mmsi),
        "raw_ownership": get_ownership_data(imo, mmsi),
    }


def insurer_agent(state: InfoAgentState) -> dict:
    """
    Analyze insurer data. Currently a stub.
    TODO: Replace with actual AI agent call (e.g. watsonx LLM).
    """
    raw = state["raw_insurer"]
    return {
        "insurer_result": {
            "insurer": raw.get("raw_lakehouse", {}).get("entity", "Unknown"),
            "insurer_known": raw.get("insurer_known", False),
            "analysis": "Stub — agent not yet integrated",
            "agent_status": "not_integrated",
            "requires_agent": True,
        }
    }


def registration_agent(state: InfoAgentState) -> dict:
    """
    Analyze registration / flag state data. Currently a stub.
    TODO: Replace with actual AI agent call (e.g. watsonx LLM).
    """
    raw = state["raw_registration"]
    return {
        "registration_result": {
            "country": raw.get("country", "Unknown"),
            "flag_of_convenience": raw.get("flag_of_convenience", False),
            "analysis": "Stub — agent not yet integrated",
            "agent_status": "not_integrated",
            "requires_agent": True,
        }
    }


def ownership_agent(state: InfoAgentState) -> dict:
    """
    Analyze ownership structure and detect shell companies. Currently a stub.
    TODO: Replace with actual AI agent call (e.g. watsonx LLM).
    """
    raw = state["raw_ownership"]
    return {
        "ownership_result": {
            "companies": [raw.get("raw_lakehouse", {}).get("entity", "Unknown")],
            "shell_company_risk": raw.get("shell_company_risk", False),
            "ownership_level": raw.get("ownership_level", "Unknown"),
            "analysis": "Stub — agent not yet integrated",
            "agent_status": "not_integrated",
            "requires_agent": True,
        }
    }


def aggregate(state: InfoAgentState) -> dict:
    """Merge parallel agent results into a single output dict."""
    return {
        "aggregated": {
            "insurer": state["insurer_result"],
            "registration": state["registration_result"],
            "ownership": state["ownership_result"],
        }
    }


# ──────────────────────────────────────────────
# Graph construction
# ──────────────────────────────────────────────

def build_info_graph() -> StateGraph:
    """
    Build a LangGraph with fan-out parallelism:

        START → fetch_raw_data
                    ├→ insurer_agent ──────┐
                    ├→ registration_agent ─┤→ aggregate → END
                    └→ ownership_agent ────┘
    """
    graph = StateGraph(InfoAgentState)

    # Add nodes
    graph.add_node("fetch_raw_data", fetch_raw_data)
    graph.add_node("insurer_agent", insurer_agent)
    graph.add_node("registration_agent", registration_agent)
    graph.add_node("ownership_agent", ownership_agent)
    graph.add_node("aggregate", aggregate)

    # Edges: START → fetch_raw_data
    graph.add_edge(START, "fetch_raw_data")

    # Fan-out: fetch_raw_data → three agents in parallel
    graph.add_edge("fetch_raw_data", "insurer_agent")
    graph.add_edge("fetch_raw_data", "registration_agent")
    graph.add_edge("fetch_raw_data", "ownership_agent")

    # Fan-in: all three agents → aggregate
    graph.add_edge("insurer_agent", "aggregate")
    graph.add_edge("registration_agent", "aggregate")
    graph.add_edge("ownership_agent", "aggregate")

    # aggregate → END
    graph.add_edge("aggregate", END)

    return graph.compile()


# Compile once at import time
info_agent_app = build_info_graph()


def run_info_agents(imo: Optional[str] = None, mmsi: Optional[str] = None) -> Dict[str, Any]:
    """
    Public entry point. Runs the parallel info agent graph and
    returns the aggregated results for insurer, registration, and ownership.
    """
    initial_state: InfoAgentState = {
        "imo": imo or "",
        "mmsi": mmsi or "",
        "raw_insurer": {},
        "raw_registration": {},
        "raw_ownership": {},
        "insurer_result": {},
        "registration_result": {},
        "ownership_result": {},
        "aggregated": {},
    }

    result = info_agent_app.invoke(initial_state)
    return result.get("aggregated", {})
