use std::time::Instant;

use winterfell::{
    crypto::{
        hashers::Blake3_256,
        DefaultRandomCoin,
        MerkleTree,
    },
    math::{
        fields::f128::BaseElement,
        FieldElement,
        ToElements,
    },
    matrix::ColMatrix,
    Air,
    AirContext,
    Assertion,
    AuxRandElements,
    BatchingMethod,
    CompositionPoly,
    CompositionPolyTrace,
    DefaultConstraintCommitment,
    DefaultConstraintEvaluator,
    DefaultTraceLde,
    EvaluationFrame,
    FieldExtension,
    PartitionOptions,
    ProofOptions,
    Prover,
    StarkDomain,
    Trace,
    TraceInfo,
    TracePolyTable,
    TraceTable,
    TransitionConstraintDegree,
};

const TRACE_WIDTH: usize = 12;
const TRACE_LENGTH: usize = 8;

// A = [1 2]
//     [3 4]
const A: [[u128; 2]; 2] = [
    [1, 2],
    [3, 4],
];

// B = [5 6]
//     [7 8]
const B: [[u128; 2]; 2] = [
    [5, 6],
    [7, 8],
];

// C = A × B
//
// C = [19 22]
//     [43 50]
const C: [[u128; 2]; 2] = [
    [19, 22],
    [43, 50],
];


// ============================================================
// PUBLIC INPUTS
// ============================================================

pub struct MatrixPublicInputs {
    pub values: [BaseElement; TRACE_WIDTH],
}

impl ToElements<BaseElement> for MatrixPublicInputs {
    fn to_elements(&self) -> Vec<BaseElement> {
        self.values.to_vec()
    }
}


// ============================================================
// AIR
// ============================================================

pub struct MatrixAir {
    context: AirContext<BaseElement>,

    a00: BaseElement,
    a01: BaseElement,
    a10: BaseElement,
    a11: BaseElement,

    b00: BaseElement,
    b01: BaseElement,
    b10: BaseElement,
    b11: BaseElement,

    c00: BaseElement,
    c01: BaseElement,
    c10: BaseElement,
    c11: BaseElement,
}

impl Air for MatrixAir {
    type BaseField = BaseElement;
    type PublicInputs = MatrixPublicInputs;

    fn new(
        trace_info: TraceInfo,
        pub_inputs: Self::PublicInputs,
        options: ProofOptions,
    ) -> Self {
        assert_eq!(TRACE_WIDTH, trace_info.width());

        let degrees = vec![
            TransitionConstraintDegree::new(2),
            TransitionConstraintDegree::new(2),
            TransitionConstraintDegree::new(2),
            TransitionConstraintDegree::new(2),
        ];

        let num_assertions = TRACE_WIDTH;

        Self {
            context: AirContext::new(
                trace_info,
                degrees,
                num_assertions,
                options,
            ),

            a00: pub_inputs.values[0],
            a01: pub_inputs.values[1],
            a10: pub_inputs.values[2],
            a11: pub_inputs.values[3],

            b00: pub_inputs.values[4],
            b01: pub_inputs.values[5],
            b10: pub_inputs.values[6],
            b11: pub_inputs.values[7],

            c00: pub_inputs.values[8],
            c01: pub_inputs.values[9],
            c10: pub_inputs.values[10],
            c11: pub_inputs.values[11],
        }
    }

    fn evaluate_transition<E: FieldElement + From<Self::BaseField>>(
        &self,
        frame: &EvaluationFrame<E>,
        _periodic_values: &[E],
        result: &mut [E],
    ) {
        let current = frame.current();

        let a00 = current[0];
        let a01 = current[1];
        let a10 = current[2];
        let a11 = current[3];

        let b00 = current[4];
        let b01 = current[5];
        let b10 = current[6];
        let b11 = current[7];

        let c00 = current[8];
        let c01 = current[9];
        let c10 = current[10];
        let c11 = current[11];

        // C00 = A00*B00 + A01*B10
        result[0] =
            c00 - (a00 * b00 + a01 * b10);

        // C01 = A00*B01 + A01*B11
        result[1] =
            c01 - (a00 * b01 + a01 * b11);

        // C10 = A10*B00 + A11*B10
        result[2] =
            c10 - (a10 * b00 + a11 * b10);

        // C11 = A10*B01 + A11*B11
        result[3] =
            c11 - (a10 * b01 + a11 * b11);
    }

    fn get_assertions(&self) -> Vec<Assertion<Self::BaseField>> {
        vec![
            Assertion::single(0, 0, self.a00),
            Assertion::single(1, 0, self.a01),
            Assertion::single(2, 0, self.a10),
            Assertion::single(3, 0, self.a11),

            Assertion::single(4, 0, self.b00),
            Assertion::single(5, 0, self.b01),
            Assertion::single(6, 0, self.b10),
            Assertion::single(7, 0, self.b11),

            Assertion::single(8, 0, self.c00),
            Assertion::single(9, 0, self.c01),
            Assertion::single(10, 0, self.c10),
            Assertion::single(11, 0, self.c11),
        ]
    }

