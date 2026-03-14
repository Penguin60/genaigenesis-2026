import os
from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

load_dotenv()

# --- Configuration from environment ---
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
WATSONX_URL = os.getenv("WATSONX_URL", "https://ca-tor.ml.cloud.ibm.com")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_MODEL_ID = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")

# Generation parameters tuned for concise analytical responses
GENERATE_PARAMS = {
    GenParams.MAX_NEW_TOKENS: 300,
    GenParams.TEMPERATURE: 0.2,
    GenParams.TOP_P: 0.9,
    GenParams.REPETITION_PENALTY: 1.1,
}

_model_instance: ModelInference | None = None


def get_watsonx_model() -> ModelInference:
    """
    Returns a singleton ModelInference instance.
    Lazily initialised so the server can still start without credentials
    (useful for local dev on non-agent endpoints).
    """
    global _model_instance
    if _model_instance is None:
        if not WATSONX_API_KEY or not WATSONX_PROJECT_ID:
            raise RuntimeError(
                "Missing WATSONX_API_KEY or WATSONX_PROJECT_ID in environment. "
                "Set them in backend/.env"
            )
        _model_instance = ModelInference(
            model_id=WATSONX_MODEL_ID,
            params=GENERATE_PARAMS,
            credentials=Credentials(
                api_key=WATSONX_API_KEY,
                url=WATSONX_URL,
            ),
            project_id=WATSONX_PROJECT_ID,
        )
    return _model_instance
