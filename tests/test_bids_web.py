from datetime import timedelta

import pytest

from tests.conftest import NOW

CLOSING = NOW + timedelta(hours=48)
P1_NAME, P2_NAME = "Tecnología Norte S.A.", "Servicios del Valle"


def add_tender(client, code="LIC-2026-001", budget="10000000.00", publish=True):
    r = client.post("/tenders", data={
        "code": code, "title": "Equipo de cómputo", "budget_crc": budget,
        "closing_at": CLOSING.strftime("%Y-%m-%dT%H:%M")})
    assert r.status_code == 303
    tid = max(t["id"] for t in client.get("/api/tenders").json())
    if publish:
        assert client.post(f"/tenders/{tid}/publish").status_code == 303
    return tid


def add_supplier(client, name):
    assert client.post("/suppliers", data={"name": name}).status_code == 303
    return max(s["id"] for s in client.get("/api/suppliers").json())


def web_bid(client, tender_id, supplier_id, amount):
    return client.post(f"/tenders/{tender_id}/bids",
                       data={"supplier_id": str(supplier_id), "amount_crc": amount})


@pytest.fixture
def world(tclient):
    return add_tender(tclient), add_supplier(tclient, P1_NAME), add_supplier(tclient, P2_NAME)


def test_page_shows_summary_form_and_empty_state(tclient, world):
    t, _, _ = world
    r = tclient.get(f"/tenders/{t}/bids")
    assert r.status_code == 200
    assert "LIC-2026-001" in r.text and "10 000 000,00" in r.text
    assert "Publicada" in r.text and "Equipo de cómputo" in r.text
    assert "<select" in r.text and P1_NAME in r.text and P2_NAME in r.text
    assert "No hay ofertas registradas." in r.text
    assert "Sin ofertas válidas" in r.text


def test_tenders_list_links_to_bids_page(tclient, world):
    assert f'href="/tenders/{world[0]}/bids"' in tclient.get("/tenders").text


def test_full_flow_reference_scenario(tclient, world):
    t, p1, p2 = world
    r = web_bid(tclient, t, p1, "9000000.00")
    assert r.status_code == 303 and r.headers["location"] == f"/tenders/{t}/bids"
    assert web_bid(tclient, t, p2, "9500000.00").status_code == 303
    page = tclient.get(f"/tenders/{t}/bids").text
    assert "9 000 000,00" in page and "9 500 000,00" in page
    assert "Mejor oferta" in page and P1_NAME in page
    assert "Ahorro: 10.00%" in page
    assert "Clasificación: Conveniente" in page
    assert "Aprobador: Gerencia" in page
    assert "Sin ofertas válidas" not in page


@pytest.mark.parametrize("amount, status, fragment", [
    ("0", 422, "mayor que cero"),
    ("-5", 422, "mayor que cero"),
    ("10000000.01", 422, "no puede superar el presupuesto"),
    ("abc", 422, "Monto inválido"),
    ("", 422, "Monto inválido"),
])
def test_invalid_amount_rerenders_with_error(tclient, world, amount, status, fragment):
    t, p1, _ = world
    r = web_bid(tclient, t, p1, amount)
    assert r.status_code == status
    assert 'role="alert"' in r.text and fragment in r.text
    assert "Traceback" not in r.text
    assert f'value="{p1}" selected' in r.text  # selection kept


def test_script_amount_rejected_and_escaped(tclient, world):
    t, p1, _ = world
    r = web_bid(tclient, t, p1, "<script>alert(1)</script>")
    assert r.status_code == 422
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;" in r.text
    assert "Traceback" not in r.text
    assert "No hay ofertas registradas." in r.text


def test_missing_or_bad_supplier_422(tclient, world):
    t, _, _ = world
    for supplier in ("", "abc", "999", "1; DROP TABLE bids"):
        r = web_bid(tclient, t, supplier, "100")
        assert r.status_code == 422 and "proveedor" in r.text.lower()
        assert "Traceback" not in r.text


def test_duplicate_409_page(tclient, world):
    t, p1, _ = world
    web_bid(tclient, t, p1, "100")
    r = web_bid(tclient, t, p1, "50")
    assert r.status_code == 409 and "ya registró una oferta" in r.text
    assert "Traceback" not in r.text


def test_closing_deadline_409(tclient, clock, world):
    t, p1, p2 = world
    clock.current = CLOSING
    r = web_bid(tclient, t, p1, "100")
    assert r.status_code == 409 and "ya cerró" in r.text
    clock.current = CLOSING - timedelta(minutes=1)
    assert web_bid(tclient, t, p2, "100").status_code == 303


def test_draft_and_closed_tender_409(tclient):
    p = add_supplier(tclient, P1_NAME)
    draft = add_tender(tclient, publish=False)
    r = web_bid(tclient, draft, p, "100")
    assert r.status_code == 409 and "estado Publicada" in r.text
    closed = add_tender(tclient, code="LIC-2")
    tclient.post(f"/tenders/{closed}/close")
    assert web_bid(tclient, closed, p, "100").status_code == 409


def test_unknown_tender_404(tclient):
    assert tclient.get("/tenders/99/bids").status_code == 404
    assert tclient.post("/tenders/99/bids",
                        data={"supplier_id": "1", "amount_crc": "1"}).status_code == 404


def test_missing_form_fields_422(tclient, world):
    r = tclient.post(f"/tenders/{world[0]}/bids")
    assert r.status_code == 422 and "Traceback" not in r.text


def test_evaluation_without_bids_and_classification_texts(tclient):
    t = add_tender(tclient, budget="1000000.00")
    p = add_supplier(tclient, P1_NAME)
    assert "Sin ofertas válidas" in tclient.get(f"/tenders/{t}/bids").text
    web_bid(tclient, t, p, "950000")
    page = tclient.get(f"/tenders/{t}/bids").text
    assert "Ahorro: 5.00%" in page and "Clasificación: Aceptable" in page
    assert "Aprobador: Encargado de Área" in page


def test_stored_script_supplier_name_never_rendered_raw(tclient, db_url, world):
    from sqlalchemy.orm import sessionmaker
    from app.database import make_engine
    from app.models import Supplier
    t, p1, _ = world
    web_bid(tclient, t, p1, "100")
    engine = make_engine(db_url)
    with sessionmaker(bind=engine)() as s:
        s.get(Supplier, p1).name = "<script>alert(1)</script>"
        s.commit()
    engine.dispose()
    for path in (f"/tenders/{t}/bids", f"/suppliers/{p1}/bids"):
        page = tclient.get(path).text
        assert "<script>alert(1)</script>" not in page
        assert "&lt;script&gt;" in page


def test_supplier_bids_page(tclient, world):
    t, p1, p2 = world
    web_bid(tclient, t, p1, "9000000.00")
    page = tclient.get(f"/suppliers/{p1}/bids").text
    assert P1_NAME in page and "LIC-2026-001" in page and "9 000 000,00" in page
    assert "No hay ofertas registradas." in tclient.get(f"/suppliers/{p2}/bids").text
    assert f'href="/suppliers/{p1}/bids"' in tclient.get("/suppliers").text


def test_supplier_bids_unknown_404(tclient):
    assert tclient.get("/suppliers/99/bids").status_code == 404
