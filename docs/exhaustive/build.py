"""Builds docs/EXHAUSTIVE_REPORT.md from the hand-written sections in docs/exhaustive/sections/
and tables generated directly from the committed result files (so no number is retyped).

Tokens inside a section:
  {{gen:NAME}}            output of generator NAME below
  {{md:PATH|SHIFT}}       a repository Markdown file, headings demoted by SHIFT levels
  {{git:REV:PATH|SHIFT}}  a Markdown file as it was at git revision REV
  {{code:PATH}}           a file verbatim in a code block

Usage (from the repository root): python docs/exhaustive/build.py
"""
from __future__ import annotations

import csv
import json
import re
import statistics as st
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
OUT = ROOT / "docs" / "EXHAUSTIVE_REPORT.md"


# ---------------------------------------------------------------- helpers
def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def f(x, d=3):
    if x is None or x == "":
        return "—"
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    if x != x:
        return "n/a"
    return f"{x:.{d}f}"


def pct(x, d=1):
    return "—" if x is None or x == "" else f"{100 * float(x):.{d}f}%"


def pval(p):
    p = float(p)
    if p != p:
        return "n/a"
    return "< 1e-6" if p < 1e-6 else (f"{p:.2e}" if p < 1e-3 else f"{p:.4f}")


def rcsv(path):
    with open(ROOT / path, newline="", encoding="utf-8-sig") as h:
        return list(csv.DictReader(h))


