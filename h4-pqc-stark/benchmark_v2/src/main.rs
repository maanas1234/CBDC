mod classical;
mod dense;
mod params;
mod pq;
mod sis;

use std::time::Instant;

use winterfell::{FieldExtension, HashFunction, ProofOptions, Prover, StarkProof};

use classical::{ClassicalAir, ClassicalProver};
use params::{amount_bits, commit, Workload, AMOUNT_BITS, N_RAND, SIS_ROWS};
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

pub fn pq_prover(workload: Workload, amount: u64) -> PqProver {
    let (bits, r) = honest_opening(amount);
    PqProver {
        options: options(),
        workload,
        commitment: commit(&bits, &r),
        bits,
        r,
        out_override: None,
        dense_y: dense::output(&dense::input()),
    }
}

struct Measurement {
    bytes: usize,
    prove_ms: f64,
    verify_ms: f64,
    security: u32,
}

fn time_pq(prover: &PqProver) -> Measurement {
    let trace = prover.build_trace();
    let t = Instant::now();
    let proof: StarkProof = prover.prove(trace).expect("PQ proof generation failed");
    let prove_ms = t.elapsed().as_secs_f64() * 1e3;
    let (bytes, security) = (proof.to_bytes().len(), proof.security_level(true));
    let t = Instant::now();
    winterfell::verify::<PqAir>(proof, prover.statement()).expect("PQ verification failed");
    Measurement { bytes, prove_ms, verify_ms: t.elapsed().as_secs_f64() * 1e3, security }
}

fn time_classical(prover: &ClassicalProver) -> Measurement {
    let trace = prover.build_trace();
    let t = Instant::now();
    let proof: StarkProof = prover.prove(trace).expect("classical proof generation failed");
    let prove_ms = t.elapsed().as_secs_f64() * 1e3;
    let (bytes, security) = (proof.to_bytes().len(), proof.security_level(true));
    let t = Instant::now();
    winterfell::verify::<ClassicalAir>(proof, prover.claim()).expect("classical verification failed");
    Measurement { bytes, prove_ms, verify_ms: t.elapsed().as_secs_f64() * 1e3, security }
}

