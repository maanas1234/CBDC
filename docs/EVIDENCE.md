# Evidence for the integrated runs and the on-chain disputes

This page is for a reviewer who wants to confirm the TRL-4 numbers instead of taking them from our
summaries. It lists the raw records, the checks we ran against the ledger itself, and how to repeat
each check, from cheapest to strongest.

| Claim | Where the number comes from | How to check it yourself |
|---|---|---|
| Integrated runs (Elliptic 1,000 tx and the four synthetic runs): every honest request settled as recorded, no faulty request settled | `integration/pipeline/runs/*/transactions.csv` (driver record) | **Level 2:** replay the exported Besu chain and run `audit_chain.py` (10 min) |
| H1 on-chain disputes with real EZKL verifiers: 7/7 scenarios correct | `h1-zkopml-v2/results/onchain_disputes_B60*.json` | **Level 2:** load the recorded chain state and run `verify_dispute_record.py` (2 min); **Level 3:** re-run `onchain_dispute.py --record` |
| Independent validator (20–21 Oct 2026): a validator key and Besu node on a second person's machine, 4-of-4 gate; its validator signed exactly the 166 honest transfers, refused all 34 falsified ones, and nothing settled without it | `integration/evidence/independent_validator/` (both sides' records) | `python3 cross_check.py` in that folder (seconds); against the exported ledger: import it into your own Besu node and run `ledger_check.py` (about 5 min) |
| Hardware integration (28 Oct 2026): memory-budgeted plans within budget; TPM identity refuses 9 of 9 attacks; TEE and offline-device simulations | `h1-zkopml-v2/results/memory_plans.json`, `integration/hw_identity/results/`, `integration/embodiments/results/` | re-run `memory_planner.py`, `hw_identity/run_demo.py`, `embodiments/tee_sim.py` and `offline_sim.py` (software TPM; minutes each) |
| Test suites | the repository | `forge test`, `pytest`, `cargo test` (already confirmed by the reviewer) |

## Level 1 – the raw records

**Integrated pipeline (`integration/`)**
- `pipeline/runs/<run>/transactions.csv` – one row per request: index, Elliptic tx id and label, injected
  fault, amount, proven EXEC/VIOL, number of validator signatures, each refusing validator's reason, outcome,
  gas and timings. `summary.json` is computed from it.
- `evidence/run_logs/run_*.log` – the driver's console output of the last three long runs
  (`run_elliptic.log` = Elliptic 1,000; `run_1000.log` = synthetic 1,000; `run_byz3.log` = 300 with a
  Byzantine validator). The 60- and 40-transaction runs printed their summary to the terminal only; their
  CSVs and summaries are in `runs/`.
- `evidence/besu_node_logs/node{0..3}.log.gz` – the four Besu validators' own logs (warning level).
- `evidence/cbdc_besu_chain.blocks.gz` + `evidence/genesis.json` – **the whole ledger**: every block
  (8,757) and every transaction of all runs, exported from validator node 0 with `besu blocks export`.

**On-chain disputes (`h1-zkopml-v2/`)**
- `evidence/original_run_logs/` – console logs of the runs behind the committed result files (one
  line per scenario with the located step, winner and gas).
- `evidence/recorded_rerun_elliptic/` – a re-run made on 16 Oct 2026 with recording switched on, on the
  same real Elliptic transaction (test index 3,915): `transactions.jsonl` (all 116 transactions with
  hashes, status and gas), `proofs/` (every step proof and the exact `verifyProof` calldata),
  `anvil_state.json` (the complete chain state), `result.json` and `verification_report.json`.
  The original dispute runs used a throw-away local chain and kept only the outcome per scenario, which
  is why this recorded re-run exists.

## Level 2 – checks against the ledger (no trust in our CSVs or summaries)

### Integrated runs: `integration/pipeline/audit_chain.py`
The script reads every block of the chain, finds every `SettlementGate.settle` transaction, decodes the
request inside it, recovers the validator signatures (EIP-191) and checks them against the QBFT
validator set, reads the receipt, gas and `Settled` event, and only then compares with each run's CSV.
The request nonce is `run_start_time × 100000 + index`, which ties every on-chain request to one CSV row.

Result (`pipeline/audit/audit_report.json`; per-transaction table in `settlements_onchain.csv`):

| Run | CSV rows settled | `settle` transactions on the chain | Rows matching the chain exactly (index, amount, EXEC, VIOL, outcome, gas) | Faulty requests with any `settle` transaction | Fewest validator signatures on a settled request |
|---|---|---|---|---|---|
| elliptic_1000 | 889 | 889 | **889** | **0 of 111** | 4 |
| synthetic_1000 | 899 | 899 | 899 | 0 of 100 | 3 (node 3 was down for the first 373 tx) |
| synthetic_300_byz3 | 244 | 244 | 244 | 0 of 56 | 4 |
| synthetic_60_byz23 | 26 | 26 | 26 | 0 of 34 | 4 |
| synthetic_40_down1 | 25 | 25 | 25 | 0 of 15 | 3 (one validator off by design) |

