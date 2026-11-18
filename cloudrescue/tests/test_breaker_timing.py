from heapq import heapify, heappop, heappush

import pytest

from backend.policies import Breaker


@pytest.mark.parametrize(
    ("arrival_span", "latency_delay", "expected_probe", "expected_successes"),
    [(1.0, 0, 6.50, 16), (0.3, 0, 6.15, 16), (1.0, 0.65, 7.80, 30), (0.3, 0.65, 7.0, 34)],
)
def test_phase5_breaker_timing(arrival_span, latency_delay, expected_probe, expected_successes):
    breaker = Breaker(threshold=3, cooldown=4)
    traffic = (4, 5, 5, 5, 6, 6, 4, 5, 6, 4, 5, 5)
    events = [
        (tick + arrival_span * index / count, True, tick)
        for tick, count in enumerate(traffic)
        for index in range(count)
    ]
    heapify(events)
    first_probe = None
    successes = 0
    while events:
        at, arrival, tick = heappop(events)
        if arrival:
            was_open = breaker.state == "open"
            if breaker.admit(at):
                if was_open and first_probe is None:
                    first_probe = at
                delay = latency_delay if tick in (2, 3) else 0
                heappush(events, (at + delay, False, tick))
        else:
            healthy = tick < 2 or tick >= 7
            breaker.record(at, healthy)
            successes += healthy

    assert first_probe == pytest.approx(expected_probe)
    assert successes == expected_successes
