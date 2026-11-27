# A10. Casos de prueba CP-001 a CP-020

Sistema de Gestión de Licitaciones (Bid-Management) · ISW-622 Práctica Integradora · Wonder Team

> Los resultados esperados proceden de las reglas REQ-001 a REQ-014 del docente (ver `plan-parte-a.md`, A3), no de la salida de la IA o de la aplicación. Los datos son sintéticos. Reloj fijo de las pruebas automatizadas: 2026-11-23 12:00:00 (cierre = ahora + 48 h). Los resultados reales de cada CP están en [`trazabilidad.md`](trazabilidad.md) y en `04_Evidencias/RUN_LOG.md`.

## Resumen

| Dato | Valor |
|---|---|
| CP diseñados | 20 |
| CP con prueba pytest automatizada | 18 (todos con ejecución real PASS) |
| CP con script/manual | 2: CP-017 (usabilidad, PENDIENTE de ejecución humana) y CP-018 (rendimiento, script `scripts/load_test.py`, ejecutado: PASS) |
| Por nivel | Unitaria: 7; Integración/API: 3; Funcional: 4; Seguridad: 2; Usabilidad: 1; Rendimiento: 1; Borde/negativo: 2 |
| Tipos | positivos, negativos y de valores límite (columna Tipo) |

## Tabla de casos

| CP | REQ | Nivel | Tipo | Prioridad | Prueba automatizada (node id) | RUN | Resultado real |
|---|---|---|---|---|---|---|---|
| CP-001 | REQ-001 | Unitaria | Negativo | Alta | `tests/qa/test_cp_unit.py::test_cp001_supplier_duplicate_by_normalization` | RUN-001 | PASS |
| CP-002 | REQ-002 | Unitaria | Límite | Alta | `tests/qa/test_cp_unit.py::test_cp002_tender_field_rules` | RUN-002 | PASS |
| CP-003 | REQ-003 | Unitaria | Positivo y negativo | Alta | `tests/qa/test_cp_unit.py::test_cp003_state_transitions` | RUN-003 | PASS |
| CP-004 | REQ-005 | Unitaria | Límite | Alta | `tests/qa/test_cp_unit.py::test_cp004_bid_amount_limits` | RUN-004 | PASS |
| CP-005 | REQ-007 | Unitaria | Positivo y límite (empate) | Alta | `tests/qa/test_cp_unit.py::test_cp005_best_bid_rules` | RUN-005 | PASS |
| CP-006 | REQ-008 | Unitaria | Límite | Alta | `tests/qa/test_cp_unit.py::test_cp006_saving_classification` | RUN-006 | PASS |
| CP-007 | REQ-009 | Unitaria | Límite | Alta | `tests/qa/test_cp_unit.py::test_cp007_approver_boundaries` | RUN-007 | PASS |
| CP-008 | REQ-006 | Integración/API | Negativo | Alta | `tests/qa/test_cp_api.py::test_cp008_duplicate_bid_rejected_by_api_and_db` | RUN-008 | PASS |
| CP-009 | REQ-011 | Integración/API | Positivo y negativo | Alta | `tests/qa/test_cp_api.py::test_cp009_persistence_after_restart_and_api_validation` | RUN-009 | PASS |
| CP-010 | REQ-010 | Integración/API | Positivo | Media | `tests/qa/test_cp_api.py::test_cp010_usd_view_does_not_change_stored_crc` | RUN-010 | PASS |
| CP-011 | REQ-001 | Funcional | Positivo y negativo | Alta | `tests/qa/test_cp_functional.py::test_cp011_register_supplier_and_reject_duplicate` | RUN-011 | PASS |
| CP-012 | REQ-002, REQ-003 | Funcional | Positivo | Alta | `tests/qa/test_cp_functional.py::test_cp012_create_and_publish_tender` | RUN-012 | PASS |
| CP-013 | REQ-007 | Funcional | Positivo | Alta | `tests/qa/test_cp_functional.py::test_cp013_bids_and_evaluation_page` | RUN-013 | PASS |
| CP-014 | REQ-004 | Funcional | Límite | Alta | `tests/qa/test_cp_functional.py::test_cp014_closing_instant_boundary` | RUN-014 | PASS |
| CP-015 | REQ-012 | Seguridad | Negativo | Alta | `tests/qa/test_cp_security.py::test_cp015_supplier_name_character_whitelist` | RUN-015 | PASS |
| CP-016 | REQ-012 | Seguridad | Negativo | Alta | `tests/qa/test_cp_security.py::test_cp016_no_script_execution_and_hidden_internal_errors` | RUN-016 | PASS |
| CP-017 | REQ-013 | Usabilidad | Positivo | Media | manual – protocolo `usabilidad-protocolo.md` | — | PENDIENTE (no ejecutado) |
| CP-018 | REQ-014 | Rendimiento | Positivo | Media | manual – script `scripts/load_test.py` | RUN-019 | PASS |
| CP-019 | REQ-004 | Borde/negativo | Negativo | Alta | `tests/qa/test_cp_functional.py::test_cp019_bid_on_draft_and_closed_tender_rejected` | RUN-017 | PASS |
| CP-020 | REQ-005 | Borde/negativo | Límite | Alta | `tests/qa/test_cp_api.py::test_cp020_bid_amount_edges_rejected_by_api` | RUN-018 | PASS |

