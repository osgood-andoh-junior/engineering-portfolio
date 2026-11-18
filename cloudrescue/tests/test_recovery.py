from random import Random

from backend.policies import Breaker, Bucket, Failover, Parameters, Retries
from backend.recovery_control import recommendation
from backend.recovery_lab import benchmark, compare


def test_breaker_controls_half_open_and_reopens():
    breaker = Breaker(2, 4)
    assert breaker.admit(0)
    breaker.record(0, False)
    assert breaker.admit(1)
    breaker.record(1, False)
    assert not breaker.admit(4)
    assert breaker.admit(5)
    assert breaker.state == "half_open"
    assert not breaker.admit(5)
    breaker.record(5, False)
    assert not breaker.admit(8)
    assert breaker.admit(9)
    breaker.record(9, True)
    assert breaker.state == "closed"


def test_retry_requires_transient_safe_budget_and_deadline():
    retries = Retries(2, 2, 80, Random(42))
    assert retries.delay(0, 500, False, True) is None
    assert retries.delay(0, 500, True, False) is None
    assert retries.delay(0, 10, True, True) is None
    assert retries.delay(2, 500, True, True) is None
    assert 40 <= retries.delay(0, 500, True, True) <= 120
    assert 80 <= retries.delay(1, 500, True, True) <= 240
    assert retries.delay(0, 500, True, True) is None


def test_token_bucket_and_failover():
    bucket = Bucket(2, 2)
    assert bucket.admit(0)
    assert bucket.admit(0)
    assert not bucket.admit(0.4)
    assert bucket.admit(0.5)
    failover = Failover(3)
    assert not failover.route(3, False, False)
    assert failover.route(4, False, True)
    assert failover.route(5, True, True)
    assert failover.route(6, True, True)
    assert not failover.route(7, True, True)


def test_experiments_reproduce_and_include_harmful_cases():
    result = benchmark()
    assert result == benchmark()
    base, *others = result["scenarios"]["primary"]
    assert base["mttd_seconds"] == 2
    assert base["mttr_seconds"] == 16
    assert base["downtime_seconds"] == 14
    assert base["error_budget_consumption"] == (
        (base["requests"] - base["successful_requests"]) / (base["requests"] * 0.01)
    )
    assert any(row["harmful"] for row in result["scenarios"]["healthy_burst"])
    assert next(row for row in others if row["policy"] == "failover")["switches"] == 2
    combined = compare("upstream", Parameters(rate=1, burst=1), 42)[-1]
    assert combined["upstream_attempts"] < combined["requests"]
    assert combined["switches"] == 0
    assert combined["retry_attempts"] == 0


def test_insufficient_evidence_requires_investigation():
    assert recommendation({"candidates": []}, [])["strategy"] == "investigate"
