# Protocolo de usabilidad (CP-017 · REQ-013)

Sistema de Gestión de Licitaciones (Bid-Management) · ISW-622 Práctica Integradora · Wonder Team

**Estado: PENDIENTE.** La sesión no se ha realizado. Este documento define el protocolo y el formulario de registro; todos los campos medidos están en blanco o marcados PENDIENTE. No se han inventado participantes, tiempos ni resultados.

## 1. Objetivo y criterio de éxito

Verificar REQ-013: en una sesión con **2 personas ajenas al equipo**, al menos **3 de 4 tareas** de registrar proveedor y ofertar se completan **sin ayuda**.

| Elemento | Definición |
|---|---|
| Éxito de una tarea | La persona la completa sola, sin pistas del moderador, y el sistema queda en el estado esperado |
| Criterio por participante | Éxito en ≥ 3 de las 4 tareas |
| Criterio de CP-017 | Se cumple si ambos participantes alcanzan el criterio por participante |
| Fuera de criterio | Tareas completadas con ayuda se registran como fallo y se anota el obstáculo |

El enunciado pide además ≥ 2 participantes distintos del equipo y 2 tareas por persona como mínimo; este protocolo propone las 4 tareas para cada persona, lo que cubre ese mínimo.

## 2. Preparación

1. Reiniciar los datos sintéticos: `python -m scripts.seed` (borra y recarga la base destino) y arrancar `uvicorn app.main:app` con las variables de entorno del README.
2. Preparar una cuenta de prueba (usuario y contraseña ficticios, no se publican en el repositorio) y entregarla al participante en papel.
3. Verificar que no existe ya el proveedor «Cooperativa Demo (CR)» ni la licitación `LIC-UX-001` (nombres reservados para la sesión; no son datos de referencia del enunciado). Si existen, reiniciar el seed.
4. Anotar navegador y versión, sistema operativo y resolución en el formulario de la sección 5.
5. Preparar el cronómetro y las consignas impresas de la sección 3.

## 3. Tareas (4 por participante)

El moderador entrega la consigna escrita y no explica la interfaz. Datos de la sesión (sintéticos):

| Tarea | Consigna al participante | Resultado esperado (verificable) |
|---|---|---|
| T1. Registrar proveedor | «Registre el proveedor Cooperativa Demo (CR).» | El proveedor aparece en `/suppliers` una sola vez |
| T2. Crear y publicar licitación | «Cree la licitación LIC-UX-001, título "Compra de equipo", presupuesto 5 000 000,00 colones, con cierre dentro de 48 horas, y publíquela.» | La licitación aparece en `/tenders` con estado Publicada |
| T3. Registrar oferta | «Registre una oferta de 4 500 000,00 colones del proveedor Cooperativa Demo (CR) en la licitación LIC-UX-001.» | La oferta aparece en la lista de ofertas de la licitación |
| T4. Leer mejor oferta y aprobador | «Indique en voz alta cuál es la mejor oferta de la licitación LIC-UX-001 y quién debe aprobarla.» | El participante responde proveedor y monto de la mejor oferta y el aprobador mostrado por la pantalla (Gerencia para 4 500 000,00 según REQ-009) |

El resultado esperado de T4 se lee de la pantalla; el moderador lo compara con las reglas REQ-007 a REQ-009, no con lo que diga la IA.

## 4. Conducción de la sesión

1. Explicar que se prueba el sistema y no a la persona; indicar que puede detenerse en cualquier momento.
2. Pedir consentimiento verbal para registrar tiempos y observaciones (ver sección 6).
3. Entregar T1 a T4 una por una. Iniciar el cronómetro al terminar de leer la consigna y detenerlo cuando la persona declare que terminó.
4. No ayudar. Si la persona queda bloqueada más de 3 minutos o pide ayuda, registrar «Éxito = N», anotar el obstáculo y continuar con la siguiente tarea (el moderador puede mostrar el resultado correcto después de registrarla).
5. Al final, preguntar qué fue lo más confuso (respuesta libre, se anota en obstáculos).

