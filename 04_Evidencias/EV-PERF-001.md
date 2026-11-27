# EV-PERF-001 – Local load test (CP-018, REQ-014)

Run on 2026-11-26 23:06:46 against `http://127.0.0.1:8765` (localhost, synthetic seed data, auth enabled).
Command: `python -m scripts.load_test --vus 5 --duration 30 --path /api/suppliers` (source: `scripts/load_test.py`, raw data: `EV-PERF-001.json`).

| Metric | Result | Threshold |
|---|---|---|
| Virtual users / duration | 5 VU / 30.0 s | 5 VU / 30 s |
| Requests (GET /api/suppliers) | 18918 (630.52 req/s) | - |
| Errors | 0 (0.0 %) | <= 5 % |
| Latency mean / p50 / p95 / max | 7.69 / 7.55 / 9.3 / 34.17 ms | p95 <= 1 500 ms |
| System CPU mean / max | 11.7 % / 15.3 % | recorded |
| System RAM mean / max | 35.0 % / 35.1 % | recorded |
| Verdict | **PASS** | |

Environment: Windows-11-10.0.26200-SP0, Intel64 Family 6 Model 141 Stepping 1, GenuineIntel, 16 logical CPUs, 31.8 GB RAM, Python 3.12.10. Server: uvicorn, single process, SQLite file.
Note: a first attempt was discarded because a shell path conversion produced an invalid URL (100 % errors, not a product result); this run is the valid one.
