"""QA unit-level cases (service layer, no HTTP). Oracles are hand-written from the rules."""
from datetime import timedelta

import pytest

from app.services import bids as bid_service
from app.services import suppliers as supplier_service
from app.services import tenders as tender_service
from tests.conftest import NOW

CLOSING = NOW + timedelta(hours=48)
P1, P2 = "Tecnología Norte S.A.", "Servicios del Valle"


def _tender(session, code="LIC-2026-001", budget="10000000.00", publish=True):
    t = tender_service.create_tender(session, NOW, code, "Equipo de cómputo", budget, CLOSING)
    if publish:
        tender_service.publish_tender(session, NOW, t.id)
    return t


def test_cp001_supplier_duplicate_by_normalization(session):
    """CP-001 | REQ-001 | Duplicate supplier names are detected after trim, space collapse and
    case folding; a distinct name is accepted | oracle: duplicates by normalized name (trim,
    collapse spaces, case-insensitive)"""
    first = supplier_service.create_supplier(session, P1)
    assert first.name == P1
    for variant in ["  Tecnología Norte S.A.  ", "Tecnología   Norte   S.A.",
                    "TECNOLOGÍA NORTE S.A.", "tecnología norte s.a.",
                    "  tecnología \t NORTE   s.a. "]:
        with pytest.raises(supplier_service.DuplicateSupplierError):
            supplier_service.create_supplier(session, variant)
    other = supplier_service.create_supplier(session, P2)
    assert other.name == P2
    assert [s.name for s in supplier_service.list_suppliers(session)] == [P1, P2]


def test_cp002_tender_field_rules(session):
    """CP-002 | REQ-002 | Tender code unique ignoring case/edge spaces; title not empty; budget
    > 0; closing strictly in the future | oracle: unique code, non-empty title, CRC budget
    > 0, future closing date"""
    t = tender_service.create_tender(session, NOW, "LIC-2026-001", "Equipo", "10000000.00", CLOSING)
    assert t.code == "LIC-2026-001"
    for dup in ["lic-2026-001", "  LIC-2026-001  ", "Lic-2026-001"]:
        with pytest.raises(tender_service.DuplicateTenderError):
            tender_service.create_tender(session, NOW, dup, "Equipo", "10000000.00", CLOSING)
    for title in ["", "   "]:
        with pytest.raises(tender_service.InvalidTenderError):
            tender_service.create_tender(session, NOW, "LIC-T", title, "100.00", CLOSING)
    for budget in ["0", "-1", "0.00", "-0.01"]:
        with pytest.raises(tender_service.InvalidTenderError):
            tender_service.create_tender(session, NOW, "LIC-B", "Equipo", budget, CLOSING)
    ok = tender_service.create_tender(session, NOW, "LIC-B", "Equipo", "0.01", CLOSING)
    assert ok.budget_cents == 1
    for i, closing in enumerate([NOW - timedelta(hours=1), NOW - timedelta(seconds=1), NOW]):
        with pytest.raises(tender_service.InvalidTenderError):
            tender_service.create_tender(session, NOW, f"LIC-C{i}", "Equipo", "100.00", closing)
    future = tender_service.create_tender(session, NOW, "LIC-F", "Equipo", "100.00",
                                          NOW + timedelta(seconds=1))
    assert future.status == "Borrador"


def test_cp003_state_transitions(session):
    """CP-003 | REQ-003 | Allowed transitions succeed and forbidden ones are rejected |
    oracle: Borrador->Publicada, Publicada->Cerrada allowed; no return to Borrador, a Cerrada
    tender is never reopened (NOTE: enunciado also lists Borrador->Cerrada; the app rejects it,
    so it is not asserted here, see report)"""
    t = tender_service.create_tender(session, NOW, "LIC-1", "Equipo", "100.00", CLOSING)
    assert t.status == "Borrador"
    assert tender_service.publish_tender(session, NOW, t.id).status == "Publicada"
    # Publicada -> Borrador impossible: publishing again / editing are rejected, state stays.
    with pytest.raises(tender_service.InvalidTransitionError):
        tender_service.publish_tender(session, NOW, t.id)
    with pytest.raises(tender_service.InvalidTransitionError):
        tender_service.update_tender(session, NOW, t.id, "LIC-1", "Otro", "100.00", CLOSING)
    assert tender_service.get_tender(session, t.id).status == "Publicada"
    assert tender_service.close_tender(session, t.id).status == "Cerrada"
    # Cerrada -> Publicada / Borrador impossible.
    with pytest.raises(tender_service.InvalidTransitionError):
        tender_service.publish_tender(session, NOW, t.id)
    with pytest.raises(tender_service.InvalidTransitionError):
        tender_service.close_tender(session, t.id)
    with pytest.raises(tender_service.InvalidTransitionError):
        tender_service.update_tender(session, NOW, t.id, "LIC-1", "Otro", "100.00", CLOSING)
    assert tender_service.get_tender(session, t.id).status == "Cerrada"


