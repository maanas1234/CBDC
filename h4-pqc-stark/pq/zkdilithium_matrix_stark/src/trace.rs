use winterfell::{
    math::{
        fields::f23201::BaseElement,
        FieldElement,
    },
    TraceTable,
};

use crate::{
    lattice,
    shortness,
};

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

pub fn build_trace(
    witness: &Witness,
    c: [u32; 2],
) -> TraceTable<BaseElement> {
    let mut columns =
        vec![
            vec![BaseElement::ZERO; TRACE_LENGTH];
            TRACE_WIDTH
        ];

    // ------------------------------------------------------
    // Witness columns
    // ------------------------------------------------------

    for row in 0..TRACE_LENGTH {
        columns[0][row] =
            BaseElement::from(witness.s0);

        columns[1][row] =
            BaseElement::from(witness.s1);

        columns[2][row] =
            BaseElement::from(witness.r0);

        columns[3][row] =
            BaseElement::from(witness.r1);

        columns[4][row] =
            BaseElement::from(witness.k0);

        columns[5][row] =
            BaseElement::from(witness.k1);

        columns[6][row] =
            BaseElement::from(row as u32);
    }

    // ------------------------------------------------------
    // Four-bit decompositions
    // ------------------------------------------------------

    let values = [
        witness.s0,
        witness.s1,
        witness.r0,
        witness.r1,
    ];

    for group in 0..4 {
        let value = values[group];

        let bits =
            if value <= shortness::BETA {
                shortness::decompose(value)
            } else {
                shortness::decompose_unchecked(value)
            };

        let start = 9 + group * 4;

        // Actual bits at row 0.
        for i in 0..4 {
            columns[start + i][0] =
                BaseElement::from(bits[i]);
        }

        // Complementary values on later rows.
        //
        // This is debug-tier scaffolding to keep the tiny
        // trace from collapsing constraint polynomials.
        for row in 1..TRACE_LENGTH {
            for i in 0..4 {
                columns[start + i][row] =
                    BaseElement::from(1u32 - bits[i]);
            }
        }
    }

    // ------------------------------------------------------
    // Lattice accumulators
    //
    // C0 =
    // 3*s0 + 5*s1 + 13*r0 + 17*r1 - q*k0
    //
    // C1 =
    // 7*s0 + 11*s1 + 19*r0 + 23*r1 - q*k1
    //
    // Then subtract public C.
    // ------------------------------------------------------

    let q = lattice::Q;

    columns[7][0] =
        BaseElement::ZERO;

    columns[8][0] =
        BaseElement::ZERO;

    // s0
    columns[7][1] =
        columns[7][0]
        + BaseElement::from(3u32)
            * columns[0][0];

    columns[8][1] =
        columns[8][0]
        + BaseElement::from(7u32)
            * columns[0][0];

    // s1
    columns[7][2] =
        columns[7][1]
        + BaseElement::from(5u32)
            * columns[1][1];

    columns[8][2] =
        columns[8][1]
        + BaseElement::from(11u32)
            * columns[1][1];

    // r0
    columns[7][3] =
        columns[7][2]
        + BaseElement::from(13u32)
            * columns[2][2];

    columns[8][3] =
        columns[8][2]
        + BaseElement::from(19u32)
            * columns[2][2];

    // r1
    columns[7][4] =
        columns[7][3]
        + BaseElement::from(17u32)
            * columns[3][3];

    columns[8][4] =
        columns[8][3]
        + BaseElement::from(23u32)
            * columns[3][3];

    // q*k
    columns[7][5] =
        columns[7][4]
        - BaseElement::from(q as u32)
            * columns[4][4];

    columns[8][5] =
        columns[8][4]
        - BaseElement::from(q as u32)
            * columns[5][4];

    // subtract public commitment
    columns[7][6] =
        columns[7][5]
        - BaseElement::from(c[0]);

    columns[8][6] =
        columns[8][5]
        - BaseElement::from(c[1]);

    // Carry final result.
    columns[7][7] =
        columns[7][6];

    columns[8][7] =
        columns[8][6];

    // IMPORTANT:
    // No assertions here.
    //
    // The AIR, not the trace builder, decides whether the
    // witness satisfies the public statement.

    TraceTable::init(columns)
}
