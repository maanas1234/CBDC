"""Gas of the optimistic path: commit per inference, and the bisection rounds of a dispute."""
import json, os, subprocess, time
from Crypto.Hash import keccak
BIN = os.environ.get("FOUNDRY_BIN", os.path.expanduser("~/.foundry/bin")); RPC = "http://127.0.0.1:8545"
PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
k256 = lambda b: keccak.new(digest_bits=256, data=b).digest()
sh = lambda *a: subprocess.run(list(a), capture_output=True, text=True, check=True).stdout.strip()
anvil = subprocess.Popen([f"{BIN}/anvil", "--silent"]); time.sleep(2)
try:
    out = sh(os.environ.get("SOLC", "solc"), "--bin", "--optimize", "contracts/OptimisticInference.sol")
    code = out.split("Binary:")[-1].strip()
    addr = json.loads(sh(f"{BIN}/cast", "send", "--rpc-url", RPC, "--private-key", PK, "--json", "--create", "0x" + code))["contractAddress"]
    N = 63  # steps in the B=60 bisectable model
    leaves = [os.urandom(32) for _ in range(N)]; pref = [os.urandom(32) for _ in range(N)]
    lv = [k256(i.to_bytes(32, "big") + leaves[i] + pref[i]) for i in range(N)]
    size = 1
    while size < N: size *= 2
    lv += [lv[-1]] * (size - N)
    tree = [lv]
    while len(tree[-1]) > 1:
        t = tree[-1]; tree.append([k256(t[i] + t[i + 1]) for i in range(0, len(t), 2)])
    root = tree[-1][0]
    def opening(i):
        pr, k = [], i
        for lvl in tree[:-1]:
            pr.append(lvl[k ^ 1]); k >>= 1
        return pr
    def send(sig, *args):
        rc = json.loads(sh(f"{BIN}/cast", "send", "--rpc-url", RPC, "--private-key", PK, "--json", addr, sig, *args))
        assert rc["status"] == "0x1"; return int(rc["gasUsed"], 16)
    g_commit = send("commit(bytes32,int256,uint32)", "0x" + root.hex(), "-1234", str(N))
    g_commit2 = send("commit(bytes32,int256,uint32)", "0x" + root.hex(), "-1234", str(N))
    g_cc1 = send("commitCompact(bytes32,int256)", "0x" + root.hex(), "-1234")
    g_cc2 = send("commitCompact(bytes32,int256)", "0x" + root.hex(), "-1234")
    reveals, responds = [], []
    lo, hi = -1, N - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        pr = "[" + ",".join("0x" + p.hex() for p in opening(mid)) + "]"
        reveals.append(send("reveal(uint256,uint256,bytes32,bytes32,bytes32[])", "0", str(mid),
                            "0x" + leaves[mid].hex(), "0x" + pref[mid].hex(), pr))
        responds.append(send("respond(uint256,uint32,bool)", "0", str(mid), "false"))
        hi = mid
    res = dict(commit_first=g_commit, commit_steady=g_commit2, commit_compact_first=g_cc1, commit_compact_steady=g_cc2, rounds=len(reveals), reveal_gas=reveals, respond_gas=responds,
               bisection_total=sum(reveals) + sum(responds))
    print(res)
    g = json.load(open("results/gas.json")) if os.path.exists("results/gas.json") else {}
    g["game_B60"] = res; json.dump(g, open("results/gas.json", "w"), indent=2)
finally:
    anvil.terminate()
