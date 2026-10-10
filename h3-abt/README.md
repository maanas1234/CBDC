# H3 — Cryptoeconomic Liability via AgentBound Tokens (ABT)

**Owner:** Anjali

**Exact hypothesis:** Binding autonomous financial agents to staked, non-transferable AgentBound Tokens (ABTs) with coded slashing conditions will produce a measurable reduction in policy-violating agent actions in a simulated multi-agent CBDC testbed, relative to an unstaked control group of equivalent agents.

**In simple words:** Give every AI agent a financial deposit tied to its identity. If it breaks a rule, the deposit gets automatically taken away. Test whether that actually makes it behave better than an agent with nothing at stake.

**Target (decided by Maanas):** Majority pass bar — with n staked agents, at least n/2 must remain violation-free over the test run, and the difference vs the unstaked control group must be statistically significant (p < 0.05, two-proportion test).

**Second, separate pass/fail test:** Sybil resistance — can a slashed agent dodge its penalty by quitting and re-registering as a new identity? Reported as its own result, not blended into the above.

**Status:** Control vs treatment comparison and one-sided two-proportion z-test are implemented. The Sybil / identity-reset probe of the in-sim registry is implemented as a **separate** result. On-chain Solidity is **not** built. **H3 is not proven.** There is **no claim of Sybil resistance.** Smoke-test `n=3` is not a confirmatory sample. A separate confirmatory config exists in `configs/experiment.yaml`; running it is not a license to retune parameters for a p-value.

## What goes here

| Planned | Current | Still missing |
|---|---|---|
| Machine-checkable violation rule | Yes (`is_violation`) | — |
| Incentive-responsive decision rule | Yes (`choose_action`) | — |
| Treatment vs control as one flag | Yes (`is_staked`) | — |
| Configurable parameters + seed | Yes (smoke + confirmatory YAML) | — |
| Stake / slash / non-transferable ABT | Yes (in-sim registry; not Solidity) | On-chain contract (optional later) |
| Multi-agent simulation | Unstaked **and** staked | — |
| Violation-rate + two-proportion test | Yes (one-sided z-test, alpha=0.05) | Majority-clean bar still separate |
| Sybil / identity-reset test | Yes (separate from any z-test) | Logical-agent / real-world binding (not invented here) |

## Experimental protocol

This is a pre-registered design for later PRs. It is **not** a completed experiment.

### 1. Machine-checkable violation

An executed transfer is a **violation** if and only if:

1. `amount > max_compliant_amount`, or
2. `destination` is in `sanctioned_destinations`.

The check is deterministic. The simulator does not need a human oracle. Later slashing should fire from this same rule, not from a separate hardcoded violation schedule.

### 2. Agent decision rule (incentive-responsive)

Every agent, staked or unstaked, uses the same function `choose_action`.

When offered a candidate transfer, the agent compares expected payoffs:

- **Refuse:** `compliant_payoff`
- **Execute a compliant transfer:** `compliant_payoff` (slash term is zero)
- **Execute a violating transfer:** `violation_payoff − expected_slash`

where

```
expected_slash = 0                                 if is_staked is false
expected_slash = 0                                 if stake_remaining <= 0
expected_slash = p_detect × min(slash, stake_left) otherwise
```

If expected payoffs tie, the default is **refuse** (`tie_break: refuse` in config).

This is the requirement that staking can change behavior: the slash term appears only for treatment agents with remaining stake. A fixed violation probability that ignores stake would **not** test H3.

### 3. Treatment vs control

| Group | Flag | Starting stake |
|---|---|---|
| Treatment | `is_staked=True` | `stake_amount` |
| Control | `is_staked=False` | `0` |

Both groups must see the same opportunities and call the same decision function. The only allowed difference is the stake flag (and the remaining stake it implies).

### 4. Config and reproducibility

Knobs live in `configs/default.yaml`:

- `n_staked`, `n_unstaked`, `n_steps`
- `stake_amount`, `slash_amount`
- `max_compliant_amount`, `sanctioned_destinations`
- `detection_probability` (default `1.0` = automatic detection)
- `tie_break`, `seed`
- Opportunity generator: `p_over_limit`, `p_sanctioned`, `over_limit_extra`, `n_clean_destinations`, payoff ranges