## Fichas detalladas

### CP-001 · REQ-001 · Unitaria · Negativo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-001 |
| Nivel / tipo | Unitaria / Negativo |
| Prioridad | Alta |
| Entrada exacta | Alta «Tecnología Norte S.A.»; luego intentos de alta con «  Tecnología Norte S.A.  », «Tecnología   Norte   S.A.», «TECNOLOGÍA NORTE S.A.», «tecnología norte s.a.», «  tecnología \t NORTE   s.a. »; luego alta «Servicios del Valle». |
| Precondiciones | BD de prueba vacía (sesión nueva). |
| Pasos | 1) Crear P1. 2) Intentar crear cada variante. 3) Crear P2. 4) Listar proveedores. |
| Resultado esperado (oráculo del enunciado) | P1 se crea; las 5 variantes se rechazan como duplicado (DuplicateSupplierError); P2 se crea; el listado es [P1, P2]. |
| Prueba automatizada | `tests/qa/test_cp_unit.py::test_cp001_supplier_duplicate_by_normalization` |
| Ejecución real | RUN-001 · PASS |

### CP-002 · REQ-002 · Unitaria · Límite

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-002 |
| Nivel / tipo | Unitaria / Límite |
| Prioridad | Alta |
| Entrada exacta | Licitación LIC-2026-001 / «Equipo» / 10000000.00 / cierre ahora+48 h (válida); códigos «lic-2026-001», «  LIC-2026-001  », «Lic-2026-001»; títulos «» y «   »; presupuestos «0», «-1», «0.00», «-0.01»; presupuesto «0.01» (válido); cierres ahora−1 h, ahora−1 s y ahora; cierre ahora+1 s (válido). |
| Precondiciones | BD vacía; reloj fijo de pruebas 2026-11-23 12:00:00 (cierre = ahora + 48 h). |
| Pasos | 1) Crear la licitación válida. 2) Repetir con cada código equivalente. 3) Crear con cada título y presupuesto inválido. 4) Crear con presupuesto 0.01. 5) Crear con cada cierre no futuro. 6) Crear con cierre ahora+1 s. |
| Resultado esperado (oráculo del enunciado) | La válida queda en Borrador; códigos equivalentes → DuplicateTenderError; título vacío, presupuesto ≤ 0 y cierre no futuro → InvalidTenderError; 0.01 se guarda como 1 centavo; cierre ahora+1 s se acepta (Borrador). |
| Prueba automatizada | `tests/qa/test_cp_unit.py::test_cp002_tender_field_rules` |
| Ejecución real | RUN-002 · PASS |

