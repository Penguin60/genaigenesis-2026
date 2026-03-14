import json
import railtracks as rt
from dotenv import load_dotenv
from agents.watson_client import get_watsonx_model

load_dotenv()

SYSTEM_PROMPT = """You are VANGUARD Advisor, an AI maritime safety assistant integrated into the VANGUARD Shadow Fleet Monitor. Your role is to help operators navigate safely by advising them based on real-time threat intelligence from the system.

You will be given a snapshot of the current threat picture, including flagged vessel positions, statuses, and identified danger zones. Use this data to give concise, actionable navigation advice.

Rules:
- Be direct and concise (3-5 sentences max)
- Reference specific vessel names, statuses, or coordinates when relevant
- Always recommend avoiding areas with AIS Gap, Dark Activity, Rendezvous, or Flag Hopping vessels
- Use nautical terminology appropriately
- If the user asks a general question not related to navigation, still answer helpfully but briefly
"""


@rt.function_node
async def generate_advisory(user_input: str) -> str:
    """
    Railtracks function node that calls the watsonx model to produce
    a maritime navigation advisory based on the operator's message
    and current threat-intelligence context.

    user_input: JSON string with keys 'message' and 'context'.
    """
    data = json.loads(user_input)
    message = data.get("message", "")
    context = data.get("context", "No threat data available.")

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"--- Current Threat Intelligence ---\n{context}\n"
        f"--- End of Intelligence ---\n\n"
        f"Operator: {message}\n"
        f"VANGUARD Advisor:"
    )

    try:
        model = get_watsonx_model()
        response = model.generate_text(prompt=prompt)
        return response.strip() if isinstance(response, str) else str(response).strip()
    except Exception as e:
        return f"Advisory unavailable: {e}"


chat_flow = rt.Flow("VANGUARD Chat Advisor", entry_point=generate_advisory)


def run_chat(message: str, context: str) -> str:
    """
    Public entry point called by the FastAPI /api/v1/chat endpoint.
    Runs the Railtracks flow and returns the advisory text.
    """
    try:
        payload = json.dumps({"message": message, "context": context})
        result = chat_flow.invoke(payload)
        return result if isinstance(result, str) else str(result)
    except Exception as e:
        return f"Advisory system error: {str(e)}"
