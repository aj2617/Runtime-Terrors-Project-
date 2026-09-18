"""Pydantic models shared by the API, LLM boundary, and optimiser."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class HourInput(StrictModel):
    hour: int = Field(ge=0, le=23)
    demand_kwh: float = Field(ge=0)
    solar_kwh: float = Field(ge=0)
    tariff_bdt_per_kwh: float = Field(ge=0)


class BatteryInput(StrictModel):
    capacity_kwh: float = Field(gt=0)
    initial_energy_kwh: float = Field(ge=0)
    minimum_energy_kwh: float = Field(ge=0)
    max_charge_kwh_per_hour: float = Field(ge=0)
    max_discharge_kwh_per_hour: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_energy_bounds(self):
        if self.initial_energy_kwh > self.capacity_kwh:
            raise ValueError("initial_energy_kwh cannot exceed capacity_kwh")
        if self.minimum_energy_kwh > self.capacity_kwh:
            raise ValueError("minimum_energy_kwh cannot exceed capacity_kwh")
        return self


class EnergyRequest(StrictModel):
    scenario_id: str = Field(min_length=1, max_length=200)
    operator_notes: list[str] = Field(min_length=1, max_length=3)
    hours: list[HourInput] = Field(min_length=24, max_length=24)
    battery: BatteryInput

    @model_validator(mode="after")
    def validate_all_hours(self):
        values = [item.hour for item in self.hours]
        if sorted(values) != list(range(24)):
            raise ValueError("hours must contain each hour from 0 through 23 exactly once")
        if any(not note.strip() for note in self.operator_notes):
            raise ValueError("operator_notes cannot contain blank notes")
        return self


class StructuredAdjustment(StrictModel):
    hours: list[int] = Field(min_length=1, max_length=24)
    factor: float | None = None
    minimum_energy_kwh: float | None = None
    max_grid_kwh: float | None = None


DirectiveType = Literal[
    "solar_reduction", "minimum_battery_reserve", "no_charge_window",
    "no_discharge_window", "max_grid_window", "no_op",
]


class DirectiveInterpretation(StrictModel):
    note_index: int = Field(ge=0)
    applies: bool
    directive_type: DirectiveType
    structured_adjustment: StructuredAdjustment | None = None
    explanation: str = Field(min_length=1, max_length=500)


BatteryAction = Literal["charge", "discharge", "idle"]


class HourlyPlanEntry(StrictModel):
    hour: int = Field(ge=0, le=23)
    grid_kwh: float = Field(ge=0)
    solar_used_kwh: float = Field(ge=0)
    battery_action: BatteryAction
    battery_kwh: float = Field(ge=0)
    battery_energy_after_kwh: float = Field(ge=0)


class EnergyResponse(StrictModel):
    scenario_id: str
    directive_interpretation: list[DirectiveInterpretation]
    hourly_plan: list[HourlyPlanEntry]
    total_grid_kwh: float
    total_cost_bdt: float
    peak_grid_kwh: float
    plan_summary: str
