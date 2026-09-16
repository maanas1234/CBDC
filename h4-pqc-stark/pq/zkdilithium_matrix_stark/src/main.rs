mod air;
mod lattice;
mod prover;
mod trace;
mod shortness;

use std::time::Instant;

use winterfell::{
    math::fields::f23201::BaseElement,
    verify,
    FieldExtension,
    HashFunction,
    ProofOptions,
    Prover,
    Trace,
};

use prover::SisProver;
use trace::Witness;

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

fn prove_and_verify(
    label: &str,
    witness: Witness,
    c: [u32; 2],
) -> bool {
    println!();
    println!("----------------------------------------");
    println!("{}", label);
    println!("----------------------------------------");

    let public_c = [
        BaseElement::new(c[0]),
        BaseElement::new(c[1]),
    ];

    let prover = SisProver::new(
        options(),
        public_c.to_vec(),
        witness,
    );

    let trace = prover.build_trace();

    println!(
        "Trace: {} columns × {} rows",
        trace.width(),
        trace.length()
    );

    let proof_start = Instant::now();

    let proof = match prover.prove(trace) {
        Ok(proof) => proof,
        Err(err) => {
            println!("Proof generation FAILED: {:?}", err);
            return false;
        }
    };

    let prove_ms =
        proof_start.elapsed().as_secs_f64() * 1000.0;

    println!("Proof generated.");
    println!(
        "Proof size: {} bytes",
        proof.to_bytes().len()
    );
    println!(
        "Proof generation: {:.3} ms",
        prove_ms
    );

    let verify_start = Instant::now();

    let result =
        verify::<air::SisAir>(
            proof,
            air::PublicInputs {
                c: public_c,
            },
        );

    let verify_ms =
        verify_start.elapsed().as_secs_f64() * 1000.0;

    match result {
        Ok(_) => {
            println!(
                "Verification: SUCCESS ({:.3} ms)",
                verify_ms
            );
            true
        }

        Err(err) => {
            println!(
                "Verification: FAILED ({:.3} ms)",
                verify_ms
            );
            println!("Reason: {:?}", err);
            false
        }
    }
}

fn main() {
    println!("========================================");
    println!(" H4 — SIS/STARK Validation Tests");
    println!(" Debug tier: n=2, beta=15");
    println!("========================================");

    // Valid witness:
    //
    // s = [2, 1]
    // r = [1, 3]
    // k = [0, 0]
    //
    // C = A*s + B*r = [75, 113]

    let valid = Witness {
        s0: 2,
        s1: 1,
        r0: 1,
        r1: 3,
        k0: 0,
        k1: 0,
    };

    // -------------------------------------------------------------------------
    // TEST 1
    // -------------------------------------------------------------------------

    let test1 = prove_and_verify(
        "[TEST 1] Valid short witness",
        valid,
        [75, 113],
    );

    println!(
        "RESULT: {}",
        if test1 { "PASS" } else { "FAIL" }
    );

    // -------------------------------------------------------------------------
    // TEST 2
    //
    // Public commitment is deliberately wrong.
    // -------------------------------------------------------------------------

    let test2 = prove_and_verify(
        "[TEST 2] Tampered public commitment",
        valid,
        [76, 113],
    );

    println!(
        "RESULT: {}",
        if !test2 { "PASS — correctly rejected" } else { "FAIL — accepted invalid proof" }
    );

    // -------------------------------------------------------------------------
    // TEST 3
    //
    // Wrong witness.
    //
    // Change s0 from 2 -> 4.
    // The trace still uses the claimed C=[75,113],
    // so the lattice equation no longer balances.
    // -------------------------------------------------------------------------

    let wrong_witness = Witness {
        s0: 4,
        s1: 1,
        r0: 1,
        r1: 3,
        k0: 0,
        k1: 0,
    };

    let test3 = prove_and_verify(
        "[TEST 3] Wrong witness",
        wrong_witness,
        [75, 113],
    );

    println!(
        "RESULT: {}",
        if !test3 { "PASS — correctly rejected" } else { "FAIL — accepted invalid proof" }
    );

    // -------------------------------------------------------------------------
    // TEST 4
    //
    // Equation-valid but non-short witness.
    //
    // We choose:
    //
    // s = [17, 1]
    // r = [1, 3]
    //
    // and adjust C to the corresponding public value.
    //
    // s0=17 is outside beta=15.
    //
    // The lattice equation is valid, but the shortness constraint
    // must reject it.
    // -------------------------------------------------------------------------

    let long_witness = Witness {
        s0: 17,
        s1: 1,
        r0: 1,
        r1: 3,
        k0: 0,
        k1: 0,
    };

    // C = A*s + B*r:
    //
    // C0 = 3*17 + 5*1 + 13*1 + 17*3 = 120
    // C1 = 7*17 + 11*1 + 19*1 + 23*3 = 218

    let test4 = prove_and_verify(
        "[TEST 4] Equation-valid but non-short witness",
        long_witness,
        [120, 218],
    );

    println!(
        "RESULT: {}",
        if !test4 {
            "PASS — correctly rejected"
        } else {
            "FAIL — RANGE CHECK IS NOT ENFORCED"
        }
    );

    println!();
    println!("========================================");
    println!(" Validation complete.");
    println!("========================================");
}
