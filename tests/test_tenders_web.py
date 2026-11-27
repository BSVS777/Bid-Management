from datetime import timedelta

from tests.conftest import NOW

CLOSING = (NOW + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M")
FORM = {"code": "LIC-2026-001", "title": "Equipo de cómputo",
        "budget_crc": "10000000.00", "closing_at": CLOSING}


def post(client, **overrides):
    return client.post("/tenders", data={**FORM, **overrides})


def test_nav_link_and_empty_list(tclient):
    r = tclient.get("/tenders")
    assert r.status_code == 200
    assert 'href="/tenders"' in r.text
    assert "No hay licitaciones registradas." in r.text
    assert 'type="datetime-local"' in r.text


def test_create_redirects_and_shows_row(tclient):
    r = post(tclient)
    assert r.status_code == 303 and r.headers["location"] == "/tenders"
    page = tclient.get("/tenders").text
    assert "LIC-2026-001" in page
    assert "10 000 000,00" in page
    assert "Borrador" in page
    assert "Publicar" in page


def test_publish_and_close_flow(tclient):
    post(tclient)
    r = tclient.post("/tenders/1/publish")
    assert r.status_code == 303
    page = tclient.get("/tenders").text
    assert "Publicada" in page and "Cerrar" in page and "/tenders/1/edit" not in page
    r = tclient.post("/tenders/1/close")
    assert r.status_code == 303
    page = tclient.get("/tenders").text
    assert "Cerrada" in page and "Cerrar</button>" not in page
    assert "Publicar</button>" not in page


def test_create_error_rerenders_with_message_and_escaped_input(tclient):
    r = post(tclient, title="<script>alert(1)</script>")
    assert r.status_code == 422
    assert 'role="alert"' in r.text
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;" in r.text
    assert "Traceback" not in r.text


def test_create_error_keeps_other_inputs(tclient):
    r = post(tclient, budget_crc="abc")
    assert r.status_code == 422
    assert 'value="LIC-2026-001"' in r.text
    assert 'value="abc"' in r.text


def test_duplicate_code_409_page(tclient):
    post(tclient)
    r = post(tclient, code="lic-2026-001")
    assert r.status_code == 409
    assert "Ya existe una licitación con ese código." in r.text
    assert "Traceback" not in r.text


def test_past_closing_422(tclient):
    r = post(tclient, closing_at="2026-11-23T11:00")
    assert r.status_code == 422
    assert "fecha de cierre" in r.text


def test_blank_fields_422(tclient):
    r = tclient.post("/tenders")
    assert r.status_code == 422
    assert "obligatorio" in r.text


def test_publish_expired_shows_error(tclient, clock):
    post(tclient)
    clock.advance(days=3)
    r = tclient.post("/tenders/1/publish")
    assert r.status_code == 422
    assert "fecha de cierre" in r.text
    assert "Traceback" not in r.text


def test_close_draft_allowed_then_second_close_shows_409(tclient):
    """REQ-003: Borrador -> Cerrada is allowed (BUG-002); closing twice is rejected."""
    post(tclient)
    assert tclient.post("/tenders/1/close").status_code in (200, 303)
    r = tclient.post("/tenders/1/close")
    assert r.status_code == 409
    assert "Solo se puede cerrar" in r.text


def test_publish_twice_shows_409(tclient):
    post(tclient)
    tclient.post("/tenders/1/publish")
    r = tclient.post("/tenders/1/publish")
    assert r.status_code == 409
    assert "Traceback" not in r.text


def test_actions_on_missing_tender_404(tclient):
    assert tclient.post("/tenders/9/publish").status_code == 404
    assert tclient.post("/tenders/9/close").status_code == 404
    assert tclient.get("/tenders/9/edit").status_code == 404
    assert tclient.post("/tenders/9/edit", data=FORM).status_code == 404


def test_edit_form_prefilled_and_save(tclient):
    post(tclient)
    page = tclient.get("/tenders/1/edit")
    assert page.status_code == 200
    assert 'value="LIC-2026-001"' in page.text
    assert f'value="{CLOSING}"' in page.text
    assert 'value="10000000.00"' in page.text
    r = tclient.post("/tenders/1/edit", data={**FORM, "title": "Otro título"})
    assert r.status_code == 303
    assert "Otro título" in tclient.get("/tenders").text


def test_edit_error_rerenders_escaped(tclient):
    post(tclient)
    r = tclient.post("/tenders/1/edit", data={**FORM, "title": "<b>x</b>"})
    assert r.status_code == 422
    assert "&lt;b&gt;" in r.text and "<b>x</b>" not in r.text
    assert "Traceback" not in r.text


def test_edit_duplicate_409(tclient):
    post(tclient)
    post(tclient, code="B")
    r = tclient.post("/tenders/2/edit", data={**FORM, "code": "lic-2026-001"})
    assert r.status_code == 409


def test_edit_blocked_after_publish(tclient):
    post(tclient)
    tclient.post("/tenders/1/publish")
    page = tclient.get("/tenders/1/edit")
    assert page.status_code == 409
    assert "Solo se puede editar" in page.text
    assert "<form" not in page.text
    r = tclient.post("/tenders/1/edit", data={**FORM, "title": "Otro"})
    assert r.status_code == 409
    assert "Solo se puede editar" in r.text
    assert "Otro" not in tclient.get("/tenders").text


def test_stored_script_title_never_rendered_raw(tclient, db_url):
    # Even if bad data got into the DB, the template must escape it.
    from sqlalchemy.orm import sessionmaker
    from app.database import make_engine
    from app.models import Tender
    post(tclient)
    engine = make_engine(db_url)
    with sessionmaker(bind=engine)() as s:
        s.get(Tender, 1).title = "<script>alert(1)</script>"
        s.commit()
    engine.dispose()
    page = tclient.get("/tenders").text
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
