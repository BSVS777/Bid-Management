# Trazabilidad REQ → CP → RUN → EV

Construida a partir de `04_Evidencias/RUN_LOG.json` y de los archivos de `04_Evidencias/`. Build de las ejecuciones RUN-001..RUN-018: `d3304e4`.

| REQ | Área | CP | RUN | Resultado | EV |
|---|---|---|---|---|---|
| REQ-001 | Proveedores | CP-001, CP-011 | RUN-001, RUN-011 | CP-001: PASS; CP-011: PASS | EV-CP-001_RUN-001.txt; EV-CP-011_RUN-011.txt |
| REQ-002 | Licitaciones | CP-002, CP-012 | RUN-002, RUN-012 | CP-002: PASS; CP-012: PASS | EV-CP-002_RUN-002.txt; EV-CP-012_RUN-012.txt |
| REQ-003 | Estados | CP-003, CP-012 | RUN-003, RUN-012 | CP-003: PASS; CP-012: PASS | EV-CP-003_RUN-003.txt; EV-CP-012_RUN-012.txt; BUG-002: EV-BUG-002_before_fix.txt → EV-BUG-002_after_fix.txt |
| REQ-004 | Vencimiento | CP-014, CP-019 | RUN-014, RUN-017 | CP-014: PASS; CP-019: PASS | EV-CP-014_RUN-014.txt; EV-CP-019_RUN-017.txt; BUG-001: RUN-020, RUN-021 (FAIL en lab 6a912eb), RUN-022 retest, RUN-023 y RUN-024 regresión (EV-BUG-001_*) |
| REQ-005 | Montos | CP-004, CP-020 | RUN-004, RUN-018 | CP-004: PASS; CP-020: PASS | EV-CP-004_RUN-004.txt; EV-CP-020_RUN-018.txt |
| REQ-006 | Duplicados | CP-008 | RUN-008 | CP-008: PASS | EV-CP-008_RUN-008.txt |
| REQ-007 | Mejor oferta | CP-005, CP-013 | RUN-005, RUN-013 | CP-005: PASS; CP-013: PASS | EV-CP-005_RUN-005.txt; EV-CP-013_RUN-013.txt |
| REQ-008 | Ahorro | CP-006 | RUN-006 | CP-006: PASS | EV-CP-006_RUN-006.txt |
| REQ-009 | Aprobación | CP-007 | RUN-007 | CP-007: PASS | EV-CP-007_RUN-007.txt; BUG-003: EV-BUG-003_before_fix.txt → EV-BUG-003_after_fix.txt |
| REQ-010 | Moneda | CP-010 | RUN-010 | CP-010: PASS | EV-CP-010_RUN-010.txt |
| REQ-011 | Persistencia/API | CP-009 | RUN-009 | CP-009: PASS | EV-CP-009_RUN-009.txt |
| REQ-012 | Seguridad | CP-015, CP-016 | RUN-015, RUN-016 | CP-015: PASS; CP-016: PASS | EV-CP-015_RUN-015.txt; EV-CP-016_RUN-016.txt |
| REQ-013 | Usabilidad | CP-017 | — | CP-017: PENDIENTE (no ejecutado) | — |
| REQ-014 | Rendimiento | CP-018 | RUN-019 | CP-018: PASS | EV-PERF-001.md / EV-PERF-001.json |

## Cobertura y huecos

- 14 de 14 REQ tienen al menos un CP.
- 13 de 14 REQ tienen ejecución real con resultado PASS; REQ-013 (usabilidad) está **PENDIENTE**: CP-017 no se ejecutó.
- CP-018 (REQ-014) se ejecutó después de las 18 pruebas automatizadas y se registró como RUN-019 con EV-PERF-001.
- BUG-001 (REQ-004), BUG-002 (REQ-003) y BUG-003 (REQ-009) se detallan en la hoja 07_Defectos del Excel.

## RUN adicionales (defecto inducido y regresión)

| RUN | CP / alcance | REQ | Commit | Resultado | EV |
|---|---|---|---|---|---|
| RUN-019 | CP-018 | REQ-014 | 2cb6a89 (script) / d3304e4 (main) | PASS | EV-PERF-001.md; EV-PERF-001.json |
| RUN-020 | CP-014 | REQ-004 | 6a912eb (rama lab/bug-001) | FAIL | EV-BUG-001_before_fix.txt |
| RUN-021 | Suite completa | REQ-004 | 6a912eb (rama lab/bug-001) | FAIL | EV-BUG-001_suite_on_lab_version.txt |
| RUN-022 | CP-014 | REQ-004 | b8e6831 (rama fix/bug-001) | PASS | EV-BUG-001_retest_after_fix.txt |
| RUN-023 | Regresión bids | REQ-004, REQ-005, REQ-006 | b8e6831 (rama fix/bug-001) | PASS | EV-BUG-001_regression_bids.txt |
| RUN-024 | Suite completa | Todos | b8e6831 (rama fix/bug-001) | PASS | EV-BUG-001_suite_after_fix.txt |

## Recuento de RUN

| Concepto | Cantidad |
|---|---|
| RUN automatizados iniciales (RUN-001..RUN-018, CP distintos) | 18 |
| RUN de rendimiento (RUN-019, CP-018) | 1 |
| RUN del defecto BUG-001 (RUN-020..RUN-024: fallo en lab, suite en lab, retest, 2 regresiones) | 5 |
| **Total de RUN registrados** | **24** |
| CP distintos ejecutados | 19 de 20 (falta CP-017) |
| Mínimo del enunciado | 20 CP distintos + ≥3 reejecuciones (≥23 RUN): el total supera 23, pero la composición **no se cumple**: falta 1 CP distinto (CP-017) |
