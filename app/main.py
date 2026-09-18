from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.schemas import EnergyRequest


app = FastAPI(
    title="GridWise Energy Optimizer",
    version="1.0.0"
)


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


@app.post("/optimize-energy")
async def optimize_energy(request: EnergyRequest):

    if len(request.operator_notes) < 1 or len(request.operator_notes) > 3:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "operator_notes must contain between 1 and 3 notes"
            }
        )

    if len(request.hours) != 24:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "hours must contain exactly 24 entries"
            }
        )

    hour_numbers = sorted(
        hour.hour for hour in request.hours
    )

    if hour_numbers != list(range(24)):
        return JSONResponse(
            status_code=400,
            content={
                "detail": "hours must contain unique hours 0 through 23"
            }
        )

    return {
        "scenario_id": request.scenario_id,
        "message": "Request validation successful. Optimizer not connected yet."
    }