mod air;
mod lattice;
mod prover;
mod trace;

use std::time::Instant;

use winterfell::{
    FieldExtension,
    HashFunction,
    ProofOptions,
    Prover,
};

use crate::lattice::{compute_commitment, compute_quotients};
use crate::prover::MatchedProver;
use crate::trace::Witness;

fn options() -> ProofOptions {
    ProofOptions::new(
        16,
        4,
        0,
        HashFunction::Blake3_256,
        FieldExtension::None,
        4,
        64,
    )
}

fn valid_witness() -> Witness {
    let amount: u64 = 123_456_789;

    let mut r = [0i64; lattice::N];

    // Deterministic bounded randomness.
    for i in 0..lattice::N {
        let x =
            ((i as i64 * 7919 + 104729) % (2 * lattice::BETA + 1))
                - lattice::BETA;

        r[i] = x;
    }

    let commitment =
        compute_commitment(amount, &r);

    let k =
        compute_quotients(amount, &r, &commitment);

    Witness {
        amount,
        r,
        k,
    }
}

fn main() {
    println!("H4 — Matched Matrix + Research-Candidate SIS STARK");
    println!("==================================================");
    println!("profile: {}", lattice::SECURITY_PROFILE);
    println!("q: {}", lattice::Q);
    println!("M: {}", lattice::M);
    println!("N: {}", lattice::N);
    println!("beta: {}", lattice::BETA);
    println!();

    println!("system,run,proof_bytes,prove_ms,verify_ms");

    for run in 1..=10 {
        let witness = valid_witness();

        let commitment =
            compute_commitment(
                witness.amount,
                &witness.r,
            );

        let prover = MatchedProver::with_matrix(
            options(),
            commitment,
            witness,
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [19, 22, 43, 50],
        );

        let trace = prover.build_trace();

        let start = Instant::now();

        let proof = match prover.prove(trace) {
            Ok(proof) => proof,
            Err(err) => {
                eprintln!(
                    "Run {}: proof generation failed: {:?}",
                    run,
                    err
                );
                return;
            }
        };

        let prove_ms =
            start.elapsed().as_secs_f64() * 1000.0;

        let proof_bytes =
            proof.to_bytes().len();

        let public_inputs =
            prover.get_pub_inputs(
                &prover.build_trace()
            );

        let start = Instant::now();

        let verification =
            winterfell::verify::<air::MatchedAir>(
                proof,
                public_inputs,
            );

        let verify_ms =
            start.elapsed().as_secs_f64() * 1000.0;

        match verification {
            Ok(_) => {
                println!(
                    "pq_matched_research_candidate,{},{},{:.3},{:.3}",
                    run,
                    proof_bytes,
                    prove_ms,
                    verify_ms
                );
            }

            Err(err) => {
                eprintln!(
                    "Run {}: verification failed: {:?}",
                    run,
                    err
                );
                return;
            }
        }
    }

    println!();
    println!("Benchmark complete: 10/10 successful.");
}
