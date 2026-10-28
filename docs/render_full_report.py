"""Renders docs/FULL_REPORT.md to a self-contained HTML file (figures embedded). Print it to PDF with any browser.

Usage (from the repository root): python docs/render_full_report.py [out.html]
Needs: markdown-it-py.
"""
import base64
import sys
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "docs" / "FULL_REPORT.md").read_text(encoding="utf-8")
body = MarkdownIt("commonmark").enable("table").render(src)
FIGS = [("Figure 1. H2 matched-recall test: test precision-recall per method (mean over 10 seeds); dots = default 0.5 threshold.", "h2-federated-aml/results/v2_scores/pr_curves.png"),
        ("Figure 2. H3 durable liability: violation rate over time per regime (200 agents each) and the registration-bond sweep.", "h3-abt/results/durable_figure.png"),
        ("Figure 3. H3 learning agents under imperfect detection (pre-registered study).", "h3-abt/results/learning_figure.png"),
        ("Figure 4. H4 overhead law: PQ/classical ratio vs classical cost across v3 workloads.", "h4-pqc-stark/benchmark_v2/results/overhead_law.png"),
        ("Figure 5. Memory-budgeted decomposition (§6B): measured peak memory of each plan against the prover node's budget.", "h1-zkopml-v2/results/memory_plans.png")]
figs = "".join(
    f'<figure><img src="data:image/png;base64,{base64.b64encode((ROOT / p).read_bytes()).decode()}"/><figcaption>{c}</figcaption></figure>'
    for c, p in FIGS if (ROOT / p).exists())
marker = "<h2>8. Reproducibility index</h2>"
assert marker in body
body = body.replace(marker, "<h2>Figures</h2>" + figs + marker)
css = """body{font-family:Georgia,serif;font-size:10.5pt;line-height:1.45;max-width:880px;margin:auto;color:#111}
h1{font-size:19pt;line-height:1.2}h2{font-size:14pt;border-bottom:1px solid #999;margin-top:22px}h3{font-size:11.5pt}
table{border-collapse:collapse;margin:8px 0;font-size:8.6pt;width:100%}th,td{border:1px solid #bbb;padding:3px 5px;text-align:left;vertical-align:top}th{background:#eee}
code{font-family:Consolas,monospace;font-size:8.8pt;background:#f3f3f3}figure{margin:12px 0;page-break-inside:avoid}img{width:100%}figcaption{font-size:9pt;color:#444}
tr{page-break-inside:avoid}@page{size:A4;margin:16mm}"""
out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "FULL_REPORT.html"
out.write_text(f'<!doctype html><html><head><meta charset="utf-8"><title>CBDC Full Results Report</title><style>{css}</style></head><body>{body}</body></html>', encoding="utf-8")
print(out, f"{out.stat().st_size:,} bytes", body.count("<table>"), "tables", body.count("<img"), "images")