The generator draws candidate transfers and payoffs. It does **not** assign violations. The unstaked baseline ignores `n_staked`. The staked treatment ignores `n_unstaked`. Both use `Random(seed)` for opportunities. Slashing detection uses a **separate** RNG (`seed + 1000003`) so enforcement cannot shift the environment stream.

Default `detection_probability: 1.0` matches automatic enforcement. A later robustness run may lower it; that value must be chosen before looking at results.

`n_staked = n_unstaked = 3` is only a smoke-test default. A confirmatory comparison at p < 0.05 needs a larger pre-registered `n` (and/or more steps or independent runs). Do not treat a 3-vs-3 wiring run as the H3 result.

### 5. Output schema

Per step, both runners record:

- `seed`, `step`, `agent_id`, `is_staked`
- `amount`, `destination`, `offer_is_policy_violation`
- `action`, `is_violation` (true only if the agent **executed** a policy-violating transfer)
- `abt_id`, `detected`, `slashed_amount`, `stake_before`, `stake_remaining`

Control fills ABT/slash fields with empty/zero. Treatment fills them from the registry.

Aggregates: `total_actions`, `total_violations`, `violation_rate`. Treatment also reports `total_slashed`.

The comparison runner also reports absolute difference, relative reduction when defined, one-sided two-proportion z-statistic, p-value, alpha=0.05, and verdict.

**Verdict rule (this experiment only):**

- `SUPPORTED` only if treatment violation rate < control violation rate **and** p < 0.05.
- Otherwise `NOT SUPPORTED BY THIS EXPERIMENT`.
- `SUPPORTED` means that predefined criterion was met **under the specified configuration**. It does not mean H3 has been universally proven.

Very small p-values are computed with `erfc` (not `1 + erf`) and printed in scientific notation. They are not displayed as `0.000000`.

Smoke-test configs (`experiment_role: smoke_test`) must not be reported as confirmatory evidence. Use `configs/experiment.yaml` for the confirmatory configuration. That file documents a priori parameter choices. Do not edit it to chase a p-value. The H3 source does not specify a minimum effect size; none is invented.

The PR 3 smoke slash of 100 sits above the default violation_payoff range [1, 30], so staked agents never find a violating offer worth taking. The confirmatory `slash_amount: 15` is inside that range so both REFUSE (slash dominates) and EXECUTE (gain dominates) remain possible. That is a parameter-box choice, not a result.

Not computed: majority-clean bar. The Sybil probe is a **separate** runner (`run_sybil.py`) and is not folded into these aggregates.

### 6. ABT registry (protocol, not the experiment)

`ABTRegistry` is the in-simulation liability mechanism:

1. `register(agent)` issues a non-transferable ABT bound to that identity.
2. `stake(agent, amount)` posts collateral and tracks remaining stake.
3. `transfer(...)` always raises. The token cannot change owner.
4. `report_violation(agent, transfer, ...)` verifies the coded policy, slashes `min(slash_amount, remaining)`, records history, and never lets stake go negative.

Automatic slashing in the treatment runner means: if the agent **executes** a policy-violating transfer **and** it is detected, the runner calls `report_violation`. Detection probability defaults to `1.0`.

Passing registry tests means the **mechanism** is correct. It does **not** mean staking reduced violations in a confirmatory experiment.

The registry keys accounts by `agent_id` string only. Re-registering the **same** string is rejected. Transferring an existing ABT is rejected. A **new** string is a new account: new ABT, independent stake, empty history. There is no logical-operator, hardware, or real-world identity link. That is the mechanism the Sybil test measures. Do not invent an on-chain KYC graph that is not implemented.

### 7. What would make this design invalid

- Hard-coding a violation coin-flip that does not use `expected_slash`
- Giving staked agents a different action set, RNG stream, or extra rules
- Mixing detection draws into the opportunity RNG (that would make treatment and control see different environments)
- Calling the smoke-test `n=3` a confirmatory result
- Mixing the Sybil test into the main treatment/control table

### 8. Sybil / identity-reset test (separate evaluation)

