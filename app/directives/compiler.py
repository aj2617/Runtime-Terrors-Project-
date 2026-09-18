"""Convert validated business directives into deterministic LP inputs."""

from dataclasses import dataclass, field

from app.schemas import BatteryInput, DirectiveInterpretation, HourInput


@dataclass
class OptimizerConstraints:
    effective_solar: list[float]
    minimum_energy: list[float]
    grid_caps: list[float | None] = field(default_factory=lambda: [None] * 24)
    no_charge_hours: set[int] = field(default_factory=set)
    no_discharge_hours: set[int] = field(default_factory=set)


def apply_directives(hours: list[HourInput], battery: BatteryInput,
                     directives: list[DirectiveInterpretation]) -> OptimizerConstraints:
    ordered = sorted(hours, key=lambda item: item.hour)
    result = OptimizerConstraints(
        effective_solar=[item.solar_kwh for item in ordered],
        minimum_energy=[battery.minimum_energy_kwh] * 24,
    )
    for directive in directives:
        if not directive.applies:
            continue
        adjustment = directive.structured_adjustment
        assert adjustment is not None
        for hour in adjustment.hours:
            if directive.directive_type == "solar_reduction":
                result.effective_solar[hour] *= adjustment.factor  # type: ignore[operator]
            elif directive.directive_type == "minimum_battery_reserve":
                result.minimum_energy[hour] = max(result.minimum_energy[hour], adjustment.minimum_energy_kwh or 0)
            elif directive.directive_type == "no_charge_window":
                result.no_charge_hours.add(hour)
            elif directive.directive_type == "no_discharge_window":
                result.no_discharge_hours.add(hour)
            elif directive.directive_type == "max_grid_window":
                cap = adjustment.max_grid_kwh
                old = result.grid_caps[hour]
                result.grid_caps[hour] = cap if old is None else min(old, cap)  # type: ignore[arg-type]
    return result
