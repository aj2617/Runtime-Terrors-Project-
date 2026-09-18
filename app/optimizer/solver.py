"""Continuous linear-programming optimiser for the 24-hour schedule."""

import numpy as np
from scipy.optimize import linprog

from app.directives.compiler import OptimizerConstraints
from app.schemas import BatteryInput, HourInput


class OptimizationError(RuntimeError):
    pass


def optimize_energy(hours: list[HourInput], battery: BatteryInput,
                    constraints: OptimizerConstraints) -> dict:
    ordered = sorted(hours, key=lambda item: item.hour)
    n = 24
    # x = [grid(24), solar_used(24), battery_delta(24)]. Positive delta charges.
    c = np.r_[[item.tariff_bdt_per_kwh for item in ordered], np.zeros(2 * n)]
    a_eq: list[np.ndarray] = []
    b_eq: list[float] = []
    for h, entry in enumerate(ordered):
        row = np.zeros(3 * n)
        row[h], row[n + h], row[2 * n + h] = 1, 1, -1
        a_eq.append(row)
        b_eq.append(entry.demand_kwh)
    final = np.zeros(3 * n)
    final[2 * n:] = 1
    a_eq.append(final)
    b_eq.append(0)

    a_ub: list[np.ndarray] = []
    b_ub: list[float] = []
    for h in range(n):
        cumulative = np.zeros(3 * n)
        cumulative[2 * n:2 * n + h + 1] = 1
        a_ub.extend((cumulative, -cumulative))
        b_ub.extend((battery.capacity_kwh - battery.initial_energy_kwh,
                     battery.initial_energy_kwh - constraints.minimum_energy[h]))

    bounds: list[tuple[float | None, float | None]] = []
    bounds.extend((0, constraints.grid_caps[h]) for h in range(n))
    bounds.extend((0, constraints.effective_solar[h]) for h in range(n))
    for h in range(n):
        lower, upper = -battery.max_discharge_kwh_per_hour, battery.max_charge_kwh_per_hour
        if h in constraints.no_charge_hours:
            upper = 0
        if h in constraints.no_discharge_hours:
            lower = 0
        bounds.append((lower, upper))

    result = linprog(c, A_ub=np.array(a_ub), b_ub=np.array(b_ub),
                     A_eq=np.array(a_eq), b_eq=np.array(b_eq), bounds=bounds, method="highs")
    if not result.success:
        raise OptimizationError(f"No feasible energy schedule: {result.message}")

    grid, solar, delta = result.x[:n], result.x[n:2 * n], result.x[2 * n:]
    energy = battery.initial_energy_kwh
    plan = []
    for h in range(n):
        energy += delta[h]
        amount = abs(delta[h]) if abs(delta[h]) > 1e-8 else 0.0
        action = "charge" if delta[h] > 1e-8 else "discharge" if delta[h] < -1e-8 else "idle"
        plan.append({"hour": h, "grid_kwh": float(grid[h]), "solar_used_kwh": float(solar[h]),
                     "battery_action": action, "battery_kwh": float(amount),
                     "battery_energy_after_kwh": float(energy)})
    return {"hourly_plan": plan, "total_grid_kwh": float(grid.sum()),
            "total_cost_bdt": float(np.dot(grid, c[:n])), "peak_grid_kwh": float(grid.max())}
