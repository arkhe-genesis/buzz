//! Policy Engine integration for quantum link authentication.

use alloc::string::String;
use alloc::format;

use crate::error::AuthResult;
use crate::fast_path::HeraldMessage;
use crate::slow_path::SlowPathMessage;

#[derive(Debug, Clone, PartialEq)]
pub enum PolicyDecision {
    Allow,
    RateLimit { delay_ns: u64 },
    Reject { reason: String },
}

#[derive(Debug, Clone)]
pub struct PolicyContext {
    pub link_id: [u8; 16],
    pub node_did: [u8; 33],
    pub burst_msg_count: u64,
    pub last_rotation_ns: u64,
    pub anomaly_score: f64,
    pub max_mode_idx: u8,
    pub clock_skew_tolerance_ns: u64,
    pub min_rotation_interval_ns: u64,
}

impl Default for PolicyContext {
    fn default() -> Self {
        Self {
            link_id: [0u8; 16],
            node_did: [0u8; 33],
            burst_msg_count: 0,
            last_rotation_ns: 0,
            anomaly_score: 0.0,
            max_mode_idx: 10,
            clock_skew_tolerance_ns: 1_000_000, // 1 ms
            min_rotation_interval_ns: 60_000_000_000, // 60 s
        }
    }
}

pub trait PolicyEngine {
    fn evaluate_herald(&self, msg: &HeraldMessage, ctx: &PolicyContext) -> PolicyDecision;
    fn evaluate_slow(&self, msg: &SlowPathMessage, ctx: &PolicyContext) -> PolicyDecision;
    fn update_context(&self, ctx: &mut PolicyContext, _msg: &HeraldMessage) {
        ctx.burst_msg_count += 1;
    }
}

pub struct QuantumLinkPolicy {
    pub max_msgs_per_burst: u64,
    pub max_burst_rate: f64,
    pub anomaly_threshold: f64,
}

impl Default for QuantumLinkPolicy {
    fn default() -> Self {
        Self {
            max_msgs_per_burst: 100_000,
            max_burst_rate: 1e6,
            anomaly_threshold: 0.95,
        }
    }
}

impl PolicyEngine for QuantumLinkPolicy {
    fn evaluate_herald(&self, msg: &HeraldMessage, ctx: &PolicyContext) -> PolicyDecision {
        if msg.mode_idx > ctx.max_mode_idx {
            return PolicyDecision::Reject {
                reason: format!("invalid_mode_idx:{}", msg.mode_idx),
            };
        }

        let now = crate::platform::monotonic_ns();
        if msg.timestamp_ns > now.saturating_add(ctx.clock_skew_tolerance_ns) {
            return PolicyDecision::Reject {
                reason: "future_timestamp".into(),
            };
        }

        if ctx.burst_msg_count > self.max_msgs_per_burst {
            return PolicyDecision::RateLimit { delay_ns: 1000 };
        }

        if ctx.anomaly_score > self.anomaly_threshold {
            return PolicyDecision::Reject {
                reason: format!("anomaly_detected:{:.4}", ctx.anomaly_score),
            };
        }

        PolicyDecision::Allow
    }

    fn evaluate_slow(&self, _msg: &SlowPathMessage, ctx: &PolicyContext) -> PolicyDecision {
        let now = crate::platform::monotonic_ns();
        let elapsed = now.saturating_sub(ctx.last_rotation_ns);
        if elapsed < ctx.min_rotation_interval_ns {
            let remaining = ctx.min_rotation_interval_ns - elapsed;
            return PolicyDecision::RateLimit { delay_ns: remaining };
        }
        PolicyDecision::Allow
    }
}
