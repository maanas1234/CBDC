//! Dense-layer block: y = W x over F_p for the first layer of the H1 MLP (165 -> 32).
//!
//! Public: weights W (periodic columns) and outputs y (assertions). Private: input x (trace).
//! Values are fixed-point integers at H1's scale (2^9); prover cost depends on the dimensions,
//! not the values. Linear part only; the ReLU after it is not proven here.

use winterfell::{
    math::{fields::f23201::BaseElement, FieldElement},
    Assertion, TransitionConstraintDegree,
};

use crate::params::{felt_from_i64, modulus};

pub const IN: usize = 165;
pub const OUT: usize = 32;
const ACC: usize = 0;
const X: usize = ACC + OUT;
pub const WIDTH: usize = X + 1;
pub const CONSTRAINTS: usize = OUT;
pub const ASSERTIONS: usize = 2 * OUT;
/// x occupies rows 1..=IN; outputs are checked at row IN + 1.
pub const FINAL_ROW: usize = IN + 1;
pub const MIN_LEN: usize = FINAL_ROW + 1;

fn splitmix(mut z: u64) -> u64 {
    z = z.wrapping_add(0x9e37_79b9_7f4a_7c15);
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    z ^ (z >> 31)
}

/// Public weight in [-512, 512] (fixed point, scale 2^9).
pub fn weight(k: usize, i: usize) -> i64 {
    (splitmix(0x5745_0000_0000 ^ ((k as u64) << 20) ^ i as u64) % 1025) as i64 - 512
}

/// Private input in [-4096, 4096] (fixed point, scale 2^9).
pub fn input() -> [i64; IN] {
    let mut x = [0i64; IN];
    for (i, v) in x.iter_mut().enumerate() {
        *v = (splitmix(0x5849_0000_0000 ^ i as u64) % 8193) as i64 - 4096;
    }
    x
}

/// y_k = sum_i W[k][i] * x_i  (mod p).
pub fn output(x: &[i64; IN]) -> [u64; OUT] {
    let p = modulus() as i128;
    let mut y = [0u64; OUT];
    for (k, yk) in y.iter_mut().enumerate() {
        let s: i128 = (0..IN).map(|i| weight(k, i) as i128 * x[i] as i128).sum();
        *yk = s.rem_euclid(p) as u64;
    }
    y
}

pub fn degrees(trace_len: usize) -> Vec<TransitionConstraintDegree> {
    vec![TransitionConstraintDegree::with_cycles(1, vec![trace_len]); OUT]
}

/// `periodic` starts at this block's first periodic column: [W_0, ..., W_{OUT-1}].
pub fn constraints<E: FieldElement + From<BaseElement>>(cur: &[E], next: &[E], periodic: &[E], base: usize, out: &mut [E]) {
    for k in 0..OUT {
        out[k] = next[base + ACC + k] - cur[base + ACC + k] - periodic[k] * cur[base + X];
    }
}

pub fn assertions(base: usize, y: &[u64; OUT]) -> Vec<Assertion<BaseElement>> {
    let mut v = Vec::with_capacity(ASSERTIONS);
    for k in 0..OUT {
        v.push(Assertion::single(base + ACC + k, 0, BaseElement::ZERO));
        v.push(Assertion::single(base + ACC + k, FINAL_ROW, BaseElement::from(y[k])));
    }
    v
}

pub fn periodic_columns(trace_len: usize) -> Vec<Vec<BaseElement>> {
    (0..OUT)
        .map(|k| {
            let mut col = vec![BaseElement::ZERO; trace_len];
            for i in 0..IN {
                col[i + 1] = felt_from_i64(weight(k, i));
            }
            col
        })
        .collect()
}

pub fn fill(columns: &mut [Vec<BaseElement>], base: usize, len: usize, x: &[i64; IN]) {
    let mut x_col = vec![0i64; len];
    x_col[1..=IN].copy_from_slice(x);
    for row in 0..len {
        columns[base + X][row] = felt_from_i64(x_col[row]);
    }
    for k in 0..OUT {
        let mut acc = BaseElement::ZERO;
        columns[base + ACC + k][0] = acc;
        for row in 0..len - 1 {
            if (1..=IN).contains(&row) {
                acc += felt_from_i64(weight(k, row - 1)) * felt_from_i64(x_col[row]);
            }
            columns[base + ACC + k][row + 1] = acc;
        }
    }
}
