import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.llm.interpreter import LLMProviderError
from app.main import app
from app.schemas import DirectiveInterpretation


CASES = json.loads(
    (Path(__file__).parents[1] / "sample_cases" / "public_cases.json").read_text(encoding="utf-8")
)["cases"]


@pytest.fixture
def client():
    return TestClient(app)


def test_health_is_ready(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_public_cases_through_api(client, monkeypatch, case):
    expected = [DirectiveInterpretation.model_validate(item) for item in case["expected_output"]["directive_interpretation"]]
    monkeypatch.setattr("app.main.interpret_notes", lambda notes, battery: expected)

    response = client.post("/optimize-energy", json=case["input"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scenario_id"] == case["input"]["scenario_id"]
    assert body["directive_interpretation"] == [item.model_dump() for item in expected]
    assert body["total_cost_bdt"] == pytest.approx(case["expected_output"]["total_cost_bdt"], abs=0.01)
    assert len(body["hourly_plan"]) == 24


def test_provider_failure_is_safe(client, monkeypatch):
    monkeypatch.setattr("app.main.interpret_notes", lambda notes, battery: (_ for _ in ()).throw(LLMProviderError("private token")))
    response = client.post("/optimize-energy", json=CASES[0]["input"])
    assert response.status_code == 500
    assert response.json()["detail"] == "Directive interpretation is temporarily unavailable"
    assert "token" not in response.text


def test_non_finite_numeric_input_is_rejected(client):
    invalid = json.loads(json.dumps(CASES[0]["input"]))
    invalid["hours"][0]["demand_kwh"] = "NaN"
    assert client.post("/optimize-energy", json=invalid).status_code == 422
