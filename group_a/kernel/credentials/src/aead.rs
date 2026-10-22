//! ChaCha20-Poly1305 (RFC 8439). No C compiler and no third-party crate.

#[derive(Clone, Copy)]
struct Wide([u64; 6]);

impl Wide {
    fn zero() -> Self {
        Self([0; 6])
    }
}

pub fn seal(key: &[u8; 32], nonce: &[u8; 12], aad: &[u8], plaintext: &[u8]) -> Vec<u8> {
    let mut ciphertext = apply_stream(key, 1, nonce, plaintext);
    let tag = tag(key, nonce, aad, &ciphertext);
    ciphertext.extend_from_slice(&tag);
    ciphertext
}

pub fn open(key: &[u8; 32], nonce: &[u8; 12], aad: &[u8], sealed: &[u8]) -> Option<Vec<u8>> {
    if sealed.len() < 16 {
        return None;
    }
    let (ciphertext, found) = sealed.split_at(sealed.len() - 16);
    let expected = tag(key, nonce, aad, ciphertext);
    if !tags_equal(found, &expected) {
        return None;
    }
    Some(apply_stream(key, 1, nonce, ciphertext))
}

fn tags_equal(left: &[u8], right: &[u8]) -> bool {
    if left.len() != right.len() {
        return false;
    }
    let mut diff = 0u8;
    for (one, other) in left.iter().zip(right) {
        diff |= one ^ other;
    }
    diff == 0
}

fn tag(key: &[u8; 32], nonce: &[u8; 12], aad: &[u8], ciphertext: &[u8]) -> [u8; 16] {
    let mut otk = [0u8; 32];
    otk.copy_from_slice(&chacha20_block(key, 0, nonce)[..32]);
    let mut mac = Vec::with_capacity(aad.len() + ciphertext.len() + 48);
    mac.extend_from_slice(aad);
    mac.extend(std::iter::repeat_n(0, pad_len(aad.len())));
    mac.extend_from_slice(ciphertext);
    mac.extend(std::iter::repeat_n(0, pad_len(ciphertext.len())));
    mac.extend_from_slice(&(aad.len() as u64).to_le_bytes());
    mac.extend_from_slice(&(ciphertext.len() as u64).to_le_bytes());
    let result = poly1305(&otk, &mac);
    wipe(&mut otk);
    wipe(&mut mac);
    result
}

fn pad_len(len: usize) -> usize {
    (16 - (len % 16)) % 16
}

fn apply_stream(key: &[u8; 32], counter: u32, nonce: &[u8; 12], data: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(data.len());
    let mut offset = 0;
    let mut block_index = 0u32;
    while offset < data.len() {
        let stream = chacha20_block(key, counter.wrapping_add(block_index), nonce);
        let end = (offset + 64).min(data.len());
        for (index, byte) in data[offset..end].iter().enumerate() {
            out.push(byte ^ stream[index]);
        }
        offset = end;
        block_index = block_index.wrapping_add(1);
    }
    out
}

fn chacha20_block(key: &[u8; 32], counter: u32, nonce: &[u8; 12]) -> [u8; 64] {
    let mut state = [0u32; 16];
    state[0] = 0x6170_7865;
    state[1] = 0x3320_646e;
    state[2] = 0x7962_2d32;
    state[3] = 0x6b20_6574;
    for index in 0..8 {
        let start = index * 4;
        state[4 + index] = u32::from_le_bytes(key[start..start + 4].try_into().unwrap());
    }
    state[12] = counter;
    for index in 0..3 {
        let start = index * 4;
        state[13 + index] = u32::from_le_bytes(nonce[start..start + 4].try_into().unwrap());
    }
    let original = state;
    for _ in 0..10 {
        quarter(&mut state, 0, 4, 8, 12);
        quarter(&mut state, 1, 5, 9, 13);
        quarter(&mut state, 2, 6, 10, 14);
        quarter(&mut state, 3, 7, 11, 15);
        quarter(&mut state, 0, 5, 10, 15);
        quarter(&mut state, 1, 6, 11, 12);
        quarter(&mut state, 2, 7, 8, 13);
        quarter(&mut state, 3, 4, 9, 14);
    }
    let mut out = [0u8; 64];
    for index in 0..16 {
        let word = state[index].wrapping_add(original[index]);
        let start = index * 4;
        out[start..start + 4].copy_from_slice(&word.to_le_bytes());
    }
    out
}

fn quarter(state: &mut [u32; 16], a: usize, b: usize, c: usize, d: usize) {
    state[a] = state[a].wrapping_add(state[b]);
    state[d] ^= state[a];
    state[d] = state[d].rotate_left(16);
    state[c] = state[c].wrapping_add(state[d]);
    state[b] ^= state[c];
    state[b] = state[b].rotate_left(12);
    state[a] = state[a].wrapping_add(state[b]);
    state[d] ^= state[a];
    state[d] = state[d].rotate_left(8);
    state[c] = state[c].wrapping_add(state[d]);
    state[b] ^= state[c];
    state[b] = state[b].rotate_left(7);
}

fn poly1305(key: &[u8; 32], message: &[u8]) -> [u8; 16] {
    let r = clamp(&key[..16]);
    let s = u128::from_le_bytes(key[16..].try_into().unwrap());
    let mut acc = Wide::zero();
    let mut offset = 0;
    while offset < message.len() {
        let end = (offset + 16).min(message.len());
        let mut block = [0u8; 17];
        let length = end - offset;
        block[..length].copy_from_slice(&message[offset..end]);
        block[length] = 1;
        let mut limb = Wide::zero();
        limb.0[0] = u64::from_le_bytes(block[0..8].try_into().unwrap());
        limb.0[1] = u64::from_le_bytes(block[8..16].try_into().unwrap());
        limb.0[2] = u64::from(block[16]);
        acc = add(acc, limb);
        acc = mul_r(acc, r);
        acc = reduce(acc);
        offset = end;
    }
    let (low, _) = residue(acc);
    let mut tag = [0u8; 16];
    tag.copy_from_slice(&low.wrapping_add(s).to_le_bytes());
    tag
}

