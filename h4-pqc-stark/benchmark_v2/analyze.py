"""Summarize the H4 v2 benchmark and apply the pre-registered overhead bounds.

Usage: python analyze.py results/benchmark_v2.csv
Bounds (committed 2026-10-06, unchanged in docs/h4_v2_security.md): size <= 20x, prove <= 200x, verify <= 10x.
"""
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

BOUNDS = {"proof_bytes": 20.0, "prove_ms": 200.0, "verify_ms": 10.0}


def main(path: Path) -> None:
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8-sig")))
    data = defaultdict(lambda: defaultdict(list))
    meta = {}
    for row in rows:
        key = (row["workload"], row["system"])
        for metric in ("proof_bytes", "prove_ms", "verify_ms"):
            data[key][metric].append(float(row[metric]))
        meta[key] = (row["trace_rows"], row["trace_width"], row["conjectured_security_bits"])

    lines = ["| Workload | System | Trace (rows x cols) | Security (bits) | Proof size (B) | Prove ms (mean ± sd) | Verify ms (mean ± sd) | Runs |", "|---|---|---|---|---|---|---|---|"]
    verdict = ["", "| Workload | Metric | Classical mean | PQ mean | Ratio (PQ/classical) | Bound | Result |", "|---|---|---|---|---|---|---|"]
    for workload in sorted({k[0] for k in data}):
        for system in ("classical", "pq_sis"):
            d = data[(workload, system)]
            rows_, cols, sec = meta[(workload, system)]
            lines.append(
                f"| {workload} | {system} | {rows_} x {cols} | {sec} | {statistics.mean(d['proof_bytes']):,.0f} | "
                f"{statistics.mean(d['prove_ms']):.3f} ± {statistics.stdev(d['prove_ms']):.3f} | "
                f"{statistics.mean(d['verify_ms']):.3f} ± {statistics.stdev(d['verify_ms']):.3f} | {len(d['prove_ms'])} |"
            )
        all_pass = True
        for metric, bound in BOUNDS.items():
            c = statistics.mean(data[(workload, "classical")][metric])
            p = statistics.mean(data[(workload, "pq_sis")][metric])
            ratio = p / c
            ok = ratio <= bound
            all_pass &= ok
            verdict.append(f"| {workload} | {metric} | {c:,.3f} | {p:,.3f} | {ratio:.2f}x | <= {bound:.0f}x | {'PASS' if ok else 'FAIL'} |")
        verdict.append(f"| {workload} | **all three** | | | | | **{'PASS' if all_pass else 'FAIL'}** |")
    out = "\n".join(lines + verdict)
    target = path.with_suffix(".md")
    target.write_text(out + "\n", encoding="utf-8")
    print(out)
    print(f"\nwrote {target}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/benchmark_v2.csv"))
