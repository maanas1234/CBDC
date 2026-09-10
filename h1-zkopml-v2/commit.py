"""Commitments for the optimistic dispute protocol.
leaf_i = Poseidon(a_i) over the fixed-point activation after unit i, using the
same Poseidon instance EZKL uses for `hashed` inputs/outputs, so a proof's
public hash instances can be compared to committed leaves directly.
root   = Merkle root over the leaves (sha256 here; keccak256 on-chain)."""
import hashlib
import ezkl
from quant import S


def felts(int_vec, s=S):
    return [ezkl.float_to_felt(float(v) / 2 ** s, s) for v in int_vec]


def leaf(int_vec, s=S):
    return ezkl.poseidon_hash(felts(int_vec, s))[0]


def merkle_root(leaves):
    lvl = [hashlib.sha256(l.encode()).digest() for l in leaves]
    while len(lvl) > 1:
        if len(lvl) % 2: lvl.append(lvl[-1])
        lvl = [hashlib.sha256(lvl[i] + lvl[i + 1]).digest() for i in range(0, len(lvl), 2)]
    return lvl[0].hex()