This is **not** part of the treatment-vs-control comparison and does **not** change any H3 statistical verdict.

The probe uses the registry as implemented:

1. Register `logical_agent_0` and post the configured stake / ABT.
2. Commit a machine-checkable violation (`amount > max_compliant_amount`).
3. Apply `report_violation` (the existing automatic slash).
4. Record original identity, remaining stake, ABT id, and violation history.
5. Attempt an identity reset: register a new string `logical_agent_0_reset` for the same logical agent.
6. Attempt to obtain a new ABT and the configured stake under that new string.
7. Ask whether previous liability/history follows the new identity.

Possible outcomes:

| Outcome | Meaning |
|---|---|
| `SYBIL_BLOCKED` | The mechanism prevents the penalized logical agent from escaping prior liability/history. |
| `SYBIL_SUCCEEDED` | A fresh identity can obtain a new ABT/stake and empty history; prior liability stays on the old id only. |
| `NOT_ENFORCED` | The simulation cannot establish Sybil resistance or success because linkage is too thin to judge. |

**Measured result of the implemented registry:** `SYBIL_SUCCEEDED`. The current prototype keys identity by `agent_id`, so a fresh identity can register again with fresh stake/history. Non-transferability stops moving the old ABT, but a new `agent_id` is unconstrained. This is not Sybil resistance. It is also not a claim that H3 is proven or disproven.

Reproducibility: the scenario is fully determined by the config (`seed` is recorded; the violating transfer is constructed, not sampled). Default config uses `seed: 42`.

## Layout

```
h3-abt/
  configs/default.yaml         # smoke test
  configs/experiment.yaml      # confirmatory config (a priori)
  run_baseline.py
  run_treatment.py
  run_experiment.py            # control vs treatment + z-test
  run_sybil.py                 # identity-reset probe (separate from z-test)
  results/                     # JSON/CSV output (generated)
  src/h3_abt/
    config.py
    protocol.py                # violation check + expected-payoff choice
    environment.py             # shared opportunity generator
    abt.py                     # ABT registry: identity, stake, slash, history
    simulation.py              # unstaked baseline runner
    treatment.py               # staked treatment runner
    experiment.py / stats.py / metrics.py
    sybil.py / sybil_cli.py    # Sybil/identity-reset probe
    baseline.py / treatment_cli.py / experiment_cli.py
    types.py
  tests/
    test_config.py
    test_protocol.py
    test_baseline.py
    test_abt.py                # protocol/mechanism correctness
    test_treatment.py          # staked runner wiring
    test_metrics.py
    test_stats.py
    test_experiment.py
    test_sybil.py              # identity-reset probe
```

## How to run tests

From `h3-abt/`:

```bash
python -m pip install -r requirements.txt
python -m pytest
```

Tests check config parsing, protocol/ABT mechanism correctness, and runner wiring (reproducibility, unstaked-only vs staked-only, decision-rule reuse, shared opportunity stream). They are not H3 pass/fail evidence.

## How to run the unstaked control/baseline

From `h3-abt/`:

```bash
python run_baseline.py
python run_baseline.py --config configs/default.yaml
python run_baseline.py --json
```

This uses `n_unstaked` and `n_steps` from the config. It **ignores** `n_staked`. Output is labeled **UNSTAKED CONTROL/BASELINE (SMOKE TEST)**. Those numbers are not a confirmatory experiment and must not be reported as H3 validation.

## How to run the staked treatment

From `h3-abt/`:

```bash
python run_treatment.py
python run_treatment.py --config configs/default.yaml
python run_treatment.py --json
```

This uses `n_staked` and `n_steps`. It **ignores** `n_unstaked`. Output is labeled **STAKED TREATMENT (SMOKE TEST)**. Those numbers are wiring output only: not a control comparison, not a p-value, and not H3 validation.

## How to run the control vs treatment comparison

From `h3-abt/`:

```bash
python run_experiment.py
python run_experiment.py --config configs/default.yaml --no-save
python run_experiment.py --config configs/experiment.yaml
```

- `configs/default.yaml` is a **SMOKE TEST** (`n=3`, `slash_amount=100`).
- `configs/experiment.yaml` is the **confirmatory configuration** (a priori; do not retune for p-values).

