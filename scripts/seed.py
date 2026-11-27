"""Reset the database and load a reproducible SYNTHETIC dataset through the services.

Usage:  python -m scripts.seed [--db-url URL]
The target is --db-url, else env BID_DB_URL, else the application default.
WARNING: all existing data in the target database is deleted.
"""
import argparse
import os
import sys
from collections.abc import Callable
from datetime import datetime, timedelta

if __package__ in (None, ""):  # allow `python scripts/seed.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import database, models  # noqa: E402,F401
from app.clock import system_clock  # noqa: E402
from app.services import bids, exchange_rate, suppliers, tenders, users  # noqa: E402

RATE = "500.00"
# (code, title, budget, [(supplier name, offer)]); all values are synthetic.
MAIN_TENDER = ("LIC-2026-001", "Licitación sintética de referencia", "10000000.00",
               [("Tecnología Norte S.A.", "9000000.00"),
                ("Servicios del Valle", "9500000.00")])
BOUNDARY_TENDERS = [
    ("LIC-2026-F10", "Escenario frontera 10 % (sintético)", "1000000.00",
     [("Proveedor Frontera 10", "900000.00")]),
    ("LIC-2026-F05", "Escenario frontera 5 % (sintético)", "1000000.00",
     [("Proveedor Frontera 05", "950000.00")]),
    ("LIC-2026-F00", "Escenario frontera 0 % (sintético)", "1000000.00",
     [("Proveedor Frontera 00", "1000000.00")]),
]


def seed(db_url: str | None = None, clock: Callable[[], datetime] = system_clock,
         env=os.environ) -> dict:
    """Drop and recreate all tables, then load the dataset. Returns a summary."""
    engine = database.make_engine(db_url or database.DATABASE_URL)
    database.Base.metadata.drop_all(bind=engine)
    database.Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    now = clock()
    summary = {"user": None, "tenders": []}
    with factory() as db:
        username, password = env.get("BID_ADMIN_USER"), env.get("BID_ADMIN_PASSWORD")
        if username and password:
            users.create_user(db, now, username, password)
            summary["user"] = username
        exchange_rate.set_rate(db, now, RATE)
        supplier_ids: dict[str, int] = {}
        for code, title, budget, offers in [MAIN_TENDER, *BOUNDARY_TENDERS]:
            tender = tenders.create_tender(
                db, now, code, title, budget, now + timedelta(hours=48))
            tenders.publish_tender(db, now, tender.id)
            for name, amount in offers:
                if name not in supplier_ids:
                    supplier_ids[name] = suppliers.create_supplier(db, name).id
                bids.create_bid(db, now, tender.id, supplier_ids[name], amount)
            ev = bids.evaluate_tender(db, tender.id)
            summary["tenders"].append(
                (code, ev.bid_count, ev.saving_percent, ev.classification, ev.approver))
    engine.dispose()
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db-url", default=None, help="target database URL")
    args = parser.parse_args(argv)
    url = args.db_url or database.DATABASE_URL
    summary = seed(args.db_url)
    print(f"Base reiniciada: {url}")
    if summary["user"]:
        print(f"Usuario creado: {summary['user']}")
    else:
        print("Aviso: BID_ADMIN_USER/BID_ADMIN_PASSWORD no definidos; no se creó usuario.")
    print(f"Tipo de cambio: {RATE} CRC/USD")
    for code, count, saving, cls, approver in summary["tenders"]:
        print(f"  {code}: {count} oferta(s), ahorro {saving} %, {cls}, {approver}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
