use winterfell::{
    math::{
        fields::f23201::BaseElement,
        FieldElement,
    },
    Air,
    AirContext,
    Assertion,
    EvaluationFrame,
    ProofOptions,
    TraceInfo,
    TransitionConstraintDegree,
};

use crate::trace::{TRACE_LENGTH, TRACE_WIDTH};

pub struct ClassicalMatchedAir {
    context: AirContext<BaseElement>,
}

impl Air for ClassicalMatchedAir {
    type BaseField = BaseElement;
    type PublicInputs = ();

    fn new(
        trace_info: TraceInfo,
        _public_inputs: Self::PublicInputs,
        options: ProofOptions,
    ) -> Self {
        let mut degrees = Vec::new();

        // Clock transition.
        degrees.push(TransitionConstraintDegree::new(1));

        // A and B witness columns remain constant.
        for _ in 0..8 {
            degrees.push(TransitionConstraintDegree::new(1));
        }

        // Four matrix multiplication constraints.
        for _ in 0..4 {
            degrees.push(TransitionConstraintDegree::new(2));
        }

        // Four constraints binding C to the computed products.
        for _ in 0..4 {
            degrees.push(TransitionConstraintDegree::new(1));
        }

        // Intermediate columns remain constant.
        for _ in 0..4 {
            degrees.push(TransitionConstraintDegree::new(1));
        }

        // Auxiliary columns.
        degrees.push(TransitionConstraintDegree::new(1));
        degrees.push(TransitionConstraintDegree::new(2));

        Self {
            context: AirContext::new(
                trace_info,
                degrees,
                22,
                options,
            ),
        }
    }

    fn context(&self) -> &AirContext<BaseElement> {
        &self.context
    }

    fn evaluate_transition<E: FieldElement<BaseField = BaseElement>>(
        &self,
        frame: &EvaluationFrame<E>,
        _periodic_values: &[E],
        result: &mut [E],
    ) {
        let current = frame.current();
        let next = frame.next();

        // 0: clock increments by one.
        result[0] = next[16] - current[16] - E::ONE;

        // 1..8: A and B remain constant.
        for i in 0..8 {
            result[1 + i] = next[i] - current[i];
        }

        // 9..12: matrix multiplication.
        result[9] =
            current[12]
            - (current[0] * current[4]
                + current[1] * current[6]);

        result[10] =
            current[13]
            - (current[0] * current[5]
                + current[1] * current[7]);

        result[11] =
            current[14]
            - (current[2] * current[4]
                + current[3] * current[6]);

        result[12] =
            current[15]
            - (current[2] * current[5]
                + current[3] * current[7]);

        // 13..16: bind C to multiplication results.
        result[13] = current[8] - current[12];
        result[14] = current[9] - current[13];
        result[15] = current[10] - current[14];
        result[16] = current[11] - current[15];

        // 17..20: intermediate columns remain constant.
        for i in 0..4 {
            result[17 + i] = next[12 + i] - current[12 + i];
        }

        // 21: auxiliary clock-like column.
        result[21] = next[17] - current[17] - E::ONE;

        // 22: auxiliary quadratic column.
        result[22] =
            next[18]
            - current[18]
            - E::from(2u32) * current[17]
            - E::ONE;
    }

    fn get_assertions(&self) -> Vec<Assertion<BaseElement>> {
        let mut assertions = Vec::new();

        // A = [1 2; 3 4]
        assertions.push(Assertion::single(0, 0, BaseElement::from(1u32)));
        assertions.push(Assertion::single(1, 0, BaseElement::from(2u32)));
        assertions.push(Assertion::single(2, 0, BaseElement::from(3u32)));
        assertions.push(Assertion::single(3, 0, BaseElement::from(4u32)));

        // B = [5 6; 7 8]
        assertions.push(Assertion::single(4, 0, BaseElement::from(5u32)));
        assertions.push(Assertion::single(5, 0, BaseElement::from(6u32)));
        assertions.push(Assertion::single(6, 0, BaseElement::from(7u32)));
        assertions.push(Assertion::single(7, 0, BaseElement::from(8u32)));

        // C = [19 22; 43 50]
        assertions.push(Assertion::single(8, 0, BaseElement::from(19u32)));
        assertions.push(Assertion::single(9, 0, BaseElement::from(22u32)));
        assertions.push(Assertion::single(10, 0, BaseElement::from(43u32)));
        assertions.push(Assertion::single(11, 0, BaseElement::from(50u32)));

        // Matrix multiplication intermediates.
        assertions.push(Assertion::single(12, 0, BaseElement::from(19u32)));
        assertions.push(Assertion::single(13, 0, BaseElement::from(22u32)));
        assertions.push(Assertion::single(14, 0, BaseElement::from(43u32)));
        assertions.push(Assertion::single(15, 0, BaseElement::from(50u32)));

        // Clock.
        assertions.push(Assertion::single(16, 0, BaseElement::ZERO));

        // Auxiliary columns.
        assertions.push(Assertion::single(17, 0, BaseElement::ZERO));
        assertions.push(Assertion::single(18, 0, BaseElement::ZERO));

        // End of trace.
        assertions.push(Assertion::single(
            16,
            TRACE_LENGTH - 1,
            BaseElement::from((TRACE_LENGTH - 1) as u32),
        ));

        assertions.push(Assertion::single(
            17,
            TRACE_LENGTH - 1,
            BaseElement::from((TRACE_LENGTH - 1) as u32),
        ));

        assertions.push(Assertion::single(
            18,
            TRACE_LENGTH - 1,
            BaseElement::from(
                ((TRACE_LENGTH - 1) * (TRACE_LENGTH - 1)) as u32
            ),
        ));

        assertions
    }

    fn get_periodic_column_values(
        &self,
    ) -> Vec<Vec<BaseElement>> {
        Vec::new()
    }
}
