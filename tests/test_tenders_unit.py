from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Tender
from app.services import tenders as svc
from tests.conftest import NOW

S = svc.TenderStatus
CODE = "LIC-2026-001"
TITLE = "Adquisición de equipo de cómputo"
BUDGET = "10000000.00"
CLOSING = NOW + timedelta(hours=48)


def make(session, code=CODE, title=TITLE, budget=BUDGET, closing=CLOSING, now=NOW):
    return svc.create_tender(session, now, code, title, budget, closing.isoformat())


# --- creation -----------------------------------------------------------------

def test_create_reference_tender(session):
    t = make(session)
    assert t.id == 1
    assert (t.code, t.title) == (CODE, TITLE)
    assert t.budget_cents == 1_000_000_000
    assert t.closing_at == CLOSING
    assert t.status == S.DRAFT
    assert t.created_at == NOW
    assert t.code_key == "lic-2026-001"


def test_code_is_trimmed_and_title_is_stripped(session):
    t = make(session, code="  LIC-9  ", title="  Algo útil  ")
    assert (t.code, t.title) == ("LIC-9", "Algo útil")


@pytest.mark.parametrize("code", ["lic-2026-001", "LIC-2026-001", "  Lic-2026-001  "])
def test_duplicate_code_variants_rejected(session, code):
    make(session)
    with pytest.raises(svc.DuplicateTenderError):
        make(session, code=code)
    assert len(svc.list_tenders(session)) == 1


@pytest.mark.parametrize("code", ["A", "a_b-C", "x" * 30, "0123456789"])
def test_valid_codes(session, code):
    assert make(session, code=code).code == code


@pytest.mark.parametrize(
    "code",
    ["", "   ", "x" * 31, "LIC 001", "LIC.001", "LIC/001", "<b>", "LIC;DROP",
     "código", "LIC\n001", "a b", "ＬＩＣ"],
)
def test_invalid_codes(session, code):
    with pytest.raises(svc.InvalidTenderError):
        make(session, code=code)


@pytest.mark.parametrize("value", [None, 5, ["a"], b"x"])
def test_non_string_code_or_title_rejected(session, value):
    with pytest.raises(svc.InvalidTenderError):
        make(session, code=value)
    with pytest.raises(svc.InvalidTenderError):
        make(session, title=value)


@pytest.mark.parametrize(
    "title",
    ["", "   ", "\t\n", "x" * 201, "<script>alert(1)</script>", "a<b", "a>b",
     "a\x00b", "a\nb"],
)
def test_invalid_titles(session, title):
    with pytest.raises(svc.InvalidTenderError):
        make(session, title=title)


def test_title_max_length_ok(session):
    assert len(make(session, title="x" * 200).title) == 200


def test_title_with_other_punctuation_ok(session):
    assert make(session, title='Compra "A&B" (lote #1) - 50% ñandú').id == 1


def test_error_messages_do_not_echo_input(session):
    with pytest.raises(svc.InvalidTenderError) as exc:
        make(session, title="<script>alert(1)</script>")
    assert "script" not in str(exc.value)


# --- budget --------------------------------------------------------------------

@pytest.mark.parametrize(
    "budget",
    ["0", "0.00", "-1", "-0.01", 0, -5, "0.001", "1.234", "abc", "", "1e3", "NaN",
     "inf", True, None, "10000000000000", "1,000"],
)
def test_invalid_budgets(session, budget):
    with pytest.raises(svc.InvalidTenderError):
        make(session, budget=budget)


@pytest.mark.parametrize(
    "budget, cents",
    [("10000000.00", 1_000_000_000), (5, 500), ("0.01", 1),
     ("9999999999999.99", 999_999_999_999_999), (12.5, 1250)],
)
def test_valid_budgets(session, budget, cents):
    assert make(session, budget=budget).budget_cents == cents


# --- closing date --------------------------------------------------------------

def test_closing_in_past_rejected(session):
    with pytest.raises(svc.InvalidTenderError):
        make(session, closing=NOW - timedelta(seconds=1))


def test_closing_exactly_now_rejected(session):
    with pytest.raises(svc.InvalidTenderError):
        make(session, closing=NOW)


def test_closing_one_second_ahead_ok(session):
    assert make(session, closing=NOW + timedelta(seconds=1)).status == S.DRAFT