- 2,197 `settle` transactions in total, none reverted, every one signed by ≥ 3 distinct QBFT validators
  and by nobody else.
- **Ledger balances:** the Elliptic run used a fresh deployment. On that contract the merchant's CBDC
  balance is 1,930,131, exactly the sum of the amounts the CSV records as Executed. The customers hold
  the rest of the 4 × 10¹² minted, so nothing else moved.
- **114 `settle` transactions belong to no run in `runs/`.** They are, by start time:
  - 4 from the first 12-transaction functional test (15 Oct, 08:57 IST);
  - 99 from the first 300-transaction attempt (09:00 IST), the run that exposed the composed-proof
    completeness bug (145 honest proofs failed; 99 settled). Its folder was deleted when the run was
    repeated after the fix; the bug and its numbers are reported in `integration/README.md`;
  - 6 from a smoke test after the validator-retry change (10:56 IST);
  - 5 from a smoke test of the Elliptic path (13:43 IST).

**To repeat it.** Versions we used: Hyperledger Besu 25.10.0 (Java 21), Python 3.13 with `web3` 8.0,
Foundry 1.5.1-stable (only for `forge build`, which produces the ABIs the decoder needs).

Every Besu node needs a node key. A bare-metal install creates one inside `--data-path`, but under
Docker the mounted folder is often not writable for the container user, so create one yourself and pass
it explicitly. Any key works: this node only replays blocks and never signs.
```bash
cd integration && forge build                      # contract ABIs for the decoder
gunzip -k evidence/cbdc_besu_chain.blocks.gz
mkdir -p /tmp/cbdc-replay && echo "0x$(openssl rand -hex 32)" > /tmp/cbdc-replay/key
besu --data-path=/tmp/cbdc-replay/data --genesis-file=evidence/genesis.json \
     --node-private-key-file=/tmp/cbdc-replay/key blocks import --from=evidence/cbdc_besu_chain.blocks
besu --data-path=/tmp/cbdc-replay/data --genesis-file=evidence/genesis.json \
     --node-private-key-file=/tmp/cbdc-replay/key --rpc-http-enabled \
     --rpc-http-api=ETH,NET,QBFT,WEB3 --p2p-enabled=false &        # read-only node on 127.0.0.1:8545
cd pipeline && python audit_chain.py /tmp/cbdc-audit             # compare with pipeline/audit/audit_report.json
```
With Docker (`hyperledger/besu:25.10.0`), the same two Besu commands become (we tested the key-file
flags with the native Besu 25.10.0 install; our build environment could not pull the Docker image):
```bash
mkdir -p replay && echo "0x$(openssl rand -hex 32)" > replay/key
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD/evidence:/ev:ro" -v "$PWD/replay:/r" hyperledger/besu:25.10.0 \
  --data-path=/r/data --genesis-file=/ev/genesis.json --node-private-key-file=/r/key \
  blocks import --from=/ev/cbdc_besu_chain.blocks
docker run -d --name cbdc-replay -u "$(id -u):$(id -g)" -p 8545:8545 -v "$PWD/evidence:/ev:ro" -v "$PWD/replay:/r" \
  hyperledger/besu:25.10.0 --data-path=/r/data --genesis-file=/ev/genesis.json --node-private-key-file=/r/key \
  --rpc-http-enabled --rpc-http-host=0.0.0.0 --host-allowlist="*" --rpc-http-api=ETH,NET,QBFT,WEB3 --p2p-enabled=false
```
Importing re-executes every block, so the replayed state (balances, slashes, registry) is recomputed
by your own node, not copied from ours. We ran exactly these commands on a fresh data directory; the
report was identical to the one from the original node.

### On-chain disputes: `h1-zkopml-v2/verify_dispute_record.py`
It rebuilds the recorded dispute chain and checks that all 116 logged transactions exist with the
logged status and gas; that each dispute's final phase, read from the game contract, names the winner
the summary reports; and that every recorded step proof, sent to its on-chain verifier, returns true.

