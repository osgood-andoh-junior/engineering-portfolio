from app.core.exceptions import DomainError

TRANSITIONS: dict[str, set[str]] = {
    "pending_payment": {"cancelled"},
    "paid": {"processing"},
    "processing": {"shipped"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
    "refunded": set(),
}


def validate_transition(current: str, requested: str) -> None:
    if requested not in TRANSITIONS.get(current, set()):
        raise DomainError("invalid_transition", "This order status change is not permitted.", 409)


def available(quantity: int, reserved: int, requested: int) -> bool:
    return 1 <= requested <= 20 and quantity - reserved >= requested


def totals(lines: list[tuple[int, int]], shipping: int) -> tuple[int, int]:
    if (
        shipping < 0
        or not lines
        or any(
            not isinstance(price, int)
            or isinstance(price, bool)
            or price < 0
            or not isinstance(qty, int)
            or isinstance(qty, bool)
            or not 1 <= qty <= 20
            for price, qty in lines
        )
    ):
        raise DomainError("invalid_totals", "Invalid order line values.")
    subtotal = sum(price * quantity for price, quantity in lines)
    return subtotal, subtotal + shipping
