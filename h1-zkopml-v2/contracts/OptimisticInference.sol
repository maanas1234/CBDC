// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Minimal on-chain side of the zk-OPML dispute game, used to measure gas.
/// commit():  asserter posts output + Merkle root over (idx, leaf_i, P_i) of the trace.
/// reveal():  one bisection round - asserter opens (leaf_i, P_i) at the queried index.
/// respond(): challenger says agree/disagree with the opened prefix (moves the interval).
/// The final step calls the EZKL verifier of the single disputed step (measured separately).
contract OptimisticInference {
    struct Claim { bytes32 root; int256 output; address asserter; uint64 t; uint32 lo; uint32 hi; }
    mapping(uint256 => Claim) public claims;
    mapping(uint256 => mapping(uint256 => bytes32)) public prefix;
    mapping(uint256 => mapping(uint256 => bytes32)) public leafAt;
    uint256 public n;

    function commit(bytes32 root, int256 output, uint32 nSteps) external returns (uint256 id) {
        id = n++;
        claims[id] = Claim(root, output, msg.sender, uint64(block.timestamp), 0, nSteps);
    }

    /// Compact commit: one storage slot per inference (digest of the claim). The full
    /// claim (root, output, asserter) is supplied again as calldata if a dispute opens.
    mapping(uint256 => bytes32) public digest;
    uint256 public m;
    function commitCompact(bytes32 root, int256 output) external returns (uint256 id) {
        id = m++;
        digest[id] = keccak256(abi.encodePacked(root, output, msg.sender));
    }

    function reveal(uint256 id, uint256 idx, bytes32 leafV, bytes32 prefixV, bytes32[] calldata proof) external {
        bytes32 h = keccak256(abi.encodePacked(idx, leafV, prefixV));
        uint256 k = idx;
        for (uint256 i; i < proof.length; i++) {
            h = (k & 1) == 0 ? keccak256(abi.encodePacked(h, proof[i])) : keccak256(abi.encodePacked(proof[i], h));
            k >>= 1;
        }
        require(h == claims[id].root, "bad opening");
        prefix[id][idx] = prefixV;
        leafAt[id][idx] = leafV;
    }

    function respond(uint256 id, uint32 mid, bool agree) external {
        Claim storage c = claims[id];
        if (agree) c.lo = mid; else c.hi = mid;
    }
}
