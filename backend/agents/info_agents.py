from typing import TypedDict, Any, Dict, Optional
from langgraph.graph import StateGraph, START, END

from ingestion.vessel_checks import (
    get_insurer_data,
    get_registration_data,
)
from agents.watson_client import get_watsonx_model


# ──────────────────────────────────────────────
# State
# ──────────────────────────────────────────────

class InfoAgentState(TypedDict):
    imo: str
    mmsi: str
    # Raw data populated by fetch_raw_data node
    raw_insurer: Dict[str, Any]
    raw_registration: Dict[str, Any]
    # Agent results populated by parallel agent nodes
    insurer_result: Dict[str, Any]
    registration_result: Dict[str, Any]
    # Final aggregated output
    aggregated: Dict[str, Any]


# ──────────────────────────────────────────────
# Prompts
# ──────────────────────────────────────────────

INSURER_PROMPT = """You are a maritime insurance analyst. Given the following vessel insurance data, determine whether the insurer is a well-known, reliable maritime insurance company.

Vessel IMO: {imo}
Vessel MMSI: {mmsi}
Insurer known: {insurer_known}
Raw data: {raw_data}

Respond in this exact format:
RELIABLE: YES or NO
RISK_LEVEL: LOW, MEDIUM, or HIGH
ANALYSIS: A brief 1-2 sentence explanation of your assessment.
"""

REGISTRATION_PROMPT = """You are a maritime compliance analyst specializing in flag state analysis. Given the following vessel registration data, determine whether the flag state is a known flag of convenience commonly used by shadow fleet ships.

Vessel IMO: {imo}
Vessel MMSI: {mmsi}
Registered country: {country}
Flag of convenience (based on known list): {foc}
Raw data: {raw_data}

Respond in this exact format:
FLAG_OF_CONVENIENCE: YES or NO
RISK_LEVEL: LOW, MEDIUM, or HIGH
ANALYSIS: A brief 1-2 sentence explanation of your assessment regarding shadow fleet risk.
"""


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _parse_llm_response(text: str) -> Dict[str, str]:
    """Parse the structured LLM response into a dict of key-value pairs."""
    result: Dict[str, str] = {}
    for line in text.strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _call_watsonx(prompt: str) -> str:
    """Call the watsonx model and return the generated text."""
    try:
        model = get_watsonx_model()
        response = model.generate_text(prompt=prompt)
        return response if isinstance(response, str) else str(response)
    except Exception as e:
        return f"Error calling watsonx: {str(e)}"


# ──────────────────────────────────────────────
# Nodes
# ──────────────────────────────────────────────

def fetch_raw_data(state: InfoAgentState) -> dict:
    """Fetch raw data for both agent-dependent checks."""
    imo = state["imo"]
    mmsi = state["mmsi"]
    return {
        "raw_insurer": get_insurer_data(imo, mmsi),
        "raw_registration": get_registration_data(imo, mmsi),
    }


def insurer_agent(state: InfoAgentState) -> dict:
    """
    Analyze insurer data using IBM watsonx to determine
    whether the vessel's insurer is a reliable, well-known company.
    """
    raw = state["raw_insurer"]

    prompt = INSURER_PROMPT.format(
        imo=state["imo"],
        mmsi=state["mmsi"],
        insurer_known=raw.get("insurer_known", False),
        raw_data=raw.get("raw_lakehouse", {}),
    )

    llm_response = _call_watsonx(prompt)
    parsed = _parse_llm_response(llm_response)

    return {
        "insurer_result": {
            "insurer_known": raw.get("insurer_known", False),
            "reliable": parsed.get("RELIABLE", "UNKNOWN"),
            "risk_level": parsed.get("RISK_LEVEL", "UNKNOWN"),
            "analysis": parsed.get("ANALYSIS", llm_response),
            "raw_llm_response": llm_response,
        }
    }


def registration_agent(state: InfoAgentState) -> dict:
    """
    Analyze registration / flag state data using IBM watsonx to determine
    whether the country is a flag of convenience used by shadow fleets.
    """
    raw = state["raw_registration"]

    prompt = REGISTRATION_PROMPT.format(
        imo=state["imo"],
        mmsi=state["mmsi"],
        country=raw.get("country", "Unknown"),
        foc=raw.get("flag_of_convenience", False),
        raw_data=raw.get("raw_registry", {}),
    )

    llm_response = _call_watsonx(prompt)
    parsed = _parse_llm_response(llm_response)

    return {
        "registration_result": {
            "country": raw.get("country", "Unknown"),
            "flag_of_convenience": parsed.get("FLAG_OF_CONVENIENCE", "UNKNOWN"),
            "risk_level": parsed.get("RISK_LEVEL", "UNKNOWN"),
            "analysis": parsed.get("ANALYSIS", llm_response),
            "raw_llm_response": llm_response,
        }
    }


def aggregate(state: InfoAgentState) -> dict:
    """Merge parallel agent results into a single output dict."""
    return {
        "aggregated": {
            "insurer": state["insurer_result"],
            "registration": state["registration_result"],
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
                    └→ registration_agent ─┘→ aggregate → END
    """
    graph = StateGraph(InfoAgentState)

    # Add nodes
    graph.add_node("fetch_raw_data", fetch_raw_data)
    graph.add_node("insurer_agent", insurer_agent)
    graph.add_node("registration_agent", registration_agent)
    graph.add_node("aggregate", aggregate)

    # Edges: START → fetch_raw_data
    graph.add_edge(START, "fetch_raw_data")

    # Fan-out: fetch_raw_data → two agents in parallel
    graph.add_edge("fetch_raw_data", "insurer_agent")
    graph.add_edge("fetch_raw_data", "registration_agent")

    # Fan-in: both agents → aggregate
    graph.add_edge("insurer_agent", "aggregate")
    graph.add_edge("registration_agent", "aggregate")

    # aggregate → END
    graph.add_edge("aggregate", END)

    return graph.compile()


# Compile once at import time
info_agent_app = build_info_graph()


def run_info_agents(imo: Optional[str] = None, mmsi: Optional[str] = None) -> Dict[str, Any]:
    """
    Public entry point. Runs the parallel info agent graph and
    returns the aggregated results for insurer and registration.
    """
    initial_state: InfoAgentState = {
        "imo": imo or "",
        "mmsi": mmsi or "",
        "raw_insurer": {},
        "raw_registration": {},
        "insurer_result": {},
        "registration_result": {},
        "aggregated": {},
    }

    result = info_agent_app.invoke(initial_state)
    return result.get("aggregated", {})
