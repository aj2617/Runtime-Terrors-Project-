"""Deterministic validation for untrusted LLM directive output."""

from app.schemas import BatteryInput, DirectiveInterpretation


class DirectiveValidationError(ValueError):
    pass


def validate_directives(directives: list[DirectiveInterpretation], note_count: int,
                        battery: BatteryInput) -> list[DirectiveInterpretation]:
    if len(directives) != note_count:
        raise DirectiveValidationError("LLM must return exactly one directive per operator note")
    if sorted(item.note_index for item in directives) != list(range(note_count)):
        raise DirectiveValidationError("directive note_index values must be unique and sequential")
    for item in directives:
        adjustment = item.structured_adjustment
        if item.directive_type == "no_op":
            if item.applies or adjustment is not None:
                raise DirectiveValidationError("no_op must have applies=false and no adjustment")
            continue
        if not item.applies or adjustment is None:
            raise DirectiveValidationError("active directives require applies=true and an adjustment")
        if adjustment.hours != sorted(set(adjustment.hours)) or any(h < 0 or h > 23 for h in adjustment.hours):
            raise DirectiveValidationError("directive hours must be unique, ascending integers from 0 to 23")
        supplied = [adjustment.factor is not None, adjustment.minimum_energy_kwh is not None,
                    adjustment.max_grid_kwh is not None]
        expected = {"solar_reduction": 0, "minimum_battery_reserve": 1, "max_grid_window": 2}.get(item.directive_type)
        if expected is None:
            if any(supplied):
                raise DirectiveValidationError(f"{item.directive_type} cannot include a numeric value")
        elif sum(supplied) != 1 or not supplied[expected]:
            raise DirectiveValidationError(f"{item.directive_type} has an invalid adjustment shape")
        if adjustment.factor is not None and not 0 <= adjustment.factor <= 1:
            raise DirectiveValidationError("solar reduction factor must be between 0 and 1")
        if adjustment.minimum_energy_kwh is not None and not 0 <= adjustment.minimum_energy_kwh <= battery.capacity_kwh:
            raise DirectiveValidationError("battery reserve must be within battery capacity")
        if adjustment.max_grid_kwh is not None and adjustment.max_grid_kwh < 0:
            raise DirectiveValidationError("grid cap cannot be negative")
    return sorted(directives, key=lambda item: item.note_index)
