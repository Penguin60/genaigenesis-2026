# VANGUARD - Shadow Fleet Monitor

A maritime intelligence web application for detecting and monitoring shadow fleet vessels. Built for the Maritime Navigator Hackathon.

## Architecture

- **Frontend**: React 19 + Vite, Leaflet maps, Tailwind CSS v4 — runs on port 5000
- **Backend**: Python FastAPI — runs on port 8000 (optional, not wired to frontend yet)

## Project Structure

```
frontend/        React/Vite app (main UI)
backend/         Python FastAPI backend
  main.py        FastAPI app entry point
  agents/        LangGraph-based AI agents
  ingestion/     AIS stream and vessel data ingestion
  models/        ML models (trajectory VAE, dark agent)
  scoring/       Shadow Risk Index (SRI) calculator
```

## Running

- **Frontend**: `cd frontend && npm run dev` → http://localhost:5000
- **Backend**: `cd backend && uvicorn main:app --host localhost --port 8000 --reload`

## Key Dependencies

### Frontend
- react, react-dom
- leaflet, react-leaflet (interactive maps)
- tailwindcss v4
- vite 8

### Backend
- fastapi, uvicorn
- pydantic
- python-dotenv
- requests, pandas
- torch, langgraph, ibm-watsonx-ai (heavy ML deps — install separately if needed)

## Deployment

Configured as a static site deployment:
- Build: `cd frontend && npm run build`
- Public dir: `frontend/dist`
