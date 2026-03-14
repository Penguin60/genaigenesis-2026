from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class AgentState(TypedDict):
    query: str
    response: str

def process_query(state: AgentState) -> AgentState:
    """
    Node that processes the query. Prompts watsonx or other models.
    """
    # TODO: Implement actual LLM call
    # llm_response = call_watsonx(state["query"])
    return {"response": f"Simulated agent response for: {state['query']}"}

def format_output(state: AgentState) -> AgentState:
    """
    Node that formats the output to the required convention.
    """
    return {"response": f"[Agent Output] {state.get('response', '')}"}

def setup_graph():
    """
    Sets up a sequential langgraph orchestrator.
    """
    workflow = StateGraph(AgentState)
    
    workflow.add_node("process_query", process_query)
    workflow.add_node("format_output", format_output)

    workflow.add_edge(START, "process_query")
    workflow.add_edge("process_query", "format_output")
    workflow.add_edge("format_output", END)

    app = workflow.compile()
    return app

# Singleton-like compilation for server startup
agent_app = setup_graph()

def query_agent(query_str: str) -> str:
    """
    Entrypoint for external queries routing through LangGraph.
    """
    state_input = {"query": query_str, "response": ""}
    # The runner processes the graph logic
    try:
        # Compatibility with new langgraph API
        output = agent_app.invoke(state_input)
        return output.get('response', "No response parsed")
    except Exception as e:
        return f"Error executing LangGraph workflow: {str(e)}"