@pytest.mark.parametrize(
    "value",
    ["", "garbage", "2026-13-40T10:00", "2026-12-31", "31/12/2026 10:00", None, 5, ["x"]],
)
def test_unparsable_closing_rejected(session, value):
    with pytest.raises(svc.InvalidTenderError):
        svc.create_tender(session, NOW, CODE, TITLE, BUDGET, value)


@pytest.mark.parametrize(
    "value",
    ["2026-12-31T10:00:00", "2026-12-31 10:00:00", "2026-12-31T10:00",
     "2026-12-31T10:00:00.500"],
)
def test_iso_formats_accepted(session, value):
    t = svc.create_tender(session, NOW, CODE, TITLE, BUDGET, value)
    assert t.closing_at.replace(microsecond=0) == datetime(2026, 12, 31, 10, 0)


def test_accepts_datetime_object():
    assert svc.parse_closing_at(datetime(2026, 12, 31, 10)) == datetime(2026, 12, 31, 10)


def test_offset_is_converted_to_local_naive():
    aware = datetime(2026, 12, 31, 16, 0, tzinfo=timezone.utc)
    parsed = svc.parse_closing_at("2026-12-31T16:00:00+00:00")
    assert parsed.tzinfo is None
    assert parsed == aware.astimezone().replace(tzinfo=None)
    assert svc.parse_closing_at("2026-12-31T16:00:00Z") == parsed


# --- persistence / lookup ------------------------------------------------------

def test_get_and_not_found(session):
    t = make(session)
    assert svc.get_tender(session, t.id).code == CODE
    with pytest.raises(svc.TenderNotFoundError):
        svc.get_tender(session, 999)


def test_list_ordered_and_filtered(session):
    make(session, code="A")
    b = make(session, code="B")
    make(session, code="C")
    svc.publish_tender(session, NOW, b.id)
    assert [t.code for t in svc.list_tenders(session)] == ["A", "B", "C"]
    assert [t.code for t in svc.list_tenders(session, S.DRAFT)] == ["A", "C"]
    assert [t.code for t in svc.list_tenders(session, S.PUBLISHED)] == ["B"]
    assert svc.list_tenders(session, S.CLOSED) == []


def test_list_invalid_status_filter(session):
    with pytest.raises(svc.InvalidTenderError):
        svc.list_tenders(session, "Otra")


def test_db_unique_constraint_on_code_key(session):
    make(session)
    session.add(Tender(code="x", code_key="lic-2026-001", title="t", budget_cents=1,
                       closing_at=CLOSING, status=S.DRAFT, created_at=NOW))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_db_rejects_bad_status_and_budget(session):
    session.add(Tender(code="x", code_key="x", title="t", budget_cents=1,
                       closing_at=CLOSING, status="Otro", created_at=NOW))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.add(Tender(code="y", code_key="y", title="t", budget_cents=0,
                       closing_at=CLOSING, status=S.DRAFT, created_at=NOW))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_integrity_race_maps_to_duplicate(session, monkeypatch):
    make(session)
    monkeypatch.setattr(svc, "_find_by_key", lambda s, k: None)  # simulate lost race
    with pytest.raises(svc.DuplicateTenderError):
        make(session, code="lic-2026-001")
    assert len(session.scalars(select(Tender)).all()) == 1


def test_integrity_race_on_update_maps_to_duplicate(session, monkeypatch):
    make(session, code="A")
    b = make(session, code="B")
    monkeypatch.setattr(svc, "_find_by_key", lambda s, k: None)
    with pytest.raises(svc.DuplicateTenderError):
        svc.update_tender(session, NOW, b.id, "a", TITLE, BUDGET, CLOSING.isoformat())


# --- state machine -------------------------------------------------------------

def test_full_lifecycle(session):
    t = make(session)
    assert svc.publish_tender(session, NOW, t.id).status == S.PUBLISHED
    assert svc.close_tender(session, t.id).status == S.CLOSED
    assert svc.get_tender(session, t.id).status == S.CLOSED


def test_publish_requires_future_closing(session):
    t = make(session)
    with pytest.raises(svc.InvalidTenderError):
        svc.publish_tender(session, CLOSING + timedelta(seconds=1), t.id)
    with pytest.raises(svc.InvalidTenderError):
        svc.publish_tender(session, CLOSING, t.id)  # exactly at closing
    assert svc.get_tender(session, t.id).status == S.DRAFT


