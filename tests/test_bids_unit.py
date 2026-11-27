from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.approval import ApprovalRange
from app.models import Bid
from app.services import bids as service
from app.services import suppliers as suppliers_service
from app.services import tenders as tenders_service
from tests.conftest import NOW

BUDGET = "10000000.00"
CLOSING = NOW + timedelta(hours=48)


def make_tender(session, code="LIC-2026-001", budget=BUDGET, publish=True):
    t = tenders_service.create_tender(session, NOW, code, "Equipo", budget, CLOSING)
    if publish:
        tenders_service.publish_tender(session, NOW, t.id)
    return t


def make_supplier(session, name="Tecnología Norte S.A."):
    return suppliers_service.create_supplier(session, name)


@pytest.fixture
def setup(session):
    tender = make_tender(session)
    p1 = make_supplier(session)
    p2 = make_supplier(session, "Servicios del Valle")
    return tender, p1, p2


def bid(session, tender, supplier, amount, now=NOW):
    return service.create_bid(session, now, tender.id, supplier.id, amount)


# --- creation / amounts (REQ-005) -------------------------------------------------

def test_valid_bids_for_two_suppliers(session, setup):
    t, p1, p2 = setup
    b1 = bid(session, t, p1, "9000000.00")
    b2 = bid(session, t, p2, "9500000.00")
    assert (b1.amount_cents, b2.amount_cents) == (900_000_000, 950_000_000)
    assert b1.created_at == NOW


def test_amount_equal_to_budget_is_valid(session, setup):
    t, p1, _ = setup
    assert bid(session, t, p1, BUDGET).amount_cents == 1_000_000_000


def test_smallest_amount_valid(session, setup):
    t, p1, _ = setup
    assert bid(session, t, p1, "0.01").amount_cents == 1


@pytest.mark.parametrize("amount", ["0", "0.00", "-1", "-0.01", "10000000.01"])
def test_amount_out_of_range_rejected(session, setup, amount):
    t, p1, _ = setup
    with pytest.raises(service.InvalidBidError):
        bid(session, t, p1, amount)
    assert session.query(Bid).count() == 0


@pytest.mark.parametrize("amount", [
    True, None, [], "abc", "", "1e3", "1,5", "1.234", "<script>alert(1)</script>",
    "9 000", "NaN", "inf",
])
def test_amount_junk_rejected(session, setup, amount):
    t, p1, _ = setup
    with pytest.raises(service.InvalidBidError):
        bid(session, t, p1, amount)


def test_budget_error_message_mentions_budget(session, setup):
    t, p1, _ = setup
    with pytest.raises(service.InvalidBidError, match="10 000 000,00"):
        bid(session, t, p1, "10000000.01")


@pytest.mark.parametrize("supplier_id", [True, "1", None, 1.0, 999])
def test_invalid_or_unknown_supplier_rejected(session, setup, supplier_id):
    t, _, _ = setup
    with pytest.raises(service.InvalidBidError):
        service.create_bid(session, NOW, t.id, supplier_id, "100")


def test_unknown_tender_not_found(session, setup):
    _, p1, _ = setup
    with pytest.raises(service.BidTargetNotFoundError):
        service.create_bid(session, NOW, 999, p1.id, "100")


# --- time and state (REQ-004) -------------------------------------------------------

def test_bid_just_before_closing_accepted(session, setup):
    t, p1, _ = setup
    assert bid(session, t, p1, "100", now=CLOSING - timedelta(microseconds=1))


def test_bid_exactly_at_closing_rejected(session, setup):
    t, p1, _ = setup
    with pytest.raises(service.BidNotAllowedError):
        bid(session, t, p1, "100", now=CLOSING)


def test_bid_after_closing_rejected(session, setup):
    t, p1, _ = setup
    with pytest.raises(service.BidNotAllowedError):
        bid(session, t, p1, "100", now=CLOSING + timedelta(seconds=1))


def test_draft_tender_rejects_bids(session):
    t = make_tender(session, publish=False)
    p = make_supplier(session)
    with pytest.raises(service.BidNotAllowedError, match="Publicada"):
        bid(session, t, p, "100")


def test_closed_tender_rejects_bids(session, setup):
    t, p1, _ = setup
    tenders_service.close_tender(session, t.id)
    with pytest.raises(service.BidNotAllowedError):
        bid(session, t, p1, "100")


