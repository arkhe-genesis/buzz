//! Authentication error types.

use alloc::string::String;
use core::fmt;

/// Errors across the quantum auth stack.
#[derive(Debug, Clone, PartialEq)]
pub enum AuthError {
    /// Fast-path MAC/tag verification failed (AES-GCM-SIV tag mismatch).
    FastPathVerification,
    /// Slow-path signature verification failed (ML-DSA-65 invalid).
    SlowPathVerification,
    /// Key derivation failed (e.g., HKDF expand too long, entropy exhausted).
    KeyDerivation,
    /// Policy engine rejected the operation.
    PolicyViolation { reason: String },
    /// Nonce/key counter overflow (triggers emergency rotation).
    CounterExhausted,
    /// Hardware or RNG failure.
    HardwareFailure,
    /// Invalid key length or format.
    InvalidKey,
    /// Decapsulation failure (KEM ciphertext malformed or wrong secret key).
    KemDecapsulation,
    /// Message deserialization failure (wrong wire format).
    Deserialization,
    /// Clock skew or replay detected.
    ReplayDetected,
}

impl fmt::Display for AuthError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AuthError::FastPathVerification => write!(f, "fast-path verification failed"),
            AuthError::SlowPathVerification => write!(f, "slow-path verification failed"),
            AuthError::KeyDerivation => write!(f, "key derivation failed"),
            AuthError::PolicyViolation { reason } => write!(f, "policy violation: {}", reason),
            AuthError::CounterExhausted => write!(f, "counter exhausted — emergency rotation required"),
            AuthError::HardwareFailure => write!(f, "hardware/RNG failure"),
            AuthError::InvalidKey => write!(f, "invalid key format"),
            AuthError::KemDecapsulation => write!(f, "KEM decapsulation failed"),
            AuthError::Deserialization => write!(f, "message deserialization failed"),
            AuthError::ReplayDetected => write!(f, "replay or clock skew detected"),
        }
    }
}

// Just impl core::error::Error since it's stabilized in 1.81.0 (workspace is 1.88.0)
impl core::error::Error for AuthError {}

/// Result type alias for auth operations.
pub type AuthResult<T> = Result<T, AuthError>;