    fn context(&self) -> &AirContext<Self::BaseField> {
        &self.context
    }
}


// ============================================================
// PROVER
// ============================================================

pub struct MatrixProver {
    options: ProofOptions,
}

impl MatrixProver {
    pub fn new(options: ProofOptions) -> Self {
        Self { options }
    }
}

impl Prover for MatrixProver {
    type BaseField = BaseElement;
    type Air = MatrixAir;
    type Trace = TraceTable<Self::BaseField>;

    type HashFn = Blake3_256<Self::BaseField>;
    type VC = MerkleTree<Self::HashFn>;
    type RandomCoin = DefaultRandomCoin<Self::HashFn>;

    type TraceLde<E: FieldElement<BaseField = Self::BaseField>> =
        DefaultTraceLde<E, Self::HashFn, Self::VC>;

    type ConstraintCommitment<
        E: FieldElement<BaseField = Self::BaseField>
    > = DefaultConstraintCommitment<
        E,
        Self::HashFn,
        Self::VC,
    >;

    type ConstraintEvaluator<
        'a,
        E: FieldElement<BaseField = Self::BaseField>
    > = DefaultConstraintEvaluator<
        'a,
        Self::Air,
        E,
    >;

    fn get_pub_inputs(
        &self,
        _trace: &Self::Trace,
    ) -> MatrixPublicInputs {
        MatrixPublicInputs {
            values: [
                BaseElement::new(A[0][0]),
                BaseElement::new(A[0][1]),
                BaseElement::new(A[1][0]),
                BaseElement::new(A[1][1]),

                BaseElement::new(B[0][0]),
                BaseElement::new(B[0][1]),
                BaseElement::new(B[1][0]),
                BaseElement::new(B[1][1]),

                BaseElement::new(C[0][0]),
                BaseElement::new(C[0][1]),
                BaseElement::new(C[1][0]),
                BaseElement::new(C[1][1]),
            ],
        }
    }

    fn options(&self) -> &ProofOptions {
        &self.options
    }

    fn new_trace_lde<E: FieldElement<BaseField = Self::BaseField>>(
        &self,
        trace_info: &TraceInfo,
        main_trace: &ColMatrix<Self::BaseField>,
        domain: &StarkDomain<Self::BaseField>,
        partition_option: PartitionOptions,
    ) -> (
        Self::TraceLde<E>,
        TracePolyTable<E>,
    ) {
        DefaultTraceLde::new(
            trace_info,
            main_trace,
            domain,
            partition_option,
        )
    }

    fn build_constraint_commitment<
        E: FieldElement<BaseField = Self::BaseField>
    >(
        &self,
        composition_poly_trace: CompositionPolyTrace<E>,
        num_constraint_composition_columns: usize,
        domain: &StarkDomain<Self::BaseField>,
        partition_options: PartitionOptions,
    ) -> (
        Self::ConstraintCommitment<E>,
        CompositionPoly<E>,
    ) {
        DefaultConstraintCommitment::new(
            composition_poly_trace,
            num_constraint_composition_columns,
            domain,
            partition_options,
        )
    }

    fn new_evaluator<
        'a,
        E: FieldElement<BaseField = Self::BaseField>
    >(
        &self,
        air: &'a Self::Air,
        aux_rand_elements: Option<AuxRandElements<E>>,
        composition_coefficients:
            winterfell::ConstraintCompositionCoefficients<E>,
    ) -> Self::ConstraintEvaluator<'a, E> {
        DefaultConstraintEvaluator::new(
            air,
            aux_rand_elements,
            composition_coefficients,
        )
    }
}


// ============================================================
// TRACE
// ============================================================