def rjson(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def demote(text, shift):
    if shift <= 0:
        return text
    lines, fence = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fence = not fence
        if not fence and re.match(r"^#{1,6} ", line):
            line = "#" * shift + line
        lines.append(line)
    return "\n".join(lines)


def sh(*cmd, cwd=ROOT):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


# ---------------------------------------------------------------- repository
def gen_pr_history():
    prs = json.loads((HERE / "pr_history.json").read_text(encoding="utf-8"))
    rows = [(f"#{p['number']}", p["state"].lower(), p["author"]["login"], p["createdAt"][:10],
             (p.get("mergedAt") or "")[:10] or "—", f"`{p['headRefName']}`", p["title"].replace("|", "/")) for p in sorted(prs, key=lambda p: p["number"])]
    return table(["PR", "State", "Author", "Opened", "Merged", "Branch", "Title"], rows)


def gen_commit_count():
    log = sh("git", "log", "--format=%an|%ad", "--date=short").strip().splitlines()
    by = defaultdict(int)
    for line in log:
        by[line.split("|")[0]] += 1
    first, last = log[-1].split("|")[1], log[0].split("|")[1]
    return f"{len(log)} commits between {first} and {last}. By author name: " + ", ".join(f"{k} {v}" for k, v in sorted(by.items(), key=lambda kv: -kv[1])) + "."


def gen_artifact_index():
    files = sh("git", "ls-files").splitlines()
    rows = []
    for p in files:
        if p == "docs/EXHAUSTIVE_REPORT.md":   # its own size would change with every rebuild
            rows.append((f"`{p}`", "(this file)"))
            continue
        size = (ROOT / p).stat().st_size if (ROOT / p).exists() else 0
        rows.append((f"`{p}`", f"{size:,}"))
    return f"{len(files)} tracked files.\n\n" + table(["Path", "Bytes"], rows)


# ---------------------------------------------------------------- H1
def gen_h1_seeds():
    d = rjson("h1-zkopml-v2/results/accuracy_suite.json")
    rows = []
    for depth, v in sorted(d.items(), key=lambda kv: int(kv[0])):
        sel = v["selected"]["seed"]
        for s in v["seeds"]:
            rows.append((depth, s["seed"], "**yes**" if s["seed"] == sel else "", f(s["val_pr_auc"]), f(s["threshold"], 2), f(s["test_f1"]),
                         f(s["test_prec"]), f(s["test_rec"]), pct(s["test_acc"], 2), f(s["test_pr_auc"]), f(s["f1_35_42"]), f(s["f1_43_49"])))
    return table(["Blocks", "Seed", "Selected (val)", "Val PR-AUC", "Threshold", "Test F1", "Precision", "Recall", "Accuracy", "Test PR-AUC", "F1 steps 35–42", "F1 steps 43–49"], rows)


def gen_h1_quant():
    rows = []
    for s in (7, 9, 10):
        d = rjson(f"h1-zkopml-v2/results/quant_accuracy_S{s}.json")
        for depth, v in sorted(d.items(), key=lambda kv: int(kv[0])):
            rows.append((f"2^{s}", depth, pct(v["float_acc"], 2), pct(v["fixed_acc"], 2), f(v["acc_drop_pp"], 2), f(v["float_f1"]), f(v["fixed_f1"]),
                         f(v["f1_drop_pp"], 2), f(v["float_pr_auc"]), f(v["fixed_pr_auc"]), pct(v["decision_agreement"], 2)))
    return table(["Scale", "Blocks", "Float acc", "Fixed acc", "Acc drop (pp)", "Float F1", "Fixed F1", "F1 drop (pp)", "Float PR-AUC", "Fixed PR-AUC", "Decisions unchanged"], rows)


def gen_h1_steps():
    rows = []
    for b in (1, 8, 24, 60):
        d = rjson(f"h1-zkopml-v2/results/steps_B{b}.json")
        for name, v in d.items():
            rows.append((b, name, v["logrows"], f"{v['num_rows']:,}", f"{v['total_assignments']:,}", f(v["calibrate_s"]), f(v["setup_s"]), f(v["witness_s"]),
                         " / ".join(f(t) for t in v["prove_times"]), f(v["prove_mean_s"]), f(v["verify_s"], 4), "yes" if v["verified"] else "NO"))
    return table(["Blocks", "Circuit", "logrows", "Rows", "Assignments", "Calibrate s", "Setup s", "Witness s", "Prove s (3 trials)", "Prove mean s", "Verify s", "Verified"], rows)


def gen_h1_sweep_committed():
    d = rjson("h1-zkopml-v2/results/summary.json")
    rows = [(s["B"], s["n_steps"], s["mono_logrows"], f"{s['mono_rows']:,}", f(s["mono_prove_s"]), f(s["worst_step_prove_s"]), f(s["speedup_worst"], 2) + "×",
             f(s["speedup_mean"], 2) + "×", s["bisection_rounds"], f(s["quant_acc_drop_pp"], 3), f(s["quant_f1_drop_pp"], 3), f(s["float_test_f1"]),
             f(s["seed_f1_mean"]) + " ± " + f(s["seed_f1_std"])) for s in d["sweep"]]
    return table(["Blocks", "Steps", "Mono logrows", "Mono rows", "Mono prove s", "Worst step s", "Worst-case speedup", "Mean speedup", "Rounds",
                  "Acc drop pp", "F1 drop pp", "Selected F1", "F1 over 3 seeds"], rows)


def gen_h1_disputes():
    d = rjson("h1-zkopml-v2/results/disputes_B60.json")
    rows = []
    for k, v in sorted(d.items(), key=lambda kv: int(kv[0])):
        sc = v["scenario"]
        rows.append((k, sc["tx"], sc["cheat"], sc["step"], v["step_name"], v["first_bad_step"], "yes" if v["located_correctly"] else "NO", v["bisection_rounds"],
                     "yes" if v["proof_verified"] else "NO", "yes" if v["input_instances_match_agreed"] else "NO",
                     "upheld" if v["asserter_claim_upheld"] else "rejected", "illicit" if v["asserter_decision_illicit"] else "licit",
                     "illicit" if v["challenger_decision_illicit"] else "licit",
                     "yes" if v["outcome_correct"] else "NO", f(v.get("prove_s", v.get("step_prove_s")), 3)))
    return table(["#", "Test tx", "Who cheats", "Tampered step", "Step name", "First differing step", "Located", "Rounds", "Step proof verified",
                  "Inputs match agreed leaves", "Asserter claim", "Asserter's decision", "Challenger's decision", "Correct outcome", "Prove s (multi-core)"], rows)


def gen_h1_gas():
    g = rjson("h1-zkopml-v2/results/gas.json")
    rows = [(k.replace("B60_", ""), f"{v['verify_tx_gas']:,}", f"{v['deploy_gas']:,}", f(v["bytecode_kb"], 1), f"{v['calldata_bytes']:,}", v["n_instances"],
             "yes" if v["call_returns_true"] else "NO") for k, v in g.items() if k.startswith("B60_")]
    out = table(["Verifier", "Verify tx gas", "Deploy gas", "Bytecode KB", "Calldata bytes", "Public instances", "Returns true"], rows)
    gm = g["game_B60"]
    game = [("Commit, first (full)", f"{gm['commit_first']:,}"), ("Commit, steady (full)", f"{gm['commit_steady']:,}"),
            ("Commit, first (compact)", f"{gm['commit_compact_first']:,}"), ("Commit, steady (compact) — used as per-inference cost", f"{gm['commit_compact_steady']:,}"),
            ("Bisection rounds measured", gm["rounds"]), ("Reveal gas per round", ", ".join(f"{x:,}" for x in gm["reveal_gas"])),
            ("Respond gas per round", ", ".join(f"{x:,}" for x in gm["respond_gas"])), ("Bisection total (5 rounds)", f"{gm['bisection_total']:,}")]
    s = rjson("h1-zkopml-v2/results/summary.json")["gas"]
    derived = [("Monolithic verify", f"{s['mono_verify']:,}"), ("Commit per inference", f"{s['commit_per_inference']:,}"),
               ("Bisection round (mean reveal+respond)", f"{s['bisection_round']:,.0f}"), ("Full dispute, typical", f"{s['dispute_total_typical']:,.0f}"),
               ("Full dispute, worst (projection-half step)", f"{s['dispute_total_worst']:,.0f}"), ("Undisputed cost ratio (mono / commit)", f(s["undisputed_cost_ratio"], 2) + "×"),
               ("Per-dispute cost ratio (mono / worst dispute)", f(s["per_dispute_cost_ratio"], 3) + "×"), ("Max dispute rate for 10× (worst case)", pct(s["max_dispute_rate_for_10x"], 2))]
    return out + "\n\nDispute-game contract:\n\n" + table(["Item", "Gas"], game) + "\n\nDerived (from `summary.json`):\n\n" + table(["Quantity", "Value"], derived)


# ---------------------------------------------------------------- H2
H2 = "h2-federated-aml/results/"


def gen_h2_inst_stats():
    rows = rcsv(H2 + "institution_stats.csv")
    return table(list(rows[0].keys()), [[f(v, 3) if "." in v else v for v in r.values()] for r in rows])


def gen_h2_scarcity_counts():
    rows = rcsv(H2 + "per_institution_scarcity_counts.csv")
    return table(list(rows[0].keys()), [list(r.values()) for r in rows])


def gen_h2_v1_baseline():
    rows = rcsv(H2 + "baseline_results.csv") + rcsv(H2 + "federated_results.csv")
    keys = ["method", "accuracy", "precision", "recall", "f1", "pr_auc", "roc_auc", "confusion_matrix"]
    return table(keys, [[f(r.get(k)) if k not in ("method", "confusion_matrix") else r.get(k) for k in keys] for r in rows])


def gen_h2_v1_seed42():
    rows = [r for r in rcsv(H2 + "scarcity_results.csv") if r["seed"] == "42"]
    keys = ["method", "scarcity", "f1", "precision", "recall", "pr_auc", "roc_auc", "confusion_matrix", "degradation_f1"]
    return table(keys, [[r[k] if k in ("method", "scarcity", "confusion_matrix") else f(r[k]) for k in keys] for r in rows])


def gen_h2_v1_summary():
    rows = rcsv(H2 + "scarcity_summary.csv")
    out = []
    for r in rows:
        out.append((r["experiment"], r["method"], r["scarcity"], r["institutions"], r["lambda"], f(r["f1_mean"]) + " ± " + f(r["f1_std"]),
                    f(r["pr_auc_mean"]) + " ± " + f(r["pr_auc_std"]), f(r["precision_mean"]), f(r["recall_mean"]), f(r["degradation_f1_mean"])))
    return table(["Experiment", "Method", "Scarcity", "K", "λ", "F1 (mean ± sd, 5 seeds)", "PR-AUC", "Precision", "Recall", "F1 degradation"], out)


def gen_h2_v1_paired():
    rows = rcsv(H2 + "paired_significance.csv")
    return table(["Scarcity", "K", "Comparison", "Metric", "Seeds", "Mean diff (first − second)", "Direction", "p (two-sided Wilcoxon)", "Significant"],
                 [(r["scarcity"], r["institutions"], r["comparison"], r["metric"], r["n_paired_seeds"], f(r["mean_difference_first_minus_second"], 4),
                   r["effect_direction"], f(r["p_value"], 4), r["statistically_significant"]) for r in rows])


def gen_h2_v1_ablations():
    out = []
    for name in ("lambda_ablation_results.csv", "institution_count_ablation_results.csv"):
        rows = rcsv(H2 + name)
        by = defaultdict(list)
        for r in rows:
            by[(r["method"], r["institutions"], r["lambda"])].append(r)
        tr = [(m, k, lam, len(v), f(st.mean(float(x["f1"]) for x in v)), f(st.mean(float(x["pr_auc"]) for x in v)),
               f(st.mean(json.loads(x["confusion_matrix"])[0][1] for x in v), 1)) for (m, k, lam), v in sorted(by.items())]
        out.append(f"`{name}` (10% labels, aggregated over seeds):\n\n" + table(["Method", "K", "λ", "Runs", "F1 mean", "PR-AUC mean", "FP mean"], tr))
    return "\n\n".join(out)


def gen_h2_v2_summary():
    rows = rcsv(H2 + "v2/summary.csv")
    out = []
    for r in rows:
        out.append((r["experiment"], r["method"], r["scarcity"], r["institutions"], r["boundary_lambda"], r.get("noise_multiplier") or "—",
                    f(r["f1_mean"]) + " ± " + f(r["f1_std"]), f(r["pr_auc_mean"]) + " ± " + f(r["pr_auc_std"]), f(r["roc_auc_mean"]),
                    f(r["precision_mean"]), f(r["recall_mean"]), f(r["false_positives_mean"], 1) + " ± " + f(r["false_positives_std"], 1),
                    f(r["false_negatives_mean"], 1)))
    return table(["Experiment", "Method", "Labels kept", "K", "λ", "Noise z", "F1", "PR-AUC", "ROC-AUC", "Precision", "Recall", "False positives", "False negatives"], out)


def gen_h2_v2_primary():
    rows = rcsv(H2 + "v2/h2_primary_fp_criterion.csv")
    return table(["Labels kept", "Seeds", "FP centralized", "FP FedAvg", "FP reduction", "p one-sided", "p Holm", "Criterion met"],
                 [(r["scarcity"], r["n_seeds"], f(r["fp_centralized_mean"], 1), f(r["fp_fedavg_mean"], 1), pct(r["fp_reduction"]), pval(r["p_one_sided"]),
                   pval(r["p_holm"]), r["criterion_met"]) for r in rows])


def gen_h2_v2_secondary():
    rows = rcsv(H2 + "v2/h2_secondary_comparisons.csv")
    return table(["Labels kept", "Comparison", "Metric", "Seeds", "Mean difference", "p two-sided"],
                 [(r["scarcity"], r["comparison"], r["metric"], r["n_seeds"], f(r["mean_difference"], 4), pval(r["p_two_sided"])) for r in rows])


def gen_h2_v2_refined():
    rows = rcsv(H2 + "v2/h2_refined_boundary_mitigation.csv")
    return table(["Labels kept", "Seeds", "F1 degradation FedAvg", "F1 degradation boundary", "Mitigation", "p one-sided"],
                 [(r["scarcity"], r["n_seeds"], f(r["degradation_fedavg_mean"]), f(r["degradation_boundary_mean"]), f(r["mitigation_mean"]), pval(r["p_one_sided"])) for r in rows])


def gen_h2_v2_privacy():
    rows = rcsv(H2 + "v2/h2_privacy_tradeoff.csv")
    return table(["Noise z", "ε (δ = 1e-5, 40 rounds)", "F1", "PR-AUC", "False positives"],
                 [(r["noise_multiplier"], f"{float(r['epsilon']):,.1f}", f(r["f1_mean"]) + " ± " + f(r["f1_std"]), f(r["pr_auc_mean"]), f(r["fp_mean"], 1)) for r in rows])


def gen_h2_v2_per_seed():
    rows = [r for r in rcsv(H2 + "v2/all_results.csv") if r["experiment"] == "main_scarcity"]
    idx = {(r["seed"], r["scarcity"], r["method"]): r for r in rows}
    methods = ("centralized", "local_only", "fedavg", "fedavg_boundary")
    out = []
    for s in sorted({r["scarcity"] for r in rows}, key=lambda x: -float(x)):
        for seed in sorted({r["seed"] for r in rows}):
            cells = [s, seed]
            for m in methods:
                r = idx[(seed, s, m)]
                cells.append(f"{f(r['f1'])} / {int(float(r['false_positives']))} / {f(r['recall'], 2)} / {r.get('best_round', '')}")
            out.append(cells)
    return table(["Labels kept", "Seed"] + [f"{m}: F1 / FP / recall / best epoch-round" for m in methods], out)


def gen_h2_v2_ablation_per_seed():
    rows = [r for r in rcsv(H2 + "v2/all_results.csv") if r["experiment"] in ("lambda_ablation", "institution_count_ablation", "privacy_sweep")]
    return table(["Experiment", "Seed", "Method", "K", "λ", "Noise z", "F1", "PR-AUC", "FP", "Recall"],
                 [(r["experiment"], r["seed"], r["method"], r["institutions"], r["boundary_lambda"], r.get("noise_multiplier") or "—", f(r["f1"]), f(r["pr_auc"]),
                   int(float(r["false_positives"])), f(r["recall"], 3)) for r in rows])


def gen_h2_mr_primary():
    rows = rcsv(H2 + "v2_scores/matched_recall_primary.csv")
    return table(["Labels kept", "Seeds evaluable", "FP reduction at 0.5", "FP centralized (matched)", "FP FedAvg (matched)", "FP reduction (matched)",
                  "Test recall centralized", "Test recall FedAvg", "p one-sided", "Holm", "p two-sided", "Holm two-sided", "Criterion at matched recall"],
                 [(r["scarcity"], r["n_seeds"], pct(r["fp_reduction_default"]), f(r["fp_centralized_matched"], 1), f(r["fp_fedavg_matched"], 1),
                   pct(r["fp_reduction_matched"]), f(r["test_recall_centralized"]), f(r["test_recall_fedavg"]), pval(r["p_one_sided"]), pval(r["p_holm"]),
                   pval(r["p_two_sided"]), pval(r["p_two_sided_holm"]), r["criterion_met_matched"]) for r in rows])


def gen_h2_mr_by_method():
    rows = rcsv(H2 + "v2_scores/matched_recall_by_method.csv")
    return table(["Labels kept", "Method", "FP matched", "Recall matched", "Precision matched", "FP at 0.5", "Recall at 0.5"],
                 [(r["scarcity"], r["method"], f(r["matched_false_positives"], 1), f(r["matched_recall"]), f(r["matched_precision"]),
                   f(r["default_false_positives"], 1), f(r["default_recall"])) for r in rows])


def gen_h2_mr_per_seed():
    rows = rcsv(H2 + "v2_scores/matched_recall_per_seed.csv")
    idx = {(r["seed"], r["scarcity"], r["method"]): r for r in rows}
    out = []
    for s in sorted({r["scarcity"] for r in rows}, key=lambda x: -float(x)):
        for seed in sorted({r["seed"] for r in rows}):
            c, fa = idx[(seed, s, "centralized")], idx[(seed, s, "fedavg")]
            if c["evaluable"] != "True":
                out.append((s, seed, f(c["target_recall_val"]), "not evaluable", "", "", "", "", ""))
                continue
            out.append((s, seed, f(c["target_recall_val"]), f(c["matched_threshold"], 4), f(fa["matched_threshold"], 4), int(float(c["matched_false_positives"])),
                        int(float(fa["matched_false_positives"])), f(c["matched_recall"]), f(fa["matched_recall"])))
    return table(["Labels kept", "Seed", "Target recall (val)", "Threshold centralized", "Threshold FedAvg", "FP centralized", "FP FedAvg", "Test recall centralized", "Test recall FedAvg"], out)


def gen_h2_mr_repro():
    r = rjson(H2 + "v2_scores/matched_recall_report.json")["reproducibility"]
    return table(["Pairs compared", "Max abs ΔF1, rerun vs v2", "Share with identical FP count"], [(r["pairs"], f(r["max_abs_f1_diff"], 4), pct(r["identical_fp_fraction"]))])


# ---------------------------------------------------------------- H3
H3 = "h3-abt/results/"


def gen_h3_confirmatory():
    d = rjson(H3 + "confirmatory_seed42.json")
    z = d["z_test"]
    rows = [(k, json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in z.items()]
    grp = []
    for g in ("control", "treatment"):
        v = d[g]
        grp.append((g, *[v.get(k, "—") for k in ("n_agents", "total_actions", "total_violations", "violation_rate", "total_slashed")]))
    return table(["Group", "Agents", "Actions", "Violations", "Rate", "Total slashed"], grp) + "\n\nz-test record:\n\n" + table(["Field", "Value"], rows)


def gen_h3_per_agent():
    rows = rcsv(H3 + "confirmatory_seed42.csv")
    acts, viol, slashed, depleted_at = defaultdict(int), defaultdict(int), defaultdict(float), {}
    for r in rows:
        key = (r["group"], r["agent_id"])
        acts[key] += 1
        viol[key] += r["is_violation"] == "True"
        slashed[key] += float(r["amount_slashed"])
        if r["group"] == "treatment" and float(r["stake_after"]) <= 0 and key not in depleted_at:
            depleted_at[key] = int(r["step"])
    out = [(g, a, acts[(g, a)], viol[(g, a)], pct(viol[(g, a)] / acts[(g, a)]), "pass" if viol[(g, a)] / acts[(g, a)] <= 0.5 else "fail",
            f(slashed[(g, a)], 0), depleted_at.get((g, a), "—")) for (g, a) in sorted(acts, key=lambda k: (k[0], int(k[1].split("_")[-1])))]
    return table(["Group", "Agent", "Actions", "Violations", "Rate", "Majority bar (≤ 50%)", "Total slashed", "Step stake hit 0"], out)


def gen_h3_depletion():
    rows = [r for r in rcsv(H3 + "confirmatory_seed42.csv") if r["group"] == "treatment"]
    live = [r for r in rows if float(r["stake_before"]) > 0]
    dead = [r for r in rows if float(r["stake_before"]) <= 0]
    rate = lambda rs: sum(r["is_violation"] == "True" for r in rs) / len(rs)
    ctrl = [r for r in rcsv(H3 + "confirmatory_seed42.csv") if r["group"] == "control"]
    win = []
    for a, b in ((1, 10), (11, 20), (21, 30), (31, 40), (41, 50)):
        win.append((f"{a}–{b}", pct(rate([r for r in ctrl if a <= int(r["step"]) <= b])), pct(rate([r for r in rows if a <= int(r["step"]) <= b]))))
    return (table(["Treatment actions", "Count", "Violation rate"], [("stake > 0 before acting", len(live), pct(rate(live))), ("stake = 0 before acting", len(dead), pct(rate(dead))),
                                                                     ("control (for reference)", len(ctrl), pct(rate(ctrl)))])
            + "\n\n" + table(["Steps", "Control rate", "Treatment rate"], win))


def gen_h3_agent_level():
    d = rjson(H3 + "agent_level_seed42.json")
    return table(["Field", "Value"], [(k, f(v, 6) if isinstance(v, float) else v) for k, v in d.items()])


def gen_h3_durable():
    d = rjson(H3 + "durable_report.json")
    tests = d["primary"] + d["secondary"]
    t = table(["Test", "Agents", "Mean rate (first)", "Mean rate (second)", "Mann–Whitney z", "p one-sided", "Permutation p", "Holm p"],
              [(x["test"], x["n"], pct(x["mean_first"]), pct(x["mean_second"]), f(x["mann_whitney_z"], 2), pval(x["p_one_sided"]),
                "≤ 1e-5" if x["permutation_p"] <= 1.1e-5 else pval(x["permutation_p"]), pval(x["p_holm"]) if "p_holm" in x else "—") for x in tests])
    desc = table(["Regime", "Violation rate", "Steps 1–10", "11–20", "21–30", "31–40", "41–50", "Agents ever depleted", "Identity resets"],
                 [(k, pct(v["rate"]), *[pct(w) for w in v["by_window"]], v["depleted_agents"], f"{v['resets']:,}") for k, v in d["descriptive"].items()])
    bond = table(["Bond B", "Violation rate", "Identity resets"], [(b["bond"], pct(b["rate"]), f"{b['resets']:,}") for b in d["bond_sweep"]])
    return f"**Tests** (seeds {d['seeds'][0]}–{d['seeds'][-1]}, {d['agents_per_regime']} agents per regime):\n\n{t}\n\n**Per regime:**\n\n{desc}\n\n**Bond sweep** (analytic break-even B* = {d['break_even_bond']}):\n\n{bond}"


def gen_h3_durable_per_seed():
    rows = rcsv(H3 + "durable_actions.csv")
    acc = defaultdict(lambda: [0, 0, 0.0, 0.0])
    for r in rows:
        a = acc[(r["seed"], r["regime"])]
        a[0] += 1
        a[1] += r["is_violation"] == "True"
        a[2] += float(r["slashed"])
    regimes = ("control", "flat", "maintained", "escalating_id", "escalating_operator")
    out = [(seed, *[pct(acc[(seed, g)][1] / acc[(seed, g)][0]) for g in regimes], *[f(acc[(seed, g)][2] / 20, 1) for g in regimes[1:]])
           for seed in sorted({r["seed"] for r in rows}, key=int)]
    return table(["Seed"] + [f"{g} rate" for g in regimes] + [f"{g} slashed/agent" for g in regimes[1:]], out)


# ---------------------------------------------------------------- H4
H4 = "h4-pqc-stark/"


def _bench(path):
    rows = rcsv(path)
    by = defaultdict(list)
    for r in rows:
        by[(r["workload"], r["system"])].append(r)
    return by


def gen_h4_bench(path):
    by = _bench(path)
    out = []
    for (w, s), rs in by.items():
        pr = [float(r["prove_ms"]) for r in rs]
        vr = [float(r["verify_ms"]) for r in rs]
        sz = sorted({r["proof_bytes"] for r in rs})
        out.append((w, s, len(rs), f"{rs[0]['trace_rows']} × {rs[0]['trace_width']}", rs[0]["conjectured_security_bits"], ", ".join(f"{int(x):,}" for x in sz),
                    f(st.mean(pr), 2) + " ± " + f(st.stdev(pr), 2), f(min(pr), 2), f(st.median(pr), 2), f(max(pr), 2),
                    f(st.mean(vr), 2) + " ± " + f(st.stdev(vr), 2), f(min(vr), 2), f(st.median(vr), 2), f(max(vr), 2)))
    stats = table(["Workload", "System", "Runs", "Trace rows × cols", "Security bits", "Proof bytes", "Prove ms mean ± sd", "min", "median", "max",
                   "Verify ms mean ± sd", "min", "median", "max"], out)
    bounds = {"proof_bytes": 20, "prove_ms": 200, "verify_ms": 10}
    rat = []
    for w in dict.fromkeys(k[0] for k in by):
        pqs = next(s for (ww, s) in by if ww == w and s != "classical")
        for m, bnd in bounds.items():
            c = st.mean(float(r[m]) for r in by[(w, "classical")])
            p = st.mean(float(r[m]) for r in by[(w, pqs)])
            rat.append((w, pqs, m, f(c, 2), f(p, 2), f(p / c, 2) + "×", f"≤ {bnd}×", "PASS" if p / c <= bnd else "**FAIL**"))
    return stats + "\n\n" + table(["Workload", "PQ system", "Metric", "Classical mean", "PQ mean", "Ratio", "Bound", "Result"], rat)


def gen_h4_v1_bench():
    rows = rcsv(H4 + "experiments/benchmark_results.csv")
    by = defaultdict(list)
    for r in rows:
        by[r["system"]].append(r)
    out = [(s, len(v), sorted({x["proof_bytes"] for x in v})[0], f(st.mean(float(x["prove_ms"]) for x in v)), f(st.stdev(float(x["prove_ms"]) for x in v)),
            f(st.mean(float(x["verify_ms"]) for x in v)), f(st.stdev(float(x["verify_ms"]) for x in v))) for s, v in by.items()]
    txt = (ROOT / H4 / "pq/matched_matrix_stark/h4_research_candidate_results.txt").read_text(encoding="utf-8")
    rc = [l.split(",") for l in txt.splitlines() if l.startswith("pq_matched_research_candidate,")]
    out.append(("pq_matched_research_candidate (128×256)", len(rc), rc[0][2], f(st.mean(float(x[3]) for x in rc)), f(st.stdev(float(x[3]) for x in rc)),
                f(st.mean(float(x[4]) for x in rc)), f(st.stdev(float(x[4]) for x in rc))))
    return table(["System", "Runs", "Proof bytes", "Prove ms mean", "sd", "Verify ms mean", "sd"], out)


def gen_h4_estimator():
    d = rjson(H4 + "docs/h4_lattice_estimator.json")
    rows = []
    def walk(x, path=""):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}.{k}" if path else k)
        else:
            rows.append((f"`{path}`", x if not isinstance(x, float) else f(x, 2)))
    walk(d)
    return table(["Key", "Value"], rows)


def gen_h4_specs():
    rows = []
    for h in ("h1", "h2", "h3"):
        d = rjson(H4 + f"benchmark_v2/specs/{h}_spec.json")
        for k, v in d.items():
            if isinstance(v, (int, float, str, bool)):
                rows.append((h.upper(), k, v))
            elif isinstance(v, dict):
                rows.append((h.upper(), k, json.dumps(v)[:400]))
            elif isinstance(v, list):
                rows.append((h.upper(), k, f"list of {len(v)}"))
    return table(["Spec", "Field", "Value"], rows)


def gen_h4_tests():
    out = sh("cargo", "test", "--release", "--", "--list", cwd=ROOT / H4 / "benchmark_v2")
    names = [l[: -len(": test")].replace("tests::", "") for l in out.splitlines() if l.endswith(": test")]
    return f"{len(names)} tests (`cargo test --release`, all passing at the time of writing):\n\n" + "\n".join(f"- `{n}`" for n in names)


def _pytest_list(folder):
    out = sh("python", "-m", "pytest", "--collect-only", "-q", "-o", "addopts=", cwd=ROOT / folder)
    names = [l for l in out.splitlines() if "::" in l]
    by = defaultdict(list)
    for n in names:
        file, test = n.split("::", 1)
        by[file].append(test)
    return f"{len(names)} tests:\n\n" + "\n".join(f"- `{k}` ({len(v)}): " + ", ".join(f"`{t}`" for t in v) for k, v in by.items())


# ---------------------------------------------------------------- integrated system (TRL 4, Oct 2026)
INT = "integration/pipeline/runs/"
RUNS_ORDER = ["elliptic_1000", "synthetic_300_byz3", "synthetic_60_byz23", "synthetic_40_down1", "synthetic_1000"]
RUN_LABEL = {"elliptic_1000": "1,000 real Elliptic transactions, 4 honest validators", "synthetic_300_byz3": "300 synthetic, 1 Byzantine validator",
             "synthetic_60_byz23": "60 synthetic, 2 Byzantine validators", "synthetic_40_down1": "40 synthetic, 1 validator down",
             "synthetic_1000": "1,000 synthetic, a validator node crashed mid-run"}


def gen_int_runs():
    out = []
    for r in RUNS_ORDER:
        s = rjson(INT + r + "/summary.json")
        h, fa = s["honest"], s["faulty"]
        out.append((RUN_LABEL[r], s["source"], s["n"], s["faults_injected"], f"{h['settled_with_expected_outcome']} / {h['n']}",
                    f"{fa['reached_quorum']} / {fa['n']}", fa["ledger_changed"], f(s["timing_ms"]["end_to_end_ms"]["mean"], 0),
                    f"{s['gas']['settle']['mean']:,.0f}", f(s["wall_s"], 0), f(s["throughput_tx_per_min"], 1)))
    return table(["Run", "Source", "Requests", "Falsified", "Honest settled as expected", "Falsified reaching quorum", "Ledger changes by falsified",
                  "End-to-end mean ms", "Settle gas mean", "Wall s", "Tx / min"], out)


def gen_int_elliptic_detail():
    s = rjson(INT + "elliptic_1000/summary.json")
    rf = s["risk_flags"]
    a = table(["Honest outcomes", "Count"], [(k, v) for k, v in s["honest"]["outcomes"].items()])
    b = table(["Falsification type", "Injected", "All rejected (not submitted)"], [(k, v, "yes") for k, v in s["faulty"]["by_type"].items()])
    m = table(["Window", "Labelled", "Illicit", "TP", "FP", "FN", "TN", "Precision", "Recall", "F1"],
              [("all time steps", rf["labelled"], rf["illicit"], rf["tp"], rf["fp"], rf["fn"], rf["tn"], f(rf["precision"], 4), f(rf["recall"], 4), f(rf["f1"], 4))] +
              [(k.replace("time_steps_", "steps ").replace("_", "-"), v["labelled"], v["illicit"], v["tp"], v["fp"], v["fn"], v["tn"], f(v["precision"], 4), f(v["recall"], 4), f(v["f1"], 4))
               for k, v in rf.items() if k.startswith("time_steps_")])
    t = table(["Stage", "Mean ms", "Median ms", "p95 ms"], [(k.replace("_ms", ""), f(v["mean"], 1), f(v["median"], 1), f(v["p95"], 1)) for k, v in s["timing_ms"].items()])
    g = table(["Gas", "Mean", "Median", "p95"], [(k, f"{v['mean']:,.0f}", f"{v['median']:,.0f}", f"{v['p95']:,.0f}") for k, v in s["gas"].items() if v])
    return ("Honest outcomes:\n\n" + a + "\n\nFalsified requests:\n\n" + b +
            f"\n\nH1 risk flag inside the proof (illicit blocked: {rf['illicit_blocked']}, illicit executed: {rf['illicit_executed']}):\n\n" + m +
            "\n\nTiming:\n\n" + t + "\n\nGas:\n\n" + g + f"\n\nProof size mean {s['proof_bytes']['mean']:,.0f} bytes.")


def gen_int_audit():
    a = rjson("integration/pipeline/audit/audit_report.json")
    rows = [(k, v["rows"], v["honest"], v["faulty"], v["csv_settled"], v["onchain_settle_txs"], v["rows_matching_chain_exactly"], v["n_mismatches"],
             v["faulty_requests_with_a_settle_tx"], v["min_validator_signatures"]) for k, v in a["runs"].items()]
    t = table(["Run", "CSV rows", "Honest", "Falsified", "CSV settled", "Settle txs on chain", "Rows matching chain exactly", "Mismatches",
               "Falsified with a settle tx", "Fewest validator signatures"], rows)
    return (f"Chain head {a['chain_head']}; {a['settle_txs_total']:,} settle transactions in total, {a['settle_txs_reverted']} reverted; "
            f"{a['settle_txs_not_in_any_run']} settle transactions belong to no recorded run (early functional tests and a deleted first 300-transaction attempt).\n\n" + t)


def gen_ind_validator():
    base = "integration/evidence/independent_validator/"
    cc, mc = rjson(base + "cross_check.json"), rjson(base + "reviewer/my_check.json")
    s1, s2 = rjson(base + "host/runs/independent_200/summary.json"), rjson(base + "host/runs/independent_200_b/summary.json")
    rows = [("Requests checked by the reviewer's validator", cc["reviewer_decisions"]), ("Signed", cc["reviewer_signed"]), ("Refused", cc["reviewer_refused"]),
            ("Host honest / falsified", f"{cc['host_honest']} / {cc['host_falsified']}"), ("Settled on the ledger", cc["host_settled"]),
            ("Settled == reviewer-signed", cc["settled_equals_reviewer_signed"]), ("Settled == honest", cc["settled_equals_honest"]),
            ("Signatures on each settled request", cc["signatures_on_settled"]), ("Signatures on each falsified request", cc["signatures_on_falsified"]),
            ("Refusal reason matches the falsification", cc["reason_matches_falsification"]), ("Refusals by falsification", cc["refusals_by_falsification"]),
            ("Host validators: identical decisions", all(cc[f"host_validator_{i}_same_request_ids_and_decisions"] for i in range(3))),
            ("First attempt (reviewer unreachable): requests settled", cc["first_attempt_reviewer_unreachable_settled"]),
            ("Reviewer's own-ledger checks (self-reported)", cc["reviewer_own_ledger_check"]), ("all_ok", cc["all_ok"])]
    runs = table(["Run", "Honest settled", "Honest outcomes", "Falsified reaching quorum", "Wall s"],
                 [("independent_200 (first attempt, reviewer unreachable)", f"{s1['honest']['settled']} / {s1['honest']['n']}", s1["honest"]["outcomes"], s1["faulty"]["reached_quorum"], f(s1["wall_s"], 1)),
                  ("independent_200_b (settled run)", f"{s2['honest']['settled']} / {s2['honest']['n']}", s2["honest"]["outcomes"], s2["faulty"]["reached_quorum"], f(s2["wall_s"], 1))])
    reasons = table(["Refusal reason (reviewer)", "Count"], [(k, v) for k, v in mc["refusal_reasons"].items()])
    return (table(["Check", "Result"], [(a, str(b)) for a, b in rows]) + "\n\n" + runs + "\n\n" + reasons +
            f"\n\nContract `{mc['gate']}`, {mc['attesters']} attesters, threshold {mc['threshold']}. Reviewer validator address `{mc['my_address'][0]}`.")


def gen_h1_v21():
    g = rjson("h1-zkopml-v2/results/gas_v2.json")
    s = g["summary"]
    rows = [(k, v["step"], f"{v['commit']:,}", f"{v['challenge']:,}", f"{v['openFinal']:,}", f"{sum(v['reveal']):,}", f"{sum(v['respond']):,}", f"{v['resolve_mock']:,}", f"{v['game_total']:,}") for k, v in g["disputes"].items()]
    t = table(["Dispute (mock verifier)", "Step", "Commit", "Challenge", "openFinal", "Reveals total", "Responds total", "Resolve (mock)", "Game total"], rows)
    d = rjson("h1-zkopml-v2/results/onchain_disputes_B60.json")
    e = rjson("h1-zkopml-v2/results/onchain_disputes_B60_elliptic.json")

    def sc(x):
        items = x["scenarios"].items() if isinstance(x["scenarios"], dict) else enumerate(x["scenarios"])
        return [(k, v["scenario"], v.get("step_name", "—"), v.get("shape", "—"), v["bisection_rounds"], f(v.get("prove_s"), 1) if v.get("prove_s") else "none needed",
                 v["winner"], "yes" if v["outcome_correct"] else "NO", f"{v['gas']['game_total']:,}") for k, v in items]
    hdr = ["#", "Scenario", "Step", "Shape", "Rounds", "Step proof s", "Winner", "Correct", "Game gas (real verifier)"]
    ver = table(["Verifier shape", "Steps served", "logrows", "Deploy gas", "Bytecode KB", "Setup s", "Proving key MB"],
                [(k, v["steps_served"], v["logrows"], f"{v['deploy_gas']:,}", f(v["bytecode_kb"], 1), f(v["setup_s"], 1), f(v["pk_mb"], 0)) for k, v in d["verifiers"].items()])
    sm = rjson("h1-zkopml-v2/results/same_machine_step_vs_mono.json")
    mono = sm["monolithic_60_blocks"]["prove_mean_s"]
    same = table(["Proof", "Weights", "logrows", "Trials (s)", "Mean s", "Speedup vs whole model"],
                 [(k, v["weights"], v["logrows"], " / ".join(f(t, 1) for t in v["prove_times_s"]), f(v["prove_mean_s"], 1), f(mono / v["prove_mean_s"], 2) + "×") for k, v in sm.items() if isinstance(v, dict)])
    summ = table(["Quantity", "Value"], [("Monolithic verification gas", f"{s['monolithic_verify']:,}"), ("Commit per inference", f"{s['commit_per_inference']:,}"),
                                         ("Undisputed ratio", f(s["undisputed_ratio"], 2) + "×"), ("Full dispute, typical (estimate)", f"{s['full_dispute_typical_est']:,}"),
                                         ("Full dispute, worst (estimate)", f"{s['full_dispute_worst_est']:,}"), ("Per-dispute ratio, worst", f(s["per_dispute_ratio_worst"], 3) + "×"),
                                         ("Max dispute rate for 10×, worst / typical", pct(s["max_dispute_rate_for_10x_worst"], 2) + " / " + pct(s["max_dispute_rate_for_10x_typical"], 2))])
    return ("Dispute game gas with a mock verifier (hardened contract v2):\n\n" + t + "\n\nDerived:\n\n" + summ +
            f"\n\nShared verifiers deployed for the B = 60 model (total deploy gas {d['verifier_deploy_gas_total']:,}, game contract {d['game_deploy_gas']:,}):\n\n" + ver +
            "\n\nComplete games with real EZKL verifiers, first transaction:\n\n" + table(hdr, sc(d)) +
            "\n\nSame games on a second real Elliptic transaction (index 3,915):\n\n" + table(hdr, sc(e)) +
            f"\n\nSame-machine latency comparison ({sm['machine']}):\n\n" + same)


def gen_h3_learning():
    l = rjson("h3-abt/results/learning_report.json")
    d = l["design"]
    prim = table(["Test", "Agents", "Mean (first)", "Mean (second)", "z", "p one-sided", "Holm p", "Supported"],
                 [(x["test"], x["n"], pct(x["mean_first"]), pct(x["mean_second"]), f(x["mann_whitney_z"], 2), pval(x["p_one_sided"]), pval(x["p_holm"]), x["supported"]) for x in l["primary"]])
    desc = []
    for p, v in l["by_p"].items():
        for reg, r in v["descriptive"].items():
            desc.append((p, reg, pct(r["rate"]), pct(r["by_window"][0]), pct(r["by_window"][-1]), r["resets"], r["agents_depleted"], f(r["slashed_per_agent"], 1)))
    dt = table(["Detection p", "Regime", "Violation rate", "First 50 steps", "Last 50 steps", "Resets", "Agents depleted", "Slashed per agent"], desc)
    return (f"Design: seeds {d['seeds'][0]}–{d['seeds'][-1]}, {d['steps']} steps, {d['agents_per_seed']} agents per seed, detection p in {d['p_values']}, epsilon-greedy exploration {d['epsilon']}.\n\n"
            "Primary tests:\n\n" + prim + "\n\nPer regime:\n\n" + dt + f"\n\nOverall: `finding_supported` = {l['finding_supported']}.")


def gen_h4_v4():
    b = rjson("h4-pqc-stark/zk_composed/results/bench_summary.json")
    sec = rjson("h4-pqc-stark/zk_composed/results/security.json")
    info = rjson("h4-pqc-stark/zk_composed/results/info.json")
    v = table(["Variant", "Runs", "Proof bytes", "Prove ms mean ± sd", "Prove median", "Verify ms mean ± sd", "Verify median"],
              [(k, x["runs"], f"{x['proof_bytes']:,}", f(x["prove_ms_mean"], 1) + " ± " + f(x["prove_ms_sd"], 1), f(x["prove_ms_median"], 1),
                f(x["verify_ms_mean"], 2) + " ± " + f(x["verify_ms_sd"], 2), f(x["verify_ms_median"], 2)) for k, x in b["variants"].items()])
    r = table(["Comparison", "Size", "Prove", "Verify"], [(k, f"{x['size']}×", f"{x['prove']}×", f"{x['verify']}×") for k, x in b["ratios"].items()])
    s = table(["Variant", "Conjectured bits", "Proven (list decoding) bits", "Proven (unique decoding) bits", "FRI queries", "log blowup", "Quotient chunks", "Constraints"],
              [(k, x["conjectured_bits"], x["proven_list_decoding_bits"], x["proven_unique_decoding_bits"], x["fri"]["num_queries"], x["fri"]["log_blowup"], x["num_quotient_chunks"], x["num_constraints"]) for k, x in sec.items() if isinstance(x, dict)])
    return (f"Circuit: {info['rows']} rows, {info['width_classical']} columns classical, {info['width_pq']} PQ; SIS {info['sis_rows']} rows, expected collisions 2^{info['sis_log2_expected_collisions']:.1f}; "
            f"model digest `{info['model_digest'][:16]}…`.\n\n" + v + "\n\nRatios:\n\n" + r + "\n\nSecurity of the whole proof:\n\n" + s)


# ---------------------------------------------------------------- hardware integration (Oct 2026, after the faculty review)
def sup(k):
    return "2" + str(k).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))