### CP-003 · REQ-003 · Unitaria · Positivo y negativo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-003 |
| Nivel / tipo | Unitaria / Positivo y negativo |
| Prioridad | Alta |
| Entrada exacta | Licitación creada en Borrador y cerrada directamente; otra licitación Borrador→Publicada→Cerrada; después publicar de nuevo, editar y cerrar de nuevo la ya Publicada/Cerrada. |
| Precondiciones | BD vacía; reloj fijo de pruebas 2026-11-23 12:00:00 (cierre = ahora + 48 h). |
| Pasos | 1) Crear L-D y cerrarla (Borrador→Cerrada). 2) Crear L-1 y publicarla. 3) Intentar publicar de nuevo y editar L-1 Publicada. 4) Cerrar L-1. 5) Intentar publicar, cerrar y editar L-1 Cerrada. |
| Resultado esperado (oráculo del enunciado) | Borrador→Cerrada permitido; Borrador→Publicada permitido; Publicada→Cerrada permitido; volver de Publicada a Borrador y reabrir una Cerrada se rechazan (InvalidTransitionError) y el estado no cambia. |
| Prueba automatizada | `tests/qa/test_cp_unit.py::test_cp003_state_transitions` |
| Ejecución real | RUN-003 · PASS |

### CP-004 · REQ-005 · Unitaria · Límite

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-005 |
| Nivel / tipo | Unitaria / Límite |
| Prioridad | Alta |
| Entrada exacta | Presupuesto 10000000.00 (Publicada); montos «0», «0.00», «-0.01», «-1», «10000000.01» (rechazar); «0.01» y «10000000.00» (aceptar); actualizar la oferta de 0.01 a «10000000.01» (rechazar). |
| Precondiciones | BD con P1, P2 y licitación Publicada de CRC 10 000 000,00. |
| Pasos | 1) Ofertar P1 con cada monto inválido. 2) Verificar que no hay ofertas. 3) Ofertar P1 con 0.01. 4) Ofertar P2 con 10000000.00. 5) Actualizar la oferta de P1 a 10000000.01. |
| Resultado esperado (oráculo del enunciado) | Montos ≤ 0 o > presupuesto → InvalidBidError y sin ofertas guardadas; 0.01 (1 centavo) y monto igual al presupuesto se aceptan; la actualización por encima del presupuesto se rechaza. |
| Prueba automatizada | `tests/qa/test_cp_unit.py::test_cp004_bid_amount_limits` |
| Ejecución real | RUN-004 · PASS |

### CP-005 · REQ-007 · Unitaria · Positivo y límite (empate)

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-007 |
| Nivel / tipo | Unitaria / Positivo y límite (empate) |
| Prioridad | Alta |
| Entrada exacta | L-EMPTY sin ofertas; L-LOW: P1=9000000.00, P2=9500000.00; L-LAST: P1=9500000.00, P2=9000000.00 (registrada después); empates a 9000000.00 en ambos órdenes de registro (P2 primero y P1 primero). |
| Precondiciones | BD con P1 y P2; licitaciones Publicadas; ofertas con 1 minuto de diferencia en el reloj fijo. |
| Pasos | 1) Evaluar licitación sin ofertas. 2) Evaluar L-LOW. 3) Evaluar L-LAST. 4) Evaluar los dos empates. |
| Resultado esperado (oráculo del enunciado) | Sin ofertas: mejor oferta vacía y mensaje «Sin ofertas válidas»; gana la menor oferta aunque se registre última; en empate gana la oferta registrada primero. |
| Prueba automatizada | `tests/qa/test_cp_unit.py::test_cp005_best_bid_rules` |
| Ejecución real | RUN-005 · PASS |

### CP-006 · REQ-008 · Unitaria · Límite

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-008 |
| Nivel / tipo | Unitaria / Límite |
| Prioridad | Alta |
| Entrada exacta | Presupuesto 1000000.00 con una oferta de P1 por licitación: 900000.00; 950000.00; 1000000.00; 900100.00. |
| Precondiciones | BD con P1; una licitación Publicada por escenario (LIC-S0..S3). |
| Pasos | 1) Registrar la oferta. 2) Evaluar la licitación y leer ahorro y clasificación. |
| Resultado esperado (oráculo del enunciado) | 900000.00 → 10.00 % Conveniente; 950000.00 → 5.00 % Aceptable; 1000000.00 → 0.00 % «Válida sin ahorro»; 900100.00 → 9.99 % Aceptable. |
| Prueba automatizada | `tests/qa/test_cp_unit.py::test_cp006_saving_classification` |
| Ejecución real | RUN-006 · PASS |

