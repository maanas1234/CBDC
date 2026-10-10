//! SIS-opening block: proves knowledge of a short (bits, r) with c = G*bits + B*r mod p.
//!
//! - B and the row-0 selector are periodic (verifier-computed) columns.
//! - Arithmetic is native mod p; there is no quotient column.
//! - bits are boolean and constant; r is constrained to {-1, 0, 1} exactly.

use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    Assertion, TransitionConstraintDegree,
};

use crate::params::{b_entry, felt_from_i64, g_entry, AMOUNT_BITS, FINAL_ROW, N_RAND, SIS_ROWS};

const ACC: usize = 0;
const BITS: usize = ACC + SIS_ROWS;
const R: usize = BITS + AMOUNT_BITS;
const U0: usize = R + 1;
const U1: usize = R + 2;
pub const WIDTH: usize = R + 3;
pub const CONSTRAINTS: usize = SIS_ROWS + 2 * AMOUNT_BITS + 4;
pub const ASSERTIONS: usize = 2 * SIS_ROWS;
pub const PERIODIC: usize = 1 + SIS_ROWS;
/// Rows needed: r occupies rows 1..=N_RAND, accumulators are checked at FINAL_ROW.
pub const MIN_LEN: usize = FINAL_ROW + 1;

pub fn degrees(trace_len: usize) -> Vec<TransitionConstraintDegree> {
    let mut d = vec![TransitionConstraintDegree::with_cycles(1, vec![trace_len]); SIS_ROWS];
    d.extend(vec![TransitionConstraintDegree::new(2); AMOUNT_BITS]);
    d.extend(vec![TransitionConstraintDegree::new(1); AMOUNT_BITS]);
    d.extend(vec![TransitionConstraintDegree::new(2); 3]);
    d.push(TransitionConstraintDegree::new(1));
    d
}

/// `periodic` starts at this block's first periodic column: [sel0, B_0, ..., B_{n-1}].
pub fn constraints<E: FieldElement + From<BaseElement>>(cur: &[E], next: &[E], periodic: &[E], base: usize, out: &mut [E]) {
    let sel0 = periodic[0];
    for j in 0..SIS_ROWS {
        let mut amount_term = E::ZERO;
        for t in 0..AMOUNT_BITS {
            amount_term += E::from(BaseElement::from(g_entry(j, t))) * cur[base + BITS + t];
        }
        out[j] = next[base + ACC + j] - cur[base + ACC + j] - sel0 * amount_term - periodic[1 + j] * cur[base + R];
    }
    let mut k = SIS_ROWS;
    for t in 0..AMOUNT_BITS {
        out[k] = cur[base + BITS + t] * (cur[base + BITS + t] - E::ONE);
        k += 1;
    }
    for t in 0..AMOUNT_BITS {
        out[k] = next[base + BITS + t] - cur[base + BITS + t];
        k += 1;
    }
    out[k] = cur[base + U0] * (cur[base + U0] - E::ONE);
    out[k + 1] = cur[base + U1] * (cur[base + U1] - E::ONE);
    out[k + 2] = cur[base + U0] * cur[base + U1];
    // r + 1 = u0 + 2*u1 with u0, u1 boolean and not both set  =>  r in {-1, 0, 1}.
    out[k + 3] = cur[base + R] + E::ONE - cur[base + U0] - E::from(BaseElement::from(2u64)) * cur[base + U1];
}

pub fn assertions(base: usize, commitment: &[u64; SIS_ROWS]) -> Vec<Assertion<BaseElement>> {
    let mut v = Vec::with_capacity(ASSERTIONS);
    for j in 0..SIS_ROWS {
        v.push(Assertion::single(base + ACC + j, 0, BaseElement::ZERO));
        v.push(Assertion::single(base + ACC + j, FINAL_ROW, BaseElement::from(commitment[j])));
    }
    v
}

pub fn periodic_columns(trace_len: usize) -> Vec<Vec<BaseElement>> {
    let mut columns = Vec::with_capacity(PERIODIC);
    let mut sel0 = vec![BaseElement::ZERO; trace_len];
    sel0[0] = BaseElement::ONE;
    columns.push(sel0);
    for j in 0..SIS_ROWS {
        let mut col = vec![BaseElement::ZERO; trace_len];
        for i in 0..N_RAND {
            col[i + 1] = BaseElement::from(b_entry(j, i));
        }
        columns.push(col);
    }
    columns
}

/// Fills the block from (bits, r) as given; malformed values are written unchanged for tests.
pub fn fill(columns: &mut [Vec<BaseElement>], base: usize, len: usize, bits: &[i64; AMOUNT_BITS], r: &[i64; N_RAND]) {
    for t in 0..AMOUNT_BITS {
        let bit = felt_from_i64(bits[t]);
        for row in 0..len {
            columns[base + BITS + t][row] = bit;
        }
    }
    let mut r_col = vec![0i64; len];
    r_col[1..=N_RAND].copy_from_slice(r);
    for row in 0..len {
        let v = r_col[row] + 1;
        columns[base + R][row] = felt_from_i64(r_col[row]);
        columns[base + U0][row] = felt_from_i64(v.rem_euclid(2));
        columns[base + U1][row] = felt_from_i64(v.div_euclid(2));
    }
    for j in 0..SIS_ROWS {
        let mut amount_term = BaseElement::ZERO;
        for t in 0..AMOUNT_BITS {
            amount_term += BaseElement::from(g_entry(j, t)) * felt_from_i64(bits[t]);
        }
        let mut acc = BaseElement::ZERO;
        columns[base + ACC + j][0] = acc;
        for row in 0..len - 1 {
            if row == 0 {
                acc += amount_term;
            }
            if (1..=N_RAND).contains(&row) {
                acc += BaseElement::from(b_entry(j, row - 1)) * felt_from_i64(r_col[row]);
            }
            columns[base + ACC + j][row + 1] = acc;
        }
    }
}