def gen_hw_resources():
    d = rjson("h1-zkopml-v2/results/dispute_resources.json")
    label = {"monolithic_60_blocks": "Whole 60-block model", "block_step_fixed": "One block step, weights fixed (own verifier)",
             "block_step_hashed": "One block step, weights hashed (shared verifier)", "projection_step_fixed": "One projection half, weights fixed",
             "projection_step_hashed": "One projection half, weights hashed (shared verifier)"}
    a = table(["Proof", "Circuit rows", "Proving key MB", "SRS MB", "Peak memory MB", "Prove s (this run)", "Proof KB", "Verified"],
              [(label[k], f"{sup(v['logrows'])} = {v['rows']:,}", f(v["pk_mb"], 1), f(v["srs_mb"], 1), f"{v['peak_rss_mb']:,}", f(v["prove_s"], 2), f(v["proof_kb"], 1), v["verified"])
               for k, v in d.items() if isinstance(v, dict) and "logrows" in v])
    z = rjson("h4-pqc-stark/zk_composed/results/resources.json")
    b = table(["Composed proof (pq_zk)", "Value"], [("Prover peak memory", f"{z['prove']['peak_rss_mb_max']} MB"), ("Verifier peak memory", f"{z['verify']['peak_rss_mb_max']} MB"),
                                                  ("Verifier binary (stripped)", f"{z['binary_stripped_mb']} MB"), ("Proof", f"{z['proof_bytes']:,} bytes"),
                                                  ("Statement", f"{z['statement_bytes']} bytes"), ("Runs per measurement", z["prove"]["runs"])])
    c = rjson("h4-pqc-stark/zk_composed/results/cache_sim.json")
    cs = table(["Run", "Data accesses", "Misses", "Hit rate"],
               [(k.replace("_D1_", ", data cache ").replace("KiB", " KiB"), f"{v['data_refs']:,}", f"{v['misses']:,}", f"{v['hit_rate_pct']}%") for k, v in c.items() if isinstance(v, dict)])
    return (f"{d['machine']}:\n\n" + a + "\n\nComposed post-quantum proof (`zk_composed/results/resources.json`):\n\n" + b +
            f"\n\nCache simulation ({c['tool']}):\n\n" + cs)


