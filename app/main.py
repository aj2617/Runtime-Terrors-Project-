from fastapi import FastAPI, HTTPException
from app.directives.compiler import apply_directives
from app.directives.validator import DirectiveValidationError
from app.llm.interpreter import LLMProviderError, interpret_notes
from app.optimizer.solver import OptimizationError, optimize_energy
from app.schemas import EnergyRequest, EnergyResponse
from app.validation.replay import ReplayValidationError, validate_plan

app = FastAPI(title="GridWise Energy Optimizer", version="1.0.0")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/optimize-energy", response_model=EnergyResponse)
async def optimize_energy_endpoint(request: EnergyRequest):
    try:
        directives = interpret_notes(request.operator_notes, request.battery)
        constraints = apply_directives(request.hours, request.battery, directives)
        result = optimize_energy(request.hours, request.battery, constraints)
        validate_plan(result["hourly_plan"], request.hours, request.battery, constraints, result)
    except DirectiveValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid directive interpretation: {exc}") from exc
    except OptimizationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=500, detail="Directive interpretation is temporarily unavailable") from exc
    except ReplayValidationError as exc:
        raise HTTPException(status_code=500, detail=f"Internal schedule validation failed: {exc}") from exc
    return {"scenario_id": request.scenario_id, "directive_interpretation": directives,
            **result, "plan_summary": "Lowest-cost feasible 24-hour schedule validated by replay."}
