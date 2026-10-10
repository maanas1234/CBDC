//! Classical baseline: STARK for the 2x2 matrix product only (no lattice commitment).

use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    Air, AirContext, Assertion, ByteWriter, EvaluationFrame, ProofOptions, Prover, Serializable,
    TraceInfo, TraceTable, TransitionConstraintDegree,
};

use crate::dense;
use crate::params::{Workload, MATRIX_A, MATRIX_B, MATRIX_C};

pub const TRACE_LEN: usize = 8;
/// Matmul block width: A, B, C, OUT (16) plus a clock column so no trace is all-constant.
pub const BLOCK_WIDTH: usize = 17;
/// Number of transition constraints in the matmul block.
pub const BLOCK_CONSTRAINTS: usize = 21;
/// Number of assertions in the matmul block.
pub const BLOCK_ASSERTIONS: usize = 13;
const A: usize = 0;
const B: usize = 4;
const C: usize = 8;
const OUT: usize = 12;
const CLOCK: usize = 16;

/// Matmul constraints, written against a column offset so the PQ circuit reuses them verbatim.
pub fn matmul_degrees() -> Vec<TransitionConstraintDegree> {
    let mut d = vec![TransitionConstraintDegree::new(1); 12];
    d.extend(vec![TransitionConstraintDegree::new(2); 4]);
    d.extend(vec![TransitionConstraintDegree::new(1); 4]);
    d.push(TransitionConstraintDegree::new(1));
    d
}

pub fn matmul_constraints<E: FieldElement>(cur: &[E], next: &[E], base: usize, out: &mut [E]) {
    for i in 0..12 {
        out[i] = next[base + i] - cur[base + i];
    }
    let (a, b, o) = (base + A, base + B, base + OUT);
    out[12] = cur[o] - (cur[a] * cur[b] + cur[a + 1] * cur[b + 2]);
    out[13] = cur[o + 1] - (cur[a] * cur[b + 1] + cur[a + 1] * cur[b + 3]);
    out[14] = cur[o + 2] - (cur[a + 2] * cur[b] + cur[a + 3] * cur[b + 2]);
    out[15] = cur[o + 3] - (cur[a + 2] * cur[b + 1] + cur[a + 3] * cur[b + 3]);
    for i in 0..4 {
        out[16 + i] = cur[o + i] - cur[base + C + i];
    }
    out[20] = next[base + CLOCK] - cur[base + CLOCK] - E::ONE;
}

pub fn matmul_assertions(base: usize) -> Vec<Assertion<BaseElement>> {
    let mut v = Vec::new();
    for i in 0..4 {
        v.push(Assertion::single(base + A + i, 0, BaseElement::from(MATRIX_A[i])));
        v.push(Assertion::single(base + B + i, 0, BaseElement::from(MATRIX_B[i])));
        v.push(Assertion::single(base + C + i, 0, BaseElement::from(MATRIX_C[i])));
    }
    v.push(Assertion::single(base + CLOCK, 0, BaseElement::ZERO));
    v
}

/// Fills the 16 matmul columns; `out_override` lets tests write a wrong product.
pub fn fill_matmul(columns: &mut [Vec<BaseElement>], base: usize, len: usize, out_override: Option<[u64; 4]>) {
    let (a, b) = (MATRIX_A, MATRIX_B);
    let product = [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3]];
    let out = out_override.unwrap_or(product);
    for row in 0..len {
        for i in 0..4 {
            columns[base + A + i][row] = BaseElement::from(a[i]);
            columns[base + B + i][row] = BaseElement::from(b[i]);
            columns[base + C + i][row] = BaseElement::from(MATRIX_C[i]);
            columns[base + OUT + i][row] = BaseElement::from(out[i]);
        }
        columns[base + CLOCK][row] = BaseElement::from(row as u64);
    }
}

/// Public statement: which workload, and (for the dense layer) the claimed outputs.
#[derive(Clone)]
pub struct Claim {
    pub workload: Workload,
    pub dense_y: [u64; dense::OUT],
}