def gen_hw_memory():
    p, pl = rjson("h1-zkopml-v2/results/memory_profile.json"), rjson("h1-zkopml-v2/results/memory_plans.json")
    rows = [(f"projection in {k} part(s): one part", sup(v['logrows']), f(v["pk_mb"], 1), v["peak_rss_mb"], f(v["prove_s"], 2)) for k, v in p["proj"].items()]
    rows += [(f"join step after {k} part(s)", sup(v['logrows']), f(v["pk_mb"], 1), v["peak_rss_mb"], f(v["prove_s"], 2)) for k, v in p["join"].items()]
    rows += [(f"{g} residual block(s) per step", sup(v['logrows']), f(v["pk_mb"], 1), v["peak_rss_mb"], f(v["prove_s"], 2)) for g, v in p["group"].items()]
    w = p["whole_model"]
    rows.append(("whole model (60 blocks)", sup(w['logrows']), f(w["pk_mb"], 1), w["peak_rss_mb"], "—"))
    prof = table(["Step shape", "Circuit rows", "Proving key MB", "Peak memory MB", "Prove s"], rows)
    pr = []
    for b, q in pl["plans"].items():
        if q.get("whole_model_fits"):
            pr.append((f"{int(b):,} MB", "whole model fits", 1, 0, w["peak_rss_mb"], "—", "—"))
        else:
            v = q["validation"]
            pr.append((f"{int(b):,} MB", f"k = {q['proj_parts']}, g = {q['blocks_per_step']}", q["steps"], q["bisection_rounds"], q["predicted_peak_mb"],
                       v["measured_peak_mb_other_positions"], "yes" if v["within_budget"] and v["all_proofs_verified"] else "NO"))
    plans = table(["Node budget", "Plan", "Steps", "Bisection rounds", "Predicted peak MB", "Measured peak MB (other positions)", "Within budget, all verified"], pr)
    return (f"Hardware profile ({p['machine']}):\n\n" + prof + f"\n\nPlans (margin {int(pl['margin'] * 100)}%):\n\n" + plans)


