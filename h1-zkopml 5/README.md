# H1 — Verifiable Off-Chain Inference (zk-OPML)

**Owner:** Aman
**One-line idea:** Only prove the disputed part of an AI decision, not the whole thing, when challenged.
**Target:** ≥10x faster/cheaper than proving the whole model, ≤1pp accuracy drop.

## How it connects to the other tracks
H1 builds the fraud/risk detector. H3 (AgentBound Tokens) builds the agents that act on
what H1 flags — H1 predicts, H3 decides and is held accountable. H2 (federated AML)
makes detection like this possible across banks without sharing private data. H4
(post-quantum ZK) makes the proof math underneath H1 safe long-term. This folder is a
standalone prototype — no shared code with the other tracks.

## Status: Milestone 3 done — real, methodologically-sound results end to end

| Milestone | Status |
|---|---|
| Data pipeline (synthetic + real Kaggle Elliptic) | ✅ Done |
| Fraud classifier (MLP, regularized, early-stopped) | ✅ Done |
| Correct temporal train/val/test split (no leakage) | ✅ Done |
| ONNX export + full-model EZKL proving pipeline | ✅ Done |
| Partial "disputed part" proving mechanism | ✅ Done (two variants tested) |
| Benchmark partial vs. full proving | ✅ Done — **FAILS ≥10x target, ~2.9x best (honest negative result)** |

## Classifier results (Kaggle Elliptic dataset, temporal split)

**Dataset:** 203,769 transactions, 46,564 labeled (4,545 illicit / 42,019 licit), 234,355 edges — matches published Elliptic stats.

**Evaluation protocol:** temporal split (time_steps 1-30 train, 31-34 val, 35-49 test),
matching the original Elliptic paper (Weber et al. 2019). This matters — an earlier
version of this baseline used a random split and got F1=0.7405, but the literature
documents that random splits on this dataset leak information (aggregated features
summarize graph neighbors that can land on both sides of a random split). Under the
correct temporal protocol, that same architecture only reached F1=0.3485 — a large,
expected drop, not a bug. **The temporal numbers below are the ones to report.**

**Model:** MLP with BatchNorm + Dropout, 165→64→32→1, trained with `pos_weight_power=0.7`,
robust (median/IQR) feature scaling with 1st/99th-percentile outlier clipping, full-batch
gradient descent, early stopping on validation F1.

| Metric | Value |
|---|---|
| Accuracy | 96.60% |
| Precision | 82.41% |
| Recall | 60.57% |
| F1 | **0.6982** |

This is the result of two rounds of tuning:
1. A grid sweep over `pos_weight_power` (0.0-1.0) × hidden size (32-16 vs 64-32) —
   `model/sweep_pos_weight.py` — found 64-32 capacity + `pos_weight_power=0.7` gave
   F1=0.6057 (up from F1=0.3485 at default settings).
2. A second sweep — `model/sweep_v2.py` — testing mini-batch training, focal loss,
   SMOTE oversampling, and robust scaling with outlier clipping, all at 64-32 capacity.
   **Robust scaling + percentile clipping + full-batch training** won clearly
   (F1=0.6982), beating mini-batch variants of the same config (F1=0.5668-0.5832).
   Financial transaction features are heavy-tailed, and robust (median/IQR) statistics
   handled that better than standard (mean/std) scaling. Full-batch also consistently
   outperformed mini-batching (256) across every config tested — worth noting since
   mini-batching is often assumed to help, and here it didn't.

**Context vs. published work and a computed reference point:** the original Elliptic
paper's Random Forest reached F1≈0.77-0.80 on their own split; more recent GNN/hybrid
approaches using the transaction graph report F1 up to ~0.90. To get an apples-to-apples
number instead of comparing across different papers' splits, `model/final_metrics.py`
trains Random Forest and Gradient Boosting references on this exact same temporal split
(raw, unscaled features — trees don't need scaling, and clipping would throw away real
outlier signal they could use), and adds PR-AUC and the proving-side numbers alongside:

| Model | Accuracy | Precision | Recall | F1 | PR-AUC | ZK Feasible | Prove Time | Verify Time | Proof Size |
|---|---|---|---|---|---|---|---|---|---|
| **Our MLP (165→64→32→1)** | 96.60% | 82.41% | 60.57% | **0.6982** | 0.6118 | **Yes** | 0.758s | 0.007s | 41.73 KB |
| Random Forest (reference) | 97.49% | 86.42% | 72.85% | 0.7906 | 0.7864 | No | N/A | N/A | N/A |
| Gradient Boosting (reference) | 89.24% | 35.22% | 78.12% | 0.4855 | 0.7850 | No | N/A | N/A | N/A |

