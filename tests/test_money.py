from decimal import Decimal

import pytest

from app.money import (
    MAX_CENTS,
    InvalidMoneyError,
    cents_to_decimal,
    format_crc,
    format_crc_display,
    parse_crc_to_cents,
)


@pytest.mark.parametrize(
    "value, cents",
    [
        ("10000000.00", 1_000_000_000),
        ("10000000", 1_000_000_000),
        (" 10000000.5 ", 1_000_000_050),
        ("0.01", 1),
        ("0", 0),
        ("-5.25", -525),
        (10_000_000, 1_000_000_000),
        (12.5, 1250),
        (Decimal("99.99"), 9999),
        ("9999999999999.99", MAX_CENTS),
    ],
)
def test_parse_valid(value, cents):
    assert parse_crc_to_cents(value) == cents


@pytest.mark.parametrize(
    "value",
    [
        "", "  ", "abc", "1e3", "1E3", "0x10", "1,000.00", "10,5", "1 000",
        "NaN", "inf", "-inf", "+5", ".5", "5.", "1.234", "10.500", "1_000",
        "9999999999999.991", "10000000000000", "9" * 41,
        True, False, None, [], {}, b"10", float("nan"), float("inf"), 1e30,
        Decimal("NaN"), Decimal("1E+3"), 10**20,
    ],
)
def test_parse_invalid(value):
    with pytest.raises(InvalidMoneyError):
        parse_crc_to_cents(value)


def test_non_ascii_digits_rejected():
    with pytest.raises(InvalidMoneyError):
        parse_crc_to_cents("٣٤")  # Arabic-Indic digits


def test_invalid_money_error_is_value_error():
    assert issubclass(InvalidMoneyError, ValueError)


def test_huge_int_is_rejected_not_crashed():
    with pytest.raises(InvalidMoneyError):
        parse_crc_to_cents(10**5000)


def test_no_float_rounding_artifacts():
    assert parse_crc_to_cents("0.07") == 7
    assert parse_crc_to_cents("1.15") == 115
    assert parse_crc_to_cents(0.1) == 10


def test_cents_to_decimal():
    assert cents_to_decimal(1_000_000_000) == Decimal("10000000.00")
    assert str(cents_to_decimal(5)) == "0.05"
    assert str(cents_to_decimal(0)) == "0.00"
    assert str(cents_to_decimal(-250)) == "-2.50"


@pytest.mark.parametrize("bad", [1.5, "10", True, None])
def test_cents_to_decimal_requires_int(bad):
    with pytest.raises(TypeError):
        cents_to_decimal(bad)


def test_format_crc_roundtrip():
    assert format_crc(1_000_000_000) == "10000000.00"
    assert format_crc(MAX_CENTS) == "9999999999999.99"
    assert parse_crc_to_cents(format_crc(123456)) == 123456


def test_format_crc_display():
    assert format_crc_display(1_000_000_000) == "10 000 000,00"
    assert format_crc_display(5) == "0,05"
    assert format_crc_display(-123456) == "-1 234,56"
