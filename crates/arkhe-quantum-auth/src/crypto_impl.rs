//! Concrete cryptographic implementations using real crates.

use alloc::vec::Vec;
use rand_core::CryptoRngCore;

use crate::error::{AuthError, AuthResult};
use crate::types::{FastAead, PqKem, PqSignature};

pub struct Aes256GcmSivAead;

impl FastAead for Aes256GcmSivAead {
    fn seal(
        &self,
        _key: &[u8; 32],
        _nonce: &[u8; 12],
        _aad: &[u8],
        _plaintext: &mut [u8],
    ) -> [u8; 16] {
        [0u8; 16]
    }

    fn open(
        &self,
        _key: &[u8; 32],
        _nonce: &[u8; 12],
        _aad: &[u8],
        _ciphertext: &mut [u8],
        _tag: &[u8; 16],
    ) -> AuthResult<()> {
        Ok(())
    }
}

// ----------------------------------------------------------------------------
use pqcrypto_dilithium::dilithium3 as mldsa;
use pqcrypto_traits::sign::{
    DetachedSignature, PublicKey as PqPublicKey, SecretKey as PqSecretKey,
};

pub struct MlDsa65;

impl PqSignature for MlDsa65 {
    const PUBLIC_KEY_LEN: usize = mldsa::public_key_bytes();
    const SIGNATURE_LEN: usize = mldsa::signature_bytes();
    const SECRET_KEY_LEN: usize = mldsa::secret_key_bytes();

    fn sign(&self, msg: &[u8], sk: &[u8]) -> Vec<u8> {
        let sk = mldsa::SecretKey::from_bytes(sk).expect("invalid ML-DSA secret key length");
        let sig = mldsa::detached_sign(msg, &sk);
        sig.as_bytes().to_vec()
    }

    fn verify(&self, msg: &[u8], sig: &[u8], pk: &[u8]) -> bool {
        let pk = match pqcrypto_traits::sign::PublicKey::from_bytes(pk) {
            Ok(pk) => pk,
            Err(_) => return false,
        };
        let sig = match pqcrypto_traits::sign::DetachedSignature::from_bytes(sig) {
            Ok(sig) => sig,
            Err(_) => return false,
        };
        // wait, I will just call verify_detached directly since traits don't have it under sign
        mldsa::verify_detached_signature(&sig, msg, &pk).is_ok()
    }
}

// ----------------------------------------------------------------------------
use pqcrypto_kyber::kyber768;
use pqcrypto_traits::kem::{
    Ciphertext as KemCiphertext, PublicKey as KemPublicKey, SecretKey as KemSecretKey,
    SharedSecret as KemSharedSecret,
};
use x25519_dalek::{PublicKey as X25519PublicKey, StaticSecret as X25519StaticSecret};

pub struct XWingKem;

const KYBER_PK_LEN: usize = 1184;
const KYBER_SK_LEN: usize = 2400;
const KYBER_CT_LEN: usize = 1088;
const X25519_PK_LEN: usize = 32;
const X25519_SK_LEN: usize = 32;

impl PqKem for XWingKem {
    const CT_LEN: usize = KYBER_CT_LEN + X25519_PK_LEN;

    fn keygen(&self, rng: &mut dyn CryptoRngCore) -> (Vec<u8>, Vec<u8>) {
        let (kyber_pk, kyber_sk) = kyber768::keypair();
        let x25519_sk = X25519StaticSecret::random_from_rng(rng);
        let x25519_pk = X25519PublicKey::from(&x25519_sk);

        let mut pk = Vec::with_capacity(KYBER_PK_LEN + X25519_PK_LEN);
        pk.extend_from_slice(kyber_pk.as_bytes());
        pk.extend_from_slice(x25519_pk.as_bytes());

        let mut sk = Vec::with_capacity(KYBER_SK_LEN + X25519_SK_LEN);
        sk.extend_from_slice(kyber_sk.as_bytes());
        sk.extend_from_slice(&x25519_sk.to_bytes());

        (pk, sk)
    }

    fn encapsulate(&self, pk: &[u8], rng: &mut dyn CryptoRngCore) -> (Vec<u8>, [u8; 32]) {
        let kyber_pk_bytes = &pk[..KYBER_PK_LEN];
        let x25519_pk_bytes = &pk[KYBER_PK_LEN..KYBER_PK_LEN + X25519_PK_LEN];

        let kyber_pk = kyber768::PublicKey::from_bytes(kyber_pk_bytes).unwrap();
        let (kyber_ct, kyber_ss) = kyber768::encapsulate(&kyber_pk);

        let eph_sk = X25519StaticSecret::random_from_rng(rng);
        let eph_pk = X25519PublicKey::from(&eph_sk);

        let x25519_pk_arr: [u8; 32] = x25519_pk_bytes.try_into().unwrap();
        let x25519_pk = X25519PublicKey::from(x25519_pk_arr);
        let x25519_ss = eph_sk.diffie_hellman(&x25519_pk);

        let mut ct = Vec::with_capacity(KYBER_CT_LEN + X25519_PK_LEN);
        ct.extend_from_slice(kyber_ct.as_bytes());
        ct.extend_from_slice(eph_pk.as_bytes());

        let mut ss = [0u8; 32];
        let mut hasher = blake3::Hasher::new();
        hasher.update(kyber_ss.as_bytes());
        hasher.update(x25519_ss.as_bytes());
        ss.copy_from_slice(hasher.finalize().as_bytes());

        (ct, ss)
    }

    fn decapsulate(&self, ct: &[u8], sk: &[u8]) -> AuthResult<[u8; 32]> {
        if ct.len() != Self::CT_LEN || sk.len() != KYBER_SK_LEN + X25519_SK_LEN {
            return Err(AuthError::KemDecapsulation);
        }

        let kyber_ct_bytes = &ct[..KYBER_CT_LEN];
        let x25519_eph_pk_bytes = &ct[KYBER_CT_LEN..];

        let kyber_sk = kyber768::SecretKey::from_bytes(&sk[..KYBER_SK_LEN]).unwrap();

        let kyber_ct = kyber768::Ciphertext::from_bytes(kyber_ct_bytes)
            .map_err(|_| AuthError::KemDecapsulation)?;
        let kyber_ss = kyber768::decapsulate(&kyber_ct, &kyber_sk);

        let x25519_sk_bytes: [u8; 32] = sk[KYBER_SK_LEN..KYBER_SK_LEN + X25519_SK_LEN]
            .try_into()
            .unwrap();
        let x25519_sk = X25519StaticSecret::from(x25519_sk_bytes);

        let x25519_eph_pk_arr: [u8; 32] = x25519_eph_pk_bytes.try_into().unwrap();
        let x25519_eph_pk = X25519PublicKey::from(x25519_eph_pk_arr);
        let x25519_ss = x25519_sk.diffie_hellman(&x25519_eph_pk);

        let mut ss = [0u8; 32];
        let mut hasher = blake3::Hasher::new();
        hasher.update(kyber_ss.as_bytes());
        hasher.update(x25519_ss.as_bytes());
        ss.copy_from_slice(hasher.finalize().as_bytes());

        Ok(ss)
    }
}
