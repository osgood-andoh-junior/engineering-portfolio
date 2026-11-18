from backend.audit_chain import GENESIS, digest, verify
from backend.benchmark import benchmark, statistics, tune, workloads


def test_audit_checkpoint_detects_tampering_and_truncation():
    payload = {"actor": "alice", "action": "approved"}
    first = digest(1, GENESIS, payload)
    record = {"id": 1, "previous": GENESIS, "digest": first, "payload": payload}
    assert verify([record], (1, first))["valid"]
    assert not verify([], (1, first))["valid"]
    assert not verify([{**record, "payload": {"actor": "eve"}}])["valid"]
    replacement = {"actor": "eve"}
    rewritten = {**record, "payload": replacement, "digest": digest(1, GENESIS, replacement)}
    assert verify([rewritten])["valid"]
    assert not verify([rewritten], (1, first))["valid"]


def test_partitions_are_disjoint_and_tuning_refuses_holdout():
    import pytest

    first = list(workloads(42))
    assert first == list(workloads(42))
    assert len(first) == len({row[2] for row in first}) == 240
    assert sum(row[0] == "held_out" for row in first) == 60
    with pytest.raises(ValueError, match="Held-out"):
        tune(first)


def test_benchmark_reports_paired_improvements_and_regressions():
    result = benchmark()
    assert len(result["raw"]) == 240 * 7
    tuned = result["held_out"]["tuned"]
    assert tuned["paired_success_delta"]["p05"] < 0 < tuned["paired_success_delta"]["p95"]
    assert 0 < tuned["harmful"]["mean"] < 1
    assert statistics([2, 2, 2])["ci95"] == [2, 2]
    assert statistics([0, 1, 2])["median"] == 1
