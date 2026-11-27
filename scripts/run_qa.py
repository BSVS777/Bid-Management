"""Run every automated QA case (CP-###) once and store the REAL output as evidence.

Usage: python -m scripts.run_qa [--start-run N] [--out-dir 04_Evidencias]
Writes one EV-<CP>.txt per case plus RUN_LOG.json / RUN_LOG.md. Nothing is simulated:
the verdict of each run is the pytest exit code.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

Q = "tests/qa/"
CASES = [  # (CP, REQ, level, node id)
    ("CP-001", "REQ-001", "Unitaria", Q + "test_cp_unit.py::test_cp001_supplier_duplicate_by_normalization"),
    ("CP-002", "REQ-002", "Unitaria", Q + "test_cp_unit.py::test_cp002_tender_field_rules"),
    ("CP-003", "REQ-003", "Unitaria", Q + "test_cp_unit.py::test_cp003_state_transitions"),
    ("CP-004", "REQ-005", "Unitaria", Q + "test_cp_unit.py::test_cp004_bid_amount_limits"),
    ("CP-005", "REQ-007", "Unitaria", Q + "test_cp_unit.py::test_cp005_best_bid_rules"),
    ("CP-006", "REQ-008", "Unitaria", Q + "test_cp_unit.py::test_cp006_saving_classification"),
    ("CP-007", "REQ-009", "Unitaria", Q + "test_cp_unit.py::test_cp007_approver_boundaries"),
    ("CP-008", "REQ-006", "Integración/API", Q + "test_cp_api.py::test_cp008_duplicate_bid_rejected_by_api_and_db"),
    ("CP-009", "REQ-011", "Integración/API", Q + "test_cp_api.py::test_cp009_persistence_after_restart_and_api_validation"),
    ("CP-010", "REQ-010", "Integración/API", Q + "test_cp_api.py::test_cp010_usd_view_does_not_change_stored_crc"),
    ("CP-011", "REQ-001", "Funcional", Q + "test_cp_functional.py::test_cp011_register_supplier_and_reject_duplicate"),
    ("CP-012", "REQ-002/003", "Funcional", Q + "test_cp_functional.py::test_cp012_create_and_publish_tender"),
    ("CP-013", "REQ-007", "Funcional", Q + "test_cp_functional.py::test_cp013_bids_and_evaluation_page"),
    ("CP-014", "REQ-004", "Funcional", Q + "test_cp_functional.py::test_cp014_closing_instant_boundary"),
    ("CP-015", "REQ-012", "Seguridad", Q + "test_cp_security.py::test_cp015_supplier_name_character_whitelist"),
    ("CP-016", "REQ-012", "Seguridad", Q + "test_cp_security.py::test_cp016_no_script_execution_and_hidden_internal_errors"),
    ("CP-019", "REQ-004", "Borde/negativo", Q + "test_cp_functional.py::test_cp019_bid_on_draft_and_closed_tender_rejected"),
    ("CP-020", "REQ-005", "Borde/negativo", Q + "test_cp_api.py::test_cp020_bid_amount_edges_rejected_by_api"),
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-run", type=int, default=1)
    ap.add_argument("--out-dir", default="04_Evidencias")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    env = dict(os.environ, PYTHONUTF8="1")
    commit = git("rev-parse", "--short", "HEAD")
    log = []
    for i, (cp, req, level, node) in enumerate(CASES):
        run_id = f"RUN-{args.start_run + i:03d}"
        start = time.perf_counter()
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        proc = subprocess.run([sys.executable, "-m", "pytest", node, "-q", "-p", "no:cacheprovider"],
                              capture_output=True, text=True, env=env, encoding="utf-8")
        secs = round(time.perf_counter() - start, 2)
        ev = f"EV-{cp}_{run_id}.txt"
        header = f"# {run_id} | {cp} | {req} | {level}\n# commit {commit} | {stamp} | {secs}s | node {node}\n\n"
        with open(os.path.join(args.out_dir, ev), "w", encoding="utf-8") as fh:
            fh.write(header + proc.stdout + proc.stderr)
        log.append({"run": run_id, "cp": cp, "req": req, "level": level, "node": node,
                    "commit": commit, "executed_at": stamp, "seconds": secs,
                    "result": "PASS" if proc.returncode == 0 else "FAIL", "evidence": ev})
        print(f"{run_id} {cp} {log[-1]['result']} ({secs}s)")
    with open(os.path.join(args.out_dir, "RUN_LOG.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2, ensure_ascii=False)
    rows = "\n".join(f"| {r['run']} | {r['cp']} | {r['req']} | {r['level']} | {r['result']} | "
                     f"{r['executed_at']} | {r['commit']} | {r['evidence']} |" for r in log)
    with open(os.path.join(args.out_dir, "RUN_LOG.md"), "w", encoding="utf-8") as fh:
        fh.write("# Execution log of automated cases (real pytest runs)\n\n"
                 "| RUN | CP | REQ | Level | Result | Executed | Commit | Evidence |\n"
                 "|---|---|---|---|---|---|---|---|\n" + rows + "\n")
    return 0 if all(r["result"] == "PASS" for r in log) else 1


if __name__ == "__main__":
    raise SystemExit(main())