**Foundry version.** The recording was made with **Foundry 1.5.1-stable** (anvil/forge commit
`b0a9dd9`, built 22 Dec 2025, EVM hardfork Prague). Its `anvil_state.json` uses that version's state
format, which newer releases cannot load (Foundry 1.8.5 rejects it with "data did not match any variant
of untagged enum SerializableTransactionType"). The verifier therefore **replays the chain by default**:
it starts an empty anvil (Prague, chain id 31337, the recorded genesis time) and sends the 116 recorded
*signed* transactions (`raw_transactions.jsonl`) with their original block timestamps. Because they
are signed, their hashes and all contract addresses come out identical, and your own EVM re-executes
every call. `--state` loads the state file instead (Foundry 1.5.1 only).

Result, identical with both Foundry versions we tried:

| Mode | Foundry | Transactions match | Winners match | Proofs verify on-chain | Report |
|---|---|---|---|---|---|
| replay (default) | 1.8.5 (commit 51a52c5) | 116/116 (status and gas) | 7/7 | 7/7 | `verification_report_replay.json` |
| `--state` | 1.5.1-stable (b0a9dd9) | 116/116 | 7/7 | 7/7 | `verification_report.json` |

The 7 proofs include the one made with another block's weights: the verifier accepts it, and the
game's `resolve` transaction with it is on the chain with status 0 (reverted: "params instance != step
weights").

```bash
cd h1-zkopml-v2 && python3 verify_dispute_record.py evidence/recorded_rerun_elliptic            # replay (any Foundry)
python3 verify_dispute_record.py evidence/recorded_rerun_elliptic --state                        # Foundry 1.5.1 only
```

Game gas in the recorded re-run differs from the committed result file by at most 0.2 % per scenario,
because zero-knowledge proofs are randomized and calldata gas depends on the proof bytes. Bisection
rounds, located steps and winners are identical.

## Level 3 – re-run it (strongest)

Levels 1–2 confirm that the records and the ledger agree. They cannot rule out that we built the
ledger dishonestly: all four validator keys were ours. Re-running on your own machine removes that.

**Disputes, about 10–20 minutes including a one-time setup (about 3 minutes, 3 GB of keys).** New
recordings also write `raw_transactions.jsonl`, so they replay with any Foundry version:
```bash
cd h1-zkopml-v2 && forge build
python3 prepare_data.py /path/to/elliptic_bitcoin_dataset     # writes X.npy, y.npy, ts.npy
python3 onchain_dispute.py --data . --record /tmp/my_run
python3 verify_dispute_record.py /tmp/my_run
```

**Integrated pipeline, a 100-transaction run takes about 4 minutes once built:**
```bash
cd h4-pqc-stark/zk_composed && cargo build --release
cd ../../integration && forge build && BESU=/path/to/besu chain/start_chain.sh
cd pipeline && python deploy.py && ./start_validators.sh
python run_pipeline.py --n 100 --source elliptic --data /path/to/elliptic_bitcoin_dataset --faults 0.1 --out runs/review_100
python audit_chain.py /tmp/review-audit
```
For an even stronger check, have someone outside the team run one validator on their own machine:
see [`docs/INDEPENDENT_VALIDATOR.md`](INDEPENDENT_VALIDATOR.md).

**Done once, 20–21 Oct 2026.** The network, the contract deployment and three validator keys ran on the
MacBook of a person outside the team; the fourth key and a separate Besu node were on Aman's MacBook Air,
connected over Tailscale, with the gate requiring all 4 signatures. Of 200 real Elliptic transfers (34
deliberately falsified), the fourth validator signed exactly the 166 honest ones and refused all 34
falsified ones, each for the matching reason; the ledger holds exactly those 166 settlements, each with 4
signatures, and its own-ledger checks are all `true`. A first attempt in which that validator could not be
reached settled nothing. Records, results and a cross-check script are in
[`integration/evidence/independent_validator/`](../integration/evidence/independent_validator/README.md).
The ledger of that run (3,033 blocks) was exported from the reviewer's node on 26 Oct 2026 and is in the
same folder (`independent_chain.blocks.gz`). Imported into a fresh node, it reproduces all 166 settlements
exactly as the host recorded them, each with all four signatures, and the reviewer's checks come out
identical (`ledger_check.py`, about 5 minutes including the import).

## Why `docs/EXHAUSTIVE_REPORT.md` changes when rebuilt
Five generated parts depend on when and where the build runs: the commit count (read from `git log`; the
committed copy is always built before the commit that adds it), the tracked-file index with sizes, the
embedded READMEs, the live test listings (H2 needs `torch` and `torch-geometric`, H4 needs a Rust
toolchain, otherwise those lists come out empty or short), and the seeded H3 Sybil run. Until 20 Oct 2026
the index also listed the report's own size, so no rebuild could ever reproduce it byte for byte; it now
prints "(this file)". Two rebuilds in a row on the same checkout and environment are now byte-identical.
Details are at the top of the report.

## Large files
The ledger export is 3.5 MB compressed and the dispute record 2.7 MB, so both are kept in the
repository; no release asset is needed.