Output includes rates, z, p (scientific notation when small), alpha=0.05, and `SUPPORTED` / `NOT SUPPORTED BY THIS EXPERIMENT`. `SUPPORTED` is the predefined rule under that config, not a universal proof of H3. JSON and CSV go to `results/` unless `--no-save` is set.

## How to run the Sybil / identity-reset test

From `h3-abt/`:

```bash
python run_sybil.py
python run_sybil.py --config configs/default.yaml
python run_sybil.py --json
```

Output reports original/new identities, slash, remaining stake, history, whether a fresh ABT/stake was obtained, whether prior liability was bypassed, and `outcome`. This result must **not** be blended into a treatment/control table or used to change an H3 z-test verdict. The current implementation outcome is `SYBIL_SUCCEEDED`. The current prototype keys identity by `agent_id`, so a fresh identity can register again with fresh stake/history.

## Confirmatory result (committed evidence)

Config: `configs/experiment.yaml`, seed 42, n=20 per group, 50 steps (1000 actions per group). Reproduced by `python run_experiment.py --config configs/experiment.yaml`. Raw output: `results/confirmatory_seed42.json` and `.csv`.

| Group | Violations | Violation rate |
|---|---|---|
| Control (unstaked) | 542 / 1000 | 54.2% |
| Treatment (staked) | 319 / 1000 | 31.9% |

- Absolute difference: −22.3 percentage points. Relative reduction: 41.1%.
- One-sided two-proportion z = −10.07, p = 3.7 × 10⁻²⁴, alpha = 0.05.
- Verdict under the predefined rule: `SUPPORTED` (this configuration only).

**Limitations of this test:**
- Pseudo-replication: the z-test treats each action as independent. Actions from the same agent across 50 steps are not independent, so the action-level p-value is overstated. **Resolved by the agent-level re-analysis below.**
- No minimum effect size was specified for H3 (the proposal sets only significance).

**Majority-clean bar (post-hoc definition).** Owner's rule: with n agents, at least n/2 must pass. An agent **passes** if its violation rate over the run is at most 50%. This definition was chosen after the per-agent counts were viewed, so it is **post-hoc and exploratory**, not pre-registered. A strict "zero violations" reading was considered and rejected as too strict to be a useful bar; under it, 0 of 20 treatment agents pass.

| Group | Agents passing (rate ≤ 50%) | Bar (n/2) | Majority bar met |
|---|---|---|---|
| Treatment (staked) | 19 / 20 | 10 | Yes |
| Control (unstaked) | 7 / 20 | 10 | No |

The majority bar is separate from the z-test verdict. Both are reported; neither replaces the other.

**Agent-level re-analysis (unit = agent, n = 20 per group).** `python run_agent_level.py` writes `results/agent_level_seed42.json`. One violation rate per agent, one-sided tests, H1: staked agents violate less.

| Test | Statistic | p (one-sided) |
|---|---|---|
| Mann–Whitney U (tie-corrected normal approx.) | U = 25.5, z = −4.73 | 1.1 × 10⁻⁶ |
| Permutation test on mean rate (100,000 permutations, seed 42) | Δ mean = −0.223 | ≤ 1.0 × 10⁻⁵ (no permutation as extreme) |

Deterrence holds at the correct unit of analysis. The earlier action-level p (3.7 × 10⁻²⁴) is overstated and should not be cited; cite the agent-level result.

**H3 final verdict:**
- Deterrence: **supported** (agent-level p ≈ 1 × 10⁻⁶; 41% relative reduction in violation rate; majority bar met by staked 19/20, not by control 7/20).
- Sybil resistance: **fails** (`SYBIL_SUCCEEDED`, documented limitation).
- Scope: one simulation configuration (seed 42, 20 agents × 50 steps per group), in-simulation registry, no on-chain contract.

**Sybil probe:** `SYBIL_SUCCEEDED` (documented limitation, see section 8). Not part of the z-test verdict.

## Next milestone

Majority-clean bar (still separate from the z-test). On-chain Solidity remains optional and unimplemented. The Sybil probe is already a separate runner and must stay separate from the treatment/control comparison.
