use thiserror::Error;

#[derive(Error, Debug)]
pub enum ArkheBuzzError {
    #[error("S-Measure computation error: {0}")]
    SMeasureComputation(String),
    #[error("Snapshot failed: {0}")]
    SnapshotFailed(String),
    #[error("Safety barrier triggered: ΔS = {delta_s}")]
    SafetyBarrierTriggered { delta_s: f32 },
    #[error("Safety violation: {0}")]
    SafetyViolation(String),
    #[error("Event validation error: {0}")]
    EventValidation(String),
    #[error("Failed to publish event: {0}")]
    PublishFailed(String),
    #[error("IPFS not configured")]
    IpfsNotConfigured,
    #[error("IPFS error: {0}")]
    IpfsError(String),
}

pub type Result<T> = std::result::Result<T, ArkheBuzzError>;
