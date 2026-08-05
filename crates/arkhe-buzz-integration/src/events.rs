//! Arkhe-specific Nostr event kinds for Buzz integration.
//!
//! Buzz uses a closed kind registry (~130 kinds). These kinds are allocated
//! in the Buzz custom range (39000-39009) to avoid collision with existing
//! Buzz event kinds.
//!
//! Reference: Buzz ARCHITECTURE.md defines kind ranges as:
//! - 0-9999: Standard NIPs
//! - 10000-19999: Replaceable events
//! - 20000-29999: Ephemeral events
//! - 30000-39999: Parameterized replaceable (Buzz custom)
//! - 40000+: Reserved

use chrono::{DateTime, Utc};
use nostr_sdk::prelude::*;
use serde::{Deserialize, Serialize};

/// Arkhe event kinds — allocated in Buzz custom range.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ArkheKind {
    /// Agent S-Measure heartbeat (parameterized replaceable).
    /// Published periodically by each agent with current S-Measure value.
    /// kind: 39000
    SMeasureHeartbeat,

    /// Safety barrier alert — triggered when ΔS < 0.
    /// kind: 39001
    SafetyAlert,

    /// Agent state snapshot (IPFS CID reference).
    /// kind: 39002
    StateSnapshot,

    /// Task delegation from orchestrator to agent.
    /// kind: 39003
    TaskDelegation,

    /// Agent capability advertisement (what this agent can do).
    /// kind: 39004
    CapabilityAdvert,

    /// Escape risk escalation (None → Escaped).
    /// kind: 39005
    EscapeRiskEvent,

    /// Consensus proposal for multi-relay decisions.
    /// kind: 39006
    ConsensusProposal,

    /// Consensus vote (yes/no) on a proposal.
    /// kind: 39007
    ConsensusVote,
}

impl ArkheKind {
    pub fn as_u16(&self) -> u16 {
        match self {
            Self::SMeasureHeartbeat => 39000,
            Self::SafetyAlert => 39001,
            Self::StateSnapshot => 39002,
            Self::TaskDelegation => 39003,
            Self::CapabilityAdvert => 39004,
            Self::EscapeRiskEvent => 39005,
            Self::ConsensusProposal => 39006,
            Self::ConsensusVote => 39007,
        }
    }

    pub fn from_u16(kind: u16) -> Option<Self> {
        match kind {
            39000 => Some(Self::SMeasureHeartbeat),
            39001 => Some(Self::SafetyAlert),
            39002 => Some(Self::StateSnapshot),
            39003 => Some(Self::TaskDelegation),
            39004 => Some(Self::CapabilityAdvert),
            39005 => Some(Self::EscapeRiskEvent),
            39006 => Some(Self::ConsensusProposal),
            39007 => Some(Self::ConsensusVote),
            _ => None,
        }
    }

    /// Whether this kind is replaceable (only latest per agent is kept).
    pub fn is_replaceable(&self) -> bool {
        matches!(
            self,
            Self::SMeasureHeartbeat | Self::CapabilityAdvert | Self::StateSnapshot
        )
    }

    /// Whether this kind is ephemeral (not stored by relay).
    pub fn is_ephemeral(&self) -> bool {
        false // All Arkhe kinds are persisted for audit
    }
}

/// S-Measure heartbeat event content.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SMeasureContent {
    pub agent_pubkey: String,
    pub s_measure: f32,
    pub f_threshold: f32,
    pub risk_level: u8, // 0=None, 1=Low, 2=Medium, 3=High, 4=Escaped
    pub timestamp: DateTime<Utc>,
    pub version: String,
}

/// Safety alert event content (ΔS < 0 triggered).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SafetyAlertContent {
    pub agent_pubkey: String,
    pub s_before: f32,
    pub s_after: f32,
    pub delta_s: f32,
    pub action_description: String,
    pub timestamp: DateTime<Utc>,
    pub rolled_back: bool,
}

/// State snapshot reference (IPFS or S3 CID).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateSnapshotContent {
    pub agent_pubkey: String,
    pub cid: String, // IPFS CID or S3 object key
    pub parent_cid: Option<String>,
    pub s_measure: f32,
    pub timestamp: DateTime<Utc>,
    pub d_subsystem_hash: String, // blake3 of D-subsystem
    pub i_subsystem_hash: String, // blake3 of I-subsystem
}

/// Task delegation from orchestrator to agent.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskDelegationContent {
    pub from_orchestrator: String, // orchestrator pubkey
    pub to_agent: String,          // target agent pubkey
    pub task_id: String,
    pub task_description: String,
    pub priority: u8, // 1-5
    pub deadline: Option<DateTime<Utc>>,
}

/// Escape risk escalation event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EscapeRiskContent {
    pub agent_pubkey: String,
    pub risk_level: String, // "NONE", "LOW", "MEDIUM", "HIGH", "ESCAPED"
    pub s_measure: f32,
    pub threshold: f32,
    pub trend: f32,
    pub recommended_action: String,
    pub timestamp: DateTime<Utc>,
}

/// Build a Nostr Event from Arkhe content.
pub async fn build_arkhe_event<C: Serialize>(
    kind: ArkheKind,
    content: &C,
    keys: &Keys,
    tags: Vec<Tag>,
) -> crate::Result<Event> {
    let content_json = serde_json::to_string(content)
        .map_err(|e| crate::error::ArkheBuzzError::EventValidation(e.to_string()))?;

    let mut event_builder = EventBuilder::new(Kind::Custom(kind.as_u16()), content_json);

    for tag in tags {
        event_builder = event_builder.tag(tag);
    }

    let event = event_builder
        .sign(keys)
        .await
        .map_err(|e| crate::error::ArkheBuzzError::PublishFailed(e.to_string()))?;

    Ok(event)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kind_roundtrip() {
        assert_eq!(ArkheKind::SMeasureHeartbeat.as_u16(), 39000);
        assert_eq!(ArkheKind::SafetyAlert.as_u16(), 39001);
        assert_eq!(
            ArkheKind::from_u16(39000),
            Some(ArkheKind::SMeasureHeartbeat)
        );
        assert_eq!(ArkheKind::from_u16(65535), None);
    }

    #[test]
    fn test_replaceable_kinds() {
        assert!(ArkheKind::SMeasureHeartbeat.is_replaceable());
        assert!(!ArkheKind::SafetyAlert.is_replaceable());
    }

    #[test]
    fn test_s_measure_content_serialization() {
        let content = SMeasureContent {
            agent_pubkey: "npub1...".to_string(),
            s_measure: 0.73,
            f_threshold: 0.65,
            risk_level: 2,
            timestamp: Utc::now(),
            version: "0.1.0".to_string(),
        };
        let json = serde_json::to_string(&content).unwrap();
        assert!(json.contains("0.73"));
        assert!(json.contains("npub1"));
    }
}