### CP-007 · REQ-009 · Unitaria · Límite

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-009 |
| Nivel / tipo | Unitaria / Límite |
| Prioridad | Alta |
| Entrada exacta | Presupuesto 20000000.00 con una oferta de P1 por licitación: 0.01; 999999.99; 1000000.00; 9999999.99; 10000000.00. |
| Precondiciones | BD con P1; una licitación Publicada por escenario (LIC-A0..A4). |
| Pasos | 1) Registrar la oferta. 2) Evaluar y leer el aprobador (texto exacto). |
| Resultado esperado (oráculo del enunciado) | 0.01 y 999999.99 → «Encargado de Área»; 1000000.00 y 9999999.99 → «Gerencia»; 10000000.00 → «Junta Directiva». |
| Prueba automatizada | `tests/qa/test_cp_unit.py::test_cp007_approver_boundaries` |
| Ejecución real | RUN-007 · PASS |

### CP-008 · REQ-006 · Integración/API · Negativo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-006 |
| Nivel / tipo | Integración/API / Negativo |
| Prioridad | Alta |
| Entrada exacta | POST /api/tenders/{id}/bids con P1 = 9000000.00 y luego P1 = 8500000.00 en la misma licitación; inserción directa en BD de otra fila Bid (tender_id, supplier_id, amount_cents=1) para el mismo par. |
| Precondiciones | App con reloj fijo; licitación L1 Publicada (CRC 10 000 000,00); P1 creado por API. |
| Pasos | 1) Ofertar 9000000.00 (espera 201). 2) Ofertar de nuevo con P1. 3) Listar ofertas. 4) Insertar la fila duplicada vía sesión de BD y hacer commit. |
| Resultado esperado (oráculo del enunciado) | Primera oferta 201; la segunda 409 y sigue habiendo 1 oferta; la inserción directa viola la restricción UNIQUE (IntegrityError) y sigue habiendo 1 oferta. |
| Prueba automatizada | `tests/qa/test_cp_api.py::test_cp008_duplicate_bid_rejected_by_api_and_db` |
| Ejecución real | RUN-008 · PASS |

### CP-009 · REQ-011 · Integración/API · Positivo y negativo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-011 |
| Nivel / tipo | Integración/API / Positivo y negativo |
| Prioridad | Alta |
| Entrada exacta | Con la app A: alta de P1, L1 (Publicada) y oferta 9000000.00. Se crea una instancia nueva de la app sobre el mismo archivo SQLite (reinicio). Entradas inválidas: POST /api/suppliers {"name": "   "}; oferta 10000000.01; los mismos valores por el formulario web. |
| Precondiciones | Archivo SQLite temporal; reloj fijo; auth deshabilitada en pruebas. |
| Pasos | 1) Crear datos y cerrar la app. 2) Abrir una app nueva sobre el mismo archivo. 3) Consultar proveedores, licitaciones y ofertas por API. 4) Enviar las entradas inválidas por API y por UI. |
| Resultado esperado (oráculo del enunciado) | Tras el reinicio persisten P1, LIC-2026-001 y la oferta (P1, 9000000.00); API y UI responden 422 a ambas entradas inválidas con mensaje controlado («obligatorio», «no puede superar el presupuesto») sin Traceback ni SQLAlchemy; sigue habiendo 1 oferta. |
| Prueba automatizada | `tests/qa/test_cp_api.py::test_cp009_persistence_after_restart_and_api_validation` |
| Ejecución real | RUN-009 · PASS |

