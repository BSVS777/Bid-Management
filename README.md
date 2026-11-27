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
- Cuerpo JSON: `{"code","title","budget_crc","closing_at"}`. Presupuesto en CRC con hasta 2 decimales (sin notacion cientifica ni separador de miles); se devuelve como texto con 2 decimales. Estados: Borrador -> Publicada/Cerrada y Publicada -> Cerrada (una Cerrada no se reabre).

## Rutas de ofertas y evaluación
- Web: `GET/POST /tenders/{id}/bids` (formulario, lista y evaluación), `GET /suppliers/{id}/bids`
- API: `POST/GET /api/tenders/{id}/bids` (cuerpo `{"supplier_id","amount_crc"}`), `GET /api/suppliers/{id}/bids`, `GET /api/tenders/{id}/evaluation`
- Reglas: solo licitaciones `Publicada` y estrictamente antes del cierre (409 por estado o plazo); monto > 0 y <= presupuesto (422); una oferta por proveedor y licitación (409, UNIQUE en BD); licitación inexistente 404, `supplier_id` inexistente en el cuerpo 422.
- Evaluación: mejor oferta = monto menor (empate: la registrada primero); ahorro = (presupuesto - mejor) / presupuesto, clasificado con aritmética exacta (>= 10 % Conveniente, > 0 % Aceptable, 0 % Válida sin ahorro); aprobador por monto de la mejor oferta (< 1 000 000,00 Encargado de Área; < 10 000 000,00 Gerencia; resto Junta Directiva). Rangos configurables en `app/approval.py` (intervalos semiabiertos en centavos) vía `create_app(approval_ranges=...)`.

## Tipo de cambio
- Web: `GET/POST /exchange-rate` (formulario y tipo vigente); en `/tenders/{id}/bids?currency=USD` se muestran los montos en USD con el tipo y la fecha usados (por defecto CRC, sin JavaScript).
- API: `POST /api/exchange-rate` (cuerpo `{"crc_per_usd": "500.00"}`, 201), `GET /api/exchange-rate` (404 si no hay tipo configurado), `GET /api/tenders/{id}/evaluation/usd` (409 si no hay tipo configurado).
- Reglas: CRC por USD > 0, hasta 2 decimales, máximo 100000.00, sin notación científica (422 si es inválido). Se conserva el historial; el último registro es el vigente. Solo se guarda CRC: USD = CRC / tipo, redondeo half-up a 2 decimales, calculado al mostrar (ej. 9 000 000,00 CRC a 500.00 = 18 000,00 USD).

## Autenticación
- Usuario y contraseña; solo biblioteca estándar (contraseñas con `scrypt` + sal aleatoria, tokens firmados con HMAC-SHA256, vigencia 8 horas).
- Primer usuario: definir antes de iniciar `BID_ADMIN_USER` y `BID_ADMIN_PASSWORD` (usuario 3-50 caracteres `A-Za-z0-9._-`, contraseña 8-128). Se crea al arrancar si no existe. Sin esas variables, los usuarios se crean con `app.services.users.create_user(...)` o desde `/users` o `POST /api/users` (ya autenticado).
- `BID_SECRET_KEY`: secreto de firma de tokens. Si no se define se genera uno aleatorio por proceso (las sesiones no sobreviven a un reinicio). En producción definirlo y servir por HTTPS.
- Web: `/login` (formulario) y `/logout`; la sesión va en una cookie `HttpOnly` `SameSite=Lax`. Sin sesión, las páginas redirigen (303) a `/login`.
- API: `POST /api/auth/login` con `{"username","password"}` devuelve `{"token","token_type":"Bearer","expires_in"}`; enviar `Authorization: Bearer <token>`. Sin token válido: 401 `{"detail": "No autenticado"}`. Credenciales erróneas: 401 genérico `Credenciales inválidas` (sin distinguir usuario inexistente de contraseña errónea).
- Abiertas: `/login`, `/logout`, `/api/auth/login`, `/docs`, `/redoc`, `/openapi.json`. El resto exige sesión. Un usuario eliminado pierde acceso de inmediato.
- Las pruebas usan `create_app(..., auth_enabled=False)` salvo las de `tests/test_auth_*.py`.

## CRUD completo
| Tabla | API | Web |
|---|---|---|
| suppliers | `POST/GET /api/suppliers`, `GET/PUT/DELETE /api/suppliers/{id}` (DELETE 409 si tiene ofertas) | `/suppliers`, `/suppliers/{id}/edit`, `POST /suppliers/{id}/delete` |
| tenders | `POST/GET /api/tenders`, `GET/PUT/DELETE /api/tenders/{id}` (DELETE solo Borrador sin ofertas, si no 409) | `/tenders`, `/tenders/{id}/edit`, `POST /tenders/{id}/delete` |
| bids | `POST/GET /api/tenders/{id}/bids`, `GET/PUT/DELETE /api/bids/{id}` (PUT/DELETE solo con licitación Publicada y antes del cierre, si no 409; PUT revalida el monto: > 0 y <= presupuesto) | `/tenders/{id}/bids`, `POST /tenders/{tid}/bids/{id}/delete` |
| exchange_rates | `POST/GET /api/exchange-rate` (vigente), `GET /api/exchange-rate/history`, `GET/DELETE /api/exchange-rate/{id}` | `/exchange-rate` (historial con eliminar) |
| users | `POST/GET /api/users`, `GET/PUT/DELETE /api/users/{id}` (PUT acepta `username` y/o `password`; nunca se devuelve la contraseña ni su hash; no se puede eliminar el propio usuario ni el último) | `/users`, `POST /users/{id}/delete` |

