from fastapi.testclient import TestClient

from app.main import create_app

P1 = "Tecnología Norte S.A."
P2 = "Servicios del Valle"


def post(client, name):
    return client.post("/api/suppliers", json={"name": name})


def test_create_p1_and_p2(client):
    r1, r2 = post(client, P1), post(client, P2)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json() == {"id": 1, "name": P1}
    assert r2.json()["name"] == P2


def test_list_and_get(client):
    post(client, P1)
    post(client, P2)
    assert [s["name"] for s in client.get("/api/suppliers").json()] == [P1, P2]
    assert client.get("/api/suppliers/2").json() == {"id": 2, "name": P2}


def test_edit(client):
    post(client, P2)
    r = client.put("/api/suppliers/1", json={"name": "  Servicios   del Valle Sur "})
    assert r.status_code == 200
    assert r.json()["name"] == "Servicios del Valle Sur"
    assert client.get("/api/suppliers/1").json()["name"] == "Servicios del Valle Sur"


def test_edit_own_name_case_variant_ok(client):
    post(client, P1)
    assert client.put("/api/suppliers/1", json={"name": P1.upper()}).status_code == 200


def test_duplicate_variants_409(client):
    post(client, P1)
    for variant in ["  TECNOLOGÍA   norte s.a. ", P1, P1.lower()]:
        r = post(client, variant)
        assert r.status_code == 409
        assert "detail" in r.json()
    assert len(client.get("/api/suppliers").json()) == 1


def test_edit_duplicate_409(client):
    post(client, P1)
    post(client, P2)
    assert client.put("/api/suppliers/2", json={"name": " tecnología norte S.A."}).status_code == 409


def test_invalid_character_422(client):
    r = post(client, "Proveedor; DROP TABLE")
    assert r.status_code == 422
    assert "detail" in r.json()


def test_script_string_422(client):
    assert post(client, "<script>alert(1)</script>").status_code == 422
    assert client.get("/api/suppliers").json() == []


def test_blank_and_too_long_422(client):
    assert post(client, "   ").status_code == 422
    assert post(client, "a" * 121).status_code == 422
    assert post(client, "a" * 120).status_code == 201


def test_missing_or_non_string_name_422(client):
    for body in [{}, {"name": 5}, {"name": None}, {"name": ["x"]}]:
        r = client.post("/api/suppliers", json=body)
        assert r.status_code == 422
        assert list(r.json()) == ["detail"]
    assert client.post("/api/suppliers", content="not json").status_code == 422


def test_unknown_id_404(client):
    assert client.get("/api/suppliers/99").status_code == 404
    assert client.put("/api/suppliers/99", json={"name": P1}).status_code == 404


def test_persistence_across_app_instances(db_url):
    with TestClient(create_app(db_url, auth_enabled=False)) as c1:
        post(c1, P1)
        post(c1, P2)
    with TestClient(create_app(db_url, auth_enabled=False)) as c2:
        assert [s["name"] for s in c2.get("/api/suppliers").json()] == [P1, P2]
        assert post(c2, P1.upper()).status_code == 409


def test_unhandled_error_is_generic(db_url):
    app = create_app(db_url, auth_enabled=False)

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret SELECT * FROM x /home/user/path")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/boom")
    assert r.status_code == 500
    assert r.json() == {"detail": "Error interno"}


def test_root_redirects_to_suppliers(client):
    r = client.get("/")
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/suppliers"


def test_web_create_flow(client):
    r = client.post("/suppliers", data={"name": P1})
    assert r.status_code == 303
    assert r.headers["location"] == "/suppliers"
    page = client.get("/suppliers")
    assert page.status_code == 200
    assert "Tecnología Norte S.A." in page.text
    assert 'href="/suppliers"' in page.text


def test_web_list_escapes_stored_name(db_url):
    from app.models import Supplier
    from sqlalchemy.orm import Session

    # Insert a hostile name directly in the DB, bypassing validation.
    with TestClient(create_app(db_url, auth_enabled=False)) as c:
        engine = c.app.state.engine
        with Session(engine) as s:
            s.add(Supplier(name="<script>alert(1)</script>", name_key="x"))
            s.commit()
        page = c.get("/suppliers")
    assert "<script>alert(1)</script>" not in page.text
    assert "&lt;script&gt;" in page.text


def test_web_errors_are_safe_and_escaped(client):
    r = client.post("/suppliers", data={"name": "<script>alert(1)</script>"})
    assert r.status_code == 422
    assert "Traceback" not in r.text
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;" in r.text
    client.post("/suppliers", data={"name": P1})
    dup = client.post("/suppliers", data={"name": "  TECNOLOGÍA   norte s.a. "})
    assert dup.status_code == 409
    assert "Ya existe" in dup.text and "Traceback" not in dup.text


def test_web_edit_flow(client):
    client.post("/suppliers", data={"name": P1})
    client.post("/suppliers", data={"name": P2})
    assert P1 in client.get("/suppliers/1/edit").text
    ok = client.post("/suppliers/1/edit", data={"name": "Tecnología Sur"})
    assert ok.status_code == 303
    assert client.get("/api/suppliers/1").json()["name"] == "Tecnología Sur"
    dup = client.post("/suppliers/1/edit", data={"name": "servicios DEL valle"})
    assert dup.status_code == 409
    bad = client.post("/suppliers/1/edit", data={"name": "a@b"})
    assert bad.status_code == 422 and "Traceback" not in bad.text
    assert client.get("/suppliers/99/edit").status_code == 404
