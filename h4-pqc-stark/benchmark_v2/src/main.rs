mod classical;
mod params;
mod pq;

use std::time::Instant;

use winterfell::{FieldExtension, HashFunction, ProofOptions, Prover, StarkProof};

use classical::{ClassicalAir, ClassicalProver};
use params::{amount_bits, commit, AMOUNT_BITS, N_RAND, SIS_ROWS};
use pq::{PqAir, PqProver};

/// Identical options for both circuits: 42 queries x log2(8) = 126 bits + 16 grinding,
/// sextic extension (138-bit field), Blake3-256. Winterfell reports the resulting
/// conjectured security per proof (limited by field size minus LDE domain bits).
pub fn options() -> ProofOptions {
    ProofOptions::new(42, 8, 16, HashFunction::Blake3_256, FieldExtension::Sextic, 4, 64)
}

pub fn honest_opening(amount: u64) -> ([i64; AMOUNT_BITS], [i64; N_RAND]) {
    let bits = amount_bits(amount).map(|b| b as i64);
    let mut r = [0i64; N_RAND];
    let mut state: u64 = 0x5eed_1234;
    for v in r.iter_mut() {
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        *v = ((state >> 33) % 3) as i64 - 1;
    }
    (bits, r)
}

pub fn pq_prover(amount: u64) -> PqProver {
    let (bits, r) = honest_opening(amount);
    PqProver { options: options(), commitment: commit(&bits, &r), bits, r, out_override: None }
}

pub fn classical_prover() -> ClassicalProver {
    ClassicalProver { options: options(), out_override: None }
}

fn time_pq(prover: &PqProver) -> (usize, f64, f64, u32) {
    let trace = prover.build_trace();
    let t = Instant::now();
    let proof: StarkProof = prover.prove(trace).expect("PQ proof generation failed");
    let prove_ms = t.elapsed().as_secs_f64() * 1e3;
    let bytes = proof.to_bytes().len();
    let security = proof.security_level(true);
    let t = Instant::now();
    winterfell::verify::<PqAir>(proof, pq::Commitment(prover.commitment)).expect("PQ verification failed");
    (bytes, prove_ms, t.elapsed().as_secs_f64() * 1e3, security)
}

fn time_classical(prover: &ClassicalProver) -> (usize, f64, f64, u32) {
    let trace = prover.build_trace();
    let t = Instant::now();
    let proof: StarkProof = prover.prove(trace).expect("classical proof generation failed");
    let prove_ms = t.elapsed().as_secs_f64() * 1e3;
    let bytes = proof.to_bytes().len();
    let security = proof.security_level(true);
    let t = Instant::now();
    winterfell::verify::<ClassicalAir>(proof, classical::NoInputs).expect("classical verification failed");
    (bytes, prove_ms, t.elapsed().as_secs_f64() * 1e3, security)
}

