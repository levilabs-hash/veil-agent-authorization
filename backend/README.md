# VEIL backend

FastAPI runtime authorization gateway. Deterministic policy evaluation belongs in `app/services/authorization.py`. Simulated tools execute only after ALLOW.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Authorization engine tests:

```
python -m pytest
```

LLM agent (optional). If `OPENAI_API_KEY` is unset, a deterministic simulated agent proposes tools instead. The LLM never authorizes or executes tools.

```
python -m app.sim.llm_scenarios
```
