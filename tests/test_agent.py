"""
agent.py tests — offline. No network, no credits, no API key, no LLM.

The architectural claim this file defends: **the LLM never changes an answer.** With and
without narration the routing, the numbers, the band and the action are identical — only
the wording differs. A safety tool whose recommendation depends on whether a language
model was reachable is not a safety tool, and that has to be enforced rather than
asserted in a README.

Also pinned: a refusal costs nothing (no call is made at all), and an empty API result is
never narrated as an all-clear.
"""

import json

import pytest

from heatguard import agent
from heatguard.router import AnalyticType, QuestionType, RefusalReason

PHX_CHASE = "PHX-CHASE"
DATE = "2025-07-15"

# Shaped like a real tcm response: 10 tiles, Celsius, a real diurnal range.
FAKE_TCM = {
    "map_data": {"features": [
        {"properties": {"tile_id": i, "average_temperature": 37.0,
                        "min_temperature": 32.8, "max_temperature": 40.2}}
        for i in range(10)
    ]},
    "stats_data": {"temperature_stats": {"minimum": 37.0, "maximum": 37.0}},
}

FAKE_EXCEEDANCE = {
    "map_data": {"features": [
        {"properties": {"tile_id": i, "value": 6.0}} for i in range(10)
    ]},
    "stats_data": {"analytic_type": "exceedance", "units": "hour", "mean": 6.0},
}

FAKE_ENV = {"locations": [{"parameters": {
    "relative_humidity_percent": [22.0] * 24}}]}


@pytest.fixture(autouse=True)
def isolate_decision_log(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "DECISIONS_LOG", tmp_path / "decisions.jsonl")


@pytest.fixture
def stub_api(monkeypatch):
    """Serve canned responses; record every call so we can assert none was made."""
    calls: list[dict] = []

    def fake_heatmap(aoi, date, filter_type, analytic_type="tcm", **kw):
        calls.append({"analytic_type": analytic_type, "filter_type": filter_type,
                      "date": date, **kw})
        if analytic_type == "tcm":
            return FAKE_TCM
        return FAKE_EXCEEDANCE

    monkeypatch.setattr(agent.tools, "heatmap", fake_heatmap)
    monkeypatch.setattr(agent.tools, "env_params", lambda **kw: FAKE_ENV)
    return calls


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


# ------------------------------------------------------------------ site registry

def test_every_site_loads_with_an_aoi():
    sites = agent.load_sites()
    assert len(sites) == 12
    for site_id, site in sites.items():
        assert site["aoi"]["features"][0]["geometry"]["type"] == "Polygon", site_id


def test_an_unknown_site_raises():
    with pytest.raises(KeyError, match="unknown site"):
        agent.answer("Is it safe?", site_id="NOPE", date=DATE)


# ---------------------------------------------------- routing happens before calls

def test_a_refusal_makes_no_api_call_at_all(stub_api):
    """The economic argument: three silent failures are billed, so refusing has to
    happen before the wire, not after."""
    out = agent.answer("Is this site chronically dangerous?",
                       site_id=PHX_CHASE, date=DATE)     # no end_date
    assert out["choice"].refused
    assert out["choice"].refusal is RefusalReason.WRONG_LAYER_WOULD_MISLEAD
    assert stub_api == [], "a refused question must not reach the API"
    assert "No API call was made" in out["narration"]


def test_a_duration_question_runs_exceedance_not_just_tcm(stub_api):
    out = agent.answer("How long were they above the danger band?",
                       site_id=PHX_CHASE, date=DATE)
    assert out["choice"].analytic_type is AnalyticType.EXCEEDANCE
    assert [c["analytic_type"] for c in stub_api] == ["tcm", "exceedance"]
    assert out["result"]["hours"] == 6.0


def test_a_snapshot_question_does_not_pay_for_a_duration_call(stub_api):
    out = agent.answer("Is it safe right now?", site_id=PHX_CHASE, date=DATE)
    assert out["choice"].question_type is QuestionType.SNAPSHOT
    assert [c["analytic_type"] for c in stub_api] == ["tcm"]


# ---------------------------------------------- the unit conversion, at the boundary

def test_the_heat_index_threshold_is_converted_to_an_air_temperature(stub_api):
    """OSHA bands are HEAT INDEX; exceedance thresholds AIR TEMPERATURE. In dry Phoenix
    air the equivalent air temperature is HIGHER than the OSHA number."""
    out = agent.answer("How long were they above the band?",
                       site_id=PHX_CHASE, date=DATE)
    r = out["result"]
    assert r["threshold_f_heat_index"] == 91.0
    assert r["threshold_f_air"] > 91.0, "at 22% humidity the equivalent must be higher"
    assert r["threshold_c_air"] < 60.0, "must be Celsius by the time it reaches the wire"

    sent = next(c for c in stub_api if c["analytic_type"] == "exceedance")
    assert sent["threshold_c"] == r["threshold_c_air"]
    assert sent["direction"] == "above"


def test_humidity_falls_back_without_pretending_to_have_measured_it(monkeypatch,
                                                                    stub_api):
    def boom(**kw):
        raise agent.tools.ToolsError("offline")

    monkeypatch.setattr(agent.tools, "env_params", boom)
    out = agent.answer("How long above the band?", site_id=PHX_CHASE, date=DATE)
    assert out["result"]["humidity_pct"] == 20.0


