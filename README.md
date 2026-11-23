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
Abrir http://127.0.0.1:8000 (redirige a `/suppliers`). Variable opcional `BID_DB_URL` (por defecto `sqlite:///./bid_management.db`).

## Pruebas
```
python -m pytest -q
python -m pytest --cov=app
```

## Reinicio de datos sintéticos
(pendiente)

## Estructura
- `app/` código fuente
- `tests/` pruebas automatizadas
- `04_Evidencias/` evidencias EV
- `05_IA/` prompts y salidas saneadas
