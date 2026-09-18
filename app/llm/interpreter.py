"""One batched, structured LLM call followed by deterministic validation."""
import json
from openai import OpenAI
from app.config import settings
from app.directives.validator import DirectiveValidationError, validate_directives
from app.schemas import BatteryInput, DirectiveInterpretation

SYSTEM_PROMPT = """Interpret 24-hour energy operator notes. Return JSON {\"directives\":[...]}, one result per note. Allowed types: solar_reduction, minimum_battery_reserve, no_charge_window, no_discharge_window, max_grid_window, no_op. Hours are ascending 0-23, start-inclusive/end-exclusive. solar factor is fraction remaining (80% reduction = 0.2). no_op has applies false and null adjustment; all others apply true. Never change inputs or invent types."""


class LLMProviderError(RuntimeError):
    """A safe, provider-agnostic error exposed without provider details or secrets."""

def interpret_notes(notes: list[str], battery: BatteryInput) -> list[DirectiveInterpretation]:
    if not settings.LLM_API_KEY or not settings.LLM_MODEL:
        raise DirectiveValidationError("LLM_API_KEY and LLM_MODEL must be configured")
    payload = {"operator_notes": notes, "battery_context": battery.model_dump()}
    client, error = OpenAI(api_key=settings.LLM_API_KEY), None
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
