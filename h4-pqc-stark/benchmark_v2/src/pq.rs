//! Post-quantum circuit: the same 2x2 matrix product, plus a proof of knowledge of a short
//! opening (bits, r) of a public SIS commitment c = G*bits + B*r over the STARK field.
//!
//! Soundness-relevant choices:
//!   - B and the row-0 selector are periodic columns. The verifier computes them; the prover
//!     cannot choose them.
//!   - Arithmetic is native mod p, so no quotient column exists to absorb a wrong opening.
//!   - Every amount bit is boolean and constant; r is constrained to {-1, 0, 1} exactly.

use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    Air, AirContext, Assertion, ByteWriter, EvaluationFrame, ProofOptions, Prover, Serializable,
    TraceInfo, TraceTable, TransitionConstraintDegree,
};

use crate::classical::{fill_matmul, matmul_assertions, matmul_constraints, matmul_degrees, BLOCK_ASSERTIONS, BLOCK_CONSTRAINTS, BLOCK_WIDTH};
use crate::params::{b_entry, felt_from_i64, g_entry, AMOUNT_BITS, FINAL_ROW, N_RAND, PQ_TRACE_LEN, SIS_ROWS};

const ACC: usize = 0;
const BITS: usize = ACC + SIS_ROWS;
const R: usize = BITS + AMOUNT_BITS;
const U0: usize = R + 1;
const U1: usize = R + 2;
const MAT: usize = R + 3;
pub const WIDTH: usize = MAT + BLOCK_WIDTH;
pub const NUM_CONSTRAINTS: usize = SIS_ROWS + 2 * AMOUNT_BITS + 4 + BLOCK_CONSTRAINTS;

#[derive(Clone)]
pub struct Commitment(pub [u64; SIS_ROWS]);

impl Serializable for Commitment {
    fn write_into<W: ByteWriter>(&self, target: &mut W) {
        let values: Vec<BaseElement> = self.0.iter().map(|&v| BaseElement::from(v)).collect();
        target.write(&values[..]);
    }
}

pub struct PqAir {
    context: AirContext<BaseElement>,
    commitment: [u64; SIS_ROWS],
}

impl Air for PqAir {
    type BaseField = BaseElement;
    type PublicInputs = Commitment;

    fn new(trace_info: TraceInfo, pub_inputs: Commitment, options: ProofOptions) -> Self {
        assert_eq!(trace_info.width(), WIDTH);
        let mut degrees = vec![TransitionConstraintDegree::with_cycles(1, vec![PQ_TRACE_LEN]); SIS_ROWS];
        degrees.extend(vec![TransitionConstraintDegree::new(2); AMOUNT_BITS]);
        degrees.extend(vec![TransitionConstraintDegree::new(1); AMOUNT_BITS]);
        degrees.extend(vec![TransitionConstraintDegree::new(2); 3]);
        degrees.push(TransitionConstraintDegree::new(1));
        degrees.extend(matmul_degrees());
        let num_assertions = 2 * SIS_ROWS + BLOCK_ASSERTIONS;
        Self { context: AirContext::new(trace_info, degrees, num_assertions, options), commitment: pub_inputs.0 }
    }

    fn context(&self) -> &AirContext<BaseElement> {
        &self.context
    }

    fn evaluate_transition<E: FieldElement + From<BaseElement>>(&self, frame: &EvaluationFrame<E>, periodic: &[E], result: &mut [E]) {
        let cur = frame.current();
        let next = frame.next();
        let sel0 = periodic[0];
        for j in 0..SIS_ROWS {
            let mut amount_term = E::ZERO;
            for t in 0..AMOUNT_BITS {
                amount_term += E::from(BaseElement::from(g_entry(j, t))) * cur[BITS + t];
            }
            result[j] = next[ACC + j] - cur[ACC + j] - sel0 * amount_term - periodic[1 + j] * cur[R];
        }
        let mut k = SIS_ROWS;
        for t in 0..AMOUNT_BITS {
            result[k] = cur[BITS + t] * (cur[BITS + t] - E::ONE);
            k += 1;
        }
        for t in 0..AMOUNT_BITS {
            result[k] = next[BITS + t] - cur[BITS + t];
            k += 1;
        }
        result[k] = cur[U0] * (cur[U0] - E::ONE);
        result[k + 1] = cur[U1] * (cur[U1] - E::ONE);
        result[k + 2] = cur[U0] * cur[U1];
        // r + 1 = u0 + 2*u1 with u0, u1 boolean and not both set  =>  r in {-1, 0, 1}.
        result[k + 3] = cur[R] + E::ONE - cur[U0] - E::from(BaseElement::from(2u64)) * cur[U1];
        matmul_constraints(cur, next, MAT, &mut result[k + 4..]);
    }

