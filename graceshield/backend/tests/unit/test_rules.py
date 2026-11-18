import pytest

from app.core.exceptions import DomainError
from app.services.rules import available, totals, validate_transition


def test_integer_money():
    assert totals([(4500, 3), (1800, 2)], 1000) == (17100, 18100)


@pytest.mark.parametrize(
    "lines,shipping",
    [([], 0), ([(1.5, 2)], 0), ([(2, 0)], 0), ([(2, 21)], 0), ([(True, 2)], 0), ([(1, 1)], -1)],
)
def test_reject_unsafe_totals(lines, shipping):
    with pytest.raises(DomainError):
        totals(lines, shipping)


@pytest.mark.parametrize(
    "quantity,reserved,requested,result",
    [(10, 8, 2, True), (10, 8, 3, False), (0, 0, 1, False), (100, 0, 21, False), (1, 0, 0, False)],
)
def test_available_stock(quantity, reserved, requested, result):
    assert available(quantity, reserved, requested) == result


@pytest.mark.parametrize(
    "current,next_status",
    [
        ("pending_payment", "paid"),
        ("pending_payment", "shipped"),
        ("cancelled", "processing"),
        ("paid", "refunded"),
        ("delivered", "shipped"),
    ],
)
def test_forbid_payment_spoofing_and_invalid_transitions(current, next_status):
    with pytest.raises(DomainError):
        validate_transition(current, next_status)


@pytest.mark.parametrize(
    "current,next_status",
    [
        ("pending_payment", "cancelled"),
        ("paid", "processing"),
        ("processing", "shipped"),
        ("shipped", "delivered"),
    ],
)
def test_valid_transitions(current, next_status):
    validate_transition(current, next_status)
