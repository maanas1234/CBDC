# H1 — Verifiable Off-Chain Inference (zk-OPML)

**Owner:** Aman

**Exact hypothesis:** Restructuring AML/credit-risk inference as a bisectable ONNX computation graph under an Optimistic-ML dispute protocol (zk-OPML) will reduce end-to-end proof-generation latency and on-chain verification cost by at least an order of magnitude relative to monolithic ZKML proofs, without degrading model accuracy by more than 1 percentage point.

**In simple words:** Instead of proving a fraud/credit-risk AI's entire decision every time (slow, expensive), assume it's correct by default. If someone challenges it, narrow down to the exact disputed step (bisection, like binary search) and prove only that part.

**Target:** ≥10x faster/cheaper proof generation & verification than proving the whole model, accuracy drop ≤1 percentage point.

**Status:** Not started — baseline (full ZKML proof) not yet built.

## What goes here

- Small AI model (fraud/credit-risk classifier), exported to ONNX
- Baseline: full ZK proof on the whole model + recorded latency/cost
- Bisection/dispute protocol implementation
- Benchmark comparing baseline vs bisected approach

## Note on scope

Bisection happens on the model's computation graph (its layers/operators), not on the transaction data itself — narrowing down WHICH LAYER caused a disputed output, not which transaction.
