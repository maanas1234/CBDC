# H1 zk-OPML prototype (v2)

This prototype tests an optimistic dispute protocol for AML inference on the Elliptic dataset:
- The model runs off-chain, and every intermediate step is committed with a Poseidon hash.
- A dispute is bisected down to a single step, and only that step is proven with EZKL.
- The result is compared against a monolithic EZKL proof of the whole model.

Results, method and pass/fail verdict: **[WRITEUP.md](WRITEUP.md)**.

## Layout

| File | Role |
|---|---|
| `prepare_data.py` | Kaggle CSVs → `X.npy`, `y.npy`, `ts.npy` (labelled rows only) |
| `data.py` | Temporal split and the fixed scaler |
| `train.py`, `train_suite.py` | NumPy residual-MLP trainer. Selection on validation only; 3 seeds per depth; writes `models/` |
| `onnx_builder.py` | Builds ONNX graphs from weights. `dispute_steps()` restructures the model into bisectable steps (projection split in two) |
| `quant.py`, `steps.py` | Fixed-point emulation of EZKL's arithmetic, matching it exactly; the step-level trace |
| `commit.py` | Poseidon leaves (same hash as EZKL's circuit hash) and the Merkle root |
| `prover.py` | EZKL pipeline for one circuit: settings, calibration on real data, compile, setup, prove ×N, verify |
| `bench_steps.py` | Proves single steps or the whole model (`mono`); writes `results/steps_B*.json` |
| `dispute.py` | End-to-end dispute scenarios: cheat, bisect, prove one step, verifier checks |
| `quant_accuracy.py` | Fixed-point vs float accuracy on the full test set |
| `check_quant.py` | Checks the emulator matches EZKL's witness exactly |
| `gas.py`, `gas_game.py`, `contracts/` | Deploy verifiers and the game contract on anvil; measure gas |
| `make_report.py` | Builds `results/summary.json` and `results/speedup_vs_depth.png` |

## Reproduce

```bash
pip install -r requirements.txt
python3 prepare_data.py /path/to/elliptic_bitcoin_dataset
python3 train_suite.py                      # models/W32_B{1,8,24,60}.pkl (models are included already)
python3 quant_accuracy.py 9                 # accuracy criterion
python3 check_quant.py                      # emulator == EZKL, exactly
for B in 1 8 24 60; do python3 bench_steps.py $B mono; done
python3 bench_steps.py 60 proj0 proj1 u1 u2 u30 u60 u61
python3 dispute.py 60 0 1 2 3 4 5 6
# gas (needs Foundry + solc 0.8.24): FOUNDRY_BIN=~/.foundry/bin SOLC=solc
python3 gas.py 60 mono:mono_ic2 proj0:proj0_ic4 u1:u1_ic2 u2:u2_ic2 u61:u61_ic2
python3 gas_game.py
python3 make_report.py
```

## Notes

- **Timings** in `results/` come from a single-CPU machine. Expect lower absolute times on a laptop;
  the speedup ratios are what matter.
- **Monolithic proof** of the 60-block model peaks around 1.3 GB RAM.
- **Solidity verifier.** `ezkl.create_evm_verifier` writes the Solidity file first, then tries to
  download solc to build the ABI. `gas.py` ignores that download error and compiles with the local solc.
- **EZKL settings used throughout:** input and parameter scale 9, `decomp_base` 256 with 4 legs. The
  smaller range-check table removes the size floor (2¹⁵ rows) that the default settings impose.
