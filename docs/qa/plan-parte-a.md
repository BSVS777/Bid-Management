# Plan de pruebas – Parte A (REQ, estrategia y riesgos)

Sistema de Gestión de Licitaciones (Bid-Management) · ISW-622 Práctica Integradora · Wonder Team

> Los casos de prueba (A10) están en [`casos-de-prueba.md`](casos-de-prueba.md) y la trazabilidad REQ → CP → RUN → EV en [`trazabilidad.md`](trazabilidad.md). El defecto inducido (A11) y el cronograma (A12) se agregan en commits posteriores.
> La columna "CP vinculados" de A3 ya está completa (CP-017 sigue PENDIENTE de ejecución humana).

## A1. Identificación y objetivo

| Campo | Contenido |
|---|---|
| Producto bajo prueba | Bid-Management: aplicación web y API REST para registrar proveedores, publicar licitaciones, recibir ofertas y evaluarlas (mejor oferta, ahorro y nivel de aprobación). |
| Objetivo del plan | Verificar que el sistema cumple las reglas de negocio definidas por el docente (REQ-001 a REQ-014), con evidencia reproducible y trazable, y que las pruebas se ejecutan de forma automatizada y local. |
| Dentro del alcance | Proveedores, licitaciones y sus estados, ofertas (plazo, monto, duplicados), mejor oferta, ahorro, aprobador, vista en USD, persistencia, API, seguridad básica de entradas, usabilidad y rendimiento del listado. |
| Fuera del alcance | Despliegue en producción, alta disponibilidad, pruebas de carga superiores a 5 VU, compatibilidad con navegadores móviles, datos reales de empresas. |

## A2. Stack, repositorio y ambiente

| Campo | Contenido |
|---|---|
| Lenguaje / framework | Python 3.12 · FastAPI 0.115 · Jinja2 3.1 |
| Base de datos | SQLite vía SQLAlchemy 2.0 (`BID_DB_URL`, por defecto `sqlite:///./bid_management.db`) |
| Framework de pruebas | pytest 8 · pytest-cov 5 · httpx 0.27 (cliente de pruebas de la API) |
| Interfaz web / API | Interfaz web con plantillas Jinja2 y API REST bajo `/api`. Documentación interactiva en `/docs` (Swagger) |
| Repositorio, ramas y Pull Request | `https://github.com/BSVS777/Bid-Management`. Rama por funcionalidad, Pull Request a `main`; quien abre el PR no lo mergea |
| Ambiente (SO, CPU, RAM, navegador) | Windows 11 · Intel Core i7-11800H @ 2,30 GHz · 31,8 GB RAM · navegador a registrar en la sesión de usabilidad |
| Versiones y build bajo prueba | Python 3.12.10; dependencias fijadas en `requirements.txt`; build: hash final de `main` (se registra al cierre) |
| CI/CD | No aplica: el proyecto es académico y las pruebas se ejecutan localmente con pytest. |

## A3. Requisitos (REQ-001 a REQ-014)

