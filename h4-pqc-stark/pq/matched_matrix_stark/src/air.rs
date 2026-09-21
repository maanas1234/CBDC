use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    Air,
    AirContext,
    Assertion,
    ByteWriter,
    EvaluationFrame,
    ProofOptions,
    Serializable,
    TraceInfo,
    TransitionConstraintDegree,
};

use crate::lattice;

use crate::trace::{
    ACC_START,
    AMOUNT_START,
    AMOUNT_SELECTOR_COL,
    B_START,
    CLOCK_COL,
    FINAL_SELECTOR_COL,
    K_START,
    MATRIX_A_START,
    MATRIX_B_START,
    MATRIX_C_START,
    MATRIX_OUT_START,
    RANDOMNESS_COL,
    TRACE_WIDTH,
};

pub struct PublicInputs {
    pub lattice_c: [u64; lattice::M],
}

impl Serializable for PublicInputs {
    fn write_into<W: ByteWriter>(&self, target: &mut W) {
        let values: Vec<BaseElement> = self
            .lattice_c
            .iter()
            .map(|&value| BaseElement::from(value))
            .collect();

        target.write(&values[..]);
    }
}

pub struct MatchedAir {
    context: AirContext<BaseElement>,
    lattice_c: [u64; lattice::M],
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

        let mut degrees = Vec::new();

        // Clock.
        degrees.push(TransitionConstraintDegree::new(1));

        // Lattice accumulators.
        for _ in 0..lattice::M {
            degrees.push(TransitionConstraintDegree::new(3));
        }

        // Quotients.
        for _ in 0..lattice::M {
            degrees.push(TransitionConstraintDegree::new(1));
        }

        // Amount limbs.
        for _ in 0..lattice::LIMBS {
            degrees.push(TransitionConstraintDegree::new(1));
        }

        // Matrix A, B, C.
        for _ in 0..12 {
            degrees.push(TransitionConstraintDegree::new(1));
        }

        // Matrix multiplication.
        for _ in 0..4 {
            degrees.push(TransitionConstraintDegree::new(2));
        }

        // Matrix output binding.
        for _ in 0..4 {
            degrees.push(TransitionConstraintDegree::new(1));
        }


        // 1 clock
        // 128 * 2 accumulator assertions
        // 12 matrix input assertions
        // 4 matrix output assertions
        //
        // = 273
        let num_assertions = 273;

