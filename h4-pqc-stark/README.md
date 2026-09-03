# H4 — Post-Quantum Zero-Knowledge Proof Feasibility

**Owner:** Simran

**Exact hypothesis:** A lattice-based ZK-STARK construction can secure ZKML proof verification for the model classes used in H1–H3 while keeping proof size and verifier latency within a bounded overhead factor relative to classical (non-quantum-resistant) ZK-STARKs, making PQC migration practical without re-architecting the settlement layer.

**In simple words:** Today's cryptography can be broken by future quantum computers. Swap in quantum-resistant ("post-quantum") proof math and check it doesn't get too slow or too big to still be usable.

**Target:** Overhead (proof size / verifier latency) vs a classical (non-quantum) proof system stays within an agreed practical bound — bound must be defined before running the final experiment, not chosen after seeing results.

**Known issue to resolve before building:** The assigned reference paper (lattice-based construction) is a SNARK paper, but this hypothesis is about STARKs. SNARK and STARK are both zero-knowledge proof systems but built differently (SNARK needs a one-time "trusted setup" step; STARK doesn't, and is naturally more quantum-resistant since it only relies on hash functions rather than elliptic-curve math). Simran needs to either justify using SNARK-derived ideas for a STARK-based build, or find a better-matched paper before implementation starts.

**Status:** Not started — classical STARK baseline not yet built.

## What goes here

- Classical (non-quantum) ZK-STARK baseline on a small computation
- Post-quantum / lattice-based construction on the same computation
- Comparison: proof size + verifier latency, classical vs post-quantum
- Migration conclusion: practical or not
