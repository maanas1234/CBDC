use winterfell::{
    math::{
        fields::f23201::BaseElement,
        StarkField,
    },
    ProofOptions,
    Prover,
    TraceTable,
};

use crate::air::{PublicInputs, SisAir};
use crate::trace::{build_trace, Witness};

pub struct SisProver {
    options: ProofOptions,
    c: Vec<BaseElement>,
    witness: Witness,
}

impl SisProver {
    pub fn new(
        options: ProofOptions,
        c: Vec<BaseElement>,
        witness: Witness,
    ) -> Self {
        Self {
            options,
            c,
            witness,
        }
    }

    pub fn build_trace(&self) -> TraceTable<BaseElement> {
        build_trace(
            &self.witness,
            [
                self.c[0].as_int() as u32,
                self.c[1].as_int() as u32,
            ],
        )
    }
}

impl Prover for SisProver {
    type BaseField = BaseElement;
    type Air = SisAir;
    type Trace = TraceTable<BaseElement>;

    fn get_pub_inputs(
        &self,
        _trace: &Self::Trace,
    ) -> PublicInputs {
        PublicInputs {
            c: [
                self.c[0],
                self.c[1],
            ],
        }
    }

    fn options(&self) -> &ProofOptions {
        &self.options
    }
}
