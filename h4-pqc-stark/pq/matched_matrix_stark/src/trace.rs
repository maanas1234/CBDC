use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    TraceTable,
};

use crate::lattice;

pub const TRACE_WIDTH: usize = 25;
pub const TRACE_LENGTH: usize = 8;

#[derive(Clone, Copy)]
pub struct Witness {
    pub s0: u32,
    pub s1: u32,
    pub r0: u32,
    pub r1: u32,
    pub k0: u32,
    pub k1: u32,
}

/// Build the normal valid test trace.
///
/// A = [1 2]
///     [3 4]
///
/// B = [5 6]
///     [7 8]
///
/// C = [19 22]
///     [43 50]
pub fn build_trace(w: &Witness) -> TraceTable<BaseElement> {
    build_trace_with_matrix(
        w,
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [19, 22, 43, 50],
    )
}

/// Build a trace using explicitly supplied matrix values.
///
/// This is used for validation tests so that we can deliberately
/// tamper with A, B, or C and verify that the STARK rejects it.
pub fn build_trace_with_matrix(
    w: &Witness,
    a: [u32; 4],
    b: [u32; 4],
    c: [u32; 4],
) -> TraceTable<BaseElement> {
    let mut columns =
        vec![vec![BaseElement::ZERO; TRACE_LENGTH]; TRACE_WIDTH];

    // ---------------------------------------------------------
    // Lattice witness: columns 0..5
    // ---------------------------------------------------------

    for row in 0..TRACE_LENGTH {
        columns[0][row] = BaseElement::from(w.s0);
        columns[1][row] = BaseElement::from(w.s1);
        columns[2][row] = BaseElement::from(w.r0);
        columns[3][row] = BaseElement::from(w.r1);
        columns[4][row] = BaseElement::from(w.k0);
        columns[5][row] = BaseElement::from(w.k1);
    }

    // ---------------------------------------------------------
    // Matrix A: columns 6..9
    //
    // A = [A00 A01]
    //     [A10 A11]
    // ---------------------------------------------------------

    for row in 0..TRACE_LENGTH {
        for i in 0..4 {
            columns[6 + i][row] = BaseElement::from(a[i]);
        }
    }

    // ---------------------------------------------------------
    // Matrix B: columns 10..13
    //
    // B = [B00 B01]
    //     [B10 B11]
    // ---------------------------------------------------------

    for row in 0..TRACE_LENGTH {
        for i in 0..4 {
            columns[10 + i][row] = BaseElement::from(b[i]);
        }
    }

    // ---------------------------------------------------------
    // Matrix output C: columns 14..17
    //
    // C = [C00 C01]
    //     [C10 C11]
    // ---------------------------------------------------------

    for row in 0..TRACE_LENGTH {
        for i in 0..4 {
            columns[14 + i][row] = BaseElement::from(c[i]);
        }
    }

    // ---------------------------------------------------------
    // Lattice accumulators: columns 18..19
    // ---------------------------------------------------------

    columns[18][0] = BaseElement::ZERO;
    columns[19][0] = BaseElement::ZERO;

    // First lattice term.
    columns[18][1] =
        columns[18][0]
        + BaseElement::from(3u32) * columns[0][0];

    columns[19][1] =
        columns[19][0]
        + BaseElement::from(7u32) * columns[0][0];

    // Second lattice term.
    columns[18][2] =
        columns[18][1]
        + BaseElement::from(5u32) * columns[1][1];

    columns[19][2] =
        columns[19][1]
        + BaseElement::from(11u32) * columns[1][1];

    // Third lattice term.
    columns[18][3] =
        columns[18][2]
        + BaseElement::from(13u32) * columns[2][2];

    columns[19][3] =
        columns[19][2]
        + BaseElement::from(19u32) * columns[2][2];

    // Fourth lattice term.
    columns[18][4] =
        columns[18][3]
        + BaseElement::from(17u32) * columns[3][3];

    columns[19][4] =
        columns[19][3]
        + BaseElement::from(23u32) * columns[3][3];

    // Quotient terms.
    columns[18][5] =
        columns[18][4]
        - BaseElement::from(lattice::Q as u32) * columns[4][4];

    columns[19][5] =
        columns[19][4]
        - BaseElement::from(lattice::Q as u32) * columns[5][4];

    // Public lattice commitments.
    columns[18][6] =
        columns[18][5] - BaseElement::from(75u32);

    columns[19][6] =
        columns[19][5] - BaseElement::from(113u32);

    // Carry final accumulator value.
    columns[18][7] = columns[18][6];
    columns[19][7] = columns[19][6];

    // ---------------------------------------------------------
    // Clock: column 20
    // ---------------------------------------------------------

    for row in 0..TRACE_LENGTH {
        columns[20][row] = BaseElement::from(row as u32);
    }

    // ---------------------------------------------------------
    // Matrix multiplication results: columns 21..24
    //
    // 21 = A00*B00 + A01*B10
    // 22 = A00*B01 + A01*B11
    // 23 = A10*B00 + A11*B10
    // 24 = A10*B01 + A11*B11
    // ---------------------------------------------------------

    columns[21][0] =
        columns[6][0] * columns[10][0]
        + columns[7][0] * columns[12][0];

    columns[22][0] =
        columns[6][0] * columns[11][0]
        + columns[7][0] * columns[13][0];

    columns[23][0] =
        columns[8][0] * columns[10][0]
        + columns[9][0] * columns[12][0];

    columns[24][0] =
        columns[8][0] * columns[11][0]
        + columns[9][0] * columns[13][0];

    // Keep the computed matrix products constant across the trace.
    for row in 1..TRACE_LENGTH {
        columns[21][row] = columns[21][0];
        columns[22][row] = columns[22][0];
        columns[23][row] = columns[23][0];
        columns[24][row] = columns[24][0];
    }

    TraceTable::init(columns)
}
