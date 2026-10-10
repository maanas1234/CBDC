//! Post-quantum circuit: the same workload as the classical circuit, plus a proof of knowledge
//! of a short opening of a public SIS commitment (see sis.rs). The workload block is identical
//! to the classical one, so the measured overhead is the cost of the lattice opening alone.

use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    Air, AirContext, Assertion, ByteWriter, EvaluationFrame, ProofOptions, Prover, Serializable,
    TraceInfo, TraceTable,
};

use crate::classical::{fill_matmul, matmul_assertions, matmul_constraints, matmul_degrees, BLOCK_ASSERTIONS, BLOCK_CONSTRAINTS, BLOCK_WIDTH};
use crate::dense;
use crate::params::{Workload, AMOUNT_BITS, N_RAND, SIS_ROWS};
use crate::sis;

pub fn trace_len(w: Workload) -> usize {
    let workload_len = match w {
        Workload::Matmul => 8,
        Workload::Dense => dense::MIN_LEN,
    };
    sis::MIN_LEN.max(workload_len).next_power_of_two()
}

fn workload_width(w: Workload) -> usize {
    match w {
        Workload::Matmul => BLOCK_WIDTH,
        Workload::Dense => dense::WIDTH,
    }
}

pub fn width(w: Workload) -> usize {
    sis::WIDTH + workload_width(w)
}

pub fn num_constraints(w: Workload) -> usize {
    sis::CONSTRAINTS
        + match w {
            Workload::Matmul => BLOCK_CONSTRAINTS,
            Workload::Dense => dense::CONSTRAINTS,
        }
}

#[derive(Clone)]
pub struct Statement {
    pub workload: Workload,
    pub commitment: [u64; SIS_ROWS],
    pub dense_y: [u64; dense::OUT],
}

impl Serializable for Statement {
    fn write_into<W: ByteWriter>(&self, target: &mut W) {
        target.write_u8(self.workload as u8);
        let mut values: Vec<BaseElement> = self.commitment.iter().map(|&v| BaseElement::from(v)).collect();
        if self.workload == Workload::Dense {
            values.extend(self.dense_y.iter().map(|&v| BaseElement::from(v)));
        }
        target.write(&values[..]);
    }
}

pub struct PqAir {
    context: AirContext<BaseElement>,
    statement: Statement,
    len: usize,
}

impl Air for PqAir {
    type BaseField = BaseElement;
    type PublicInputs = Statement;

    fn new(trace_info: TraceInfo, statement: Statement, options: ProofOptions) -> Self {
        let w = statement.workload;
        assert_eq!(trace_info.width(), width(w));
        let len = trace_info.length();
        let mut degrees = sis::degrees(len);
        let workload_assertions = match w {
            Workload::Matmul => {
                degrees.extend(matmul_degrees());
                BLOCK_ASSERTIONS
            }
            Workload::Dense => {
                degrees.extend(dense::degrees(len));
                dense::ASSERTIONS
            }
        };
        let context = AirContext::new(trace_info, degrees, sis::ASSERTIONS + workload_assertions, options);
        Self { context, statement, len }
    }

    fn context(&self) -> &AirContext<BaseElement> {
        &self.context
    }

    fn evaluate_transition<E: FieldElement + From<BaseElement>>(&self, frame: &EvaluationFrame<E>, periodic: &[E], result: &mut [E]) {
        let (cur, next) = (frame.current(), frame.next());
        let (sis_out, work_out) = result.split_at_mut(sis::CONSTRAINTS);
        sis::constraints(cur, next, &periodic[..sis::PERIODIC], 0, sis_out);
        match self.statement.workload {
            Workload::Matmul => matmul_constraints(cur, next, sis::WIDTH, work_out),
            Workload::Dense => dense::constraints(cur, next, &periodic[sis::PERIODIC..], sis::WIDTH, work_out),
        }
    }

    fn get_assertions(&self) -> Vec<Assertion<BaseElement>> {
        let mut v = sis::assertions(0, &self.statement.commitment);
        match self.statement.workload {
            Workload::Matmul => v.extend(matmul_assertions(sis::WIDTH)),
            Workload::Dense => v.extend(dense::assertions(sis::WIDTH, &self.statement.dense_y)),
        }
        v
    }

    fn get_periodic_column_values(&self) -> Vec<Vec<BaseElement>> {
        let mut columns = sis::periodic_columns(self.len);
        if self.statement.workload == Workload::Dense {
            columns.extend(dense::periodic_columns(self.len));
        }
        columns
    }
}

/// Prover. `bits` and `r` are deliberately unchecked so tests can attempt malformed openings.
pub struct PqProver {
    pub options: ProofOptions,
    pub workload: Workload,
    pub commitment: [u64; SIS_ROWS],
    pub bits: [i64; AMOUNT_BITS],
    pub r: [i64; N_RAND],
    pub out_override: Option<[u64; 4]>,
    pub dense_y: [u64; dense::OUT],
}

impl PqProver {
    pub fn statement(&self) -> Statement {
        Statement { workload: self.workload, commitment: self.commitment, dense_y: self.dense_y }
    }

    pub fn build_trace(&self) -> TraceTable<BaseElement> {
        let len = trace_len(self.workload);
        let mut columns = vec![vec![BaseElement::ZERO; len]; width(self.workload)];
        sis::fill(&mut columns, 0, len, &self.bits, &self.r);
        match self.workload {
            Workload::Matmul => fill_matmul(&mut columns, sis::WIDTH, len, self.out_override),
            Workload::Dense => dense::fill(&mut columns, sis::WIDTH, len, &dense::input()),
        }
        TraceTable::init(columns)
    }
}

impl Prover for PqProver {
    type BaseField = BaseElement;
    type Air = PqAir;
    type Trace = TraceTable<BaseElement>;

    fn get_pub_inputs(&self, _trace: &Self::Trace) -> Statement {
        self.statement()
    }

    fn options(&self) -> &ProofOptions {
        &self.options
    }
}