fn main() {
    let runs: usize = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(30);
    let warmup = 3;
    eprintln!(
        "H4 benchmark v2: SIS n={} rows, {} amount bits, {} ternary r, p={}; {} warmup + {} measured runs per system",
        SIS_ROWS, AMOUNT_BITS, N_RAND, params::modulus(), warmup, runs
    );
    println!("workload,system,run,trace_rows,trace_width,proof_bytes,prove_ms,verify_ms,conjectured_security_bits");
    for workload in [Workload::Matmul, Workload::Dense] {
        let classical = ClassicalProver::new(options(), workload);
        let pq = pq_prover(workload, 123_456_789);
        for run in 0..warmup + runs {
            // Interleave the two systems so drift in machine load affects both equally.
            let c = time_classical(&classical);
            let p = time_pq(&pq);
            if run >= warmup {
                let n = run - warmup + 1;
                println!("{},classical,{},{},{},{},{:.4},{:.4},{}", workload.name(), n, classical::trace_len(workload), classical::width(workload), c.bytes, c.prove_ms, c.verify_ms, c.security);
                println!("{},pq_sis,{},{},{},{},{:.4},{:.4},{}", workload.name(), n, pq::trace_len(workload), pq::width(workload), p.bytes, p.prove_ms, p.verify_ms, p.security);
            }
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

    const WORKLOADS: [Workload; 2] = [Workload::Matmul, Workload::Dense];

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
        let (w, len) = (pq::width(p.workload), pq::trace_len(p.workload));
        let air = PqAir::new(TraceInfo::new(w, len), p.statement(), options());
        air_satisfied(&air, &p.build_trace(), w, len, pq::num_constraints(p.workload))
    }

    fn classical_air_ok(p: &ClassicalProver) -> bool {
        let (w, len) = (classical::width(p.workload), classical::trace_len(p.workload));
        let air = ClassicalAir::new(TraceInfo::new(w, len), p.claim(), options());
        air_satisfied(&air, &p.build_trace(), w, len, classical::num_constraints(p.workload))
    }

    fn malformed(workload: Workload, commit_bits: [i64; AMOUNT_BITS], commit_r: [i64; N_RAND], bits: [i64; AMOUNT_BITS], r: [i64; N_RAND]) -> PqProver {
        let mut p = pq_prover(workload, 0);
        p.commitment = commit(&commit_bits, &commit_r);
        p.bits = bits;
        p.r = r;
        p
    }

    /// True only if a proof is produced and verifies. Provers panic on traces that violate the
    /// AIR (composition-degree check); that also counts as rejection.
    fn pq_accepted(prover: PqProver) -> bool {
        let statement = prover.statement();
        catch_unwind(AssertUnwindSafe(|| match prover.prove(prover.build_trace()) {
            Ok(proof) => winterfell::verify::<PqAir>(proof, statement).is_ok(),
            Err(_) => false,
        }))
        .unwrap_or(false)
    }

    fn classical_accepted(prover: ClassicalProver) -> bool {
        let claim = prover.claim();
        catch_unwind(AssertUnwindSafe(|| match prover.prove(prover.build_trace()) {
            Ok(proof) => winterfell::verify::<ClassicalAir>(proof, claim).is_ok(),
            Err(_) => false,
        }))
        .unwrap_or(false)
    }

    #[test]
    fn air_accepts_honest_traces_for_both_workloads() {
        for w in WORKLOADS {
            assert!(pq_air_ok(&pq_prover(w, 123_456_789)), "{:?}", w);
            assert!(classical_air_ok(&ClassicalProver::new(options(), w)), "{:?}", w);
        }
    }

    #[test]
    fn air_rejects_every_lattice_forgery_for_both_workloads() {
        for w in WORKLOADS {
            let (b1000, r) = honest_opening(1000);
            let (b999, _) = honest_opening(999);
            assert!(!pq_air_ok(&malformed(w, b1000, r, b999, r)), "{:?}: different amount, same commitment", w);
            let (b, mut r5) = honest_opening(42);
            r5[0] = 5;
            assert!(!pq_air_ok(&malformed(w, b, r5, b, r5)), "{:?}: r = 5 that genuinely opens c", w);
            let (b, mut r2) = honest_opening(42);
            r2[10] = 2;
            assert!(!pq_air_ok(&malformed(w, b, r2, b, r2)), "{:?}: r = 2 that genuinely opens c", w);
            let (mut b2, r) = honest_opening(42);
            b2[3] = 2;
            assert!(!pq_air_ok(&malformed(w, b2, r, b2, r)), "{:?}: non-boolean bit that genuinely opens c", w);
        }
    }

    #[test]
    fn air_rejects_wrong_workload_results() {
        let mut p = pq_prover(Workload::Matmul, 42);
        p.out_override = Some([20, 22, 43, 50]);
        assert!(!pq_air_ok(&p), "pq: wrong matrix product");
        let mut c = ClassicalProver::new(options(), Workload::Matmul);
        c.out_override = Some([20, 22, 43, 50]);
        assert!(!classical_air_ok(&c), "classical: wrong matrix product");
        let mut p = pq_prover(Workload::Dense, 42);
        p.dense_y[0] = (p.dense_y[0] + 1) % params::modulus();
        assert!(!pq_air_ok(&p), "pq: wrong dense output");
        let mut c = ClassicalProver::new(options(), Workload::Dense);
        c.dense_y[5] = (c.dense_y[5] + 1) % params::modulus();
        assert!(!classical_air_ok(&c), "classical: wrong dense output");
    }

    #[test]
    fn end_to_end_honest_accepted_and_forgeries_rejected() {
        for w in WORKLOADS {
            assert!(pq_accepted(pq_prover(w, 123_456_789)), "{:?}", w);
            assert!(classical_accepted(ClassicalProver::new(options(), w)), "{:?}", w);
            let (b1000, r) = honest_opening(1000);
            let (b999, _) = honest_opening(999);
            assert!(!pq_accepted(malformed(w, b1000, r, b999, r)), "{:?}", w);
            let (b, mut r5) = honest_opening(42);
            r5[0] = 5;
            assert!(!pq_accepted(malformed(w, b, r5, b, r5)), "{:?}", w);
        }
        let mut c = ClassicalProver::new(options(), Workload::Dense);
        c.dense_y[0] = (c.dense_y[0] + 1) % params::modulus();
        assert!(!classical_accepted(c));
    }

    #[test]
    fn options_reach_at_least_120_bits_for_every_circuit() {
        for w in WORKLOADS {
            let p = pq_prover(w, 7);
            let s = p.prove(p.build_trace()).unwrap().security_level(true);
            assert!(s >= 120, "pq {:?}: {} bits", w, s);
            let c = ClassicalProver::new(options(), w);
            let s = c.prove(c.build_trace()).unwrap().security_level(true);
            assert!(s >= 120, "classical {:?}: {} bits", w, s);
        }
    }
}
