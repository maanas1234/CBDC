"""End-to-end optimistic dispute on the bisectable model (zk-OPML prototype).

Protocol
  1. Asserter runs the model off-chain and posts: claimed output + Merkle root
     over (leaf_i, P_i) for every step i, where leaf_i = Poseidon(step i output)
     and P_i = H(P_{i-1} || leaf_i) is a prefix accumulator. No proof yet.
  2. A challenger recomputes the (deterministic, fixed-point) trace. If the
     claimed output differs, it opens a dispute.
  3. Bisection over P_i: prefix agreement is monotone (once any leaf differs,
     every later prefix differs), so binary search finds the FIRST step k whose
     leaf differs in ceil(log2 n) rounds. All leaves before k are agreed, so
     step k's inputs (earlier leaves or the public tx) are agreed.
  4. One EZKL proof of step k alone, on the agreed inputs. The verifier checks
     proof validity, that its input-hash instances equal the agreed leaves, and
     compares its output instance with the asserter's leaf_k. Mismatch -> the
     asserter's claim is rejected (and its bond slashed); match -> the
     challenger's dispute is rejected.
Usage: python3 dispute.py B scenario_id [scenario_id ...]
"""
import hashlib, json, os, pickle, subprocess, sys, time
import numpy as np
import ezkl
from data import load, temporal_split, apply_scaler
from onnx_builder import build, build_join_block, dispute_steps
from steps import quantize_steps, run_steps
from commit import leaf, felts
from quant import S

B = int(sys.argv[1]); ids = [int(a) for a in sys.argv[2:]]
WD = f"work/S{B}"; os.makedirs(WD, exist_ok=True)
m = pickle.load(open(f"models/W32_B{B}.pkl", "rb"))
X, y, ts = load(); _, _, (Xte, yte), _ = temporal_split(X, y, ts); Xte = apply_scaler(Xte, m["scaler"])
steps = quantize_steps(dispute_steps(m["units"])); n = len(steps)
steps_bench = json.load(open(f"results/steps_B{B}.json"))
rng = np.random.default_rng(0); cidx = rng.choice(len(Xte), 16, replace=False)
cx, couts = run_steps(steps, Xte[cidx])
deq = lambda a: a / 2 ** S
H = lambda a, b: hashlib.sha256((a + b).encode()).hexdigest()

# scenarios: (tx index, who cheats, cheated step, corruption)
illicit = np.where(yte == 1)[0]; licit = np.where(yte == 0)[0]
SCEN = [
    dict(tx=int(illicit[0]), cheat="asserter", step=0),          # tamper with first projection half
    dict(tx=int(illicit[5]), cheat="asserter", step=1),          # second projection half
    dict(tx=int(licit[3]), cheat="asserter", step=17),           # a middle block
    dict(tx=int(illicit[9]), cheat="asserter", step=n - 2),      # last block
    dict(tx=int(licit[11]), cheat="asserter", step=n - 1),       # the decision itself (head)
    dict(tx=int(illicit[2]), cheat="asserter", step=40),
    dict(tx=int(licit[20]), cheat="challenger", step=33),        # false dispute against an honest asserter
]


def trace_commit(outs):
    leaves = [leaf(o[0]) for o in outs]
    P, acc = [], ""
    for l in leaves:
        acc = H(acc, l); P.append(acc)
    return leaves, P


def corrupt_fn(step):
    def f(o):
        if step == n - 1:
            o[0, 0] = -o[0, 0] if o[0, 0] != 0 else 2 ** S   # flip the decision
        else:
            o[0, int(np.argmax(o[0]))] += 3 * 2 ** S          # nudge one activation by +3.0
        return o
    return f


def prove_step(k, inputs, calib_inputs, name):
    st = steps[k]
    iv = "public" if st["inputs"] == [-1] else "hashed"; ov = "public" if k == n - 1 else "hashed"
    onnx = f"{WD}/{name}.onnx"
    if len(st["inputs"]) > 1: build_join_block(st["unit"], [a.shape[1] for a in inputs], onnx)
    else: build([st["unit"]], onnx)
    json.dump({"input_data": [deq(c).reshape(-1).tolist() for c in calib_inputs]}, open(f"{WD}/{name}_calib.json", "w"))
    json.dump([deq(a).reshape(-1).tolist() for a in inputs], open(f"{WD}/{name}_in.json", "w"))
    best_ic = steps_bench.get(st["name"], {}).get("num_inner_cols", 2 if st["kind"] != "proj" else 4)
    r = subprocess.run(["python3", "prover.py", onnx, f"{WD}/{name}_in.json", f"{WD}/{name}_d", iv, ov, "1",
                        f"{WD}/{name}_calib.json"], capture_output=True, text=True,
                       env=dict(os.environ, ZK_INNER_COLS=str(best_ic)))
    line = [l for l in r.stdout.splitlines() if l.startswith("RESULT_JSON")]
    if not line: raise RuntimeError(r.stderr[-500:])
    return json.loads(line[0][12:]), iv, ov