# --- duplicates (REQ-006) ----------------------------------------------------------

def test_duplicate_bid_rejected_in_service(session, setup):
    t, p1, _ = setup
    bid(session, t, p1, "9000000")
    with pytest.raises(service.DuplicateBidError):
        bid(session, t, p1, "8000000")
    assert session.query(Bid).count() == 1


def test_same_supplier_can_bid_on_other_tender(session, setup):
    t, p1, _ = setup
    t2 = make_tender(session, code="LIC-2")
    bid(session, t, p1, "100")
    assert bid(session, t2, p1, "100")


def test_db_unique_constraint_enforced(session, setup):
    t, p1, _ = setup
    bid(session, t, p1, "100")
    session.add(Bid(tender_id=t.id, supplier_id=p1.id, amount_cents=5, created_at=NOW))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_db_check_constraint_positive_amount(session, setup):
    t, p1, _ = setup
    session.add(Bid(tender_id=t.id, supplier_id=p1.id, amount_cents=0, created_at=NOW))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_integrity_error_race_maps_to_duplicate(session, setup, monkeypatch):
    t, p1, _ = setup
    bid(session, t, p1, "100")
    original = session.scalars

    class _Empty:
        def first(self):
            return None

    def blind_precheck(statement, *a, **kw):
        # Simulate the race: the duplicate pre-check does not see the other bid.
        if "bids.id" in str(statement) and "count" not in str(statement):
            return _Empty()
        return original(statement, *a, **kw)

    monkeypatch.setattr(session, "scalars", blind_precheck)
    with pytest.raises(service.DuplicateBidError):
        bid(session, t, p1, "200")
    monkeypatch.undo()
    assert session.query(Bid).count() == 1


# --- listings ---------------------------------------------------------------------

def test_listings(session, setup):
    t, p1, p2 = setup
    t2 = make_tender(session, code="LIC-2")
    bid(session, t, p1, "300")
    bid(session, t, p2, "200", now=NOW + timedelta(minutes=1))
    bid(session, t2, p1, "400")
    assert [b.supplier_id for b in service.list_bids_by_tender(session, t.id)] == [
        p1.id, p2.id]
    assert [b.tender_id for b in service.list_bids_by_supplier(session, p1.id)] == [
        t.id, t2.id]
    assert service.list_bids_by_supplier(session, p2.id)[0].tender.code == "LIC-2026-001"


def test_listing_unknown_targets(session):
    with pytest.raises(service.BidTargetNotFoundError):
        service.list_bids_by_tender(session, 5)
    with pytest.raises(service.BidTargetNotFoundError):
        service.list_bids_by_supplier(session, 5)
    with pytest.raises(service.BidTargetNotFoundError):
        service.evaluate_tender(session, 5)


# --- evaluation (REQ-007..009) -----------------------------------------------------

def test_reference_scenario(session, setup):
    t, p1, p2 = setup
    bid(session, t, p1, "9000000.00")
    bid(session, t, p2, "9500000.00", now=NOW + timedelta(minutes=1))
    ev = service.evaluate_tender(session, t.id)
    assert ev.best_bid.supplier_id == p1.id
    assert ev.bid_count == 2
    assert ev.saving_percent == "10.00"
    assert ev.classification == "Conveniente"
    assert ev.approver == "Gerencia"
    assert ev.message is None


def test_no_bids(session, setup):
    t, _, _ = setup
    ev = service.evaluate_tender(session, t.id)
    assert ev.best_bid is None and ev.bid_count == 0
    assert ev.approver is None and ev.saving_percent is None
    assert ev.classification is None
    assert ev.message == "Sin ofertas válidas"


def test_tie_goes_to_earliest_bid(session, setup):
    t, p1, p2 = setup
    bid(session, t, p2, "9000000", now=NOW)
    bid(session, t, p1, "9000000", now=NOW + timedelta(seconds=5))
    assert service.evaluate_tender(session, t.id).best_bid.supplier_id == p2.id


def test_tie_same_instant_goes_to_lowest_id(session, setup):
    t, p1, p2 = setup
    bid(session, t, p1, "9000000")
    bid(session, t, p2, "9000000")
    assert service.evaluate_tender(session, t.id).best_bid.supplier_id == p1.id


