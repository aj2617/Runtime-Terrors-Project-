import pytest

from app.directives.validator import DirectiveValidationError, validate_directives
from app.schemas import BatteryInput, DirectiveInterpretation


@pytest.fixture
def battery():
    return BatteryInput(
        capacity_kwh=200,
        initial_energy_kwh=100,
        minimum_energy_kwh=40,
        max_charge_kwh_per_hour=50,
        max_discharge_kwh_per_hour=50,
    )


def test_rejects_unsorted_or_duplicate_directive_hours(battery):
    directive = DirectiveInterpretation.model_validate({
        "note_index": 0,
        "applies": True,
        "directive_type": "no_charge_window",
        "structured_adjustment": {"hours": [14, 13, 13]},
        "explanation": "Invalid ordering.",
    })
    with pytest.raises(DirectiveValidationError, match="unique, ascending"):
        validate_directives([directive], 1, battery)


def test_rejects_out_of_range_reserve(battery):
    directive = DirectiveInterpretation.model_validate({
        "note_index": 0,
        "applies": True,
        "directive_type": "minimum_battery_reserve",
        "structured_adjustment": {"hours": [18], "minimum_energy_kwh": 201},
        "explanation": "Invalid reserve.",
    })
    with pytest.raises(DirectiveValidationError, match="within battery capacity"):
        validate_directives([directive], 1, battery)