Códigos: 404 id inexistente, 422 entrada inválida (incluye id no numérico), 409 conflicto de reglas; DELETE exitoso responde 204 (web: 303). Los botones web de eliminar piden confirmación.

## Puesta en marcha y datos sintéticos
Requiere Python 3.12. Los valores `<...>` son placeholders: elija los suyos y no los suba al repositorio (`.env` está en `.gitignore`; las variables son `BID_ADMIN_USER`, `BID_ADMIN_PASSWORD`, `BID_SECRET_KEY` y opcional `BID_DB_URL`).

**1. Entorno e instalación**

PowerShell:
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:BID_ADMIN_USER = "<usuario>"
$env:BID_ADMIN_PASSWORD = "<clave-de-8-o-mas-caracteres>"
$env:BID_SECRET_KEY = "<secreto-largo-aleatorio>"
```
bash:
```
python -m venv .venv
source .venv/Scripts/activate   # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
export BID_ADMIN_USER="<usuario>" BID_ADMIN_PASSWORD="<clave-de-8-o-mas-caracteres>" BID_SECRET_KEY="<secreto-largo-aleatorio>"
```

**2. Cargar datos sintéticos (reinicia la base)**
```
python -m scripts.seed            # usa BID_DB_URL o sqlite:///./bid_management.db
python -m scripts.seed --db-url sqlite:///./otra.db
```
**Borra todo el contenido** de la base destino y la recrea con datos ficticios, usando los servicios (se aplican las reglas de negocio). Es idempotente: ejecutarlo dos veces deja los mismos datos. Sin `BID_ADMIN_USER`/`BID_ADMIN_PASSWORD` avisa y no crea usuario.

Datos cargados: tipo de cambio 500.00 CRC/USD; proveedores P1 `Tecnología Norte S.A.` y P2 `Servicios del Valle`; licitación `LIC-2026-001` (presupuesto 10 000 000,00, cierre en 48 h, Publicada) con ofertas P1 9 000 000,00 y P2 9 500 000,00. Resultado esperado: mejor oferta P1, ahorro 10 %, Conveniente, aprobador Gerencia, P1 = USD 18 000,00. Escenarios frontera (presupuesto 1 000 000,00, un proveedor cada uno): `LIC-2026-F10` oferta 900 000,00 -> 10 % Conveniente; `LIC-2026-F05` 950 000,00 -> 5 % Aceptable; `LIC-2026-F00` 1 000 000,00 -> 0 % Válida sin ahorro.

**3. Iniciar el servidor e ingresar**
```
uvicorn app.main:app --reload
```
Abrir http://127.0.0.1:8000/login e ingresar con `BID_ADMIN_USER`/`BID_ADMIN_PASSWORD` (el servidor debe iniciarse con las mismas variables y la misma `BID_DB_URL` que el seed). Con `BID_SECRET_KEY` fijo las sesiones sobreviven a un reinicio.

**4. Pruebas**
```
python -m pytest -q
python -m pytest --cov=app --cov-report=term-missing
```
(La cobertura requiere `pytest-cov`.) Las pruebas usan bases SQLite temporales: no tocan `bid_management.db`.

**5. Base de datos y persistencia**
- SQLite en `bid_management.db` (raíz del proyecto), o la indicada en `BID_DB_URL`. Las tablas se crean al iniciar.
- Reinicio manual: detener el servidor, borrar `bid_management.db` y volver a ejecutar el seed.
- Verificar persistencia tras reinicio: cargar el seed, iniciar el servidor, anotar el total de ofertas de `/tenders/1/bids`, detener (Ctrl+C), iniciar de nuevo y comprobar que los datos siguen iguales (con `BID_SECRET_KEY` fijo no hace falta volver a ingresar).

## Requisitos y trazabilidad
La matriz de requisitos, el plan de pruebas y la trazabilidad requisito -> prueba -> evidencia están en [`docs/qa/`](docs/qa/) (ver `docs/qa/plan-parte-a.md`); las evidencias en `04_Evidencias/`.

## Estructura
- `app/` código fuente
- `scripts/` seed de datos sintéticos
- `tests/` pruebas automatizadas
- `docs/qa/` requisitos y trazabilidad
- `04_Evidencias/` evidencias EV
- `05_IA/` prompts y salidas saneadas
