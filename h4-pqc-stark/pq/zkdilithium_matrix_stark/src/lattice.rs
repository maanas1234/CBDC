// Small SIS-style lattice relation:
//
//     C = A*s + B*r (mod q)
//
// A and B are public.
// s and r are the private witness.
// C is the public commitment.

pub const Q: i64 = 65537;

pub const A: [[i64; 2]; 2] = [
    [3, 5],
    [7, 11],
];

pub const B: [[i64; 2]; 2] = [
    [13, 17],
    [19, 23],
];

// Private witness.
// We use only non-negative values in this first prototype
// so that signed-integer/range constraints do not obscure
// the lattice-backed STARK construction.
pub const S: [i64; 2] = [2, 1];
pub const R: [i64; 2] = [1, 3];

pub fn compute_commitment() -> [i64; 2] {
    let mut c = [0i64; 2];

    for i in 0..2 {
        let mut value = 0i64;

        for j in 0..2 {
            value += A[i][j] * S[j];
            value += B[i][j] * R[j];
        }

        c[i] = value.rem_euclid(Q);
    }

    c
}

pub fn verify_commitment(c: [i64; 2]) -> bool {
    compute_commitment() == c
}
