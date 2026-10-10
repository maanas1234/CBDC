//! Public parameters shared by the classical and post-quantum circuits.
//!
//! SIS commitment over the STARK field itself: q = p = 7 * 2^20 + 1 = 7_340_033 (f23201).
//! Commitment c = G * bits(amount) + B * r  (mod p), with
//!   - bits(amount) in {0,1}^64   (enforced boolean in the AIR)
//!   - r in {-1,0,1}^N_RAND       (enforced exactly in the AIR)
//! Binding reduces to SIS with ||z||_inf <= 2 over an n x (64 + N_RAND) matrix.
//! See docs/h4_v2_security.md for the parameter estimate.

use winterfell::math::{fields::f23201::BaseElement, FieldElement, StarkField};

/// SIS rows (commitment length).
pub const SIS_ROWS: usize = 80;
/// Bits used to encode the amount.
pub const AMOUNT_BITS: usize = 64;
/// Ternary randomness coordinates.
pub const N_RAND: usize = 448;
/// Trace length for the PQ circuit (randomness occupies rows 1..=N_RAND).
pub const PQ_TRACE_LEN: usize = 512;
/// Row at which every accumulator must equal its commitment coordinate.
pub const FINAL_ROW: usize = N_RAND + 1;

/// Matrix workload shared by both circuits.
pub const MATRIX_A: [u64; 4] = [1, 2, 3, 4];
pub const MATRIX_B: [u64; 4] = [5, 6, 7, 8];
pub const MATRIX_C: [u64; 4] = [19, 22, 43, 50];

pub fn modulus() -> u64 {
    BaseElement::MODULUS as u64
}

fn splitmix(mut z: u64) -> u64 {
    z = z.wrapping_add(0x9e37_79b9_7f4a_7c15);
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    z ^ (z >> 31)
}

/// Public pseudo-random entry of G (amount part), uniform mod p.
pub fn g_entry(row: usize, bit: usize) -> u64 {
    splitmix(0x4731_0000_0000 ^ ((row as u64) << 20) ^ bit as u64) % modulus()
}

/// Public pseudo-random entry of B (randomness part), uniform mod p.
pub fn b_entry(row: usize, col: usize) -> u64 {
    splitmix(0x4232_0000_0000 ^ ((row as u64) << 20) ^ col as u64) % modulus()
}

pub fn felt_from_i64(value: i64) -> BaseElement {
    if value >= 0 {
        BaseElement::from(value as u64)
    } else {
        BaseElement::ZERO - BaseElement::from((-value) as u64)
    }
}

pub fn amount_bits(amount: u64) -> [u64; AMOUNT_BITS] {
    let mut bits = [0u64; AMOUNT_BITS];
    for (t, bit) in bits.iter_mut().enumerate() {
        *bit = (amount >> t) & 1;
    }
    bits
}

/// c_j = sum_t G[j][t] * bit_t + sum_i B[j][i] * r_i  (mod p), computed exactly.
/// `bits` and `r` are taken as given so tests can build commitments to malformed openings.
pub fn commit(bits: &[i64; AMOUNT_BITS], r: &[i64; N_RAND]) -> [u64; SIS_ROWS] {
    let p = modulus() as i128;
    let mut c = [0u64; SIS_ROWS];
    for (j, cj) in c.iter_mut().enumerate() {
        let mut acc: i128 = 0;
        for t in 0..AMOUNT_BITS {
            acc += g_entry(j, t) as i128 * bits[t] as i128;
        }
        for i in 0..N_RAND {
            acc += b_entry(j, i) as i128 * r[i] as i128;
        }
        *cj = acc.rem_euclid(p) as u64;
    }
    c
}
