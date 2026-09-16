use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    Air, AirContext, Assertion, ByteWriter, EvaluationFrame,
    ProofOptions, Serializable, TraceInfo,
    TransitionConstraintDegree,
};

use crate::trace::TRACE_WIDTH;

pub struct PublicInputs {
    pub lattice_c: [BaseElement; 2],
}

impl Serializable for PublicInputs {
    fn write_into<W: ByteWriter>(&self, target: &mut W) {
        target.write(&self.lattice_c[..]);
    }
}

pub struct MatchedAir {
    context: AirContext<BaseElement>,
    lattice_c: [BaseElement; 2],
}

impl Air for MatchedAir {
    type BaseField = BaseElement;
    type PublicInputs = PublicInputs;

    fn new(
        trace_info: TraceInfo,
        pub_inputs: PublicInputs,
        options: ProofOptions,
    ) -> Self {
        assert_eq!(trace_info.width(), TRACE_WIDTH);

        let degrees = vec![
            // Clock
            TransitionConstraintDegree::new(1),

            // Lattice witness is constant
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),

            // Matrix multiplication constraints.
            // Degree 2 because they contain products.
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),

            // Matrix output binding.
            TransitionConstraintDegree::with_cycles(1, vec![8]),
            TransitionConstraintDegree::with_cycles(1, vec![8]),
            TransitionConstraintDegree::with_cycles(1, vec![8]),
            TransitionConstraintDegree::with_cycles(1, vec![8]),

