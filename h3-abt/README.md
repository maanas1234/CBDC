# H3 — Cryptoeconomic Liability via AgentBound Tokens (ABT)

**Owner:** Anjali

**Exact hypothesis:** Binding autonomous financial agents to staked, non-transferable AgentBound Tokens (ABTs) with coded slashing conditions will produce a measurable reduction in policy-violating agent actions in a simulated multi-agent CBDC testbed, relative to an unstaked control group of equivalent agents.

**In simple words:** Give every AI agent a financial deposit tied to its identity. If it breaks a rule, the deposit gets automatically taken away. Test whether that actually makes it behave better than an agent with nothing at stake.

**Target (decided by Maanas):** Majority pass bar — with n staked agents, at least n/2 must remain violation-free over the test run, and the difference vs the unstaked control group must be statistically significant (p < 0.05, two-proportion test).

**Second, separate pass/fail test:** Sybil resistance — can a slashed agent dodge its penalty by quitting and re-registering as a new identity? Reported as its own result, not blended into the above.

**Status:** Unstaked control/baseline and staked treatment (ABT + automatic slashing) are implemented. The Sybil / identity-reset probe of the in-sim registry is implemented as a **separate** result. Two-group statistical comparison, p-values, and on-chain Solidity are **not** on this branch. **No confirmatory H3 results** and **no claim of Sybil resistance.** Default `n=3`, `n_steps=20` is a wiring smoke test, not a confirmatory sample size for p < 0.05.

## What goes here

| Planned | Current | Still missing |
|---|---|---|
| Machine-checkable violation rule | Yes (`is_violation`) | — |
| Incentive-responsive decision rule | Yes (`choose_action`) | — |
| Treatment vs control as one flag | Yes (`is_staked`) | Joint comparison runner |
| Configurable parameters + seed | Yes (`configs/default.yaml`) | — |
| Stake / slash / non-transferable ABT | Yes (in-sim registry; not Solidity) | On-chain contract (optional later) |
| Multi-agent simulation | Unstaked baseline **and** staked treatment | Combined experiment |
| Violation-rate + two-proportion test | Counts/rate per group separately | Two-group z-test, p < 0.05 |
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

Not computed here: two-proportion z-test, majority-clean bar. The Sybil probe is a **separate** runner (`run_sybil.py`) and is not folded into these aggregates.

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

**Measured result of the implemented registry:** `SYBIL_SUCCEEDED`. Non-transferability stops moving the old ABT, but a new `agent_id` is unconstrained. This is not Sybil resistance. It is also not a claim that H3 is proven or disproven.

Reproducibility: the scenario is fully determined by the config (`seed` is recorded; the violating transfer is constructed, not sampled). Default config uses `seed: 42`.

## Layout

```
h3-abt/
  configs/default.yaml
  run_baseline.py              # unstaked control/baseline CLI
  run_treatment.py             # staked treatment CLI
  run_sybil.py                 # identity-reset probe (separate from z-test)
  src/h3_abt/
    config.py
    protocol.py                # violation check + expected-payoff choice
    environment.py             # shared opportunity generator
    abt.py                     # ABT registry: identity, stake, slash, history
    simulation.py              # unstaked baseline runner
    treatment.py               # staked treatment runner
    sybil.py / sybil_cli.py    # Sybil/identity-reset probe
    baseline.py / treatment_cli.py
    types.py
  tests/
    test_config.py
    test_protocol.py
    test_baseline.py
    test_abt.py                # protocol/mechanism correctness
    test_treatment.py          # staked runner wiring
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

## How to run the Sybil / identity-reset test

From `h3-abt/`:

```bash
python run_sybil.py
python run_sybil.py --config configs/default.yaml
python run_sybil.py --json
```

Output reports original/new identities, slash, remaining stake, history, whether a fresh ABT/stake was obtained, whether prior liability was bypassed, and `outcome`. This result must **not** be blended into a treatment/control table or used to change an H3 z-test verdict. The current implementation outcome is `SYBIL_SUCCEEDED`.

## Next milestone

Same-environment treatment-vs-control comparison harness (still no p-value unless explicitly scoped). The Sybil probe is already a separate runner and must stay separate from that comparison.