fn clamp(bytes: &[u8]) -> u128 {
    let mut r = [0u8; 16];
    r.copy_from_slice(bytes);
    r[3] &= 15;
    r[7] &= 15;
    r[11] &= 15;
    r[15] &= 15;
    r[4] &= 252;
    r[8] &= 252;
    r[12] &= 252;
    u128::from_le_bytes(r)
}

fn add(left: Wide, right: Wide) -> Wide {
    let mut out = [0u64; 6];
    let mut carry = 0u128;
    for (index, slot) in out.iter_mut().enumerate() {
        let sum = left.0[index] as u128 + right.0[index] as u128 + carry;
        *slot = sum as u64;
        carry = sum >> 64;
    }
    Wide(out)
}

fn mul_r(value: Wide, r: u128) -> Wide {
    let r0 = (r as u64) as u128;
    let r1 = ((r >> 64) as u64) as u128;
    let mut acc = [0u128; 8];
    for index in 0..6 {
        mac(&mut acc, index, value.0[index] as u128 * r0);
        mac(&mut acc, index + 1, value.0[index] as u128 * r1);
    }
    let mut out = [0u64; 6];
    for index in 0..6 {
        out[index] = acc[index] as u64;
    }
    Wide(out)
}

fn mac(acc: &mut [u128; 8], index: usize, value: u128) {
    let mut carry = value;
    let mut slot = index;
    while carry != 0 && slot < acc.len() {
        let sum = acc[slot] + carry;
        acc[slot] = sum & (u64::MAX as u128);
        carry = sum >> 64;
        slot += 1;
    }
}

/// `n ≡ (n mod 2^130) + 5 * (n >> 130)  (mod 2^130 − 5)`.
fn reduce(mut value: Wide) -> Wide {
    for _ in 0..8 {
        let (low, high) = split_130(value);
        if high.0.iter().all(|limb| *limb == 0) {
            return low;
        }
        value = add(low, mul_r(high, 5));
    }
    split_130(value).0
}

fn split_130(value: Wide) -> (Wide, Wide) {
    let mut low = Wide::zero();
    low.0[0] = value.0[0];
    low.0[1] = value.0[1];
    low.0[2] = value.0[2] & 3;
    let mut high = Wide::zero();
    let mut carry = value.0[2] >> 2;
    for index in 0..4 {
        let next = if index + 3 < 6 { value.0[index + 3] } else { 0 };
        high.0[index] = (next << 62) | carry;
        carry = next >> 2;
    }
    (low, high)
}

/// Low 128 bits and the two bits above them. The residue is less than 2^130 − 5.
fn residue(value: Wide) -> (u128, u8) {
    let mut low = (value.0[0] as u128) | ((value.0[1] as u128) << 64);
    let mut top = (value.0[2] & 3) as u8;
    let prime_top = 3u8;
    let prime_low = u128::MAX - 4;
    let over = top > prime_top || (top == prime_top && low >= prime_low);
    if over {
        let (sum, wrapped) = low.overflowing_add(5);
        low = sum;
        if wrapped {
            top = top.wrapping_add(1);
        }
        top &= 3;
    }
    (low, top)
}

fn wipe(bytes: &mut [u8]) {
    for byte in bytes.iter_mut() {
        unsafe { std::ptr::write_volatile(byte, 0) }
    }
    std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
}

#[cfg(test)]
mod tests {
    use super::{chacha20_block, open, seal};

    #[test]
    fn the_rfc_block_matches() {
        let key: [u8; 32] = core::array::from_fn(|index| index as u8);
        let nonce = [0x00, 0x00, 0x00, 0x09, 0x00, 0x00, 0x00, 0x4a, 0x00, 0x00, 0x00, 0x00];
        let block = chacha20_block(&key, 1, &nonce);
        assert_eq!(
            &block[..16],
            &[0x10, 0xf1, 0xe7, 0xe4, 0xd1, 0x3b, 0x59, 0x15, 0x50, 0x0f, 0xdd, 0x1f, 0xa3, 0x20, 0x71, 0xc4]
        );
    }

    #[test]
    fn the_rfc_aead_tag_matches_and_a_changed_byte_is_refused() {
        let key: [u8; 32] = core::array::from_fn(|index| 0x80 + index as u8);
        let nonce = [0x07, 0x00, 0x00, 0x00, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47];
        let aad = [0x50, 0x51, 0x52, 0x53, 0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7];
        let plaintext = b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, sunscreen would be it.";
        let sealed = seal(&key, &nonce, &aad, plaintext);
        assert_eq!(&sealed[..4], &[0xd3, 0x1a, 0x8d, 0x34]);
        assert_eq!(
            &sealed[sealed.len() - 16..],
            &[0x1a, 0xe1, 0x0b, 0x59, 0x4f, 0x09, 0xe2, 0x6a, 0x7e, 0x90, 0x2e, 0xcb, 0xd0, 0x60, 0x06, 0x91]
        );
        assert_eq!(open(&key, &nonce, &aad, &sealed).as_deref(), Some(plaintext.as_slice()));
        let mut tampered = sealed.clone();
        tampered[0] ^= 1;
        assert!(open(&key, &nonce, &aad, &tampered).is_none());
    }
}
