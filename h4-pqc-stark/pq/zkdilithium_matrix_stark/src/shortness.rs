/// Debug-tier shortness parameters.
///
/// beta = 2^4 - 1 = 15.
/// Every witness component must therefore be representable
/// using exactly four Boolean bits.

pub const BITS: usize = 4;
pub const BETA: u32 = (1 << BITS) - 1;

/// Return the little-endian bit decomposition of a short value.
///
/// This is used for valid witnesses.
pub fn decompose(x: u32) -> [u32; BITS] {
    assert!(x <= BETA);

    [
        x & 1,
        (x >> 1) & 1,
        (x >> 2) & 1,
        (x >> 3) & 1,
    ]
}

/// Return the low four bits without checking the range.
///
/// This is intentionally used for negative tests.
/// For example:
///
///     17 -> [1, 0, 0, 0]
///
/// which reconstructs to 1 rather than 17.
/// The STARK's reconstruction constraint should therefore
/// reject the witness.
pub fn decompose_unchecked(x: u32) -> [u32; BITS] {
    [
        x & 1,
        (x >> 1) & 1,
        (x >> 2) & 1,
        (x >> 3) & 1,
    ]
}

/// Check that four bits reconstruct x.
pub fn reconstruct(bits: [u32; BITS]) -> u32 {
    bits[0]
        + 2 * bits[1]
        + 4 * bits[2]
        + 8 * bits[3]
}