def test_draft_cannot_be_closed_directly(session):
    t = make(session)
    with pytest.raises(svc.InvalidTransitionError):
        svc.close_tender(session, t.id)
    assert svc.get_tender(session, t.id).status == S.DRAFT


def test_publish_twice_rejected(session):
    t = make(session)
    svc.publish_tender(session, NOW, t.id)
    with pytest.raises(svc.InvalidTransitionError):
        svc.publish_tender(session, NOW, t.id)


def test_close_twice_rejected(session):
    t = make(session)
    svc.publish_tender(session, NOW, t.id)
    svc.close_tender(session, t.id)
    with pytest.raises(svc.InvalidTransitionError):
        svc.close_tender(session, t.id)


def test_closed_cannot_be_reopened_or_republished(session):
    t = make(session)
    svc.publish_tender(session, NOW, t.id)
    svc.close_tender(session, t.id)
    with pytest.raises(svc.InvalidTransitionError):
        svc.publish_tender(session, NOW, t.id)
    assert svc.get_tender(session, t.id).status == S.CLOSED


def test_transitions_on_missing_tender(session):
    with pytest.raises(svc.TenderNotFoundError):
        svc.publish_tender(session, NOW, 1)
    with pytest.raises(svc.TenderNotFoundError):
        svc.close_tender(session, 1)


# --- editing -------------------------------------------------------------------

def test_edit_draft(session):
    t = make(session)
    new_closing = (NOW + timedelta(days=5)).isoformat()
    u = svc.update_tender(session, NOW, t.id, "LIC-2026-002", " Nuevo ", "5.50", new_closing)
    assert (u.code, u.title, u.budget_cents) == ("LIC-2026-002", "Nuevo", 550)
    assert u.closing_at == NOW + timedelta(days=5)
    assert u.code_key == "lic-2026-002"


def test_edit_own_code_case_variant_ok(session):
    t = make(session)
    u = svc.update_tender(session, NOW, t.id, CODE.lower(), TITLE, BUDGET,
                          CLOSING.isoformat())
    assert u.code == CODE.lower()


def test_edit_to_other_tenders_code_rejected(session):
    make(session, code="A")
    b = make(session, code="B")
    with pytest.raises(svc.DuplicateTenderError):
        svc.update_tender(session, NOW, b.id, " a ", TITLE, BUDGET, CLOSING.isoformat())
    assert svc.get_tender(session, b.id).code == "B"


@pytest.mark.parametrize(
    "fields",
    [dict(code=""), dict(title=" "), dict(budget="0"), dict(closing="nope"),
     dict(title="<b>x</b>")],
)
def test_edit_validates(session, fields):
    t = make(session)
    args = dict(code=CODE, title=TITLE, budget=BUDGET, closing=CLOSING.isoformat())
    args.update(fields)
    with pytest.raises(svc.InvalidTenderError):
        svc.update_tender(session, NOW, t.id, args["code"], args["title"],
                          args["budget"], args["closing"])


def test_edit_new_closing_must_be_future(session):
    t = make(session)
    with pytest.raises(svc.InvalidTenderError):
        svc.update_tender(session, NOW, t.id, CODE, TITLE, BUDGET,
                          (NOW - timedelta(hours=1)).isoformat())


def test_edit_unchanged_expired_closing_allowed(session):
    t = make(session)
    later = CLOSING + timedelta(days=1)
    u = svc.update_tender(session, later, t.id, CODE, "Otro título", BUDGET,
                          CLOSING.isoformat())
    assert u.title == "Otro título"


@pytest.mark.parametrize("final", [S.PUBLISHED, S.CLOSED])
def test_edit_blocked_after_publish(session, final):
    t = make(session)
    svc.publish_tender(session, NOW, t.id)
    if final == S.CLOSED:
        svc.close_tender(session, t.id)
    with pytest.raises(svc.InvalidTransitionError):
        svc.update_tender(session, NOW, t.id, "ZZZ", TITLE, BUDGET, CLOSING.isoformat())
    assert svc.get_tender(session, t.id).code == CODE


def test_edit_missing_tender(session):
    with pytest.raises(svc.TenderNotFoundError):
        svc.update_tender(session, NOW, 7, CODE, TITLE, BUDGET, CLOSING.isoformat())
