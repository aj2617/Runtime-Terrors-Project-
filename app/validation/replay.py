"""Independent validation of an optimiser response before it reaches the caller."""

from app.directives.compiler import OptimizerConstraints
from app.schemas import BatteryInput, HourInput


class ReplayValidationError(ValueError):
    pass


def validate_plan(plan: list[dict], hours: list[HourInput], battery: BatteryInput,
                  constraints: OptimizerConstraints, totals: dict, tolerance: float = 0.01) -> None:
    if len(plan) != 24 or [item["hour"] for item in plan] != list(range(24)):
        raise ReplayValidationError("hourly plan must contain hours 0 through 23 once each")
    ordered = sorted(hours, key=lambda item: item.hour)
    energy = battery.initial_energy_kwh
    total_grid = total_cost = peak = 0.0
    for h, (entry, source) in enumerate(zip(plan, ordered)):
        grid, solar, amount = entry["grid_kwh"], entry["solar_used_kwh"], entry["battery_kwh"]
        if grid < -tolerance or solar < -tolerance or solar > constraints.effective_solar[h] + tolerance:
            raise ReplayValidationError(f"invalid grid or solar value at hour {h}")
        if constraints.grid_caps[h] is not None and grid > constraints.grid_caps[h] + tolerance:
            raise ReplayValidationError(f"grid cap exceeded at hour {h}")
        delta = amount if entry["battery_action"] == "charge" else -amount if entry["battery_action"] == "discharge" else 0.0
        if entry["battery_action"] == "idle" and amount > tolerance:
            raise ReplayValidationError(f"idle battery has nonzero amount at hour {h}")
        if (h in constraints.no_charge_hours and delta > tolerance) or (h in constraints.no_discharge_hours and delta < -tolerance):
            raise ReplayValidationError(f"battery window violated at hour {h}")
        if delta > battery.max_charge_kwh_per_hour + tolerance or -delta > battery.max_discharge_kwh_per_hour + tolerance:
            raise ReplayValidationError(f"battery rate exceeded at hour {h}")
        if abs(grid + solar - delta - source.demand_kwh) > tolerance:
            raise ReplayValidationError(f"energy balance violated at hour {h}")
        energy += delta
        if not constraints.minimum_energy[h] - tolerance <= energy <= battery.capacity_kwh + tolerance:
            raise ReplayValidationError(f"battery bounds violated at hour {h}")
        if abs(entry["battery_energy_after_kwh"] - energy) > tolerance:
            raise ReplayValidationError(f"reported battery state incorrect at hour {h}")
        total_grid += grid
        total_cost += grid * source.tariff_bdt_per_kwh
        peak = max(peak, grid)
    if abs(energy - battery.initial_energy_kwh) > tolerance:
        raise ReplayValidationError("final battery energy must equal initial energy")
    for key, actual in (("total_grid_kwh", total_grid), ("total_cost_bdt", total_cost), ("peak_grid_kwh", peak)):
        if abs(totals[key] - actual) > tolerance:
            raise ReplayValidationError(f"reported {key} does not match hourly plan")
