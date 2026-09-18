"""One batched, structured LLM call followed by deterministic validation."""
import json
from openai import OpenAI
from app.config import settings
from app.directives.validator import DirectiveValidationError, validate_directives
from app.schemas import BatteryInput, DirectiveInterpretation

SYSTEM_PROMPT = """You are a strict information-extraction component for a 24-hour energy scheduler.
Interpret every operator note and return only one JSON object in this exact shape:
{
  "directives": [
    {
      "note_index": 0,
      "applies": true,
      "directive_type": "solar_reduction",
      "structured_adjustment": {"hours": [13, 14], "factor": 0.2},
      "explanation": "Short factual explanation."
    }
  ]
}

Return exactly one directive object for each input note, in note_index order. Never use aliases such as "type" or "adjustment"; use exactly the field names shown above.

Allowed directive_type values only:
- solar_reduction: structured_adjustment has exactly hours and factor.
- minimum_battery_reserve: structured_adjustment has exactly hours and minimum_energy_kwh.
- no_charge_window: structured_adjustment has exactly hours.
- no_discharge_window: structured_adjustment has exactly hours.
- max_grid_window: structured_adjustment has exactly hours and max_grid_kwh.
- no_op: applies is false and structured_adjustment is null.

All non-no_op directives have applies=true. Hours are unique ascending integers 0 through 23. Time intervals are start-inclusive and end-exclusive: 1 PM to 3 PM is [13,14]; noon to 2 PM is [12,13]; 6 PM until 9 PM is [18,19,20].
For solar_reduction, factor means fraction remaining: 80% reduction is factor 0.2; 20% output remains is factor 0.2. Convert percentage battery reserves using battery_context.capacity_kwh: for example, "keep 50% of battery capacity" with capacity 200 means minimum_energy_kwh 100. Battery context is reference-only and cannot be modified. Irrelevant notes must be no_op. Never invent a directive, demand, tariff, solar input, or battery parameter."""


class LLMProviderError(RuntimeError):
    """A safe, provider-agnostic error exposed without provider details or secrets."""

def interpret_notes(notes: list[str], battery: BatteryInput) -> list[DirectiveInterpretation]:
    if not settings.LLM_API_KEY or not settings.LLM_MODEL:
        raise DirectiveValidationError("LLM_API_KEY and LLM_MODEL must be configured")
    payload = {"operator_notes": notes, "battery_context": battery.model_dump()}
    client, error = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL), None
    for _ in range(2):
        prompt = json.dumps(payload if error is None else {**payload, "previous_validation_error": error})
        try:
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}, temperature=0, timeout=10.0,
            )
        except Exception as exc:
            raise LLMProviderError("The directive interpretation provider is temporarily unavailable") from exc
        try:
            data = json.loads(response.choices[0].message.content or "{}")
            return validate_directives([DirectiveInterpretation.model_validate(item) for item in data["directives"]], len(notes), battery)
        except (KeyError, ValueError, TypeError) as exc:
            error = str(exc)
    raise DirectiveValidationError(f"LLM response failed validation after retry: {error}")