fn main() {
    let runs: usize = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(20);
    let warmup = 2;
    let pq = pq_prover(123_456_789);
    let classical = classical_prover();
    eprintln!("H4 benchmark v2: SIS rows n={}, amount bits={}, ternary r={}, p={}", SIS_ROWS, AMOUNT_BITS, N_RAND, params::modulus());
    println!("system,run,proof_bytes,prove_ms,verify_ms,conjectured_security_bits");
    for run in 0..warmup + runs {
        let (cb, cp, cv, cs) = time_classical(&classical);
        let (pb, pp, pv, ps) = time_pq(&pq);
        if run >= warmup {
            let n = run - warmup + 1;
            println!("classical,{},{},{:.4},{:.4},{}", n, cb, cp, cv, cs);
            println!("pq_sis,{},{},{:.4},{:.4},{}", n, pb, pp, pv, ps);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::panic::{catch_unwind, AssertUnwindSafe};
    use winterfell::{
        math::{fields::f23201::BaseElement, FieldElement},
        Air, EvaluationFrame, TraceInfo, TraceTable,
    };

    /// Evaluates every transition constraint on every row (with the verifier-side periodic
    /// values) and every assertion. This checks the AIR itself, independent of prover internals.
    fn air_satisfied<A: Air<BaseField = BaseElement>>(air: &A, trace: &TraceTable<BaseElement>, width: usize, len: usize, n_constraints: usize) -> bool {
        let periodic = air.get_periodic_column_values();
        let mut result = vec![BaseElement::ZERO; n_constraints];
        for row in 0..len - 1 {
            let cur: Vec<BaseElement> = (0..width).map(|c| trace.get(c, row)).collect();
            let next: Vec<BaseElement> = (0..width).map(|c| trace.get(c, row + 1)).collect();
            let values: Vec<BaseElement> = periodic.iter().map(|col| col[row % col.len()]).collect();
            air.evaluate_transition(&EvaluationFrame::from_rows(cur, next), &values, &mut result);
            if result.iter().any(|v| *v != BaseElement::ZERO) {
                return false;
            }
        }
        air.get_assertions().iter().all(|a| {
            let steps: Vec<usize> = if a.stride() == 0 { vec![a.first_step()] } else { (a.first_step()..len).step_by(a.stride()).collect() };
            steps.iter().enumerate().all(|(i, &step)| trace.get(a.column(), step) == a.values()[i.min(a.values().len() - 1)])
        })
    }

    fn pq_air_ok(p: &PqProver) -> bool {
        let air = PqAir::new(TraceInfo::new(pq::WIDTH, params::PQ_TRACE_LEN), pq::Commitment(p.commitment), options());
        air_satisfied(&air, &p.build_trace(), pq::WIDTH, params::PQ_TRACE_LEN, pq::NUM_CONSTRAINTS)
    }

    fn classical_air_ok(p: &ClassicalProver) -> bool {
        let air = ClassicalAir::new(TraceInfo::new(classical::WIDTH, classical::TRACE_LEN), classical::NoInputs, options());
        air_satisfied(&air, &p.build_trace(), classical::WIDTH, classical::TRACE_LEN, classical::BLOCK_CONSTRAINTS)
    }

    fn malformed(commit_bits: [i64; AMOUNT_BITS], commit_r: [i64; N_RAND], bits: [i64; AMOUNT_BITS], r: [i64; N_RAND]) -> PqProver {
        PqProver { options: options(), commitment: commit(&commit_bits, &commit_r), bits, r, out_override: None }
    }

    #[test]
    fn air_accepts_honest_traces() {
        assert!(pq_air_ok(&pq_prover(123_456_789)));
        assert!(classical_air_ok(&classical_prover()));
    }

    #[test]
    fn air_rejects_every_forgery_attempt() {
        let (b1000, r) = honest_opening(1000);
        let (b999, _) = honest_opening(999);
        assert!(!pq_air_ok(&malformed(b1000, r, b999, r)), "different amount, same commitment");
        let (b, mut r5) = honest_opening(42);
        r5[0] = 5;
        assert!(!pq_air_ok(&malformed(b, r5, b, r5)), "r = 5 that genuinely opens c");
        let (b, mut r2) = honest_opening(42);
        r2[10] = 2;
        assert!(!pq_air_ok(&malformed(b, r2, b, r2)), "r = 2 that genuinely opens c");
        let (mut b2, r) = honest_opening(42);
        b2[3] = 2;
        assert!(!pq_air_ok(&malformed(b2, r, b2, r)), "non-boolean bit that genuinely opens c");
        let mut p = pq_prover(42);
        p.out_override = Some([20, 22, 43, 50]);
        assert!(!pq_air_ok(&p), "wrong matrix product");
        assert!(!classical_air_ok(&ClassicalProver { options: options(), out_override: Some([20, 22, 43, 50]) }));
    }

    /// True only if a proof is produced and it verifies. Debug builds panic on invalid traces
    /// during proving; that also counts as rejection.
    fn pq_accepted(prover: PqProver) -> bool {
        let commitment = prover.commitment;
        catch_unwind(AssertUnwindSafe(|| {
            let trace = prover.build_trace();
            match prover.prove(trace) {
                Ok(proof) => winterfell::verify::<PqAir>(proof, pq::Commitment(commitment)).is_ok(),
                Err(_) => false,
            }
        }))
        .unwrap_or(false)
    }

    #[test]
    fn honest_opening_is_accepted() {
        assert!(pq_accepted(pq_prover(123_456_789)));
    }

    #[test]
    fn classical_honest_is_accepted_and_wrong_product_rejected() {
        let ok = catch_unwind(AssertUnwindSafe(|| {
            let p = classical_prover();
            let proof = p.prove(p.build_trace()).unwrap();
            winterfell::verify::<ClassicalAir>(proof, classical::NoInputs).is_ok()
        }));
        assert_eq!(ok.ok(), Some(true));
        let bad = catch_unwind(AssertUnwindSafe(|| {
            let p = ClassicalProver { options: options(), out_override: Some([20, 22, 43, 50]) };
            match p.prove(p.build_trace()) {
                Ok(proof) => winterfell::verify::<ClassicalAir>(proof, classical::NoInputs).is_ok(),
                Err(_) => false,
            }
        }))
        .unwrap_or(false);
        assert!(!bad);
    }

    #[test]
    fn forgery_open_commitment_to_a_different_amount_is_rejected() {
        // Commitment to amount 1000; prover tries to open it with amount 999 and the same r.
        let (bits_real, r) = honest_opening(1000);
        let c = commit(&bits_real, &r);
        let (bits_fake, _) = honest_opening(999);
        assert!(!pq_accepted(PqProver { options: options(), commitment: c, bits: bits_fake, r, out_override: None }));
    }

    #[test]
    fn out_of_range_randomness_is_rejected_even_when_it_opens_the_commitment() {
        // A long r vector that genuinely satisfies c = G*bits + B*r must still fail the range check.
        let (bits, mut r) = honest_opening(42);
        r[0] = 5;
        let c = commit(&bits, &r);
        assert!(!pq_accepted(PqProver { options: options(), commitment: c, bits, r, out_override: None }));
    }

    #[test]
    fn r_value_two_is_rejected() {
        // u0 = u1 = 1 would encode r = 2; the u0*u1 = 0 constraint must reject it.
        let (bits, mut r) = honest_opening(42);
        r[10] = 2;
        let c = commit(&bits, &r);
        assert!(!pq_accepted(PqProver { options: options(), commitment: c, bits, r, out_override: None }));
    }

    #[test]
    fn non_boolean_amount_bit_is_rejected_even_when_it_opens_the_commitment() {
        let (mut bits, r) = honest_opening(42);
        bits[3] = 2;
        let c = commit(&bits, &r);
        assert!(!pq_accepted(PqProver { options: options(), commitment: c, bits, r, out_override: None }));
    }

    #[test]
    fn wrong_matrix_product_is_rejected_in_pq_circuit() {
        let mut p = pq_prover(42);
        p.out_override = Some([20, 22, 43, 50]);
        assert!(!pq_accepted(p));
    }

    #[test]
    fn options_reach_at_least_120_bits_for_both_circuits() {
        let pq = pq_prover(7);
        let proof = pq.prove(pq.build_trace()).unwrap();
        assert!(proof.security_level(true) >= 120, "pq security {}", proof.security_level(true));
        let c = classical_prover();
        let proof = c.prove(c.build_trace()).unwrap();
        assert!(proof.security_level(true) >= 120, "classical security {}", proof.security_level(true));
    }
}
