# VEIL

Runtime authorization gateway for AI agents. Proposed tool actions are intercepted before execution and evaluated in application code (not by the LLM) against user policy, user intent, instruction provenance, the requested action, and resource context.

Decisions are exactly one of `ALLOW`, `REVIEW`, or `BLOCK`. A `BLOCK` decision must prevent the underlying tool from running. Every decision writes an audit record.

This repository currently contains the project skeleton only.

## Layout

- `backend/` — FastAPI gateway, deterministic authorization stubs, simulated agent, SQLite
- `frontend/` — Next.js + TypeScript + Tailwind operator UI

## Run (after later implementation)

Backend:

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

Frontend:

```
cd frontend
npm run dev
```
