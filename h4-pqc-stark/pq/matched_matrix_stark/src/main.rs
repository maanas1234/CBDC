mod air;
mod lattice;
mod prover;
mod trace;

use std::time::Instant;

use winterfell::{
    math::fields::f23201::BaseElement,
    FieldExtension,
    HashFunction,
    ProofOptions,
    Prover,
    Trace,
};

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
    Witness {
        s0: 2,
        s1: 1,
        r0: 1,
        r1: 3,
        k0: 0,
        k1: 0,
    }
}

fn lattice_commitment() -> [BaseElement; 2] {
    [
        BaseElement::from(75u32),
        BaseElement::from(113u32),
    ]
}

fn main() {
    println!("H4 — Matched Matrix + Lattice STARK Benchmark");
    println!("==============================================");
    println!();
    println!("system,run,proof_bytes,prove_ms,verify_ms");

    for run in 1..=10 {
        let prover = MatchedProver::with_matrix(
            options(),
            lattice_commitment(),
            valid_witness(),
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [19, 22, 43, 50],
        );

        let trace = prover.build_trace();

        let start = Instant::now();

        let proof = match prover.prove(trace) {
            Ok(proof) => proof,
            Err(err) => {
                eprintln!("Run {}: proof generation failed: {:?}", run, err);
                return;
            }
        };

        let prove_ms = start.elapsed().as_secs_f64() * 1000.0;

        let proof_bytes = proof.to_bytes().len();

        let public_inputs = prover.get_pub_inputs(
            &prover.build_trace()
        );

        let start = Instant::now();

        let verification =
            winterfell::verify::<air::MatchedAir>(
                proof,
                public_inputs,
            );

        let verify_ms = start.elapsed().as_secs_f64() * 1000.0;

        match verification {
            Ok(_) => {
                println!(
                    "pq_matched,{},{},{:.3},{:.3}",
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