impl Serializable for Claim {
    fn write_into<W: ByteWriter>(&self, target: &mut W) {
        target.write_u8(self.workload as u8);
        if self.workload == Workload::Dense {
            let values: Vec<BaseElement> = self.dense_y.iter().map(|&v| BaseElement::from(v)).collect();
            target.write(&values[..]);
        }
    }
}

pub fn trace_len(w: Workload) -> usize {
    match w {
        Workload::Matmul => TRACE_LEN,
        Workload::Dense => dense::MIN_LEN.next_power_of_two(),
    }
}

pub fn width(w: Workload) -> usize {
    match w {
        Workload::Matmul => BLOCK_WIDTH,
        Workload::Dense => dense::WIDTH,
    }
}

pub fn num_constraints(w: Workload) -> usize {
    match w {
        Workload::Matmul => BLOCK_CONSTRAINTS,
        Workload::Dense => dense::CONSTRAINTS,
    }
}

pub struct ClassicalAir {
    context: AirContext<BaseElement>,
    claim: Claim,
    len: usize,
}

impl Air for ClassicalAir {
    type BaseField = BaseElement;
    type PublicInputs = Claim;

    fn new(trace_info: TraceInfo, claim: Claim, options: ProofOptions) -> Self {
        let w = claim.workload;
        assert_eq!(trace_info.width(), width(w));
        let len = trace_info.length();
        let (degrees, n_assert) = match w {
            Workload::Matmul => (matmul_degrees(), BLOCK_ASSERTIONS),
            Workload::Dense => (dense::degrees(len), dense::ASSERTIONS),
        };
        Self { context: AirContext::new(trace_info, degrees, n_assert, options), claim, len }
    }

    fn context(&self) -> &AirContext<BaseElement> {
        &self.context
    }

    fn evaluate_transition<E: FieldElement + From<BaseElement>>(&self, frame: &EvaluationFrame<E>, periodic: &[E], result: &mut [E]) {
        match self.claim.workload {
            Workload::Matmul => matmul_constraints(frame.current(), frame.next(), 0, result),
            Workload::Dense => dense::constraints(frame.current(), frame.next(), periodic, 0, result),
        }
    }

    fn get_assertions(&self) -> Vec<Assertion<BaseElement>> {
        match self.claim.workload {
            Workload::Matmul => matmul_assertions(0),
            Workload::Dense => dense::assertions(0, &self.claim.dense_y),
        }
    }

    fn get_periodic_column_values(&self) -> Vec<Vec<BaseElement>> {
        match self.claim.workload {
            Workload::Matmul => Vec::new(),
            Workload::Dense => dense::periodic_columns(self.len),
        }
    }
}

pub struct ClassicalProver {
    pub options: ProofOptions,
    pub workload: Workload,
    pub out_override: Option<[u64; 4]>,
    pub dense_y: [u64; dense::OUT],
}

impl ClassicalProver {
    pub fn new(options: ProofOptions, workload: Workload) -> Self {
        Self { options, workload, out_override: None, dense_y: dense::output(&dense::input()) }
    }

    pub fn claim(&self) -> Claim {
        Claim { workload: self.workload, dense_y: self.dense_y }
    }

    pub fn build_trace(&self) -> TraceTable<BaseElement> {
        let (w, len) = (width(self.workload), trace_len(self.workload));
        let mut columns = vec![vec![BaseElement::ZERO; len]; w];
        match self.workload {
            Workload::Matmul => fill_matmul(&mut columns, 0, len, self.out_override),
            Workload::Dense => dense::fill(&mut columns, 0, len, &dense::input()),
        }
        TraceTable::init(columns)
    }
}

impl Prover for ClassicalProver {
    type BaseField = BaseElement;
    type Air = ClassicalAir;
    type Trace = TraceTable<BaseElement>;

    fn get_pub_inputs(&self, _trace: &Self::Trace) -> Claim {
        self.claim()
    }

    fn options(&self) -> &ProofOptions {
        &self.options
    }
}