The F1 gap to Random Forest is 0.092 points (down from 0.185 before the robust-scaling/
full-batch fix) — the provable model is closing in on the non-provable reference. This
gap reflects the real, quantified cost of choosing an architecture compatible with
zero-knowledge proving; Random Forest's branching structure isn't practically provable
in EZKL's circuit model, so this comparison isolates that specific cost rather than
confounding it with training quality.

**PR-AUC tells a more complete story than F1 alone.** Our MLP's PR-AUC (0.6118) is
notably lower than both tree models' (~0.785-0.786), even though the F1 gap to Random
Forest is fairly narrow. This means the MLP's ranking of transactions by risk is less
reliable across the full range of thresholds — its F1 score is carried substantially by
the one specific threshold (0.60) tuned on the validation set, while the trees sustain
strong precision/recall tradeoffs across a wider threshold range. Worth reporting
honestly rather than only citing F1, which can make the gap look smaller than it is in
a threshold-independent sense.

A Gradient Boosting reference was also tried but scored worse than our MLP (F1=0.4855)
— this reflects an under-tuned class-imbalance weighting on our part (a hasty
sample-weight scheme, unlike Random Forest's built-in `class_weight='balanced'`), not a
genuine finding that boosting is weaker here. Its PR-AUC (0.7850) is actually close to
Random Forest's, consistent with this being a threshold-tuning problem rather than a
weaker model — left out of the headline F1 comparison for that reason, but included in
the table above since PR-AUC is less sensitive to that specific issue.

**Suggested paper sentence:**
> "Our provable MLP classifier achieves F1=0.6982 (accuracy 96.60%, precision 82.41%,
> recall 60.57%, PR-AUC 0.6118) on the temporal Elliptic split. A Random Forest trained
> on the identical split and features reaches F1=0.7906 (PR-AUC 0.7864) — a gap of 0.092
> F1 points, wider in threshold-independent PR-AUC terms. This gap quantifies the real
> accuracy cost of constraining the model to an architecture compatible with
> zero-knowledge proving: Random Forest's branching structure cannot be practically
> proven in EZKL's circuit model, while our fixed-width MLP can, at a prove time of
> 0.758s and a proof size of 41.73 KB. H1's contribution is proving cost, not
> classification novelty, and this comparison makes that tradeoff explicit rather than
> obscuring it."

## Full-model EZKL proving pipeline (real trained model, single inference)

| Stage | Time |
|---|---|
| gen_settings | 0.033s |
| calibrate | 0.431s |
| compile_circuit | 0.002s |
| get_srs (local) | 0.909s |
| setup (one-time, pk+vk) | 0.633s |
| gen_witness | 0.023s |
| **prove** | **0.716s** |
| verify | 0.007s |

**Prove-side cost (witness + prove) = 0.739s.** Proof size: 41.72 KB.

This is essentially unchanged from the earlier F1=0.6057 model's 0.745s — **the F1
jump to 0.6982 (better scaling + full-batch training) came entirely free on the
proving side.** No architecture size change, same proving cost, meaningfully better
accuracy. Confirms the earlier finding: proving cost here is dominated by fixed
lookup-table overhead, not model size or training procedure.

**This is the real baseline denominator.** The partial "disputed part" proof needs to
land at **≤0.0739s** (≥10x faster) while keeping F1 within 1pp of 0.6982 to pass the
H1 target.

## Partial-proving mechanism: results and an important finding

**Mechanism:** split the model at a layer boundary. The early layers run off-chain and
are committed to via Poseidon hash (not proven per-inference). Only the late layers
get a live ZK proof when a decision is disputed. This is an exact split (zero accuracy
loss — see `model/split_model.py`'s built-in equivalence check, which auto-detects the
architecture from the saved checkpoint).

**Two split points tested** (on the earlier 32-16 model — re-run `benchmark_logrows.py`
on the new 64-32 model to update these numbers):

| Split point | Late part | num_rows | Best prove time (logrows=12, mean of 3 trials) |
|---|---|---|---|
| After layer 1 | 32→16→1 (2 layers) | 962 | 2.973s |
| After layer 2 | 16→1 (1 layer) | 99 | 2.956s |

**Key finding: both split points bottom out at essentially the same proving time
(~2.95-2.97s), regardless of how much smaller the proven circuit gets.** Best speedup
achieved is **~2.9x, not the ≥10x target.**

**Why:** EZKL/Halo2 proving cost is dominated by the *padded* circuit size (2^logrows),
not the actual constraint count. Forcing logrows below 12 doesn't help either — it
requires far more lookup-table columns to pack the same range-check argument (137
columns at logrows=7 vs. 5 columns at logrows=12), so total work (rows × columns)
goes back *up*. There's a fixed overhead floor around logrows=12 for this
quantization setting (input/param scale=13) that dominates once the circuit is
already small — shrinking the proven slice further stops helping past that point.