def _scen(d, skip=()):
    rows = []
    for k, v in d.items():
        if k in skip:
            continue
        if isinstance(v, dict):
            res = "accepted" if v.get("ok") or v.get("accepted") else ("refused" if ("ok" in v or "accepted" in v) else "")
            why = v.get("reason") or ", ".join(f"{a}: {b}" for a, b in v.items() if a not in ("ok", "accepted", "credential_tx", "operator_id", "reason") and not isinstance(b, (dict, list)))
            why = str(why).replace("|", "/").replace("\n", " ")[:220]
            rows.append((k.replace("_", " "), f"**{res}**: {why}" if res else why))
        else:
            rows.append((k.replace("_", " "), str(v)))
    return table(["Scenario", "Outcome"], rows)


def gen_hw_identity():
    h = rjson("integration/hw_identity/results/hw_identity.json")
    t = h["timing_ms"]
    return (_scen(h["scenarios"]) + f"\n\nAll as expected: **{h['all_as_expected']}**. Median of {t['runs']}: TPM increment + certify {t['tpm_increment_and_certify_median']} ms; "
            f"registry verification {t['registry_verify_median']} ms. Environment: {h['environment']['tpm']}; tpm2-tools {h['environment']['tpm2_tools']}; {h['environment']['chain']}.")


