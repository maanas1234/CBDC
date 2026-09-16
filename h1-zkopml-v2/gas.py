"""On-chain verification cost: deploy each circuit's EZKL Solidity verifier on a
local anvil chain and measure gasUsed of a verifyProof transaction.
Usage: python3 gas.py B name:dir [name:dir ...]"""
import json, os, subprocess, sys, time
import ezkl

BIN = os.environ.get("FOUNDRY_BIN", os.path.expanduser("~/.foundry/bin")); os.environ["PATH"] = BIN + ":" + os.environ["PATH"]
RPC = "http://127.0.0.1:8545"
PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"  # anvil default key #0
B = int(sys.argv[1]); WD = f"work/S{B}"
anvil = subprocess.Popen([f"{BIN}/anvil", "--code-size-limit", "1000000", "--gas-limit", "300000000", "--silent"])
time.sleep(2)


def sh(*a):
    r = subprocess.run(list(a), capture_output=True, text=True)
    if r.returncode: raise RuntimeError(" ".join(a[:3]) + ": " + r.stderr[-400:])
    return r.stdout.strip()


path = "results/gas.json"
out = json.load(open(path)) if os.path.exists(path) else {}
async def main():
  for spec in sys.argv[2:]:
        name, d = spec.split(":"); d = f"{WD}/{d}"
        s = json.load(open(f"{d}/settings.json")); srs = f"{WD}/srs_{s['run_args']['logrows']}.srs"
        sol, abi = f"{d}/Verifier.sol", f"{d}/Verifier.abi"
        try:  # writes Verifier.sol, then tries to fetch solc via svm for the ABI (blocked here) -> ignore
            await ezkl.create_evm_verifier(f"{d}/vk.key", f"{d}/settings.json", sol, abi, srs, False)
        except RuntimeError:
            pass
        assert os.path.exists(sol)
        bytecode = sh(os.environ.get("SOLC", "solc"), "--bin", "--optimize", "--optimize-runs", "1", sol).split("Binary:")[-1].strip()
        code_kb = len(bytecode) / 2 / 1024
        rc = json.loads(sh("cast", "send", "--rpc-url", RPC, "--private-key", PK, "--json", "--create", "0x" + bytecode))
        addr, deploy_gas = rc["contractAddress"], int(rc["gasUsed"], 16)
        cd = bytes(ezkl.encode_evm_calldata(f"{d}/proof.json", f"{d}/calldata.bytes")).hex()
        tx = json.loads(sh("cast", "send", "--rpc-url", RPC, "--private-key", PK, "--json", addr, "0x" + cd))
        ok = sh("cast", "call", "--rpc-url", RPC, addr, "0x" + cd)
        verify_gas = int(tx["gasUsed"], 16)
        out[f"B{B}_{name}"] = dict(verify_tx_gas=verify_gas, deploy_gas=deploy_gas, bytecode_kb=code_kb,
                                   calldata_bytes=len(cd) // 2, n_instances=len(json.load(open(f"{d}/proof.json"))["instances"][0]),
                                   call_returns_true=ok.endswith("1"), tx_status=tx["status"])
        print(name, out[f"B{B}_{name}"], flush=True)
        json.dump(out, open(path, "w"), indent=2)
import asyncio
try:
    asyncio.run(main())
finally:
    anvil.terminate()