    fn get_assertions(&self) -> Vec<Assertion<BaseElement>> {
        let mut v = Vec::new();
        for j in 0..SIS_ROWS {
            v.push(Assertion::single(ACC + j, 0, BaseElement::ZERO));
            v.push(Assertion::single(ACC + j, FINAL_ROW, BaseElement::from(self.commitment[j])));
        }
        v.extend(matmul_assertions(MAT));
        v
    }

    fn get_periodic_column_values(&self) -> Vec<Vec<BaseElement>> {
        let mut columns = Vec::with_capacity(1 + SIS_ROWS);
        let mut sel0 = vec![BaseElement::ZERO; PQ_TRACE_LEN];
        sel0[0] = BaseElement::ONE;
        columns.push(sel0);
        for j in 0..SIS_ROWS {
            let mut col = vec![BaseElement::ZERO; PQ_TRACE_LEN];
            for i in 0..N_RAND {
                col[i + 1] = BaseElement::from(b_entry(j, i));
            }
            columns.push(col);
        }
        columns
    }
}

/// Prover. `bits` and `r` are deliberately unchecked so tests can attempt malformed openings.
pub struct PqProver {
    pub options: ProofOptions,
    pub commitment: [u64; SIS_ROWS],
    pub bits: [i64; AMOUNT_BITS],
    pub r: [i64; N_RAND],
    pub out_override: Option<[u64; 4]>,
}

impl PqProver {
    pub fn build_trace(&self) -> TraceTable<BaseElement> {
        let mut columns = vec![vec![BaseElement::ZERO; PQ_TRACE_LEN]; WIDTH];
        for t in 0..AMOUNT_BITS {
            let bit = felt_from_i64(self.bits[t]);
            for row in 0..PQ_TRACE_LEN {
                columns[BITS + t][row] = bit;
            }
        }
        let mut r_col = vec![0i64; PQ_TRACE_LEN];
        for i in 0..N_RAND {
            r_col[i + 1] = self.r[i];
        }
        for row in 0..PQ_TRACE_LEN {
            let v = r_col[row] + 1;
            columns[R][row] = felt_from_i64(r_col[row]);
            columns[U0][row] = felt_from_i64(v.rem_euclid(2));
            columns[U1][row] = felt_from_i64(v.div_euclid(2));
        }
        for j in 0..SIS_ROWS {
            let mut amount_term = BaseElement::ZERO;
            for t in 0..AMOUNT_BITS {
                amount_term += BaseElement::from(g_entry(j, t)) * felt_from_i64(self.bits[t]);
            }
            let mut acc = BaseElement::ZERO;
            columns[ACC + j][0] = acc;
            for row in 0..PQ_TRACE_LEN - 1 {
                if row == 0 {
                    acc += amount_term;
                }
                if (1..=N_RAND).contains(&row) {
                    acc += BaseElement::from(b_entry(j, row - 1)) * felt_from_i64(r_col[row]);
                }
                columns[ACC + j][row + 1] = acc;
            }
        }
        fill_matmul(&mut columns, MAT, PQ_TRACE_LEN, self.out_override);
        TraceTable::init(columns)
    }
}

impl Prover for PqProver {
    type BaseField = BaseElement;
    type Air = PqAir;
    type Trace = TraceTable<BaseElement>;

    fn get_pub_inputs(&self, _trace: &Self::Trace) -> Commitment {
        Commitment(self.commitment)
    }

    fn options(&self) -> &ProofOptions {
        &self.options
    }
}