def gen_hw_tee():
    d = rjson("integration/embodiments/results/tee_sim.json")
    s = d["scenarios"]
    dec = table(["Request to the approved environment", "Signed", "Reason", "Signature counts at settlement"],
                [(k, v["signed"], (v["reason"] or "—").split(": {")[0], v.get("signature_counts_at_settlement", "—")) for k, v in s["approved_enclave_decisions"].items()])
    rest = {k: v for k, v in s.items() if k not in ("approved_enclave_decisions",)}
    return (dec + "\n\n" + _scen(rest) + f"\n\nAll as expected: **{d['all_as_expected']}**. TPM quote {d['timing_ms']['tpm_quote']} ms; check and sign {d['timing_ms']['enclave_check_and_sign_median']} ms (median). Limits: {d['limits']}.")


def gen_hw_offline():
    d = rjson("integration/embodiments/results/offline_sim.json")
    s = d["scenarios"]
    sync = table(["Payee", "Amount", "Declared total", "Counter", "Settled", "Reason"],
                 [(x["payee"], f"{x['amount']:,}", f"{x['declared_total']:,}", x["counter"], x["settled"], x["reason"]) for x in s["14_sync"]])
    m = d["measurements"]
    meas = table(["Measurement", "Value"], [(k.replace("_", " "), v) for k, v in m.items()])
    return (_scen({k: v for k, v in s.items() if k not in ("14_sync",)}) + "\n\nSynchronisation (all payees together, settled in secure-element counter order):\n\n" + sync +
            "\n\n" + meas + f"\n\nAll as expected: **{d['all_as_expected']}**; settled total {d['settled_total']:,}.")