fn build_trace() -> TraceTable<BaseElement> {
    let mut trace =
        TraceTable::new(TRACE_WIDTH, TRACE_LENGTH);

trace.fill(
    |state| {
        // Row 0: t = 1

        state[0] = BaseElement::new(A[0][0]);
        state[1] = BaseElement::new(A[0][1]);
        state[2] = BaseElement::new(A[1][0]);
        state[3] = BaseElement::new(A[1][1]);

        state[4] = BaseElement::new(B[0][0]);
        state[5] = BaseElement::new(B[0][1]);
        state[6] = BaseElement::new(B[1][0]);
        state[7] = BaseElement::new(B[1][1]);

        state[8] = BaseElement::new(C[0][0]);
        state[9] = BaseElement::new(C[0][1]);
        state[10] = BaseElement::new(C[1][0]);
        state[11] = BaseElement::new(C[1][1]);
    },
    |step, state| {
        // t goes from 1, 2, 3, ...
        let t = BaseElement::new((step + 2) as u128);

        // A' = tA
        state[0] = BaseElement::new(A[0][0]) * t;
        state[1] = BaseElement::new(A[0][1]) * t;
        state[2] = BaseElement::new(A[1][0]) * t;
        state[3] = BaseElement::new(A[1][1]) * t;

        // B' = tB
        state[4] = BaseElement::new(B[0][0]) * t;
        state[5] = BaseElement::new(B[0][1]) * t;
        state[6] = BaseElement::new(B[1][0]) * t;
        state[7] = BaseElement::new(B[1][1]) * t;

        // C' = t²C
        let t2 = t * t;

        state[8] = BaseElement::new(C[0][0]) * t2;
        state[9] = BaseElement::new(C[0][1]) * t2;
        state[10] = BaseElement::new(C[1][0]) * t2;
        state[11] = BaseElement::new(C[1][1]) * t2;
    },
);
    trace
}


// ============================================================
// MAIN
// ============================================================

fn main() {
    println!("==========================================");
    println!(" Classical ZK-STARK Matrix Multiplication");
    println!("==========================================");
    println!();

    println!("Matrix A:");
    println!("[1 2]");
    println!("[3 4]");
    println!();

    println!("Matrix B:");
    println!("[5 6]");
    println!("[7 8]");
    println!();

    println!("Expected A × B:");
    println!("[19 22]");
    println!("[43 50]");
    println!();

    println!("Building execution trace...");

    let trace = build_trace();

    println!("Trace width : {}", trace.width());
    println!("Trace length: {}", trace.length());
    println!();

    let options = ProofOptions::new(
        32,
        8,
        0,
        FieldExtension::None,
        8,
        31,
        BatchingMethod::Linear,
        BatchingMethod::Linear,
    );

    let prover = MatrixProver::new(options);

    println!("Generating STARK proof...");

    let proving_start = Instant::now();

    let proof = prover.prove(trace);

    let proving_time = proving_start.elapsed();

    match proof {
        Ok(proof) => {
            println!("Proof generated successfully.");

            let proof_bytes = proof.to_bytes();
            let proof_size = proof_bytes.len();

            println!(
                "Proof size: {} bytes ({:.2} KB)",
                proof_size,
                proof_size as f64 / 1024.0
            );

            println!(
                "Proof generation time: {:.3} ms",
                proving_time.as_secs_f64() * 1000.0
            );

            println!();
            println!("Verifying proof...");

            let public_inputs = MatrixPublicInputs {
                values: [
                    BaseElement::new(A[0][0]),
                    BaseElement::new(A[0][1]),
                    BaseElement::new(A[1][0]),
                    BaseElement::new(A[1][1]),

                    BaseElement::new(B[0][0]),
                    BaseElement::new(B[0][1]),
                    BaseElement::new(B[1][0]),
                    BaseElement::new(B[1][1]),

                    BaseElement::new(C[0][0]),
                    BaseElement::new(C[0][1]),
                    BaseElement::new(C[1][0]),
                    BaseElement::new(C[1][1]),
                ],
            };

            let acceptable_options =
                winterfell::AcceptableOptions::MinConjecturedSecurity(95);

            let verification_start = Instant::now();

            let verification_result =
                winterfell::verify::<
                    MatrixAir,
                    Blake3_256<BaseElement>,
                    DefaultRandomCoin<Blake3_256<BaseElement>>,
                    MerkleTree<Blake3_256<BaseElement>>,
                >(
                    proof,
                    public_inputs,
                    &acceptable_options,
                );

            let verification_time =
                verification_start.elapsed();

            match verification_result {
                Ok(_) => {
                    println!("STARK verification SUCCESSFUL.");

                    println!(
                        "Verification time: {:.3} ms",
                        verification_time.as_secs_f64() * 1000.0
                    );

                    println!();
                    println!("==========================================");
                    println!(" Classical STARK Baseline");
                    println!("==========================================");
                    println!(
                        "Proof size        : {} bytes ({:.2} KB)",
                        proof_size,
                        proof_size as f64 / 1024.0
                    );
                    println!(
                        "Proving time      : {:.3} ms",
                        proving_time.as_secs_f64() * 1000.0
                    );
                    println!(
                        "Verification time : {:.3} ms",
                        verification_time.as_secs_f64() * 1000.0
                    );
                    println!("==========================================");
                }

                Err(error) => {
                    println!("STARK verification FAILED.");
                    println!("Error: {:?}", error);
                }
            }
        }

        Err(error) => {
            println!("STARK proof generation FAILED.");
            println!("Error: {:?}", error);
        }
    }
}
