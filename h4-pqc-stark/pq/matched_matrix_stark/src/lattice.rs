pub const Q: u64 = 8_380_417;
pub const M: usize = 128;
pub const N: usize = 256;
pub const LIMBS: usize = 4;
pub const BETA: i64 = (1 << 17) - 1;

pub const SECURITY_PROFILE: &str = "research-candidate-128x256";

#[inline]
pub fn g_coeff(row: usize, limb: usize) -> u64 {
    debug_assert!(row < M);
    debug_assert!(limb < LIMBS);

    if row < LIMBS {
        return u64::from(row == limb);
    }

    let mix =
        ((row as u64 + 17) * (limb as u64 + 29) + 97) % Q;

    (mix + 1) % Q
}

#[inline]
pub fn b_coeff(row: usize, col: usize) -> u64 {
    debug_assert!(row < M);
    debug_assert!(col < N);

    let x =
        ((row as u64 + 1) << 32) ^ (col as u64 + 1);

    let mut z =
        x.wrapping_add(0x9e37_79b9_7f4a_7c15);

    z = (z ^ (z >> 30))
        .wrapping_mul(0xbf58_476d_1ce4_e5b9);

    z = (z ^ (z >> 27))
        .wrapping_mul(0x94d0_49bb_1331_11eb);

    let value = z ^ (z >> 31);

    value % Q
}

pub fn amount_to_limbs(amount: u64) -> [u16; LIMBS] {
    [
        (amount & 0xffff) as u16,
        ((amount >> 16) & 0xffff) as u16,
        ((amount >> 32) & 0xffff) as u16,
        ((amount >> 48) & 0xffff) as u16,
    ]
}

#[inline]
fn mod_q_i128(x: i128) -> u64 {
    x.rem_euclid(i128::from(Q)) as u64
}

pub fn compute_commitment(
    amount: u64,
    r: &[i64; N],
) -> [u64; M] {
    let amount_limbs = amount_to_limbs(amount);
    let mut c = [0u64; M];

    for j in 0..M {
        let mut acc = 0i128;

        for limb_idx in 0..LIMBS {
            acc +=
                i128::from(g_coeff(j, limb_idx))
                * i128::from(amount_limbs[limb_idx]);
        }

        for i in 0..N {
            acc +=
                i128::from(b_coeff(j, i))
                * i128::from(r[i]);
        }

        c[j] = mod_q_i128(acc);
    }

    c
}

pub fn compute_quotients(
    amount: u64,
    r: &[i64; N],
    c: &[u64; M],
) -> [i64; M] {
    let amount_limbs = amount_to_limbs(amount);
    let mut k = [0i64; M];

    for j in 0..M {
        let mut acc = 0i128;

        for limb_idx in 0..LIMBS {
            acc +=
                i128::from(g_coeff(j, limb_idx))
                * i128::from(amount_limbs[limb_idx]);
        }

        for i in 0..N {
            acc +=
                i128::from(b_coeff(j, i))
                * i128::from(r[i]);
        }

        acc -= i128::from(c[j]);

        debug_assert_eq!(
            acc.rem_euclid(i128::from(Q)),
            0
        );

        k[j] = (acc / i128::from(Q)) as i64;
    }

    k
}
