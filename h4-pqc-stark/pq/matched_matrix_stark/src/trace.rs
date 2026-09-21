use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    TraceTable,
};

use crate::lattice;

pub const TRACE_LENGTH: usize = 512;

// 128 accumulators
pub const ACC_START: usize = 0;

// 128 quotient values
pub const K_START: usize = 128;

// 4 amount limbs
pub const AMOUNT_START: usize = 256;

// randomness
pub const RANDOMNESS_COL: usize = 260;

// clock
pub const CLOCK_COL: usize = 261;

// matrix A
pub const MATRIX_A_START: usize = 262;

// matrix B
pub const MATRIX_B_START: usize = 266;

// matrix C
pub const MATRIX_C_START: usize = 270;

// matrix outputs
pub const MATRIX_OUT_START: usize = 274;

// B coefficient columns: 128 columns
pub const B_START: usize = 278;

// amount selector
pub const AMOUNT_SELECTOR_COL: usize = 406;

// final selector
pub const FINAL_SELECTOR_COL: usize = 407;

pub const TRACE_WIDTH: usize = 408;

pub struct Witness {
    pub amount: u64,
    pub r: [i64; lattice::N],
    pub k: [i64; lattice::M],
}

fn field_from_i64(value: i64) -> BaseElement {
    if value >= 0 {
        BaseElement::from(value as u64)
    } else {
        BaseElement::ZERO - BaseElement::from((-value) as u64)
    }
}

pub fn build_trace(
    witness: &Witness,
    commitment: &[u64; lattice::M],
    matrix_a: [u32; 4],
    matrix_b: [u32; 4],
    matrix_c: [u32; 4],
) -> TraceTable<BaseElement> {
    let mut columns =
        vec![vec![BaseElement::ZERO; TRACE_LENGTH]; TRACE_WIDTH];

    let amount_limbs = lattice::amount_to_limbs(witness.amount);

    // ---------------------------------------------------------
    // Amount limbs
    // ---------------------------------------------------------

    for row in 0..TRACE_LENGTH {
        for limb in 0..lattice::LIMBS {
            columns[AMOUNT_START + limb][row] =
                BaseElement::from(amount_limbs[limb] as u32);
        }
    }

    // ---------------------------------------------------------
    // Randomness
    //
    // row 0 is reserved for the amount contribution.
    // r[0] starts at row 1.
    // ---------------------------------------------------------

    columns[RANDOMNESS_COL][0] = BaseElement::ZERO;

    for i in 0..lattice::N {
        columns[RANDOMNESS_COL][i + 1] =
            field_from_i64(witness.r[i]);
    }

    for row in (lattice::N + 1)..TRACE_LENGTH {
        columns[RANDOMNESS_COL][row] =
            BaseElement::ZERO;
    }

    // ---------------------------------------------------------
    // Quotients
    // ---------------------------------------------------------

    for j in 0..lattice::M {
        for row in 0..TRACE_LENGTH {
            columns[K_START + j][row] =
                field_from_i64(witness.k[j]);
        }
    }

    // ---------------------------------------------------------
    // Clock
    // ---------------------------------------------------------

    for row in 0..TRACE_LENGTH {
        columns[CLOCK_COL][row] =
            BaseElement::from(row as u32);
    }

    // ---------------------------------------------------------
    // Matrix inputs
    // ---------------------------------------------------------

    for row in 0..TRACE_LENGTH {
        for i in 0..4 {
            columns[MATRIX_A_START + i][row] =
                BaseElement::from(matrix_a[i]);

            columns[MATRIX_B_START + i][row] =
                BaseElement::from(matrix_b[i]);

            columns[MATRIX_C_START + i][row] =
                BaseElement::from(matrix_c[i]);
        }
    }

    // ---------------------------------------------------------
    // Matrix multiplication
    // ---------------------------------------------------------

    let out = [
        matrix_a[0] * matrix_b[0]
            + matrix_a[1] * matrix_b[2],

        matrix_a[0] * matrix_b[1]
            + matrix_a[1] * matrix_b[3],

        matrix_a[2] * matrix_b[0]
            + matrix_a[3] * matrix_b[2],

        matrix_a[2] * matrix_b[1]
            + matrix_a[3] * matrix_b[3],
    ];

    for row in 0..TRACE_LENGTH {
        for i in 0..4 {
            columns[MATRIX_OUT_START + i][row] =
                BaseElement::from(out[i]);
        }
    }

    // ---------------------------------------------------------
    // B coefficient columns
    // ---------------------------------------------------------

    for j in 0..lattice::M {
        for row in 0..TRACE_LENGTH {
            let coefficient =
                if row >= 1 && row <= lattice::N {
                    lattice::b_coeff(j, row - 1)
                } else {
                    0
                };

            columns[B_START + j][row] =
                BaseElement::from(coefficient);
        }
    }

    // ---------------------------------------------------------
    // Amount selector
    // ---------------------------------------------------------

    columns[AMOUNT_SELECTOR_COL][0] =
        BaseElement::from(1u32);

    // ---------------------------------------------------------
    // Final selector
    //
    // transition 257 -> 258
    // ---------------------------------------------------------

    columns[FINAL_SELECTOR_COL][lattice::N + 1] =
        BaseElement::from(1u32);

    // ---------------------------------------------------------
    // Lattice accumulators
    // ---------------------------------------------------------

    for j in 0..lattice::M {
        columns[ACC_START + j][0] =
            BaseElement::ZERO;

        // Amount contribution.
        let mut amount_term = BaseElement::ZERO;

        for limb in 0..lattice::LIMBS {
            amount_term +=
                BaseElement::from(
                    lattice::g_coeff(j, limb),
                )
                * columns[AMOUNT_START + limb][0];
        }

        columns[ACC_START + j][1] =
            amount_term;

        // B*r contributions.
        for i in 0..lattice::N {
            let previous =
                columns[ACC_START + j][i + 1];

            let contribution =
                BaseElement::from(
                    lattice::b_coeff(j, i),
                )
                * field_from_i64(witness.r[i]);

            columns[ACC_START + j][i + 2] =
                previous + contribution;
        }

        // Final commitment + quotient subtraction.
        let before_final =
            columns[ACC_START + j][lattice::N + 1];

        let c =
            BaseElement::from(commitment[j]);

        let kq =
            field_from_i64(witness.k[j])
            * BaseElement::from(lattice::Q);

        columns[ACC_START + j][lattice::N + 2] =
            before_final - c - kq;

        // Carry final value.
        for row in (lattice::N + 3)..TRACE_LENGTH {
            columns[ACC_START + j][row] =
                columns[ACC_START + j][lattice::N + 2];
        }
    }

    TraceTable::init(columns)
}