path = f"results/disputes_B{B}.json"
allres = json.load(open(path)) if os.path.exists(path) else {}
for sid in ids:
    sc = SCEN[sid]; x = Xte[sc["tx"]:sc["tx"] + 1]
    xq, honest = run_steps(steps, x)
    _, bad = run_steps(steps, x, corrupt=(sc["step"], corrupt_fn(sc["step"])))
    A_outs, C_outs = (bad, honest) if sc["cheat"] == "asserter" else (honest, bad)
    A_leaves, A_P = trace_commit(A_outs); C_leaves, C_P = trace_commit(C_outs)
    thr_logit = np.log(m["res"]["threshold"] / (1 - m["res"]["threshold"]))
    a_dec, c_dec = A_outs[-1][0, 0] / 2 ** S > thr_logit, C_outs[-1][0, 0] / 2 ** S > thr_logit

    # --- bisection over prefix accumulators ---
    lo, hi, rounds = -1, n - 1, 0          # invariant: P[lo] agreed (lo=-1: empty prefix), P[hi] disputed
    assert A_P[hi] != C_P[hi]
    while hi - lo > 1:
        mid = (lo + hi) // 2; rounds += 1
        if A_P[mid] == C_P[mid]: lo = mid
        else: hi = mid
    k = hi
    # agreed inputs of step k
    ins = [xq if j == -1 else C_outs[j] for j in steps[k]["inputs"]]
    agreed_in_leaves = [None if j == -1 else A_leaves[j] for j in steps[k]["inputs"]]
    assert all(j == -1 or A_leaves[j] == C_leaves[j] for j in steps[k]["inputs"]), "inputs of k must be agreed"
    true_inputs = [xq if j == -1 else honest[j] for j in steps[k]["inputs"]]
    assert all((a == b).all() for a, b in zip(ins, true_inputs))

    # --- one-step ZK proof on the agreed inputs (honest computation) ---
    cins = [cx if j == -1 else couts[j] for j in steps[k]["inputs"]]
    t = time.time(); pr, iv, ov = prove_step(k, ins, cins, f"dispute{sid}"); wall = time.time() - t
    inst = pr["instances"]
    # verifier-side checks
    if iv == "public":
        in_ok = inst[:xq.shape[1]] == felts(xq[0]); out_inst = inst[xq.shape[1]:]
    else:
        nin = len(steps[k]["inputs"]); in_ok = inst[:nin] == agreed_in_leaves; out_inst = inst[nin:]
    if ov == "hashed":
        proven_out = out_inst[0]; a_claim = A_leaves[k]
    else:
        proven_out = out_inst[0]; a_claim = felts(A_outs[k][0])[0]
    asserter_wins = pr["verified"] and in_ok and proven_out == a_claim
    correct = (asserter_wins and sc["cheat"] == "challenger") or (not asserter_wins and sc["cheat"] == "asserter")
    res = dict(scenario=sc, n_steps=n, first_bad_step=k, cheated_step=sc["step"], located_correctly=k == sc["step"],
               bisection_rounds=rounds, step_name=steps[k]["name"], proof_verified=pr["verified"],
               input_instances_match_agreed=in_ok, asserter_claim_upheld=asserter_wins, outcome_correct=correct,
               asserter_decision_illicit=bool(a_dec), challenger_decision_illicit=bool(c_dec),
               prove_s=pr["prove_mean_s"], witness_s=pr["witness_s"], setup_s=pr["setup_s"], verify_s=pr["verify_s"],
               proof_kb=pr["proof_kb"], logrows=pr["logrows"], wall_s=wall)
    allres[str(sid)] = res
    json.dump(allres, open(path, "w"), indent=2, default=float)
    print(f"scenario {sid}: cheat={sc['cheat']:10s} at step {sc['step']:2d} -> bisection found step {k:2d} "
          f"in {rounds} rounds | proof ok={pr['verified']} inputs ok={in_ok} | "
          f"{'ASSERTER UPHELD' if asserter_wins else 'ASSERTER SLASHED'} | correct={correct} | "
          f"prove={pr['prove_mean_s']:.2f}s", flush=True)
