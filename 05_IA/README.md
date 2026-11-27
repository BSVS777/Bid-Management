# Registro de uso de IA (05_IA)

Intervenciones de IA del proyecto Bid-Management (ISW-622). Cada archivo contiene herramienta, proveedor, modelo, fecha, finalidad, prompt saneado y condensado, salida resumida, partes incorporadas, cambios humanos, commits y EV vinculados, y la sección «Revisión humana».

Los prompts son versiones condensadas y saneadas (requisitos preservados), sin secretos ni datos personales. Todas las decisiones de revisión están **PENDIENTE – decisión humana**; ningún registro indica aprobación por una persona.

| ID | Finalidad | Tipo | Commits | EV | Decisión humana |
|---|---|---|---|---|---|
| [IA-001](IA-001.md) | Código y pruebas de la función de tipo de cambio (configuración CRC por USD y alternancia de vista CRC/USD) | Código + pruebas | 05f9b6e (merge 60db6a5, PR #5) | EV-CP-010_RUN-010.txt; EV-SUITE-COVERAGE_d3304e4.txt | PENDIENTE |
| [IA-002](IA-002.md) | Código y pruebas de la autenticación (usuario y contraseña) y del CRUD completo de todas las tablas | Código + pruebas | 3b0e780 (merge 53d2431, PR #6) | EV-SUITE-COVERAGE_d3304e4.txt | PENDIENTE |
| [IA-003](IA-003.md) | Pruebas QA mapeadas a CP-001..CP-016, CP-019 y CP-020 y diagnóstico que expuso BUG-002 y BUG-003 | Pruebas + revisión/diagnóstico | a139fa8, d97ac1d, ab97a86 (merges a09239d, f6be14e); diagnóstico: 7a83adb, 83b328f | EV-CP-001_RUN-001.txt .. EV-CP-016_RUN-016.txt, EV-CP-019_RUN-017.txt, EV-CP-020_RUN-018.txt, EV-BUG-002_before_fix.txt, EV-BUG-003_before_fix.txt | PENDIENTE |
| [IA-004](IA-004.md) | Script de datos sintéticos reproducible (seed) y las instrucciones de puesta en marcha del README | Código | 5242ced (merge 796c5e2, PR #7) | EV-SUITE-COVERAGE_d3304e4.txt | PENDIENTE |
| [IA-005](IA-005.md) | Script de carga local controlada (5 VU, 30 s) y reporte de rendimiento | Código | 2cb6a89 (merge d3304e4, PR #12) | EV-PERF-001.md; EV-PERF-001.json | PENDIENTE |

Herramienta común: Claude Code (Anthropic), modelo Claude Sonnet 5.5 (`claude-sonnet-5-5`), 2026-11-26.

Equivalencia en el Excel: hojas `09_IA_Usos` y `10_Revision_IA` de `entrega/03_Registro_QA.xlsx`.
