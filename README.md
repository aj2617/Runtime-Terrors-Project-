# GridWise Energy Optimizer

GridWise is a deployed FastAPI service for the BUP CSE Fest 24-hour smart-campus energy challenge. It receives hourly demand, solar, tariff, battery data, and one to three natural-language operator notes; it returns machine-checkable note interpretations and a valid minimum-cost schedule.

## Public API

Base URL: `https://runtime-terrors-project.onrender.com`

- `GET /` — service welcome message
- `GET /health` — readiness response: `{"status":"ok"}`
- `POST /optimize-energy` — LLM interpretation and 24-hour optimization
- `GET /docs` — interactive Swagger API documentation

The judge-facing endpoints are public, require no login, and use structured JSON.

## Architecture

`POST /optimize-energy` follows this fixed pipeline:

1. Pydantic validates the request: 24 unique hours `0`–`23`, valid battery bounds, and 1–3 non-empty notes.
2. Groq `openai/gpt-oss-120b` makes one batched LLM call to extract exactly one directive per note.
3. Deterministic guardrails validate note indexes, directive types, adjustment shape, ordered hours, factors, reserves, grid caps, and `no_op` semantics.
4. The directive compiler converts validated output into optimizer constraints.
5. SciPy `linprog` with HiGHS minimizes grid-electricity cost.
6. An independent replay validator checks every hourly balance, solar cap, battery transition/bounds/rates, directive, final neutrality, and reported total.

The LLM only interprets human language. It never directly schedules energy or changes input demand, tariff, solar forecast, or battery parameters.

## Supported directives

`solar_reduction`, `minimum_battery_reserve`, `no_charge_window`, `no_discharge_window`, `max_grid_window`, and `no_op` are the only supported directive types. Windows are start-inclusive/end-exclusive; for example, 1 PM–3 PM maps to `[13, 14]`. A solar factor is the fraction remaining, so an 80% reduction means `factor: 0.2`.

## Local setup

Requirements: Python 3.11+ and a Groq API key.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set these environment variables in `.env`:

```env
LLM_API_KEY=your-groq-api-key
LLM_MODEL=openai/gpt-oss-120b
LLM_BASE_URL=https://api.groq.com/openai/v1
```

Run locally:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Verify the API

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Run the official `SAMPLE-01` input through the local API:

```powershell
$body = Get-Content -Raw sample_cases\sample_01_request.json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/optimize-energy `
  -ContentType "application/json" -Body $body
```

Expected: `scenario_id` is `SAMPLE-01`, there are two directives and 24 plan entries, and `total_cost_bdt` is `38365`.

For the deployed service, replace `http://127.0.0.1:8000` with `https://runtime-terrors-project.onrender.com` or use [the deployed API docs](https://runtime-terrors-project.onrender.com/docs).

## Tests

The official ten public cases are stored unmodified in `sample_cases/public_cases.json`. Run:

```powershell
pytest -q
```

Expected result: `26 passed`. Tests cover public-case optimal costs, replay validity, API responses, malformed input, provider failures, and directive guardrails. Equivalent schedules are accepted; tests compare constraints and cost rather than byte-for-byte plans.

## Docker fallback

Published image:

```text
shihab34/gridwise:latest
shihab34/gridwise@sha256:6d9a402c50ffc05a2bca4b5a9337b1b5382030fd46e998b7b804b09c2a819117
```

Run it with runtime secrets only:

```powershell
docker pull shihab34/gridwise:latest
docker run --rm -p 8000:8000 --env-file .env shihab34/gridwise:latest
```

The image exposes port `8000`, binds to `0.0.0.0`, supports Render's `PORT` environment variable, and does not contain `.env`. GitHub Actions also publishes `ghcr.io/aj2617/runtime-terrors-project-:latest`.

## Security and limitations

Never commit `.env`, Docker Hub tokens, or LLM keys. Keep secrets in local `.env` files and deployment environment variables. Provider/network failures return a controlled error without exposing raw provider details or credentials.

The solver intentionally implements only the challenge rules. It does not invent battery efficiency, degradation, export, solar selling, carbon cost, or demand shifting. A live request requires a reachable Groq provider and valid configured environment variables.
