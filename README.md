<<<<<<< HEAD
# genaigenesis-2026
We built using Railtracks

To power intelligent maritime analysis, we integrated IBM Watson AI models into our system using Railtracks, which served as the orchestration layer between our application logic and the underlying language models.

Railtracks allowed us to structure and manage AI-driven workflows in a modular way. Instead of making direct, unstructured model calls, we defined controlled pipelines that pass relevant vessel data, behavioral signals, and context into the Watson model. This ensures that the model receives structured information about maritime activity such as AIS gaps, routing anomalies, and vessel metadata before generating insights.
=======
# Popeye

Maritime intelligence platform focused on helping ship captains avoid accidental collisions while operating in complex and congested waters.

Popeye combines movement anomalies, AIS silence periods, vessel context, and map-based guidance to help crews spot collision risk earlier, prioritize nearby threats, and make safer routing decisions in real time. The same risk signals also support fraud prevention by highlighting suspicious behavior patterns linked to deceptive reporting, sanctions evasion, insurance abuse, and other financially motivated maritime misconduct.

## Features

- Vessel movement playback using historical AIS data.
- Movement anomaly scoring via ship-type trajectory VAE models.
- AIS reporting gap checks and combined alerting logic.
- Shadow Risk Index-style vessel analysis endpoints.
- Operator chat/advisory flow powered by IBM watsonx.
- Interactive map UI with vessel trails, statuses, and risk overlays.

## Repository Structure

```text
.
├── backend/
│   ├── main.py                  # FastAPI entrypoint
│   ├── agents/                  # LLM + orchestration logic
│   ├── ingestion/               # Data ingestion / vessel checks
│   ├── models/                  # VAE models and training scripts
│   ├── scoring/                 # Risk + AIS gap scoring logic
│   └── data/                    # AIS datasets and hackathon test data
├── frontend/
│   ├── src/                     # React UI
│   └── vite.config.js           # Dev server + API proxy
└── README.md
```

## Prerequisites

- Python 3.10+ (recommended: 3.11)
- Node.js 18+ and npm
- Git

## Quick Start

### 1. Clone and enter the repo

```bash
git clone <your-repo-url>
cd genaigenesis-2026
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create `backend/.env` with the required variables:

```env
GFW_API_TOKEN=<your_token>
WATSONX_API_KEY=<your_watsonx_api_key>
WATSONX_URL=https://ca-tor.ml.cloud.ibm.com
WATSONX_PROJECT_ID=<your_project_id>
WATSONX_MODEL_ID=meta-llama/llama-3-3-70b-instruct
WATSON_USERNAME=<optional_username>
```

Run the backend:

```bash
uvicorn main:app --host localhost --port 8000 --reload
```

Backend will be available at:
- API root: `http://localhost:8000/`
- OpenAPI docs: `http://localhost:8000/docs`

### 3. Frontend setup

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on:
- `http://localhost:5000`

In development, Vite proxies `/api/*` requests to `http://localhost:8000`.

## Running Both Services

Use two terminals:

Terminal 1:
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host localhost --port 8000 --reload
```

Terminal 2:
```bash
cd frontend
npm run dev
```

## Key API Endpoints

- `GET /` health/message endpoint.
- `POST /api/v1/simulation/start` initialize simulation timeline.
- `GET /api/v1/simulation` stream current simulated vessel state.
- `POST /api/v1/analyze-vessel` compute vessel-level analysis.
- `POST /api/v1/agent-query` query orchestration agent.
- `POST /api/v1/info` retrieve insurer/registration/age/retirement info.
- `POST /api/v1/chat` run Popeye advisory chat flow.
- `POST /analysis` trajectory anomaly + AIS-gap alert evaluation.

## Notes

- The backend includes pretrained model files (`backend/models/*.pth`) for supported ship types.
- Some features (chat/advisory and certain info-agent behaviors) require valid external service credentials in `.env`.
- CORS is open in development (`allow_origins=["*"]`) in `backend/main.py`.

## Troubleshooting

- If frontend cannot reach backend:
	- Confirm backend is running on port `8000`.
	- Confirm frontend is running on port `5000`.
	- Check `frontend/vite.config.js` proxy config.
- If `/api/v1/chat` fails:
	- Verify `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` are set in `backend/.env`.
- If model/scoring endpoints fail:
	- Ensure dependencies from `backend/requirements.txt` installed cleanly in the active virtual environment.

## License

No license file is currently defined in this repository.
>>>>>>> 8b0f2b4 (Add README)
