# Bid-Management – Sistema de Gestión de Licitaciones

Práctica integradora ISW-622 (UTN). Stack: Python 3.12, FastAPI, SQLAlchemy, SQLite, pytest.

## Instalación
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución
```
uvicorn app.main:app --reload
```
Abrir http://127.0.0.1:8000 (redirige a `/suppliers`). Licitaciones en `/tenders`. Variable opcional `BID_DB_URL` (por defecto `sqlite:///./bid_management.db`).

## Pruebas
```
python -m pytest -q
python -m pytest --cov=app
```

## Rutas de licitaciones
- Web: `GET/POST /tenders`, `GET/POST /tenders/{id}/edit`, `POST /tenders/{id}/publish`, `POST /tenders/{id}/close`
- API: `POST/GET /api/tenders` (`?status=`), `GET/PUT /api/tenders/{id}`, `POST /api/tenders/{id}/publish`, `POST /api/tenders/{id}/close`
- Cuerpo JSON: `{"code","title","budget_crc","closing_at"}`. Presupuesto en CRC con hasta 2 decimales (sin notacion cientifica ni separador de miles); se devuelve como texto con 2 decimales. Estados: Borrador -> Publicada -> Cerrada.

## Reinicio de datos sintéticos
(pendiente)

## Estructura
- `app/` código fuente
- `tests/` pruebas automatizadas
- `04_Evidencias/` evidencias EV
- `05_IA/` prompts y salidas saneadas
