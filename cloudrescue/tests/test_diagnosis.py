import pytest

from backend.diagnosis import Observation, diagnose
from backend.evaluation import evaluate
from backend.replay import SCENARIOS, scenario_result
from backend.topology import DEFAULT_EDGES, validate


def test_topology_rejects_cycles_duplicates_and_unknown_services():
    assert validate(reversed(DEFAULT_EDGES)) == DEFAULT_EDGES
    for edges in [
        [("identity", "identity")],
        [("identity", "storage"), ("storage", "messaging"), ("messaging", "identity")],
        [("storage", "identity"), ("storage", "identity")],
        [("identity", "outside")],
    ]:
        with pytest.raises(ValueError):
            validate(edges)


def test_missing_upstream_and_single_slow_probe_abstain():
    for sample in [
        Observation(0, "storage", False, 10, 503, "identity"),
        Observation(0, "messaging", True, 800, 200),
    ]:
        assert diagnose([sample], DEFAULT_EDGES, 500, 25)["status"] == "insufficient_evidence"


@pytest.mark.parametrize("name", SCENARIOS)
def test_seeded_replay_is_reproducible(name):
    result = scenario_result(name)
    assert result == scenario_result(name)
    assert set(result["predictions"]) == set(result["ground_truth"])
    assert [frame["time"] for frame in result["frames"]] == list(range(0, 35, 5))
    if name == "cascade":
        assert result["frames"][1]["candidates"][0]["symptoms"] == ["messaging", "storage"]
    if name == "spike":
        assert result["first_detection"] == {}


def test_evaluation_denominators():
    result = evaluate()
    assert result["counts"] == {"tp": 5, "tn": 10, "fp": 0, "fn": 0}
    assert result["accuracy"] == result["precision"] == result["recall"] == 1
    assert result["false_positive_rate"] == 0
    assert result["detection_samples"] == 6
    assert result["mean_detection_seconds"] == 10
    assert result["mean_diagnosis_seconds"] == 1
    assert result["calibration"] is None