| ID | Área | Criterio verificable | Prioridad | CP vinculados |
|---|---|---|---|---|
| REQ-001 | Proveedores | Crear/editar/listar; duplicados por nombre normalizado (recortar, compactar espacios, sin distinguir mayúsculas) | Alta | CP-001, CP-011 |
| REQ-002 | Licitaciones | Código único (sin distinguir mayúsculas/espacios laterales); título no vacío; presupuesto CRC > 0; cierre futuro al crear/publicar | Alta | CP-002, CP-012 |
| REQ-003 | Estados | Solo Borrador→Publicada/Cerrada y Publicada→Cerrada; sin regresar a Borrador ni reabrir Cerrada | Alta | CP-003, CP-012 |
| REQ-004 | Vencimiento | Ofertas solo en Publicadas y antes del cierre; exactamente en el cierre se rechazan | Alta | CP-014, CP-019 |
| REQ-005 | Montos | Oferta > 0 y ≤ presupuesto; igual al presupuesto es válida; cero, negativo o superior se rechazan | Alta | CP-004, CP-020 |
| REQ-006 | Duplicados | Un proveedor, una oferta por licitación; duplicados también rechazados por la BD | Alta | CP-008 |
| REQ-007 | Mejor oferta | Menor oferta válida en CRC; empate gana la primera registrada; sin ofertas: "Sin ofertas válidas" | Alta | CP-005, CP-013 |
| REQ-008 | Ahorro | ((presupuesto − mejor oferta)/presupuesto)×100; ≥10 % conveniente; >0 y <10 % aceptable; 0 % válida sin ahorro | Alta | CP-006 |
| REQ-009 | Aprobación | Rangos configurables sin traslape: Encargado de Área / Gerencia / Junta Directiva (sobre la mejor oferta válida) | Alta | CP-007 |
| REQ-010 | Moneda | Solo CRC persistido; USD = CRC/tasa (>0); mostrar tasa y fecha; alternar vista no modifica la BD | Media | CP-010 |
| REQ-011 | Persistencia/API | Datos persisten al reiniciar; API con respuestas de éxito y error; no acepta lo que la UI rechazaría | Alta | CP-009 |
| REQ-012 | Seguridad | Solo letras, números, espacios, punto, coma y paréntesis en nombre de proveedor; sin ejecución HTML/script; ocultar errores internos | Alta | CP-015, CP-016 |
| REQ-013 | Usabilidad | Con 2 personas ajenas al equipo, ≥3 de 4 tareas completadas sin ayuda | Media | CP-017 |
| REQ-014 | Rendimiento | 5 VU, 30 s, GET listado: p95 ≤ 1 500 ms y errores ≤ 5 %; registrar CPU/RAM y configuración | Media | CP-018 |

## A4. Datos de prueba y versiones

Todos los datos son sintéticos. No se usan datos reales.

| Dato | Valor de referencia | Propósito |
|---|---|---|
| Proveedor P1 | Tecnología Norte S.A. | Alta válida y unicidad normalizada |
| Proveedor P2 | Servicios del Valle | Segunda oferta y comparación |
| Licitación L1 | LIC-2026-001 · CRC 10 000 000,00 · cierre ahora +48 h | Publicación, ofertas, mejor oferta |
| Ofertas L1 | P1 = 9 000 000,00; P2 = 9 500 000,00 | Mejor P1; ahorro 10 %; Gerencia |
| Tipo de cambio | CRC 500,00 por USD; fecha actual | P1 = USD 18 000,00; CRC intacto |
| Escenarios aislados | Presupuesto 1 000 000 · ofertas 900 000 / 950 000 / 1 000 000 | Frontera 10 %, 5 % y 0 % |

Comando/script de carga y reinicio de datos: pendiente (se define con el script de datos sintéticos).

## A5. Estrategia y niveles de prueba

El oráculo de cada prueba son las reglas del docente (tabla A3), no la salida de la IA. Cualquier resultado esperado generado con IA se contrasta contra estas reglas antes de usarse.

| Nivel | Mínimo | Herramienta | Técnica / enfoque |
|---|---|---|---|
| Unitarias | 7 | pytest | Funciones de dominio (dinero, normalización, estados, ahorro, aprobador). Valores límite y particiones de equivalencia. |
| Integración / API | 3 | pytest + httpx; Swagger/curl para evidencia manual | Contratos de la API: códigos 2xx/4xx, persistencia y reglas entre módulos. |
| Funcionales | 4 | Ejecución manual guiada sobre la interfaz web | Flujos completos: proveedor → licitación → oferta → evaluación. |
| Seguridad | 2 | pytest + revisión manual | Caracteres no permitidos en nombres, HTML/script en campos, mensajes de error sin detalles internos. |
| Usabilidad | 1 (2 participantes) | Sesión observada, 4 tareas | Éxito sin ayuda; se registran tiempos y observaciones. |
| Rendimiento | 1 (5 VU, 30 s) | Script de carga local | GET del listado; p95 y tasa de error; CPU/RAM registrados. |
| Borde / negativo adicionales | 2 | pytest | Oferta igual al presupuesto, oferta exactamente en el cierre, tasa de cambio ≤ 0, ahorro 0 %. |

