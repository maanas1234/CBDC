use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    TraceTable,
};

pub const TRACE_WIDTH: usize = 19;
pub const TRACE_LENGTH: usize = 8;

#[derive(Clone, Copy)]
pub struct Witness {
    pub a00: u32,
    pub a01: u32,
    pub a10: u32,
    pub a11: u32,

    pub b00: u32,
    pub b01: u32,
    pub b10: u32,
    pub b11: u32,
}

/// Builds the same 2×2 matrix multiplication workload
/// used by the PQ matched prototype.
///
/// A = [1 2]
///     [3 4]
///
/// B = [5 6]
///     [7 8]
///
/// C = [19 22]
///     [43 50]
///
/// The trace contains:
/// 0..3   = A
/// 4..7   = B
/// 8..11  = C
/// 12..15 = matrix multiplication intermediates
/// 16     = clock
/// 17..18 = duplicated accumulator-style columns
pub fn build_trace(w: &Witness) -> TraceTable<BaseElement> {
    let mut columns =
        vec![vec![BaseElement::ZERO; TRACE_LENGTH]; TRACE_WIDTH];

    for row in 0..TRACE_LENGTH {
        // Matrix A
        columns[0][row] = BaseElement::from(w.a00);
        columns[1][row] = BaseElement::from(w.a01);
        columns[2][row] = BaseElement::from(w.a10);
        columns[3][row] = BaseElement::from(w.a11);

        // Matrix B
        columns[4][row] = BaseElement::from(w.b00);
        columns[5][row] = BaseElement::from(w.b01);
        columns[6][row] = BaseElement::from(w.b10);
        columns[7][row] = BaseElement::from(w.b11);

        // Expected matrix C
        columns[8][row] =
            BaseElement::from(w.a00 * w.b00 + w.a01 * w.b10);

        columns[9][row] =
            BaseElement::from(w.a00 * w.b01 + w.a01 * w.b11);

        columns[10][row] =
            BaseElement::from(w.a10 * w.b00 + w.a11 * w.b10);

        columns[11][row] =
            BaseElement::from(w.a10 * w.b01 + w.a11 * w.b11);

        // Clock
        columns[16][row] = BaseElement::from(row as u32);
    }

    // Matrix multiplication intermediates.
    //
    // These are kept as explicit trace columns so the AIR
    // constrains the multiplication directly.
    columns[12][0] =
        columns[0][0] * columns[4][0]
        + columns[1][0] * columns[6][0];

    columns[13][0] =
        columns[0][0] * columns[5][0]
        + columns[1][0] * columns[7][0];

    columns[14][0] =
        columns[2][0] * columns[4][0]
        + columns[3][0] * columns[6][0];

    columns[15][0] =
        columns[2][0] * columns[5][0]
        + columns[3][0] * columns[7][0];

    for row in 1..TRACE_LENGTH {
        columns[12][row] = columns[12][0];
        columns[13][row] = columns[13][0];
        columns[14][row] = columns[14][0];
        columns[15][row] = columns[15][0];
    }

    // Auxiliary columns are simple zero columns.
    // They provide non-constant trace structure for the old
    // Winterfell fork without changing the computation.
    for row in 0..TRACE_LENGTH {
        columns[17][row] = BaseElement::from(row as u32);
        columns[18][row] =
            BaseElement::from((row * row) as u32);
    }

    TraceTable::init(columns)
}
