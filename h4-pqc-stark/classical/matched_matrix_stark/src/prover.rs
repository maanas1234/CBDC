use winterfell::{
    math::fields::f23201::BaseElement,
    ProofOptions,
    Prover,
    TraceTable,
};

use crate::air::ClassicalMatchedAir;
use crate::trace::{build_trace, Witness};

pub struct ClassicalProver {
    options: ProofOptions,
    witness: Witness,
}

impl ClassicalProver {
    pub fn new(
        options: ProofOptions,
        witness: Witness,
    ) -> Self {
        Self {
            options,
            witness,
        }
    }

    pub fn build_trace(&self) -> TraceTable<BaseElement> {
        build_trace(&self.witness)
    }
}

impl Prover for ClassicalProver {
    type BaseField = BaseElement;
    type Air = ClassicalMatchedAir;
    type Trace = TraceTable<BaseElement>;

    fn get_pub_inputs(
        &self,
        _trace: &Self::Trace,
    ) -> () {
        ()
    }

    fn options(&self) -> &ProofOptions {
        &self.options
    }
}