def test_cp004_bid_amount_limits(session):
    """CP-004 | REQ-005 | Bid amount boundaries against the budget | oracle: amount > 0 and
    <= budget; equal to budget is valid; 0, negative and above budget rejected"""
    t = _tender(session)  # budget 10 000 000,00
    p1 = supplier_service.create_supplier(session, P1)
    p2 = supplier_service.create_supplier(session, P2)
    for bad in ["0", "0.00", "-0.01", "-1", "10000000.01"]:
        with pytest.raises(bid_service.InvalidBidError):
            bid_service.create_bid(session, NOW, t.id, p1.id, bad)
    assert bid_service.list_bids_by_tender(session, t.id) == []
    low = bid_service.create_bid(session, NOW, t.id, p1.id, "0.01")
    assert low.amount_cents == 1
    # equal to the budget is valid (update re-validates with the same rules)
    top = bid_service.create_bid(session, NOW, t.id, p2.id, "10000000.00")
    assert top.amount_cents == 1_000_000_000
    with pytest.raises(bid_service.InvalidBidError):
        bid_service.update_bid(session, NOW, low.id, "10000000.01")


def test_cp005_best_bid_rules(session):
    """CP-005 | REQ-007 | Best bid is the lowest; ties go to the first registered; no bids
    gives the 'Sin ofertas válidas' message | oracle: lowest valid offer wins, tie -> first
    registered, none -> 'Sin ofertas válidas'"""
    p1 = supplier_service.create_supplier(session, P1)
    p2 = supplier_service.create_supplier(session, P2)
    empty = _tender(session, "LIC-EMPTY")
    ev = bid_service.evaluate_tender(session, empty.id)
    assert ev.best_bid is None and ev.message == "Sin ofertas válidas"
    lowest = _tender(session, "LIC-LOW")
    bid_service.create_bid(session, NOW, lowest.id, p1.id, "9000000.00")
    bid_service.create_bid(session, NOW + timedelta(minutes=1), lowest.id, p2.id, "9500000.00")
    ev = bid_service.evaluate_tender(session, lowest.id)
    assert ev.best_bid.supplier_id == p1.id and ev.best_bid.amount_cents == 900_000_000
    # lowest wins even if registered last
    last = _tender(session, "LIC-LAST")
    bid_service.create_bid(session, NOW, last.id, p1.id, "9500000.00")
    bid_service.create_bid(session, NOW + timedelta(minutes=1), last.id, p2.id, "9000000.00")
    assert bid_service.evaluate_tender(session, last.id).best_bid.supplier_id == p2.id
    # tie: first registered wins (both orders)
    tie = _tender(session, "LIC-TIE")
    bid_service.create_bid(session, NOW, tie.id, p2.id, "9000000.00")
    bid_service.create_bid(session, NOW + timedelta(minutes=1), tie.id, p1.id, "9000000.00")
    assert bid_service.evaluate_tender(session, tie.id).best_bid.supplier_id == p2.id
    tie2 = _tender(session, "LIC-TIE2")
    bid_service.create_bid(session, NOW, tie2.id, p1.id, "9000000.00")
    bid_service.create_bid(session, NOW + timedelta(minutes=1), tie2.id, p2.id, "9000000.00")
    assert bid_service.evaluate_tender(session, tie2.id).best_bid.supplier_id == p1.id


def test_cp006_saving_classification(session):
    """CP-006 | REQ-008 | Saving percentage and classification at the 10 % / 5 % / 0 % edges |
    oracle: saving=((budget-best)/budget)*100; >=10 % Conveniente; >0 and <10 % Aceptable;
    0 % Válida sin ahorro"""
    p1 = supplier_service.create_supplier(session, P1)
    cases = [  # offer on budget 1 000 000,00 -> (percent, classification)
        ("900000.00", "10.00", "Conveniente"),
        ("950000.00", "5.00", "Aceptable"),
        ("1000000.00", "0.00", "Válida sin ahorro"),
        ("900100.00", "9.99", "Aceptable"),
    ]
    for i, (offer, percent, label) in enumerate(cases):
        t = _tender(session, f"LIC-S{i}", "1000000.00")
        bid_service.create_bid(session, NOW, t.id, p1.id, offer)
        ev = bid_service.evaluate_tender(session, t.id)
        assert (ev.saving_percent, ev.classification) == (percent, label), offer


def test_cp007_approver_boundaries(session):
    """CP-007 | REQ-009 | Approver at every range boundary | oracle: 0,01-999 999,99 Encargado
    de Área; 1 000 000,00-9 999 999,99 Gerencia; >= 10 000 000,00 Junta Directiva (NOTE: app
    label is 'Encargado de área', compared case-insensitively, see report)"""
    p1 = supplier_service.create_supplier(session, P1)
    cases = [
        ("0.01", "Encargado de Área"),
        ("999999.99", "Encargado de Área"),
        ("1000000.00", "Gerencia"),
        ("9999999.99", "Gerencia"),
        ("10000000.00", "Junta Directiva"),
    ]
    for i, (offer, approver) in enumerate(cases):
        t = _tender(session, f"LIC-A{i}", "20000000.00")
        bid_service.create_bid(session, NOW, t.id, p1.id, offer)
        got = bid_service.evaluate_tender(session, t.id).approver
        assert got.casefold() == approver.casefold(), (offer, got)