GENERATORS = {
    "pr_history": gen_pr_history, "commit_count": gen_commit_count, "artifact_index": gen_artifact_index,
    "h1_seeds": gen_h1_seeds, "h1_quant": gen_h1_quant, "h1_steps": gen_h1_steps, "h1_sweep_committed": gen_h1_sweep_committed,
    "h1_disputes": gen_h1_disputes, "h1_gas": gen_h1_gas,
    "h2_inst_stats": gen_h2_inst_stats, "h2_scarcity_counts": gen_h2_scarcity_counts, "h2_v1_baseline": gen_h2_v1_baseline,
    "h2_v1_seed42": gen_h2_v1_seed42, "h2_v1_summary": gen_h2_v1_summary, "h2_v1_paired": gen_h2_v1_paired, "h2_v1_ablations": gen_h2_v1_ablations,
    "h2_v2_summary": gen_h2_v2_summary, "h2_v2_primary": gen_h2_v2_primary, "h2_v2_secondary": gen_h2_v2_secondary,
    "h2_v2_refined": gen_h2_v2_refined, "h2_v2_privacy": gen_h2_v2_privacy, "h2_v2_per_seed": gen_h2_v2_per_seed,
    "h2_v2_ablation_per_seed": gen_h2_v2_ablation_per_seed, "h2_mr_primary": gen_h2_mr_primary, "h2_mr_by_method": gen_h2_mr_by_method,
    "h2_mr_per_seed": gen_h2_mr_per_seed, "h2_mr_repro": gen_h2_mr_repro, "h2_tests": lambda: _pytest_list("h2-federated-aml"),
    "h3_confirmatory": gen_h3_confirmatory, "h3_per_agent": gen_h3_per_agent, "h3_depletion": gen_h3_depletion, "h3_agent_level": gen_h3_agent_level,
    "h3_durable": gen_h3_durable, "h3_durable_per_seed": gen_h3_durable_per_seed, "h3_tests": lambda: _pytest_list("h3-abt"),
    "h3_sybil_output": lambda: "```text\n" + sh("python", "run_sybil.py", cwd=ROOT / "h3-abt").strip() + "\n```",
    "h4_v1_bench": gen_h4_v1_bench, "h4_v2_bench": lambda: gen_h4_bench(H4 + "benchmark_v2/results/benchmark_v2.csv"),
    "h4_v3_bench": lambda: gen_h4_bench(H4 + "benchmark_v2/results/benchmark_v3.csv"),
    "h4_coverage_bench": lambda: gen_h4_bench(H4 + "benchmark_v2/results/benchmark_coverage.csv"),
    "h4_composed_bench": lambda: gen_h4_bench(H4 + "benchmark_v2/results/benchmark_composed.csv"),
    "int_runs": gen_int_runs, "int_elliptic_detail": gen_int_elliptic_detail, "int_audit": gen_int_audit, "ind_validator": gen_ind_validator,
    "h1_v21": gen_h1_v21, "h3_learning": gen_h3_learning, "h4_v4": gen_h4_v4,
    "h4_estimator": gen_h4_estimator, "h4_specs": gen_h4_specs, "h4_tests": gen_h4_tests,
    "hw_resources": gen_hw_resources, "hw_memory": gen_hw_memory, "hw_identity": gen_hw_identity, "hw_tee": gen_hw_tee, "hw_offline": gen_hw_offline,
}


def expand(text):
    def repl(m):
        kind, arg = m.group(1), m.group(2)
        if kind == "gen":
            return GENERATORS[arg]()
        if kind == "md":
            path, _, shift = arg.partition("|")
            return demote((ROOT / path).read_text(encoding="utf-8"), int(shift or 0))
        if kind == "git":
            rev, path_shift = arg.split(":", 1)
            path, _, shift = path_shift.partition("|")
            return demote(sh("git", "show", f"{rev}:{path}"), int(shift or 0))
        if kind == "code":
            return "```text\n" + (ROOT / arg).read_text(encoding="utf-8").rstrip() + "\n```"
        raise ValueError(kind)
    return re.sub(r"\{\{(gen|md|git|code):([^}]+)\}\}", repl, text)


def main():
    parts = [expand(p.read_text(encoding="utf-8")) for p in sorted((HERE / "sections").glob("*.md"))]
    OUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes, {sum(len(p.splitlines()) for p in parts):,} lines)")


if __name__ == "__main__":
    main()
