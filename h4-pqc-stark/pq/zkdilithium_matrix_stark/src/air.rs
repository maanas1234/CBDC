use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    Air, AirContext, Assertion, ByteWriter, EvaluationFrame,
    ProofOptions, Serializable, TraceInfo,
    TransitionConstraintDegree,
};

use crate::trace::TRACE_WIDTH;

pub struct PublicInputs {
    pub c: [BaseElement; 2],
}

impl Serializable for PublicInputs {
    fn write_into<W: ByteWriter>(&self, target: &mut W) {
        target.write(&self.c[..]);
    }
}

pub struct SisAir {
    context: AirContext<BaseElement>,
    c: [BaseElement; 2],
}

impl Air for SisAir {
    type BaseField = BaseElement;
    type PublicInputs = PublicInputs;

    fn new(
        trace_info: TraceInfo,
        pub_inputs: PublicInputs,
        options: ProofOptions,
    ) -> Self {
        assert_eq!(trace_info.width(), TRACE_WIDTH);

        let degrees = vec![
            // 0: clock
            TransitionConstraintDegree::new(1),

            // 1..6: witness-copy constraints
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),

            // 7..8: lattice accumulator constraints
            TransitionConstraintDegree::with_cycles(1, vec![8]),
            TransitionConstraintDegree::with_cycles(1, vec![8]),

            // 9..24: Booleanity constraints
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),
            TransitionConstraintDegree::with_cycles(2, vec![8]),

            // 25..28: bit reconstruction
            TransitionConstraintDegree::with_cycles(1, vec![8]),
            TransitionConstraintDegree::with_cycles(1, vec![8]),
            TransitionConstraintDegree::with_cycles(1, vec![8]),
            TransitionConstraintDegree::with_cycles(1, vec![8]),
        ];

        Self {
            context: AirContext::new(
                trace_info,
                degrees,
                53,
                options,
            ),
            c: pub_inputs.c,
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

        // --------------------------------------------------
        // Clock
        // --------------------------------------------------

        result[0] =
            next[6] - current[6] - E::ONE;

        // --------------------------------------------------
        // Witness columns remain constant
        // --------------------------------------------------

        result[1] = next[0] - current[0];
        result[2] = next[1] - current[1];
        result[3] = next[2] - current[2];
        result[4] = next[3] - current[3];
        result[5] = next[4] - current[4];
        result[6] = next[5] - current[5];

        // --------------------------------------------------
        // Periodic selectors
        // --------------------------------------------------

        let s0_flag = periodic_values[0];
        let s1_flag = periodic_values[1];
        let r0_flag = periodic_values[2];
        let r1_flag = periodic_values[3];
        let k_flag = periodic_values[4];
        let c_flag = periodic_values[5];

        let shortness_flag = periodic_values[6];

        // --------------------------------------------------
        // SIS relation
        //
        // C0 =
        // 3*s0 + 5*s1 + 13*r0 + 17*r1 - q*k0
        //
        // C1 =
        // 7*s0 + 11*s1 + 19*r0 + 23*r1 - q*k1
        // --------------------------------------------------

        let term0 =
            s0_flag * E::from(3u32) * current[0]
            + s1_flag * E::from(5u32) * current[1]
            + r0_flag * E::from(13u32) * current[2]
            + r1_flag * E::from(17u32) * current[3]
            - k_flag * E::from(65537u32) * current[4]
            - c_flag * E::from(self.c[0]);

        let term1 =
            s0_flag * E::from(7u32) * current[0]
            + s1_flag * E::from(11u32) * current[1]
            + r0_flag * E::from(19u32) * current[2]
            + r1_flag * E::from(23u32) * current[3]
            - k_flag * E::from(65537u32) * current[5]
            - c_flag * E::from(self.c[1]);

        result[7] =
            next[7] - current[7] - term0;

        result[8] =
            next[8] - current[8] - term1;

        // --------------------------------------------------
        // Booleanity of witness bits
        //
        // b(b - 1) = 0
        // --------------------------------------------------

        for i in 0..16 {
            let b = current[9 + i];

            result[9 + i] =
                shortness_flag * b * (b - E::ONE);
        }

        // --------------------------------------------------
        // Bit reconstruction
        // --------------------------------------------------

        let s0 =
            current[9]
            + E::from(2u32) * current[10]
            + E::from(4u32) * current[11]
            + E::from(8u32) * current[12];

        let s1 =
            current[13]
            + E::from(2u32) * current[14]
            + E::from(4u32) * current[15]
            + E::from(8u32) * current[16];

        let r0 =
            current[17]
            + E::from(2u32) * current[18]
            + E::from(4u32) * current[19]
            + E::from(8u32) * current[20];

        let r1 =
            current[21]
            + E::from(2u32) * current[22]
            + E::from(4u32) * current[23]
            + E::from(8u32) * current[24];

        result[25] =
            shortness_flag * (current[0] - s0);

        result[26] =
            shortness_flag * (current[1] - s1);

        result[27] =
            shortness_flag * (current[2] - r0);

        result[28] =
            shortness_flag * (current[3] - r1);
    }

    fn get_assertions(&self) -> Vec<Assertion<Self::BaseField>> {
        let s = [2u32, 1u32];
        let r = [1u32, 3u32];
        let k = [0u32, 0u32];

        let mut assertions = Vec::with_capacity(53);

        // 48 witness boundary assertions
        for row in 0..8 {
            assertions.push(
                Assertion::single(
                    0,
                    row,
                    BaseElement::from(s[0]),
                )
            );

            assertions.push(
                Assertion::single(
                    1,
                    row,
                    BaseElement::from(s[1]),
                )
            );

            assertions.push(
                Assertion::single(
                    2,
                    row,
                    BaseElement::from(r[0]),
                )
            );

            assertions.push(
                Assertion::single(
                    3,
                    row,
                    BaseElement::from(r[1]),
                )
            );

            assertions.push(
                Assertion::single(
                    4,
                    row,
                    BaseElement::from(k[0]),
                )
            );

            assertions.push(
                Assertion::single(
                    5,
                    row,
                    BaseElement::from(k[1]),
                )
            );
        }

        // Clock starts at zero.
        assertions.push(
            Assertion::single(
                6,
                0,
                BaseElement::ZERO,
            )
        );

        // Accumulators start at zero.
        assertions.push(
            Assertion::single(
                7,
                0,
                BaseElement::ZERO,
            )
        );

        assertions.push(
            Assertion::single(
                8,
                0,
                BaseElement::ZERO,
            )
        );

        // Accumulators must finish at zero.
        assertions.push(
            Assertion::single(
                7,
                7,
                BaseElement::ZERO,
            )
        );

        assertions.push(
            Assertion::single(
                8,
                7,
                BaseElement::ZERO,
            )
        );

        assertions
    }

    fn get_periodic_column_values(
        &self,
    ) -> Vec<Vec<Self::BaseField>> {
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

            // public C
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

            // shortness selector
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
