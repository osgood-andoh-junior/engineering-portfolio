from dataclasses import dataclass
from random import Random
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    failure_threshold: Annotated[int, Field(ge=1, le=10)] = 3
    breaker_cooldown: Annotated[int, Field(ge=1, le=30)] = 4
    retry_limit: Annotated[int, Field(ge=0, le=5)] = 2
    retry_budget: Annotated[int, Field(ge=0, le=100)] = 20
    retry_base_ms: Annotated[int, Field(ge=10, le=500)] = 80
    deadline_ms: Annotated[int, Field(ge=50, le=990)] = 650
    rate: Annotated[int, Field(ge=1, le=40)] = 9
    burst: Annotated[int, Field(ge=1, le=40)] = 10
    failover_cooldown: Annotated[int, Field(ge=1, le=30)] = 4
    failover_health_ticks: Annotated[int, Field(ge=1, le=8)] = 2


@dataclass
class Breaker:
    threshold: int
    cooldown: int
    failures: int = 0
    open_until: float = 0
    state: str = "closed"

    def admit(self, now: float) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open" and now >= self.open_until:
            self.state = "half_open"
            return True
        return False

    def record(self, now: float, ok: bool) -> None:
        if ok:
            self.state, self.failures = "closed", 0
            return
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.threshold:
            self.state, self.open_until = "open", now + self.cooldown


@dataclass
class Retries:
    budget: int
    limit: int
    base_ms: int
    rng: Random

    def delay(self, used: int, remaining_ms: float, transient: bool, safe: bool) -> float | None:
        if not transient or not safe or used >= self.limit or not self.budget:
            return None
        delay = self.base_ms * (2**used) * self.rng.uniform(0.5, 1.5)
        if delay >= remaining_ms:
            return None
        self.budget -= 1
        return delay


class Bucket:
    def __init__(self, rate: int, burst: int):
        self.rate, self.burst = rate, burst
        self.tokens = float(burst)
        self.updated = 0.0

    def admit(self, now: float) -> bool:
        self.tokens = min(self.burst, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True


@dataclass
class Failover:
    cooldown: int
    health_threshold: int = 2
    standby: bool = False
    changed_at: int = 0
    healthy_ticks: int = 0

    def route(self, tick: int, primary_ok: bool, standby_ok: bool) -> bool:
        self.healthy_ticks = self.healthy_ticks + 1 if primary_ok else 0
        if (
            not self.standby
            and not primary_ok
            and standby_ok
            and tick - self.changed_at >= self.cooldown
        ):
            self.standby, self.changed_at = True, tick
        elif (
            self.standby
            and primary_ok
            and (
                not standby_ok
                or (
                    self.healthy_ticks >= self.health_threshold
                    and tick - self.changed_at >= self.cooldown
                )
            )
        ):
            self.standby, self.changed_at = False, tick
        return self.standby