def test_lowest_wins_even_if_registered_later(session, setup):
    t, p1, p2 = setup
    bid(session, t, p1, "9500000")
    bid(session, t, p2, "9000000", now=NOW + timedelta(hours=1))
    assert service.evaluate_tender(session, t.id).best_bid.supplier_id == p2.id


@pytest.mark.parametrize("best, percent, classification", [
    ("900000", "10.00", "Conveniente"),
    ("950000", "5.00", "Aceptable"),
    ("1000000", "0.00", "Válida sin ahorro"),
    ("500000", "50.00", "Conveniente"),
    ("0.01", "100.00", "Conveniente"),
])
def test_savings_scenarios(session, best, percent, classification):
    t = make_tender(session, budget="1000000.00")
    p = make_supplier(session)
    bid(session, t, p, best)
    ev = service.evaluate_tender(session, t.id)
    assert (ev.saving_percent, ev.classification) == (percent, classification)


def test_9_99_percent_stays_acceptable_despite_rounding(session):
    # saving = 9.9995 % -> displays as 10.00 but must classify as Aceptable.
    t = make_tender(session, budget="1000000.00")
    p = make_supplier(session)
    bid(session, t, p, "900005.00")
    ev = service.evaluate_tender(session, t.id)
    assert ev.saving_percent == "10.00"
    assert ev.classification == "Aceptable"


def test_awkward_budget_below_ten_percent_is_acceptable(session):
    t = make_tender(session, budget="333.33")
    p = make_supplier(session)
    bid(session, t, p, "300.00")  # saving 9.9991...%
    ev = service.evaluate_tender(session, t.id)
    assert (ev.saving_percent, ev.classification) == ("10.00", "Aceptable")


@pytest.mark.parametrize("budget_cents, best_cents, expected", [
    (10_000, 9_000, 1000), (3, 2, 3333), (3, 1, 6667), (200, 199, 50),
    (400, 399, 25), (1_000_000, 0, 10000),
])
def test_percent_rounding_half_up(budget_cents, best_cents, expected):
    assert service.saving_percent_hundredths(budget_cents, best_cents) == expected


def test_percent_half_up_exact_tie():
    # 1/8 = 12.5 %; 1/16000 = 0.00625 % -> 0.625 hundredths -> 0.01
    assert service.format_percent(service.saving_percent_hundredths(8, 7)) == "12.50"
    assert service.format_percent(
        service.saving_percent_hundredths(16_000, 15_999)) == "0.01"
    assert service.format_percent(
        service.saving_percent_hundredths(40_000, 39_999)) == "0.00"
    # exact half: 1/20000 = 0.005 % -> 0.5 hundredths -> half-up -> 0.01
    assert service.format_percent(
        service.saving_percent_hundredths(20_000, 19_999)) == "0.01"


@pytest.mark.parametrize("best, approver", [
    ("0.01", "Encargado de Área"),
    ("999999.99", "Encargado de Área"),
    ("1000000.00", "Gerencia"),
    ("9999999.99", "Gerencia"),
    ("10000000.00", "Junta Directiva"),
])
def test_approver_by_best_bid_amount(session, best, approver):
    t = make_tender(session, budget="10000000.00")
    p = make_supplier(session)
    bid(session, t, p, best)
    assert service.evaluate_tender(session, t.id).approver == approver


def test_approver_uses_best_not_other_bids(session, setup):
    t, p1, p2 = setup
    bid(session, t, p1, "10000000.00")
    bid(session, t, p2, "999999.99")
    assert service.evaluate_tender(session, t.id).approver == "Encargado de Área"


def test_custom_ranges_used(session, setup):
    t, p1, _ = setup
    bid(session, t, p1, "9000000")
    custom = (ApprovalRange(1, None, "Único"),)
    assert service.evaluate_tender(session, t.id, custom).approver == "Único"


def test_evaluation_does_not_modify_data(session, setup):
    t, p1, p2 = setup
    bid(session, t, p1, "9000000")
    bid(session, t, p2, "9500000")

    def snapshot():
        return [(b.id, b.tender_id, b.supplier_id, b.amount_cents, b.created_at)
                for b in service.list_bids_by_tender(session, t.id)]

    before = snapshot()
    service.evaluate_tender(session, t.id)
    service.evaluate_tender(session, t.id)
    session.expire_all()
    assert snapshot() == before
    assert not session.new and not session.dirty