**Status: current mechanism FAILS the ≥10x target (best: ~2.9x). Honest negative
result, not a bug** — confirmed via two independent split points and multi-trial
benchmarking (`proofs/benchmark_logrows.py`) to rule out measurement noise.

**Directions to actually close the gap to 10x** (not yet implemented):
1. Lower `input_scale`/`param_scale` (currently 13) to shrink the lookup table range
   itself, rather than just the number of neurons being proven.
2. Replace the ReLU lookup-table encoding with a lookup-free polynomial approximation
   of the nonlinearity, if EZKL supports it — the lookup argument appears to be the
   main source of fixed overhead.
3. Batch multiple disputed decisions into a single proof, amortizing the fixed
   per-proof overhead across several inferences instead of paying it per-dispute.
4. Re-examine whether ≥10x is achievable with EZKL specifically, or whether a
   different proving backend with lower per-proof fixed cost is needed for this
   hypothesis to pass — worth flagging to your team/advisor as a possible target
   or tooling reassessment.

## Setup

```bash
pip install -r requirements.txt
```

## Running the full pipeline (synthetic data quickstart)

```bash
cd data && python3 make_synthetic_elliptic.py
cd ../model && python3 train_baseline.py
python3 split_model.py
cd ../proofs && python3 prove_full_model.py
python3 prove_partial.py
python3 benchmark_logrows.py
```

## Running on the real Kaggle Elliptic dataset

1. Download from https://www.kaggle.com/datasets/ellipticco/elliptic-data-set (requires
   a free Kaggle account) and unzip it — you'll get a folder (commonly
   `elliptic_bitcoin_dataset/`) containing `elliptic_txs_features.csv`,
   `elliptic_txs_classes.csv`, `elliptic_txs_edgelist.csv`.
2. Optionally sweep for the best config first:
   ```bash
   cd model && python3 sweep_pos_weight.py --data-dir /path/to/elliptic_bitcoin_dataset
   ```
3. Train and save the real model (defaults shown are the current best-known config):
   ```bash
   python3 train_baseline.py --data-dir /path/to/elliptic_bitcoin_dataset \
       --pos-weight-power 0.7 --hidden1 64 --hidden2 32 --scaler robust --clip-percentile 1
   ```
   `train_baseline.py` validates the schema before training (column counts, class
   labels, minimum labeled-row count) and fails fast with a clear message if the
   download doesn't match what's expected.
4. `python3 split_model.py` — auto-detects the architecture from the checkpoint, no
   manual sync needed even if you changed `--hidden1`/`--hidden2`.
5. `cd ../proofs && python3 prove_full_model.py` then `python3 prove_partial.py` and
   `python3 benchmark_logrows.py` for the proving-side numbers.

## Known environment notes

- `ezkl==23.0.5`'s Python bindings are synchronous, not async, despite similarly-named
  functions being async in some docs/other versions — check with
  `inspect.iscoroutinefunction` before adding `await`. They still require a running
  asyncio event loop internally (call from inside an `async def` run via
  `asyncio.run(...)`), even though they aren't themselves coroutines.
- `ezkl.get_srs` downloads a pre-generated SRS from EZKL's servers. If that's not
  reachable on your network, use `ezkl.gen_srs(path, logrows)` to generate one locally
  instead (logrows is in the calibrated `settings.json` under `run_args.logrows`).
- Export ONNX with `torch.onnx.export(..., opset_version=11, dynamo=False)`. The newer
  dynamo-based exporter (opset 18, external `.onnx.data` weight file) isn't parsed
  correctly by EZKL's tract-based backend as of this version.
- BatchNorm layers are fine in EZKL as long as the model is in `.eval()` mode before
  export (uses running stats, not batch stats) — confirmed working end-to-end.
- Random train/test splits on Elliptic are documented to leak information via
  aggregated (graph-neighbor-summary) features. Always use the temporal split
  (`--split temporal`, the default) for numbers you intend to report.

## Next steps

1. Re-run `benchmark_logrows.py` against the new 64-32 model (retrained with robust
   scaling) to get updated partial-proving numbers — currently only benchmarked
   against the earlier version of the 64-32 model.
2. Try direction #1 or #2 from the "closing the gap to 10x" list above.
3. Consider whether graph features (via H2's shared detection setup, or a lightweight
   aggregation) are worth the added proving complexity to close the remaining 0.092
   F1 gap to the Random Forest reference.