### CP-010 · REQ-010 · Integración/API · Positivo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-010 |
| Nivel / tipo | Integración/API / Positivo |
| Prioridad | Media |
| Entrada exacta | Oferta de P1 = 9000000.00 en L1 (presupuesto 10000000.00); POST /api/exchange-rate {"crc_per_usd": "500.00"}; GET /api/tenders/{id}/evaluation/usd; GET /tenders/{id}/bids?currency=USD y sin currency. |
| Precondiciones | App con reloj fijo; L1 Publicada; oferta registrada; BD sin tipo de cambio previo. |
| Pasos | 1) Verificar el monto almacenado (centavos). 2) Configurar tasa 500.00 (201). 3) Consultar evaluación USD. 4) Abrir la vista USD y la vista CRC. 5) Verificar de nuevo el monto almacenado. |
| Resultado esperado (oráculo del enunciado) | USD = 9 000 000,00 / 500,00 = 18 000,00 (presupuesto USD 20 000,00); se muestran tasa 500.00 y fecha; el monto almacenado sigue siendo 900 000 000 centavos antes y después; la vista CRC conserva 9 000 000,00. |
| Prueba automatizada | `tests/qa/test_cp_api.py::test_cp010_usd_view_does_not_change_stored_crc` |
| Ejecución real | RUN-010 · PASS |

### CP-011 · REQ-001 · Funcional · Positivo y negativo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-001 |
| Nivel / tipo | Funcional / Positivo y negativo |
| Prioridad | Alta |
| Entrada exacta | Formulario web: alta «Tecnología Norte S.A.»; luego alta «  TECNOLOGÍA   norte   s.a.  ». |
| Precondiciones | App web con reloj fijo, BD vacía. |
| Pasos | 1) POST /suppliers con P1. 2) Abrir /suppliers. 3) POST /suppliers con la variante. 4) Revisar mensaje y listado. |
| Resultado esperado (oráculo del enunciado) | P1 aparece una sola vez en el listado; la variante responde 409 con «Ya existe un proveedor con ese nombre.» en un elemento role="alert"; la API lista 1 proveedor. |
| Prueba automatizada | `tests/qa/test_cp_functional.py::test_cp011_register_supplier_and_reject_duplicate` |
| Ejecución real | RUN-011 · PASS |

### CP-012 · REQ-002, REQ-003 · Funcional · Positivo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-002, REQ-003 |
| Nivel / tipo | Funcional / Positivo |
| Prioridad | Alta |
| Entrada exacta | Formulario web: código LIC-2026-001, título «Equipo de cómputo», presupuesto 10000000.00, cierre ahora+48 h; después publicar. |
| Precondiciones | App web con reloj fijo, BD vacía. |
| Pasos | 1) POST /tenders con los datos. 2) Revisar el listado. 3) POST /tenders/{id}/publish. 4) Revisar el listado y la API. |
| Resultado esperado (oráculo del enunciado) | Tras crear: LIC-2026-001, estado Borrador y «10 000 000,00»; tras publicar: Publicada (sin Borrador) y la API devuelve status Publicada. |
| Prueba automatizada | `tests/qa/test_cp_functional.py::test_cp012_create_and_publish_tender` |
| Ejecución real | RUN-012 · PASS |

### CP-013 · REQ-007 · Funcional · Positivo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-007 |
| Nivel / tipo | Funcional / Positivo |
| Prioridad | Alta |
| Entrada exacta | P1 y P2 dados de alta; L1 Publicada (10000000.00); ofertas P1 = 9000000.00 y P2 = 9500000.00 por el formulario; abrir /tenders/{id}/bids. |
| Precondiciones | App web con reloj fijo, BD vacía. |
| Pasos | 1) Crear P1, P2 y L1 publicada. 2) Registrar ambas ofertas. 3) Abrir la página de ofertas y evaluación. |
| Resultado esperado (oráculo del enunciado) | Se listan 9 000 000,00 y 9 500 000,00; «Mejor oferta: Tecnología Norte S.A.»; «Ahorro: 10.00%»; «Clasificación: Conveniente»; «Aprobador: Gerencia»; no aparece «Sin ofertas válidas». |
| Prueba automatizada | `tests/qa/test_cp_functional.py::test_cp013_bids_and_evaluation_page` |
| Ejecución real | RUN-013 · PASS |

