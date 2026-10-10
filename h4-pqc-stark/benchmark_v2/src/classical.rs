//! Classical baseline: STARK for the 2x2 matrix product only (no lattice commitment).

use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    Air, AirContext, Assertion, ByteWriter, EvaluationFrame, ProofOptions, Prover, Serializable,
    TraceInfo, TraceTable, TransitionConstraintDegree,
};

use crate::params::{MATRIX_A, MATRIX_B, MATRIX_C};

pub const TRACE_LEN: usize = 8;
pub const WIDTH: usize = BLOCK_WIDTH;
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

#[derive(Clone)]
pub struct NoInputs;
impl Serializable for NoInputs {
    fn write_into<W: ByteWriter>(&self, _target: &mut W) {}
}

pub struct ClassicalAir {
    context: AirContext<BaseElement>,
}

impl Air for ClassicalAir {
    type BaseField = BaseElement;
    type PublicInputs = NoInputs;

    fn new(trace_info: TraceInfo, _pub_inputs: NoInputs, options: ProofOptions) -> Self {
        assert_eq!(trace_info.width(), WIDTH);
        Self { context: AirContext::new(trace_info, matmul_degrees(), BLOCK_ASSERTIONS, options) }
    }

    fn context(&self) -> &AirContext<BaseElement> {
        &self.context
    }

    fn evaluate_transition<E: FieldElement + From<BaseElement>>(&self, frame: &EvaluationFrame<E>, _periodic: &[E], result: &mut [E]) {
        matmul_constraints(frame.current(), frame.next(), 0, result);
    }

    fn get_assertions(&self) -> Vec<Assertion<BaseElement>> {
        matmul_assertions(0)
    }
}

pub struct ClassicalProver {
    pub options: ProofOptions,
    pub out_override: Option<[u64; 4]>,
}

impl ClassicalProver {
    pub fn build_trace(&self) -> TraceTable<BaseElement> {
        let mut columns = vec![vec![BaseElement::ZERO; TRACE_LEN]; WIDTH];
        fill_matmul(&mut columns, 0, TRACE_LEN, self.out_override);
        TraceTable::init(columns)
    }
}

impl Prover for ClassicalProver {
    type BaseField = BaseElement;
    type Air = ClassicalAir;
    type Trace = TraceTable<BaseElement>;

    fn get_pub_inputs(&self, _trace: &Self::Trace) -> NoInputs {
        NoInputs
    }

    fn options(&self) -> &ProofOptions {
        &self.options
    }
}