Técnicas aplicadas: análisis de valores límite (monto = presupuesto, cierre exacto, 10 % de ahorro), particiones de equivalencia (estados, rangos de aprobación) y pruebas negativas (entradas inválidas, transiciones prohibidas).

## A6. Roles y responsabilidades

| Integrante | Rol | Responsabilidades QA | Desarrollo |
|---|---|---|---|
| Josué David Solís Gamboa | Líder de QA | Diseña el plan y los CP, define el oráculo, coordina la trazabilidad y el informe | Participa en módulos asignados en el plan de commits |
| Bernal Santiago Vargas Solís | Líder de QC | Ejecuta pruebas, registra evidencias y defectos, revisa los Pull Request del otro integrante | Participa en módulos asignados en el plan de commits |

Cada integrante defiende ante el docente las partes que escribió. El uso de IA se registra como IA-### con su revisión humana.

## A7. Herramientas y automatización local

| Suite / script | Comando | Reporte generado |
|---|---|---|
| Todas las pruebas automatizadas | `python -m pytest -q` | Resumen en consola |
| Cobertura | `python -m pytest --cov=app` | Tabla de cobertura en consola |
| Solo unitarias | `python -m pytest -q tests/test_*_unit.py tests/test_money.py tests/test_approval.py` | Resumen en consola |
| Solo API | `python -m pytest -q tests/test_*_api.py` | Resumen en consola |
| Carga (5 VU, 30 s) | pendiente (script de rendimiento) | p95, tasa de error, CPU/RAM |

Meta: al menos 8 pruebas automatizadas (≥5 unitarias y ≥2 de integración/API); la suite actual ya las supera.

## A8. Criterios de entrada, salida y umbrales

| Criterio | Umbral | Cómo se mide |
|---|---|---|
| Entrada | Rama integrada en `main`; instalación sin errores; la suite existente ejecuta | `pip install -r requirements.txt` y `python -m pytest -q` |
| Salida – CP ejecutados / pasados | 100 % ejecutados; ≥ 95 % pasados | Tabla de CP del informe |
| Salida – defectos críticos/altos abiertos | 0 | Hoja de defectos |
| Rendimiento p95 / tasa de error | ≤ 1 500 ms / ≤ 5 % | Script de carga (5 VU, 30 s) |
| Usabilidad | ≥ 3 de 4 tareas | Sesión con 2 participantes ajenos al equipo |

## A9. Riesgos (RSK)

| ID | Riesgo | Prob. | Impacto | Prevención | Contingencia |
|---|---|---|---|---|---|
| RSK-001 | Mal manejo de montos con decimales binarios produce ahorros o aprobadores incorrectos en los límites (10 %, rangos de aprobación) | Media | Alto | Aritmética exacta en centavos; pruebas de valor límite | Corregir el cálculo y repetir las pruebas de frontera |
| RSK-002 | Ofertas aceptadas en el instante de cierre por comparación de fechas incorrecta o reloj no controlado | Media | Alto | Reloj inyectable en las pruebas; caso de borde "exactamente en el cierre" | Corregir la comparación estricta y repetir retest y regresión |
| RSK-003 | Resultados esperados tomados de la IA en lugar de las reglas del docente | Media | Alto | Oráculo basado en la tabla A3; revisión humana registrada por cada IA-### | Rehacer el caso con la regla correcta y documentar la corrección |
| RSK-004 | Inyección de HTML/script en nombres o campos de texto | Baja | Alto | Lista blanca de caracteres y escape en plantillas; pruebas de seguridad | Bloquear la entrada, corregir la plantilla y repetir las pruebas |
| RSK-005 | Datos de prueba inconsistentes entre ejecuciones | Media | Medio | Script reproducible de datos sintéticos y base de datos aislada por prueba | Reiniciar la base y recargar los datos de referencia |
| RSK-006 | Participantes de usabilidad no disponibles o ajenos al equipo insuficientes | Media | Medio | Coordinar las sesiones con anticipación | Reprogramar o buscar participantes alternos |
