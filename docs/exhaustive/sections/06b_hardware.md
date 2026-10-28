# Part 6B — Hardware integration, October 2026

**Added by:** Aman Hooda (PR #43), 26–28 Oct 2026, after a faculty review of the invention disclosure (IDF-B). **Independently verified:** not yet; everything in this part comes from Aman's runs on a 2-vCPU, 8 GB cloud machine.

Code: `h1-zkopml-v2/bench_resources.py`, `h1-zkopml-v2/memory_planner.py`, `h4-pqc-stark/zk_composed/measure_resources.py`, `integration/hw_identity/` (TPM identity), `integration/embodiments/` (TEE and offline-device simulations). Results: the `results/` folder next to each script.

**Why this part exists.** The faculty pointed out that an Indian examiner would very likely object under Section 3(k) of the Patents Act (computer programme *per se*, mathematical or business method). The current test (the 2025 Guidelines for Examination of Computer Related Inventions; *Ferid Allani*, Delhi HC 2019; *Microsoft*, Delhi HC 2024) asks for a technical effect, not new hardware. So the work below makes hardware properties and hardware components **steps of the method**, and measures their effect on the machines. It adds:
- a decomposition of the H1 model computed from the prover node's memory (§6B.2);
- measurements of what each proof costs the machine (§6B.1);
- an operator identity anchored in a TPM 2.0 (§6B.3);
- a simulated verify-then-sign trusted execution environment for validators (§6B.4);
- simulated offline payment devices with a secure element (§6B.5).

What was **left out on purpose**, because it was not built or measured: "eliminates DRAM bottlenecks", network-card packet filtering, AVX-512, and a speed-up combined with shared verifiers (§6A.2 measured that shared verifiers cancel the speed-up).

## 6B.1 What each proof costs the machine

*(generated from `h1-zkopml-v2/results/dispute_resources.json`, `h4-pqc-stark/zk_composed/results/resources.json` and `cache_sim.json`)*

{{gen:hw_resources}}

**Reading.**
- **Dispute steps with their own verifier are much lighter.** A block step with its weights fixed in its verifier has 32× fewer circuit rows than the whole 60-block model, a 13.5× smaller proving key, and needs 11.6× less memory (107 MB against 1,243 MB).
- **Shared verifiers cost more, not less.** With the weights hashed, a step needs 1.4–4.0 GB, as much as or more than the whole model. They save deployment gas (§6A.2) but not proving resources.
- **The composed proof fits small devices.** It needs about 20 MB to prove and 12.5 MB to verify, with a 2.4 MB verifier program. Each ledger node stores a 32-byte hash of it instead of the 170 KB proof.
- **The cache simulation is only a measurement.** No other trace layout was compared, so it does not show that the layout causes the high hit rate.

## 6B.2 Memory-budgeted decomposition

*(generated from `h1-zkopml-v2/results/memory_profile.json` and `memory_plans.json`, written by `memory_planner.py`)*

**Method.** Before deployment, the prover node:
1. Reads its memory budget M (its container limit or available RAM).
2. Uses a **hardware profile** of its own machine: one circuit of each candidate step shape, proven in a fresh process, with its size, proving key and peak memory recorded.
3. Chooses the smallest number k of partial-neuron parts for the 165→32 projection and the largest number g of residual blocks per step whose measured peak is at most 0.9·M.
4. If the whole model fits, a dispute needs no bisection. Otherwise the plan has n = k + 1 + ⌈59/g⌉ + 1 steps and a dispute takes ⌈log₂ n⌉ rounds.
5. Registers the step layout with the dispute contract.

Each plan was then **validated** by proving its largest steps at other positions in the model than the profile used.

{{gen:hw_memory}}

**Reading.** A node with 1 GB or less cannot prove the whole model at all. With the memory-budgeted decomposition, every step of every plan was proven within the node's budget, and every proof verified. A larger node gets larger steps and fewer rounds. The fixed decomposition of Part 2 (63 steps, 6 rounds) is the case g = 1. The same profile decides whether a model is proven in full for every transfer (as the composed proof is, §6A.4) or posted optimistically with step disputes (§6A.2), which links the two mechanisms in one method.

**Closest prior art:** [DSperse](https://arxiv.org/html/2508.06972v3) (Inference Labs, 2025) slices a model into layer groups proven separately with EZKL and reports lower prover memory, but slice sizes are set by hand. [zkComposer](https://arxiv.org/abs/2607.08095) (July 2026) splits zkML proofs into linked sub-proofs for parallelism, not for memory.

## 6B.3 TPM-anchored operator identity (prototype)

*(generated from `integration/hw_identity/results/hw_identity.json`, written by `run_demo.py`)*

**Design.**
- **Identity:** the operator identity k(O) of the H3 registry is the SHA-256 of the operator node's TPM endorsement key (EK), whose certificate chains to the TPM manufacturer.
- **Enrolment:** the registry checks:
  - the EK certificate chain;
  - that the attestation key (AK) is a restricted, fixedTPM, fixedParent key;
  - that the TPM can recover a secret bound to that AK (TPM2_MakeCredential / ActivateCredential).

  One TPM is bound to one operator account. On enrolment the registry issues the operator credential on `LiabilityRegistry`.
- **Each new agent identity:** the TPM increments its monotonic NV counter and signs the value together with H(nonce ‖ agent id) (TPM2_NV_Certify). The registry accepts only:
  - a nonce it issued and has not seen;
  - the operator's counter index (its name is recomputed from the expected attributes);
  - a counter above the last one accepted.

  Without such an attestation, an identity is admitted only with a deposit of at least B*.

Test with two software TPMs (swtpm, EK certificates from its local CA) and the contract on anvil:

{{gen:hw_identity}}

**Reading.** The honest flow was accepted and all 9 attacks were refused. A deleted and re-created counter resumed above its old value (a TPM property), so the history cannot be reset. Escaping a violation history therefore needs new TPM hardware plus a deposit.

**Limits:**
- The TPMs are software TPMs with a local certificate authority, not manufacturer TPMs.
- The agent-level check runs in an off-chain admission registry; the contract receives only the operator credential.

## 6B.4 Verify-then-sign in a trusted execution environment (simulation)

*(generated from `integration/embodiments/results/tee_sim.json`, written by `tee_sim.py`)*

**Design.**
- **The environment (`enclave.py`):** a separate process. It copies the verifier into a private directory at launch, generates its signing key in memory, re-hashes its verifier before every use, and has no command that signs without running the validator's checks.
- **Remote attestation:** the launcher measures it (SHA-256 of `enclave.py` and of the verifier binary) into PCR 16 of the machine's TPM. A TPM quote over PCR 16, naming the environment's key in its qualifying data, is the attestation.
- **Registration:** the attester registry accepts a key only with a quote from an enrolled TPM that shows an approved verifier build.
- **Requests:** the same falsified requests as in the integrated runs (§6A.1), on real Elliptic transactions.

{{gen:hw_tee}}

**Reading.**
- The approved environment signed the honest request and refused all five falsified ones, each for the matching reason.
- A patched verifier that accepts every proof did sign a corrupted proof, but its key was never registered, so the signature does not count.
- Replayed quotes, keys outside the environment and unenrolled TPMs were refused.

**What a hardware TEE adds** (Intel SGX/TDX, ARM TrustZone, AMD SEV-SNP) is memory isolation from a compromised operating system and a measurement taken by the CPU. The simulation has neither and trusts the launcher.

## 6B.5 Offline payment devices with a secure element (simulation)

*(generated from `integration/embodiments/results/offline_sim.json`, written by `offline_sim.py`)*

**Design.**
1. **Online, once:** the payer device's secure element (a TPM here) is enrolled as in §6B.3. Three of four validators sign a policy snapshot naming its key. The snapshot holds the limit, sanctioned list, current slash, an offline allowance (12,000) and an expiry.
2. **Payer, offline:**
   - the device runs the risk model and rule and makes the composed proof itself;
   - the secure element generates the commitment randomness with its hardware random-number generator;
   - for every payment it increments its counter and certifies it, bound to H(commitment ‖ proof ‖ payee ‖ amount ‖ cumulative offline spending).
3. **Payee, offline:** checks:
   - the snapshot;
   - the attestation, and a counter above the last one seen from that device;
   - the proof, the commitment opening, EXEC = 1 and VIOL = 0;
   - the recipient;
   - that the cumulative spending is within the allowance.
4. **On reconnection:** validators re-check every bundle and settle in counter order. A repeated counter or commitment, or a cumulative total that does not follow from earlier payments, is refused and the device flagged.

{{gen:hw_offline}}

**Reading.**
- All four honest payments were accepted offline and settled.
- Replays, redirected or altered payments, a sanctioned payee, expired or altered snapshots, a forged secure-element signature and a software wallet were all refused offline.
- A manipulated app that hides earlier spending cannot be detected without a network. It was accepted offline, then refused at synchronisation as an overspend, and the device was flagged. This detect-and-penalise pattern is also how other offline CBDC designs handle it.
- Timings are from the cloud VM, not from a phone or a payment terminal.

## 6B.6 Changes to the invention disclosure (IDF-B)

The IDF-B grew from 13 to 22 pages:
- **Generic framing:** the title and the first claim are now about execution gating of AI-driven state transfers on a distributed ledger, with CBDC as one application. A terms table (IDF 7.0) maps each technical term to its CBDC meaning.
- **New hardware sections:**
  - node hardware with a figure (IDF 7.8);
  - the offline device (IDF 7.9) and the TEE (IDF 7.10);
  - physical features and technical effects (IDF 7.11).
- **Results:** IDF 8.6 to 8.10 hold the measurements of this part.
- **Fig. 1** shows the TPM block and the validator's two planes: the native verifier outside the virtual machine, and the consensus plane that sees only 65-byte signatures and a 32-byte proof hash.
- **Claims:** claim 3 is the memory-budgeted dispute method; claim 4 is Sybil-resistant admission control with the TPM identity; claim 5 is the offline device with the secure element's counter and allowance.
- **Prior art:** DSperse and zkComposer were added (§6B.2).

**Open.** The project repositories are public, so earlier work may count as prior disclosure under Indian law (Section 31's grace period covers exhibitions and learned-society papers, not repositories). The IPR cell is to advise on a provisional filing, a possible split into several applications, and inventorship.
