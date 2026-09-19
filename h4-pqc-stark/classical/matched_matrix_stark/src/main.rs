mod air;
mod prover;
mod trace;

use std::time::Instant;

use winterfell::{
    FieldExtension,
    HashFunction,
    ProofOptions,
    Prover,
    Trace,
};

use crate::prover::ClassicalProver;
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
        a00: 1,
        a01: 2,
        a10: 3,
        a11: 4,
        b00: 5,
        b01: 6,
        b10: 7,
        b11: 8,
    }
}

fn main() {
    println!("H4 — Matched Classical STARK Benchmark");
    println!("========================================");
    println!();
    println!("system,run,proof_bytes,prove_ms,verify_ms");

    for run in 1..=10 {
        let prover = ClassicalProver::new(
            options(),
            valid_witness(),
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

        let proof_bytes = proof.to_bytes().len();

        let public_inputs =
            prover.get_pub_inputs(
                &prover.build_trace()
            );

        let start = Instant::now();

        let verification =
            winterfell::verify::<air::ClassicalMatchedAir>(
                proof,
                public_inputs,
            );

        let verify_ms =
            start.elapsed().as_secs_f64() * 1000.0;

        match verification {
            Ok(_) => {
                println!(
                    "classical_matched,{},{},{:.3},{:.3}",
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