# ------------------------------------------ THE ARCHITECTURAL CLAIM: the LLM is inert

def test_the_llm_cannot_change_any_number_band_or_action(monkeypatch, stub_api):
    """Run the same question with narration off and with a stubbed LLM. Everything that
    could drive a decision must be identical; only the prose may differ."""
    without = agent.answer("How long were they above the band?",
                           site_id=PHX_CHASE, date=DATE, narrate=False)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(agent, "_llm_narration",
                        lambda *a, **k: "Crews are fine, work straight through.")
    with_llm = agent.answer("How long were they above the band?",
                            site_id=PHX_CHASE, date=DATE)

    decisive = ("question_type", "analytic_type", "filter_type", "endpoint",
                "granularity", "threshold_f_heat_index", "threshold_c_air",
                "peak_f", "hours_above", "action", "band", "refusal")
    for field in decisive:
        assert without["record"][field] == with_llm["record"][field], field

    assert without["narration"] != with_llm["narration"]


def test_an_llm_outage_falls_back_to_the_template_silently(monkeypatch, stub_api):
    """A model outage must never take an answer down, and never change one.

    This patches the SDK call INSIDE _llm_narration rather than the function itself, so
    the internal exception handling is what is actually under test.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    class Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("model unreachable")

    fake_sdk = type("anthropic", (), {"Anthropic": Boom})
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake_sdk)

    out = agent.answer("How long were they above the band?",
                       site_id=PHX_CHASE, date=DATE)

    assert out["error"] is None, "an LLM outage is not an answer failure"
    assert out["narration"], "the answer must still carry prose"
    assert "Layer chosen" in out["narration"], "fell through to the template"
    assert out["record"]["hours_above"] == 6.0, "the numbers are unaffected"
    assert out["record"]["action"] is not None
    assert out["record"]["narration_source"] == "template", (
        "the audit trail must record what actually wrote the prose, not what was "
        "configured — claiming a model narrated while it was down is worse than no field"
    )


def test_no_llm_key_means_template_narration(stub_api):
    out = agent.answer("How long were they above the band?",
                       site_id=PHX_CHASE, date=DATE)
    assert out["record"]["narration_source"] == "template"
    assert out["narration"]
    assert "Layer chosen" in out["narration"]


def test_the_llm_is_never_asked_which_layer_to_use():
    """Structural: the narration prompt forbids it in as many words."""
    import inspect
    source = inspect.getsource(agent._llm_narration)
    assert "Never suggest a different analysis layer" in source
    assert "made deterministically upstream" in source


# --------------------------------------------------- an empty result is not safety

def test_an_empty_result_is_never_narrated_as_an_all_clear(monkeypatch):
    """A non-US AOI and a date outside coverage both return Completed with zero tiles,
    and both are billed. Reporting that as 'safe' is the worst available bug."""
    monkeypatch.setattr(agent.tools, "heatmap",
                        lambda *a, **k: {"map_data": {"features": []}})
    out = agent.answer("Is it safe right now?", site_id=PHX_CHASE, date=DATE)
    assert out["result"]["empty"] is True
    assert out["record"]["peak_f"] is None
    assert out["record"]["action"] is None
    assert "coverage gap" in out["narration"]
    assert "not reporting it as an all-clear" in out["narration"]


# ------------------------------------------------------------------- audit trail

def test_every_decision_is_logged(stub_api):
    agent.answer("How long were they above the band?", site_id=PHX_CHASE, date=DATE)
    agent.answer("Is this site chronically dangerous?", site_id=PHX_CHASE, date=DATE)

    lines = agent.DECISIONS_LOG.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    assert records[1]["refusal"] == "wrong_layer_would_mislead"


def test_the_log_records_the_layer_and_the_reason_for_it(stub_api):
    agent.answer("How long were they above the band?", site_id=PHX_CHASE, date=DATE)
    record = json.loads(agent.DECISIONS_LOG.read_text(encoding="utf-8").strip())
    for field in ("analytic_type", "filter_type", "rationale", "threshold_f_heat_index",
                  "site_id", "date", "question", "at"):
        assert record[field] is not None, field
    assert record["analytic_type"] == "exceedance"


def test_an_escalation_is_recorded_in_the_audit_trail(stub_api):
    """'worst' overrides the classifier; the log must show that it did."""
    agent.answer("Tell me about the worst at this site", site_id=PHX_CHASE, date=DATE)
    record = json.loads(agent.DECISIONS_LOG.read_text(encoding="utf-8").strip())
    assert record["escalated_from"] == "snapshot"
    assert record["question_type"] == "duration"


def test_a_tools_error_is_reported_not_swallowed(monkeypatch):
    def boom(*a, **k):
        raise agent.tools.ToolsError("network unreachable")

    monkeypatch.setattr(agent.tools, "heatmap", boom)
    # A question that ROUTES. "Is it safe?" used to reach the API by falling through to
    # the snapshot dustbin; it now refuses as unrecognised, so it would never call
    # heatmap at all and this test would pass for the wrong reason.
    out = agent.answer("How hot is it right now?", site_id=PHX_CHASE, date=DATE)
    assert out["error"] and "network unreachable" in out["error"]
    assert out["record"]["peak_f"] is None
