"""Controlled local load test: N virtual users issue GET requests for a fixed duration.

Usage (server already running, synthetic data seeded):
  BID_ADMIN_USER=... BID_ADMIN_PASSWORD=... python -m scripts.load_test \
      --base-url http://127.0.0.1:8000 --vus 5 --duration 30 --path /api/suppliers --out 04_Evidencias/EV-PERF-001
Only localhost targets are accepted (practice scope: 5 VU, 30 s, synthetic data).
"""
import argparse
import json
import math
import os
import platform
import statistics
import sys
import threading
import time
from urllib.parse import urlparse

import httpx
import psutil

P95_LIMIT_MS = 1500.0
ERROR_LIMIT_PCT = 5.0


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile."""
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def worker(client: httpx.Client, path: str, headers: dict, stop_at: float, out: list):
    while time.perf_counter() < stop_at:
        start = time.perf_counter()
        try:
            ok = client.get(path, headers=headers).status_code == 200
        except httpx.HTTPError:
            ok = False
        out.append(((time.perf_counter() - start) * 1000.0, ok))


def sample_resources(stop: threading.Event, samples: list):
    psutil.cpu_percent(None)
    while not stop.is_set():
        time.sleep(1.0)
        samples.append((psutil.cpu_percent(None), psutil.virtual_memory().percent))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--vus", type=int, default=5)
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--path", default="/api/suppliers")
    ap.add_argument("--out", default="04_Evidencias/EV-PERF-001")
    args = ap.parse_args(argv)
    host = urlparse(args.base_url).hostname
    if host not in ("127.0.0.1", "localhost"):
        print("Refused: only localhost targets are allowed.", file=sys.stderr)
        return 2
    if args.vus > 5 or args.duration > 30:
        print("Refused: practice limit is 5 VU and 30 s.", file=sys.stderr)
        return 2
    user, pwd = os.environ.get("BID_ADMIN_USER"), os.environ.get("BID_ADMIN_PASSWORD")
    headers = {}
    with httpx.Client(base_url=args.base_url, timeout=10.0) as probe:
        if user and pwd:
            r = probe.post("/api/auth/login", json={"username": user, "password": pwd})
            r.raise_for_status()
            headers["Authorization"] = f"Bearer {r.json()['token']}"
    results: list[tuple[float, bool]] = []
    samples: list[tuple[float, float]] = []
    stop = threading.Event()
    sampler = threading.Thread(target=sample_resources, args=(stop, samples), daemon=True)
    sampler.start()
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    stop_at = time.perf_counter() + args.duration
    t0 = time.perf_counter()
    clients = [httpx.Client(base_url=args.base_url, timeout=10.0) for _ in range(args.vus)]
    threads = [threading.Thread(target=worker, args=(c, args.path, headers, stop_at, results))
               for c in clients]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0
    stop.set()
    sampler.join(timeout=3)
    for c in clients:
        c.close()
    lat = [ms for ms, _ in results]
    errors = sum(1 for _, ok in results if not ok)
    total = len(results)
    cpu = [c for c, _ in samples] or [0.0]
    ram = [m for _, m in samples] or [0.0]
    summary = {
        "started": started, "path": args.path, "vus": args.vus,
        "duration_s": round(elapsed, 2), "requests": total, "errors": errors,
        "error_rate_pct": round(100.0 * errors / total, 3) if total else 100.0,
        "rps": round(total / elapsed, 2) if elapsed else 0.0,
        "latency_ms": {"min": round(min(lat), 2), "mean": round(statistics.fmean(lat), 2),
                       "p50": round(percentile(lat, 50), 2), "p95": round(percentile(lat, 95), 2),
                       "max": round(max(lat), 2)} if lat else {},
        "cpu_percent": {"mean": round(statistics.fmean(cpu), 1), "max": round(max(cpu), 1)},
        "ram_percent": {"mean": round(statistics.fmean(ram), 1), "max": round(max(ram), 1)},
        "environment": {
            "os": platform.platform(), "processor": platform.processor(),
            "logical_cpus": psutil.cpu_count(), "ram_gb": round(psutil.virtual_memory().total / 2**30, 1),
            "python": platform.python_version(),
        },
        "thresholds": {"p95_ms_max": P95_LIMIT_MS, "error_rate_pct_max": ERROR_LIMIT_PCT},
    }
    p95 = summary["latency_ms"].get("p95", float("inf"))
    summary["verdict"] = ("PASS" if p95 <= P95_LIMIT_MS and summary["error_rate_pct"] <= ERROR_LIMIT_PCT
                          else "FAIL")
    with open(args.out + ".json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
