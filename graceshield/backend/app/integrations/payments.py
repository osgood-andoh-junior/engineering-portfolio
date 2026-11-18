from dataclasses import dataclass
from typing import Literal, Protocol

from app.core.exceptions import DomainError


@dataclass(frozen=True)
class VerifiedPayment:
    provider: str
    event_id: str
    reference: str
    amount_minor: int
    currency: str
    status: Literal["paid", "failed", "pending", "refunded"]


class PaymentProvider(Protocol):
    def initialize(self, order_reference: str, amount_minor: int, idempotency_key: str) -> dict: ...
    def verify(self, reference: str) -> VerifiedPayment: ...
    def authenticate_webhook(
        self, body: bytes, signature: str, timestamp: str
    ) -> VerifiedPayment: ...
    def refund(self, reference: str, amount_minor: int, idempotency_key: str) -> dict: ...
    def reconcile(self) -> list[VerifiedPayment]: ...


def configured_provider() -> PaymentProvider:
    raise DomainError(
        "payments_unavailable",
        "No approved payment provider is configured. No payment has been processed.",
        503,
    )
