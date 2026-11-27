import pytest
from fastapi.testclient import TestClient

from app.approval import (DEFAULT_APPROVAL_RANGES, ApprovalRange, approver_for,
                          validate_ranges)
from app.main import create_app

R = DEFAULT_APPROVAL_RANGES


@pytest.mark.parametrize("cents, expected", [
    (1, "Encargado de área"),                 # 0,01
    (99_999_999, "Encargado de área"),        # 999 999,99
    (100_000_000, "Gerencia"),                # 1 000 000,00
    (999_999_999, "Gerencia"),                # 9 999 999,99
    (1_000_000_000, "Junta Directiva"),       # 10 000 000,00
    (999_999_999_999_999, "Junta Directiva"),
])
def test_default_boundaries(cents, expected):
    assert approver_for(R, cents) == expected


def test_default_config_is_valid_and_contiguous():
    assert validate_ranges(R) == R
    for prev, nxt in zip(R, R[1:]):
        assert prev.max_cents == nxt.min_cents  # half-open: no gap, no overlap


def test_custom_config_changes_approver():
    custom = validate_ranges([
        ApprovalRange(1, 500, "A"), ApprovalRange(500, None, "B")])
    assert approver_for(custom, 499) == "A"
    assert approver_for(custom, 500) == "B"


@pytest.mark.parametrize("ranges, fragment", [
    ([], "vacía"),
    ([ApprovalRange(1, 100, "A"), ApprovalRange(50, None, "B")], "traslapan"),
    ([ApprovalRange(1, 100, "A"), ApprovalRange(101, None, "B")], "hueco"),
    ([ApprovalRange(2, None, "A")], "comenzar en 1"),
    ([ApprovalRange(0, 100, "A"), ApprovalRange(100, None, "B")], "positivo"),
    ([ApprovalRange(-5, 100, "A"), ApprovalRange(100, None, "B")], "positivo"),
    ([ApprovalRange(1, 0, "A"), ApprovalRange(0, None, "B")], "positivo"),
    ([ApprovalRange(1, 100, "A")], "ilimitado"),
    ([ApprovalRange(1, None, "A"), ApprovalRange(100, None, "B")], "último"),
    ([ApprovalRange(1, 100, "A"), ApprovalRange(100, 100, "B"),
      ApprovalRange(100, None, "C")], "mayor que su mínimo"),
    ([ApprovalRange(1, 100, "A"), ApprovalRange(100, 200, "B"),
      ApprovalRange(50, None, "C")], "ordenados"),
    ([ApprovalRange(1, None, "  ")], "aprobador"),
    ([ApprovalRange(True, None, "A")], "positivo"),
    (["x"], "ApprovalRange"),
])
def test_invalid_configs_rejected(ranges, fragment):
    with pytest.raises(ValueError) as exc:
        validate_ranges(ranges)
    assert fragment in str(exc.value)


def test_amount_outside_config_raises():
    with pytest.raises(ValueError):
        approver_for(R, 0)


def test_create_app_rejects_invalid_ranges(db_url):
    with pytest.raises(ValueError):
        create_app(db_url, auth_enabled=False, approval_ranges=[ApprovalRange(1, 10, "A")])


def test_create_app_stores_validated_ranges(db_url):
    custom = [ApprovalRange(1, 100, "A"), ApprovalRange(100, None, "B")]
    app = create_app(db_url, auth_enabled=False, approval_ranges=custom)
    assert app.state.approval_ranges == tuple(custom)
    assert create_app(db_url, auth_enabled=False).state.approval_ranges == R
    with TestClient(app):
        pass