            // Lattice accumulators.
            TransitionConstraintDegree::with_cycles(1, vec![8]),
            TransitionConstraintDegree::with_cycles(1, vec![8]),
        ];

        Self {
            context: AirContext::new(
                trace_info,
                degrees,
                23,
                options,
            ),
            lattice_c: pub_inputs.lattice_c,
        }
    }

    fn context(&self) -> &AirContext<Self::BaseField> {
        &self.context
    }

    fn evaluate_transition<E: FieldElement + From<Self::BaseField>>(
        &self,
        frame: &EvaluationFrame<E>,
        periodic_values: &[E],
        result: &mut [E],
    ) {
        let current = frame.current();
        let next = frame.next();

        // =========================================================
        // 0. Clock
        // =========================================================

        result[0] =
            next[20] - current[20] - E::from(1u32);

        // =========================================================
        // 1-6. Lattice witness remains constant
        // =========================================================

        result[1] = next[0] - current[0];
        result[2] = next[1] - current[1];
        result[3] = next[2] - current[2];
        result[4] = next[3] - current[3];
        result[5] = next[4] - current[4];
        result[6] = next[5] - current[5];

        // =========================================================
        // 7-10. REAL MATRIX MULTIPLICATION
        //
        // A = [A00 A01]
        //     [A10 A11]
        //
        // B = [B00 B01]
        //     [B10 B11]
        //
        // Products stored in columns 21-24.
        // =========================================================

        let a00 = current[6];
        let a01 = current[7];
        let a10 = current[8];
        let a11 = current[9];

        let b00 = current[10];
        let b01 = current[11];
        let b10 = current[12];
        let b11 = current[13];

        result[7] =
            current[21]
            - (a00 * b00 + a01 * b10);

        result[8] =
            current[22]
            - (a00 * b01 + a01 * b11);

        result[9] =
            current[23]
            - (a10 * b00 + a11 * b10);

        result[10] =
            current[24]
            - (a10 * b01 + a11 * b11);

        // =========================================================
        // 11-14. Bind computed products to C
        //
        // C00 = product 21
        // C01 = product 22
        // C10 = product 23
        // C11 = product 24
        // =========================================================

        result[11] =
            current[14] - current[21];

        result[12] =
            current[15] - current[22];

        result[13] =
            current[16] - current[23];

        result[14] =
            current[17] - current[24];

        // =========================================================
        // 15-16. LATTICE RELATION
        // =========================================================

        let s0 = periodic_values[0];
        let s1 = periodic_values[1];
        let r0 = periodic_values[2];
        let r1 = periodic_values[3];
        let k = periodic_values[4];
        let c = periodic_values[5];

        let term0 =
            s0 * E::from(3u32) * current[0]
            + s1 * E::from(5u32) * current[1]
            + r0 * E::from(13u32) * current[2]
            + r1 * E::from(17u32) * current[3]
            - k * E::from(65537u32) * current[4]
            - c * E::from(self.lattice_c[0]);

        let term1 =
            s0 * E::from(7u32) * current[0]
            + s1 * E::from(11u32) * current[1]
            + r0 * E::from(19u32) * current[2]
            + r1 * E::from(23u32) * current[3]
            - k * E::from(65537u32) * current[5]
            - c * E::from(self.lattice_c[1]);

        result[15] =
            next[18] - current[18] - term0;

        result[16] =
            next[19] - current[19] - term1;
    }

    fn get_assertions(&self) -> Vec<Assertion<Self::BaseField>> {
        let mut assertions = Vec::with_capacity(15);

        // Lattice witness.
        assertions.push(
            Assertion::single(0, 0, BaseElement::from(2u32))
        );
        assertions.push(
            Assertion::single(1, 0, BaseElement::from(1u32))
        );
        assertions.push(
            Assertion::single(2, 0, BaseElement::from(1u32))
        );
        assertions.push(
            Assertion::single(3, 0, BaseElement::from(3u32))
        );
        assertions.push(
            Assertion::single(4, 0, BaseElement::ZERO)
        );
        assertions.push(
            Assertion::single(5, 0, BaseElement::ZERO)
        );

        // Clock.
        assertions.push(
            Assertion::single(20, 0, BaseElement::ZERO)
        );

        // Matrix inputs.
        assertions.push(
            Assertion::single(6, 0, BaseElement::from(1u32))
        );
        assertions.push(
            Assertion::single(7, 0, BaseElement::from(2u32))
        );
        assertions.push(
            Assertion::single(8, 0, BaseElement::from(3u32))
        );
        assertions.push(
            Assertion::single(9, 0, BaseElement::from(4u32))
        );

        // Matrix B.
        assertions.push(
            Assertion::single(10, 0, BaseElement::from(5u32))
        );
        assertions.push(
            Assertion::single(11, 0, BaseElement::from(6u32))
        );
        assertions.push(
            Assertion::single(12, 0, BaseElement::from(7u32))
        );
        assertions.push(
            Assertion::single(13, 0, BaseElement::from(8u32))
        );

        // Matrix output.
        assertions.push(
            Assertion::single(14, 0, BaseElement::from(19u32))
        );
        assertions.push(
            Assertion::single(15, 0, BaseElement::from(22u32))
        );
        assertions.push(
            Assertion::single(16, 0, BaseElement::from(43u32))
        );
        assertions.push(
            Assertion::single(17, 0, BaseElement::from(50u32))
        );

        // Lattice accumulator boundaries.
        assertions.push(
            Assertion::single(18, 0, BaseElement::ZERO)
        );
        assertions.push(
            Assertion::single(18, 7, BaseElement::ZERO)
        );
        assertions.push(
            Assertion::single(19, 0, BaseElement::ZERO)
        );
        assertions.push(
            Assertion::single(19, 7, BaseElement::ZERO)
        );

        assertions
    }

    fn get_periodic_column_values(&self) -> Vec<Vec<Self::BaseField>> {
        vec![
            // s0
            vec![
                BaseElement::ONE,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
            ],

            // s1
            vec![
                BaseElement::ZERO,
                BaseElement::ONE,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
            ],

            // r0
            vec![
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ONE,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
            ],

            // r1
            vec![
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ONE,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
            ],

            // k
            vec![
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ONE,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
            ],

            // commitment
            vec![
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ONE,
                BaseElement::ZERO,
                BaseElement::ZERO,
            ],

            // Dummy selector to make the matrix constraint
            // polynomial non-zero over the trace domain.
            vec![
                BaseElement::ONE,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
                BaseElement::ZERO,
            ],
        ]
    }
}
