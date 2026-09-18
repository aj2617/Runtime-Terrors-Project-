import json
from pathlib import Path

import pytest

from app.directives.compiler import apply_directives
from app.directives.validator import validate_directives
from app.optimizer.solver import optimize_energy
from app.schemas import DirectiveInterpretation, EnergyRequest
from app.validation.replay import validate_plan


CASES = json.loads(
    (Path(__file__).parents[1] / "sample_cases" / "public_cases.json").read_text(encoding="utf-8")
)["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_public_case_optimizer_matches_reference_cost(case):
    """Schedules may differ, but every feasible optimal cost must match the public reference."""
    request = EnergyRequest.model_validate(case["input"])
    directives = [
        DirectiveInterpretation.model_validate(item)
        for item in case["expected_output"]["directive_interpretation"]
    ]
    directives = validate_directives(directives, len(request.operator_notes), request.battery)
    constraints = apply_directives(request.hours, request.battery, directives)
    result = optimize_energy(request.hours, request.battery, constraints)
    validate_plan(result["hourly_plan"], request.hours, request.battery, constraints, result)

    assert result["total_cost_bdt"] == pytest.approx(
        case["expected_output"]["total_cost_bdt"], abs=0.01
    )
