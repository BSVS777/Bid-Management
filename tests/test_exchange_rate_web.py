from datetime import timedelta

from sqlalchemy import create_engine, text

from tests.conftest import NOW

CLOSING = NOW + timedelta(hours=48)


def setup_bid(client, amount="9000000.00"):
    client.post("/tenders", data={
        "code": "LIC-2026-001", "title": "Equipo", "budget_crc": "10000000.00",
        "closing_at": CLOSING.strftime("%Y-%m-%dT%H:%M")})
    tid = client.get("/api/tenders").json()[0]["id"]
    client.post(f"/tenders/{tid}/publish")
    client.post("/suppliers", data={"name": "Tecnología Norte S.A."})
    sid = client.get("/api/suppliers").json()[0]["id"]
    client.post(f"/tenders/{tid}/bids",
                data={"supplier_id": str(sid), "amount_crc": amount})
    return tid


def test_nav_links_to_exchange_rate(tclient):
    assert 'href="/exchange-rate"' in tclient.get("/suppliers").text


def test_page_unset(tclient):
    r = tclient.get("/exchange-rate")
    assert r.status_code == 200
    assert "No hay un tipo de cambio configurado." in r.text
    assert "<form" in r.text


def test_set_rate_via_form_and_show_it(tclient):
    r = tclient.post("/exchange-rate", data={"crc_per_usd": "500.00"})
    assert r.status_code == 303 and r.headers["location"] == "/exchange-rate"
    page = tclient.get("/exchange-rate").text
    assert "500.00" in page and "2026-11-23 12:00:00" in page


def test_invalid_form_shows_error_and_stores_nothing(tclient):
    for bad in ("0", "-3", "abc", "1e3", ""):
        r = tclient.post("/exchange-rate", data={"crc_per_usd": bad})
        assert r.status_code == 422
        assert 'role="alert"' in r.text
    assert tclient.get("/api/exchange-rate").status_code == 404


def test_default_view_is_crc(tclient):
    tid = setup_bid(tclient)
    tclient.post("/exchange-rate", data={"crc_per_usd": "500.00"})
    page = tclient.get(f"/tenders/{tid}/bids").text
    assert "9 000 000,00 CRC" in page
    assert "Tipo de cambio usado" not in page


def test_usd_toggle_shows_converted_amounts_with_rate_and_date(tclient):
    tid = setup_bid(tclient)
    tclient.post("/exchange-rate", data={"crc_per_usd": "500.00"})
    page = tclient.get(f"/tenders/{tid}/bids?currency=USD").text
    assert "18 000,00 USD" in page      # best bid
    assert "20 000,00 USD" in page      # budget 10 000 000 / 500
    assert "500.00 CRC por USD" in page
    assert "2026-11-23 12:00:00" in page
    assert "9 000 000,00" not in page


def test_usd_without_rate_falls_back_to_crc_with_notice(tclient):
    tid = setup_bid(tclient)
    r = tclient.get(f"/tenders/{tid}/bids?currency=USD")
    assert r.status_code == 200
    assert "No hay un tipo de cambio configurado" in r.text
    assert "9 000 000,00 CRC" in r.text


def test_unknown_currency_value_defaults_to_crc(tclient):
    tid = setup_bid(tclient)
    tclient.post("/exchange-rate", data={"crc_per_usd": "500.00"})
    assert "9 000 000,00 CRC" in tclient.get(f"/tenders/{tid}/bids?currency=EUR").text


def test_toggle_does_not_change_database(tclient, db_url):
    tid = setup_bid(tclient)
    tclient.post("/exchange-rate", data={"crc_per_usd": "500.00"})
    eng = create_engine(db_url)

    def snapshot():
        with eng.connect() as c:
            return [c.execute(text(f"select * from {t} order by id")).all()
                    for t in ("tenders", "bids", "suppliers", "exchange_rates")]

    before = snapshot()
    tclient.get(f"/tenders/{tid}/bids?currency=USD")
    tclient.get(f"/tenders/{tid}/bids?currency=CRC")
    assert snapshot() == before
    eng.dispose()