        Self {
            context: AirContext::new(
                trace_info,
                degrees,
                num_assertions,
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
        _periodic_values: &[E],
        result: &mut [E],
    ) {
        let current = frame.current();
        let next = frame.next();

        // ---------------------------------------------------------
        // Clock
        // ---------------------------------------------------------

        result[0] =
            next[CLOCK_COL]
            - current[CLOCK_COL]
            - E::ONE;

        // ---------------------------------------------------------
        // Lattice relation
        // ---------------------------------------------------------

        for j in 0..lattice::M {
            let acc_current =
                current[ACC_START + j];

            let acc_next =
                next[ACC_START + j];

            let b =
                current[B_START + j];

            let randomness =
                current[RANDOMNESS_COL];

            let amount_selector =
                current[AMOUNT_SELECTOR_COL];

            let final_selector =
                current[FINAL_SELECTOR_COL];

            let mut amount_term = E::ZERO;

            for limb in 0..lattice::LIMBS {
                amount_term +=
                    E::from(
                        BaseElement::from(
                            lattice::g_coeff(j, limb),
                        ),
                    )
                    * current[AMOUNT_START + limb];
            }

            let commitment =
                E::from(
                    BaseElement::from(
                        self.lattice_c[j],
                    ),
                );

            let quotient =
                current[K_START + j]
                * E::from(
                    BaseElement::from(lattice::Q),
                );

            let normal_selector =
                E::ONE
                - amount_selector
                - final_selector;

            let normal =
                normal_selector
                * b
                * randomness;

            let amount =
                amount_selector
                * amount_term;

            let final_term =
                final_selector
                * (commitment + quotient);

            result[1 + j] =
                acc_next
                - acc_current
                - normal
                - amount
                + final_term;
        }

        let mut index =
            1 + lattice::M;

        // ---------------------------------------------------------
        // Quotients constant
        // ---------------------------------------------------------

        for j in 0..lattice::M {
            result[index] =
                next[K_START + j]
                - current[K_START + j];

            index += 1;
        }

        // ---------------------------------------------------------
        // Amount limbs constant
        // ---------------------------------------------------------

        for limb in 0..lattice::LIMBS {
            result[index] =
                next[AMOUNT_START + limb]
                - current[AMOUNT_START + limb];

            index += 1;
        }

        // ---------------------------------------------------------
        // Matrix inputs constant
        // ---------------------------------------------------------

        for i in 0..12 {
            result[index] =
                next[MATRIX_A_START + i]
                - current[MATRIX_A_START + i];

            index += 1;
        }

        // ---------------------------------------------------------
        // Matrix multiplication
        // ---------------------------------------------------------

        let a00 = current[MATRIX_A_START];
        let a01 = current[MATRIX_A_START + 1];
        let a10 = current[MATRIX_A_START + 2];
        let a11 = current[MATRIX_A_START + 3];

        let b00 = current[MATRIX_B_START];
        let b01 = current[MATRIX_B_START + 1];
        let b10 = current[MATRIX_B_START + 2];
        let b11 = current[MATRIX_B_START + 3];

        let o00 = current[MATRIX_OUT_START];
        let o01 = current[MATRIX_OUT_START + 1];
        let o10 = current[MATRIX_OUT_START + 2];
        let o11 = current[MATRIX_OUT_START + 3];

        result[index] =
            o00 - (a00 * b00 + a01 * b10);
        index += 1;

        result[index] =
            o01 - (a00 * b01 + a01 * b11);
        index += 1;

        result[index] =
            o10 - (a10 * b00 + a11 * b10);
        index += 1;

        result[index] =
            o11 - (a10 * b01 + a11 * b11);
        index += 1;

        // ---------------------------------------------------------
        // Matrix output binding
        // ---------------------------------------------------------

        result[index] =
            current[MATRIX_OUT_START]
            - current[MATRIX_C_START];
        index += 1;

        result[index] =
            current[MATRIX_OUT_START + 1]
            - current[MATRIX_C_START + 1];
        index += 1;

        result[index] =
            current[MATRIX_OUT_START + 2]
            - current[MATRIX_C_START + 2];
        index += 1;

        result[index] =
            current[MATRIX_OUT_START + 3]
            - current[MATRIX_C_START + 3];

        index += 1;

        // ---------------------------------------------------------
        // B coefficient columns constant
        // ---------------------------------------------------------

    }

    fn get_assertions(&self) -> Vec<Assertion<Self::BaseField>> {
        let mut assertions =
            Vec::with_capacity(273);

        // Clock.
        assertions.push(
            Assertion::single(
                CLOCK_COL,
                0,
                BaseElement::ZERO,
            ),
        );

        // Accumulators.
        for j in 0..lattice::M {
            assertions.push(
                Assertion::single(
                    ACC_START + j,
                    0,
                    BaseElement::ZERO,
                ),
            );

            assertions.push(
                Assertion::single(
                    ACC_START + j,
                    lattice::N + 2,
                    BaseElement::ZERO,
                ),
            );
        }

        // Matrix A.
        for i in 0..4 {
            assertions.push(
                Assertion::single(
                    MATRIX_A_START + i,
                    0,
                    BaseElement::from((i + 1) as u32),
                ),
            );
        }

        // Matrix B.
        for i in 0..4 {
            assertions.push(
                Assertion::single(
                    MATRIX_B_START + i,
                    0,
                    BaseElement::from((i + 5) as u32),
                ),
            );
        }

        // Matrix C.
        let c = [19u32, 22, 43, 50];

        for i in 0..4 {
            assertions.push(
                Assertion::single(
                    MATRIX_C_START + i,
                    0,
                    BaseElement::from(c[i]),
                ),
            );
        }

        // Matrix output.
        for i in 0..4 {
            assertions.push(
                Assertion::single(
                    MATRIX_OUT_START + i,
                    0,
                    BaseElement::from(c[i]),
                ),
            );
        }

        assertions
    }

    fn get_periodic_column_values(
        &self,
    ) -> Vec<Vec<Self::BaseField>> {
        // No periodic columns.
        //
        // All coefficients and selectors are explicitly stored
        // in the trace, avoiding periodic-column/OOD ambiguity.
        Vec::new()
    }
}
