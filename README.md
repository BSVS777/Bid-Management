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

## Rutas de ofertas y evaluación
- Web: `GET/POST /tenders/{id}/bids` (formulario, lista y evaluación), `GET /suppliers/{id}/bids`
- API: `POST/GET /api/tenders/{id}/bids` (cuerpo `{"supplier_id","amount_crc"}`), `GET /api/suppliers/{id}/bids`, `GET /api/tenders/{id}/evaluation`
- Reglas: solo licitaciones `Publicada` y estrictamente antes del cierre (409 por estado o plazo); monto > 0 y <= presupuesto (422); una oferta por proveedor y licitación (409, UNIQUE en BD); licitación inexistente 404, `supplier_id` inexistente en el cuerpo 422.
- Evaluación: mejor oferta = monto menor (empate: la registrada primero); ahorro = (presupuesto - mejor) / presupuesto, clasificado con aritmética exacta (>= 10 % Conveniente, > 0 % Aceptable, 0 % Válida sin ahorro); aprobador por monto de la mejor oferta (< 1 000 000,00 Encargado de área; < 10 000 000,00 Gerencia; resto Junta Directiva). Rangos configurables en `app/approval.py` (intervalos semiabiertos en centavos) vía `create_app(approval_ranges=...)`.

## Reinicio de datos sintéticos
(pendiente)

## Estructura
- `app/` código fuente
- `tests/` pruebas automatizadas
- `04_Evidencias/` evidencias EV
- `05_IA/` prompts y salidas saneadas
