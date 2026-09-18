from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class HourInput(BaseModel):
    hour: int
    demand_kwh: float
    solar_kwh: float
    tariff_bdt_per_kwh: float

    @field_validator("hour")
    @classmethod
    def validate_hour(cls, value):
        if value < 0 or value > 23:
            raise ValueError("hour must be between 0 and 23")
        return value


class BatteryInput(BaseModel):
    capacity_kwh: float
    initial_energy_kwh: float
    minimum_energy_kwh: float
    max_charge_kwh_per_hour: float
    max_discharge_kwh_per_hour: float


class EnergyRequest(BaseModel):
    scenario_id: str
    operator_notes: List[str]
    hours: List[HourInput]
    battery: BatteryInput


class StructuredAdjustment(BaseModel):
    hours: List[int]
    factor: Optional[float] = None
    minimum_energy_kwh: Optional[float] = None
    max_grid_kwh: Optional[float] = None


DirectiveType = Literal[
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
]


class DirectiveInterpretation(BaseModel):
    note_index: int
    applies: bool
    directive_type: DirectiveType
    structured_adjustment: Optional[StructuredAdjustment] = None
    explanation: str


BatteryAction = Literal[
    "charge",
    "discharge",
    "idle",
]


class HourlyPlanEntry(BaseModel):
    hour: int
    grid_kwh: float
    solar_used_kwh: float
    battery_action: BatteryAction
    battery_kwh: float
    battery_energy_after_kwh: float


class EnergyResponse(BaseModel):
    scenario_id: str
    directive_interpretation: List[DirectiveInterpretation]
    hourly_plan: List[HourlyPlanEntry]

    total_grid_kwh: float
    total_cost_bdt: float
    peak_grid_kwh: float

    plan_summary: str