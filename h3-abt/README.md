# H3 — Cryptoeconomic Liability via AgentBound Tokens (ABT)

**Owner:** Anjali

**Exact hypothesis:** Binding autonomous financial agents to staked, non-transferable AgentBound Tokens (ABTs) with coded slashing conditions will produce a measurable reduction in policy-violating agent actions in a simulated multi-agent CBDC testbed, relative to an unstaked control group of equivalent agents.

**In simple words:** Give every AI agent a financial deposit tied to its identity. If it breaks a rule, the deposit gets automatically taken away. Test whether that actually makes it behave better than an agent with nothing at stake.

**Target (decided by Maanas):** Majority pass bar — with n staked agents, at least n/2 must remain violation-free over the test run, and the difference vs the unstaked control group must be statistically significant (p < 0.05, two-proportion test).

**Second, separate pass/fail test:** Sybil resistance — can a slashed agent dodge its penalty by quitting and re-registering as a new identity? Reported as its own result, not blended into the above.

**Status:** Experimental protocol and Python scaffold only. No multi-agent run, no statistical test, no on-chain contract, and **no experimental results**. Default `n_staked = n_unstaked = 3` is a wiring smoke-test size, not a confirmatory sample size for p < 0.05.

## What goes here

| Planned | This PR | Still missing |
|---|---|---|
| Machine-checkable violation rule | Yes (`is_violation`) | Environment that offers transfers over time |
| Incentive-responsive decision rule | Yes (`choose_action`) | Agents acting across many steps |
| Treatment vs control as one flag | Yes (`is_staked`) | Group assignment in a run |
| Configurable parameters + seed | Yes (`configs/default.yaml`) | Runner that consumes them |
| Stake / slash / non-transferable ABT | Slash term in expected payoff only | Token, staking, history, on-chain |
| Multi-agent simulation | No | Next milestone |
| Violation-rate + two-proportion test | No | Later |
| Sybil / identity-reset test | No | Later |

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

Default `detection_probability: 1.0` matches automatic enforcement. A later robustness run may lower it; that value must be chosen before looking at results.

`n_staked = n_unstaked = 3` is only a smoke-test default. A confirmatory comparison at p < 0.05 needs a larger pre-registered `n` (and/or more steps or independent runs). Do not treat a 3-vs-3 wiring run as the H3 result.

### 5. Output schema (for the future runner)

Not produced yet. The intended per-step record is:

- `seed`, `step`, `agent_id`, `is_staked`
- `amount`, `destination`, `is_policy_violation`
- `action`, `detected`, `slashed_amount`, `stake_remaining`

Aggregate later: per-agent and per-group violation rates; two-proportion z-test; majority-clean bar for staked agents; Sybil test as a **separate** table.

### 6. What would make this design invalid

- Hard-coding a violation coin-flip that does not use `expected_slash`
- Giving staked agents a different action set, RNG stream, or extra rules
- Calling the smoke-test `n=3` a confirmatory result
- Mixing the Sybil test into the main treatment/control table

## Layout

```
h3-abt/
  configs/default.yaml
  src/h3_abt/
    config.py      # YAML load + validation
    protocol.py    # violation check + expected-payoff choice
    types.py
  tests/
    test_config.py
    test_protocol.py
  requirements.txt
  pyproject.toml
```

## How to run tests

From `h3-abt/`:

```bash
python -m pip install -r requirements.txt
python -m pytest
```

Tests check config parsing and the protocol functions on **constructed** examples. They are not a multi-agent experiment and are not H3 pass/fail evidence.

## Next milestone

Unstaked baseline simulation: one agent type, no stake, logged actions over `n_steps`, same seed → same trace. No statistical claim.
