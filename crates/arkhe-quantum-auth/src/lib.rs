#![no_std]
#![warn(missing_docs, unsafe_op_in_unsafe_fn)]
#![cfg_attr(feature = "no_std", deny(std))]

extern crate alloc;

pub mod crypto_impl;
pub mod error;
pub mod fast_path;
pub mod key_hierarchy;
pub mod policy;
pub mod quantum_memory;
pub mod slow_path;
pub mod types;

// Re-exports for ergonomic use
pub use error::{AuthError, AuthResult};
pub use fast_path::{FastPathAuth, HeraldMessage};
pub use key_hierarchy::KeyHierarchy;
pub use policy::{PolicyContext, PolicyDecision, PolicyEngine, QuantumLinkPolicy};
pub use quantum_memory::QuantumMemoryController;
pub use slow_path::{SlowPathAuth, SlowPathMessage};
pub use types::{NodeId, StorageHandle};

// Conditional re-exports for concrete crypto implementations
#[cfg(feature = "std")]
pub use crypto_impl::{Aes256GcmSivAead, MlDsa65, XWingKem};

/// Unified authentication stack for a quantum repeater link endpoint.
///
/// Combines Fast Path (symmetric AEAD), Slow Path (PQ signatures + KEM),
/// and policy enforcement into a single type.
pub struct QuantumAuthStack<A, S, K, P>
where
    A: types::FastAead,
    S: types::PqSignature,
    K: types::PqKem,
    P: PolicyEngine,
{
    /// Fast-path symmetric authenticator.
    pub fast: FastPathAuth<A>,
    /// Slow-path post-quantum authenticator.
    pub slow: SlowPathAuth<S, K>,
    /// Policy engine (rate limiting, anomaly detection).
    pub policy: P,
    /// Mutable policy context (burst counters, timestamps).
    pub context: PolicyContext,
}

impl<A, S, K, P> QuantumAuthStack<A, S, K, P>
where
    A: types::FastAead,
    S: types::PqSignature,
    K: types::PqKem,
    P: PolicyEngine,
{
    /// Create a new auth stack from pre-initialized components.
    pub fn new(fast: FastPathAuth<A>, slow: SlowPathAuth<S, K>, policy: P, context: PolicyContext) -> Self {
        Self { fast, slow, policy, context }
    }

    /// Process an incoming herald message: policy -> verify.
    pub fn receive_herald(&mut self, msg: &HeraldMessage) -> AuthResult<()> {
        match self.policy.evaluate_herald(msg, &self.context) {
            PolicyDecision::Allow => self.fast.verify_herald(msg),
            PolicyDecision::RateLimit { delay_ns } => {
                log::debug!("herald rate-limited: delay={}ns", delay_ns);
                Err(AuthError::PolicyViolation { reason: alloc::format!("rate_limited:{}ns", delay_ns) })
            }
            PolicyDecision::Reject { reason } => Err(AuthError::PolicyViolation { reason }),
        }
    }

    /// Send a herald message: policy -> seal.
    pub fn send_herald(&mut self, msg: &mut HeraldMessage) -> AuthResult<()> {
        match self.policy.evaluate_herald(msg, &self.context) {
            PolicyDecision::Allow => self.fast.seal_herald(msg),
            PolicyDecision::RateLimit { delay_ns } => {
                log::debug!("herald send rate-limited: delay={}ns", delay_ns);
                Err(AuthError::PolicyViolation { reason: alloc::format!("rate_limited:{}ns", delay_ns) })
            }
            PolicyDecision::Reject { reason } => Err(AuthError::PolicyViolation { reason }),
        }
    }

    /// Execute key rotation via Slow Path.
    pub fn rotate_keys(&mut self, new_counter: u64) -> AuthResult<SlowPathMessage> {
        let ts = platform::monotonic_ns();
        let cmd = self.slow.sign_rotation(new_counter, ts, &self.context.node_did);
        match self.policy.evaluate_slow(&cmd, &self.context) {
            PolicyDecision::Allow => {
                self.fast.key_hierarchy.rotate_session()?;
                self.context.last_rotation_ns = ts;
                Ok(cmd)
            }
            PolicyDecision::Reject { reason } => Err(AuthError::PolicyViolation { reason }),
            _ => Err(AuthError::PolicyViolation { reason: "rotation_rate_limited".into() }),
        }
    }
}

// =============================================================================
// Platform Abstraction
// =============================================================================

/// Platform-specific utilities (time, entropy hooks).
pub mod platform {
    use core::sync::atomic::{AtomicU64, Ordering};

    static TIME_NS: AtomicU64 = AtomicU64::new(0);

    /// Set the monotonic time source (nanoseconds).
    ///
    /// # Safety
    /// Must be called during system initialization, before any auth operations.
    /// In multi-core contexts, ensure happens-before with appropriate barriers.
    pub fn set_monotonic_ns(ns: u64) {
        TIME_NS.store(ns, Ordering::SeqCst);
    }

    /// Increment monotonic time by `delta_ns`.
    pub fn tick_monotonic(delta_ns: u64) {
        TIME_NS.fetch_add(delta_ns, Ordering::Relaxed);
    }

    /// Read monotonic time in nanoseconds.
    ///
    /// In `std` builds, delegates to `std::time::Instant`.
    /// In `no_std` builds, returns the value set by `set_monotonic_ns`.
    pub fn monotonic_ns() -> u64 {
        #[cfg(feature = "std")]
        {
            extern crate std;
            use std::time::{SystemTime, UNIX_EPOCH};
            // Use system time for absolute timestamps; Instant for relative
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_nanos() as u64;
            now
        }
        #[cfg(not(feature = "std"))]
        {
            TIME_NS.load(Ordering::Relaxed)
        }
    }
}