### CP-014 · REQ-004 · Funcional · Límite

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-004 |
| Nivel / tipo | Funcional / Límite |
| Prioridad | Alta |
| Entrada exacta | L1 Publicada con cierre = C. Oferta de P1 = 9000000.00 con reloj C−1 s; oferta de P2 = 9000000.00 con reloj C; oferta de P3 = 9000000.00 con reloj C+1 s. |
| Precondiciones | App web con reloj fijo manipulable; P1, P2 y P3 dados de alta; L1 Publicada. |
| Pasos | 1) Fijar reloj C−1 s y ofertar con P1. 2) Fijar reloj C y ofertar con P2. 3) Fijar reloj C+1 s y ofertar con P3. 4) Listar ofertas. |
| Resultado esperado (oráculo del enunciado) | C−1 s: aceptada (200); exactamente en C: 409 con «ya cerró»; C+1 s: 409 con «ya cerró»; la lista contiene solo la oferta de P1. |
| Prueba automatizada | `tests/qa/test_cp_functional.py::test_cp014_closing_instant_boundary` |
| Ejecución real | RUN-014 · PASS |

### CP-015 · REQ-012 · Seguridad · Negativo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-012 |
| Nivel / tipo | Seguridad / Negativo |
| Prioridad | Alta |
| Entrada exacta | Nombres inválidos por API y por web: «Proveedor@Norte», «A#B», «X;DROP TABLE», «Y$», «<b>», «Proveedor 😀», «A/B», «A'B», «A"B», «A&B», «A-B», «A_B». Nombres válidos: «Tecnología Norte S.A.», «Servicios del Valle», «Ñandú (Costa Rica), S.A.», «José Pérez 123.», «Compañía, Ltda (CR)». |
| Precondiciones | App web con reloj fijo, BD vacía. |
| Pasos | 1) Enviar cada nombre inválido a POST /api/suppliers y a POST /suppliers. 2) Verificar que no se guardó nada. 3) Enviar los nombres válidos alternando API y web. 4) Listar. |
| Resultado esperado (oráculo del enunciado) | Cada nombre inválido → 422 con el mensaje «letras, números, espacios, punto, coma y paréntesis» (API) y alerta «El nombre solo puede contener…» (web); no se guarda ninguno; los 5 nombres válidos se aceptan y se listan en orden. |
| Prueba automatizada | `tests/qa/test_cp_security.py::test_cp015_supplier_name_character_whitelist` |
| Ejecución real | RUN-015 · PASS |

### CP-016 · REQ-012 · Seguridad · Negativo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-012 |
| Nivel / tipo | Seguridad / Negativo |
| Prioridad | Alta |
| Entrada exacta | Cadena «<script>alert(1)</script>» en nombre de proveedor (web y API), título y código de licitación, monto y supplier_id de oferta y parámetro currency; después un fallo interno forzado en el servicio de proveedores (RuntimeError con texto «secret-db-path C:\x»). |
| Precondiciones | App web con reloj fijo y raise_server_exceptions=False; datos mínimos creados (Proveedor Uno, LIC-1 Publicada). |
| Pasos | 1) Enviar cada entrada con script. 2) Revisar que ninguna respuesta sea 5xx ni contenga «<script». 3) Simular el fallo interno con monkeypatch. 4) GET /api/suppliers y GET /suppliers. |
| Resultado esperado (oráculo del enunciado) | Sin respuestas 5xx por la entrada; ningún cuerpo contiene el script sin escapar (el nombre se muestra escapado como «&lt;script&gt;»); el fallo interno devuelve 500 con {"detail": "Error interno"} sin traceback, tipo de excepción, rutas, «.py» ni «sqlalchemy». |
| Prueba automatizada | `tests/qa/test_cp_security.py::test_cp016_no_script_execution_and_hidden_internal_errors` |
| Ejecución real | RUN-016 · PASS |

