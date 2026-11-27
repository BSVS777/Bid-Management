import pytest

from app.models import ExchangeRate
from app.services import exchange_rate as svc
from tests.conftest import NOW


@pytest.mark.parametrize("text,hundredths", [
    ("500", 50000), ("500.00", 50000), ("0.01", 1), ("512.35", 51235),
    ("  520.5 ", 52050), ("100000.00", 10_000_000),
])
def test_parse_valid(text, hundredths):
    assert svc.parse_rate_hundredths(text) == hundredths


@pytest.mark.parametrize("bad", [
    "0", "0.00", "-1", "-500.00", "abc", "", "  ", "1e3", "1E3", "5e2", "500,00",
    "500.001", "100000.01", "99999999999", "1 000", "NaN", "inf", "+5", ".5",
    "500.", None, True, [], 0, -3, 0.0, 1e30,
])
def test_parse_rejects_invalid(bad):
    with pytest.raises(svc.InvalidRateError):
        svc.parse_rate_hundredths(bad)


def test_parse_accepts_numeric_types():
    assert svc.parse_rate_hundredths(500) == 50000
    assert svc.parse_rate_hundredths(512.5) == 51250


def test_get_current_rate_none_when_unset(session):
    assert svc.get_current_rate(session) is None
    with pytest.raises(svc.RateNotConfiguredError):
        svc.require_rate(session)


def test_set_rate_keeps_history_and_latest_is_current(session):
    svc.set_rate(session, NOW, "500.00")
    svc.set_rate(session, NOW.replace(hour=13), "510.25")
    assert session.query(ExchangeRate).count() == 2
    current = svc.get_current_rate(session)
    assert current.rate_hundredths == 51025
    assert current.created_at == NOW.replace(hour=13)


def test_invalid_set_rate_stores_nothing(session):
    with pytest.raises(svc.InvalidRateError):
        svc.set_rate(session, NOW, "-5")
    assert session.query(ExchangeRate).count() == 0


def test_reference_case_nine_million_at_500_is_18000():
    # 9 000 000,00 CRC = 900_000_000 cents; 18 000,00 USD = 1_800_000 cents.
    assert svc.crc_to_usd(900_000_000, 50000) == 1_800_000


@pytest.mark.parametrize("crc_cents,rate_h,usd_cents", [
    (50000, 50000, 100),  # 500.00 CRC at 500.00 = 1.00 USD
    (1, 50000, 0),        # 0.01 CRC = 0.00002 USD -> 0.00
    (249, 50000, 0),      # 0.498 of a USD cent -> down
    (250, 50000, 1),      # exactly half a USD cent -> up (half-up)
    (251, 50000, 1),
    (100, 30000, 0),      # 1 CRC at 300.00 = 0.0033 USD -> 0.00
    (1_000_000, 51235, 1952),  # 10 000.00 CRC / 512.35 = 19.5179 USD
])
def test_crc_to_usd_rounding(crc_cents, rate_h, usd_cents):
    assert svc.crc_to_usd(crc_cents, rate_h) == usd_cents


def test_usd_to_crc():
    assert svc.usd_to_crc(1_800_000, 50000) == 900_000_000
    assert svc.usd_to_crc(1, 51235) == 512  # 512.35 CRC cents -> 512
    assert svc.usd_to_crc(1, 50050) == 501  # 500.50 CRC cents -> half-up


def test_conversion_rejects_non_positive_rate():
    with pytest.raises(svc.InvalidRateError):
        svc.crc_to_usd(100, 0)
    with pytest.raises(svc.InvalidRateError):
        svc.usd_to_crc(100, -1)


def test_format_rate():
    assert svc.format_rate(50000) == "500.00"
    assert svc.format_rate(1) == "0.01"
