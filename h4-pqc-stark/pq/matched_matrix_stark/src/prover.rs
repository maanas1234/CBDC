use winterfell::{
    math::fields::f23201::BaseElement,
    ProofOptions,
    Prover,
    TraceTable,
};

use crate::air::{MatchedAir, PublicInputs};
use crate::trace::{build_trace, build_trace_with_matrix, Witness};

pub struct MatchedProver {
    options: ProofOptions,
    lattice_c: [BaseElement; 2],
    witness: Witness,
    matrix_a: [u32; 4],
    matrix_b: [u32; 4],
    matrix_c: [u32; 4],
}

impl MatchedProver {
    pub fn new(
        options: ProofOptions,
        lattice_c: [BaseElement; 2],
        witness: Witness,
    ) -> Self {
        Self {
            options,
            lattice_c,
            witness,
            matrix_a: [1, 2, 3, 4],
            matrix_b: [5, 6, 7, 8],
            matrix_c: [19, 22, 43, 50],
        }
    }

    pub fn with_matrix(
        options: ProofOptions,
        lattice_c: [BaseElement; 2],
        witness: Witness,
        matrix_a: [u32; 4],
        matrix_b: [u32; 4],
        matrix_c: [u32; 4],
    ) -> Self {
        Self {
            options,
            lattice_c,
            witness,
            matrix_a,
            matrix_b,
            matrix_c,
        }
    }

    pub fn build_trace(&self) -> TraceTable<BaseElement> {
        build_trace_with_matrix(
            &self.witness,
            self.matrix_a,
            self.matrix_b,
            self.matrix_c,
        )
    }

    pub fn build_default_trace(&self) -> TraceTable<BaseElement> {
        build_trace(&self.witness)
    }
}

impl Prover for MatchedProver {
    type BaseField = BaseElement;
    type Air = MatchedAir;
    type Trace = TraceTable<BaseElement>;

    fn get_pub_inputs(&self, _trace: &Self::Trace) -> PublicInputs {
        PublicInputs {
            lattice_c: self.lattice_c,
        }
    }

    fn options(&self) -> &ProofOptions {
        &self.options
    }
}