## 5. Formulario de registro (en blanco)

Datos de la sesión:

| Campo | Valor |
|---|---|
| Fecha y hora | PENDIENTE |
| Moderador / observador (integrante del equipo) | PENDIENTE |
| Navegador y versión | PENDIENTE |
| Sistema operativo | PENDIENTE |
| Build probado (hash de `main`) | PENDIENTE |

Registro por tarea (2 participantes × 4 tareas; las 2 primeras tareas de cada persona son las mínimas exigidas por el enunciado):

| Participante | Tarea | Tiempo (mm:ss) | Éxito sin ayuda (S/N) | Obstáculos y observaciones |
|---|---|---|---|---|
| Participante A (código P-A) | T1. Registrar proveedor | PENDIENTE | PENDIENTE | PENDIENTE |
| Participante A (código P-A) | T2. Crear y publicar licitación | PENDIENTE | PENDIENTE | PENDIENTE |
| Participante A (código P-A) | T3. Registrar oferta | PENDIENTE | PENDIENTE | PENDIENTE |
| Participante A (código P-A) | T4. Leer mejor oferta y aprobador | PENDIENTE | PENDIENTE | PENDIENTE |
| Participante B (código P-B) | T1. Registrar proveedor | PENDIENTE | PENDIENTE | PENDIENTE |
| Participante B (código P-B) | T2. Crear y publicar licitación | PENDIENTE | PENDIENTE | PENDIENTE |
| Participante B (código P-B) | T3. Registrar oferta | PENDIENTE | PENDIENTE | PENDIENTE |
| Participante B (código P-B) | T4. Leer mejor oferta y aprobador | PENDIENTE | PENDIENTE | PENDIENTE |

Resumen por participante:

| Participante | Tareas exitosas (de 4) | ¿Cumple ≥ 3 de 4? |
|---|---|---|
| Participante A (código P-A) | PENDIENTE | PENDIENTE |
| Participante B (código P-B) | PENDIENTE | PENDIENTE |

Resultado de CP-017: PENDIENTE (Cumple / No cumple).

## 6. Consentimiento y anonimato

- Los participantes deben ser personas **ajenas al equipo** y mayores de edad, y participan de forma voluntaria.
- Se registran únicamente códigos (P-A, P-B). **No se guardan nombres, correos, fotos ni grabaciones** en el repositorio, el Excel, el Word ni las evidencias.
- Se usan solo datos sintéticos; la persona no ingresa datos propios ni reales en el sistema.
- Las capturas de pantalla, si se toman, no deben mostrar datos personales ni credenciales.

## 7. Cómo alimentan los resultados el Excel y el Word

| Destino | Qué se traslada |
|---|---|
| Excel `14_Usabilidad` | Cada fila de la sección 5 reemplaza la fila PENDIENTE correspondiente (participante, tarea, tiempo, éxito, obstáculos) y el resultado por participante |
| Excel `06_Ejecuciones` | Un RUN nuevo para CP-017 con fecha, build, resultado (PASS/FAIL) y su EV |
| Excel `11_Evidencias` | El formulario completado (sin datos personales) como EV de usabilidad, por ejemplo `EV-UX-001` |
| Excel `01_Resumen` | Las fórmulas se actualizan al llenar las hojas; se revisa que «Usabilidad» pase de Pendiente a Cumple o No cumple |
| Word B3 (Usabilidad) | La tabla Participante / Tarea / Tiempo / Éxito / Obstáculos con los mismos valores |
| Word D3 y `trazabilidad.md` | REQ-013 → CP-017 → RUN → EV con el estado real |

Si algún participante no alcanza 3 de 4 tareas, el resultado se informa tal cual como no cumplido y se registra un defecto o una mejora si corresponde; no se repite la sesión para «mejorar» el número.