### CP-017 · REQ-013 · Usabilidad · Positivo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-013 |
| Nivel / tipo | Usabilidad / Positivo |
| Prioridad | Media |
| Entrada exacta | 4 tareas por participante (registrar proveedor; crear y publicar licitación; registrar oferta; leer mejor oferta y aprobador), según docs/qa/usabilidad-protocolo.md. |
| Precondiciones | 2 personas ajenas al equipo; app local con datos sintéticos reiniciados; moderador que no ayuda. |
| Pasos | 1) Dar la consigna escrita de cada tarea. 2) Observar sin ayudar. 3) Registrar tiempo, éxito (S/N) y obstáculos. |
| Resultado esperado (oráculo del enunciado) | Cada participante completa al menos 3 de las 4 tareas sin ayuda. ESTADO: NO EJECUTADO (PENDIENTE; requiere 2 participantes reales). |
| Prueba automatizada | manual |
| Ejecución real | — · PENDIENTE (no ejecutado) |

### CP-018 · REQ-014 · Rendimiento · Positivo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-014 |
| Nivel / tipo | Rendimiento / Positivo |
| Prioridad | Media |
| Entrada exacta | GET /api/suppliers durante 30 s con 5 usuarios virtuales: python -m scripts.load_test --vus 5 --duration 30 --path /api/suppliers. |
| Precondiciones | Servidor local en http://127.0.0.1:8765 con datos sintéticos y autenticación habilitada; sin otras cargas. |
| Pasos | 1) Cargar el seed. 2) Iniciar uvicorn. 3) Ejecutar el script de carga. 4) Leer p95, errores y CPU/RAM del reporte. |
| Resultado esperado (oráculo del enunciado) | p95 ≤ 1 500 ms y tasa de error ≤ 5 %; CPU/RAM y configuración registradas. |
| Prueba automatizada | manual (script scripts/load_test.py; no es un test pytest) |
| Ejecución real | RUN-019 · PASS |

### CP-019 · REQ-004 · Borde/negativo · Negativo

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-004 |
| Nivel / tipo | Borde/negativo / Negativo |
| Prioridad | Alta |
| Entrada exacta | Oferta de P1 = 9000000.00 sobre LIC-DRAFT (Borrador) y sobre LIC-CLOSED (Publicada y luego cerrada). |
| Precondiciones | App web con reloj fijo; P1 dado de alta. |
| Pasos | 1) Crear LIC-DRAFT sin publicar y ofertar. 2) Crear LIC-CLOSED, publicarla, cerrarla y ofertar. 3) Listar ofertas de ambas. |
| Resultado esperado (oráculo del enunciado) | Ambas ofertas se rechazan con 409 y «estado Publicada»; LIC-CLOSED figura como Cerrada; ninguna licitación tiene ofertas. |
| Prueba automatizada | `tests/qa/test_cp_functional.py::test_cp019_bid_on_draft_and_closed_tender_rejected` |
| Ejecución real | RUN-017 · PASS |

### CP-020 · REQ-005 · Borde/negativo · Límite

| Campo | Contenido |
|---|---|
| Requisito(s) | REQ-005 |
| Nivel / tipo | Borde/negativo / Límite |
| Prioridad | Alta |
| Entrada exacta | Por API, montos «10000000.01», «0», «0.00», «-0.01», «-5», 0, -1, 10000000.01 (rechazar); luego «10000000.00» (aceptar). |
| Precondiciones | App con reloj fijo; L1 Publicada (CRC 10 000 000,00); P1 dado de alta. |
| Pasos | 1) POST de cada monto inválido. 2) Listar ofertas. 3) POST con 10000000.00. |
| Resultado esperado (oráculo del enunciado) | Cada monto inválido → 422 con detail de texto, sin Traceback; la lista queda vacía; el monto igual al presupuesto se acepta (201). |
| Prueba automatizada | `tests/qa/test_cp_api.py::test_cp020_bid_amount_edges_rejected_by_api` |
| Ejecución real | RUN-018 · PASS |

## Notas

- CP-017 no se ejecutó: requiere 2 personas ajenas al equipo (REQ-013). El protocolo está en [`usabilidad-protocolo.md`](usabilidad-protocolo.md).
- CP-019 y CP-020 son los 2 casos adicionales de borde/negativo exigidos por el enunciado; CP-019 está implementado en `test_cp_functional.py` y CP-020 en `test_cp_api.py`.
- Revisión humana de los CP asistidos por IA: ver `05_IA/` (IA-003) y la hoja 10_Revision_IA del Excel; la decisión está PENDIENTE.
