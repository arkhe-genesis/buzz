use serde::{Deserialize, Serialize};
use crate::mhd::EvoField;
use crate::shadow::Shadow;
use crate::retro::EchoSignal;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeBlock {
    pub height: u64,
    pub timestamp_phase: f64,
    pub helicity: f64,
    pub delta_helicity: f64,
    pub shadow: Shadow,
    pub echo_signature: EchoSignal,
    pub transactions: Vec<String>,
}

impl TimeBlock {
    pub fn new(height: u64, field: &EvoField, shadow: Shadow, echo: EchoSignal) -> Self {
        let h = field.helicity();
        Self {
            height,
            timestamp_phase: 0.0,
            helicity: h,
            delta_helicity: 0.0,
            shadow,
            echo_signature: echo,
            transactions: Vec::new(),
        }
    }
}

pub struct ChernSimonsOracle { pub tolerance: f64 }
impl ChernSimonsOracle {
    pub fn new(tolerance: f64) -> Self { Self { tolerance } }
    pub fn verify(&self, block: &TimeBlock, field: &EvoField) -> bool {
        let predicted_h = block.echo_signature.predicted_helicity;
        let actual_h = field.helicity();
        (predicted_h - actual_h).abs() < self.tolerance
    }
}
