import os
from pathlib import Path
from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

env_path = Path(__file__).resolve().parent.parent / '.env'
_model_instance: ModelInference | None = None

def get_watsonx_model() -> ModelInference:
    global _model_instance

    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("WATSONX_API_KEY", "")
    project_id = os.getenv("WATSONX_PROJECT_ID", "")
    url = os.getenv("WATSONX_URL", "https://ca-tor.ml.cloud.ibm.com")
    model_id = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")

    if _model_instance is None:
        if not api_key or not project_id:
            # This is the error triggering in your screenshot
            raise RuntimeError(
                f"Missing credentials in environment. checked: {env_path}"
            )

        _model_instance = ModelInference(
            model_id=model_id,
            params={
                GenParams.MAX_NEW_TOKENS: 300,
                GenParams.TEMPERATURE: 0.2,
                GenParams.TOP_P: 0.9,
                GenParams.REPETITION_PENALTY: 1.1,
            },
            credentials=Credentials(
                api_key=api_key,
                url=url,
            ),
            project_id=project_id,
        )
    return _model_instance