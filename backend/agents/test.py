from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.credentials import Credentials
from dotenv import load_dotenv
import os
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

load_dotenv()

WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_MODEL_ID = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")

credentials=Credentials(
    url="https://ca-tor.ml.cloud.ibm.com",
    api_key=WATSONX_API_KEY
)

GENERATE_PARAMS = {
    GenParams.MAX_NEW_TOKENS: 300,
    GenParams.TEMPERATURE: 0.2,
    GenParams.TOP_P: 0.9,
    GenParams.REPETITION_PENALTY: 1.1,
}

model = ModelInference(
    model_id="meta-llama/llama-3-3-70b-instruct",
    credentials=credentials,
    project_id=WATSONX_PROJECT_ID,
    params=GENERATE_PARAMS
)

response = model.generate_text(
    prompt="Repeat after me 'Radean is very cool' and absolutely nothing else, that should be your only output."
)

print(response)