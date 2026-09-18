# GridWise Energy Optimizer

GridWise is a 24-hour smart-campus energy scheduling API for the BUP CSE Fest challenge. It uses one LLM call to convert 1–3 operator notes into a strict directive schema, validates that untrusted output deterministically, solves the resulting linear program with SciPy HiGHS, and replays the schedule before returning it.

## Architecture

`POST /optimize-energy` → Pydantic validation → batched LLM interpretation → directive guardrails → LP optimizer → independent replay validation → JSON response.

The model only interprets note meaning. It cannot alter demand, tariffs, solar, or battery inputs; deterministic code enforces the six allowed directive types and all numerical constraints.

## Requirements and setup

Use Python 3.11+ and create a virtual environment. Install dependencies, then configure an OpenAI-compatible model:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set the following values in `.env` (never commit this file):

```env
LLM_API_KEY=your-provider-key
LLM_MODEL=openai/gpt-oss-120b
LLM_BASE_URL=https://api.groq.com/openai/v1
```

Start the service:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Check readiness at `GET http://127.0.0.1:8000/health`; interactive API documentation is at `/docs`.

## Test

The official public fixture is stored in `sample_cases/public_cases.json`. It contains ten scenarios. Run:

```powershell
pytest -q
```

Expected result: `23 passed`. Tests validate the public optimizer costs, replay rules, and API contract using mocked structured LLM interpretations. A configured provider is needed for live natural-language interpretation.

## Docker fallback

Build and run locally without baking in secrets:

```powershell
docker build -t gridwise:local .
docker run --rm -p 8000:8000 --env-file .env gridwise:local
```

Then open `http://127.0.0.1:8000/health`. Before submission, publish this image to your chosen registry with a fixed tag or digest and replace this README section with its exact pull command.

## Limitations and security

The default example configuration uses Groq's OpenAI-compatible API and `openai/gpt-oss-120b`. Another OpenAI-compatible provider can be used by changing `LLM_BASE_URL` and `LLM_MODEL`. Provider failures return a controlled error; raw provider errors and keys are not returned by the API. `.env` is ignored by Git. The LP deliberately models only rules defined in the challenge: no efficiency, export, degradation, or demand-shifting assumptions are added.
