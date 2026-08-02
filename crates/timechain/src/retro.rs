use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EchoSignal {
    pub timestamp: f64, pub strength: f64, pub predicted_helicity: f64,
    pub origin_height: u64, pub pattern: Vec<f64>,
}
impl EchoSignal {
    pub fn new(strength: f64, predicted_helicity: f64, origin: u64) -> Self {
        Self { timestamp: 0.0, strength, predicted_helicity, origin_height: origin, pattern: vec![] }
    }
}

pub struct RetroCausalChannel {
    pub buffer: Vec<EchoSignal>, pub max_delay: f64, pub v_eco: f64,
}
impl RetroCausalChannel {
    pub fn new(max_delay: f64, v_eco: f64) -> Self { Self { buffer: vec![], max_delay, v_eco } }
    pub fn emit(&mut self, echo: EchoSignal) { self.buffer.push(echo); }
    pub fn receive(&mut self, current_time: f64) -> Vec<EchoSignal> {
        let mut arrived = Vec::new();
        self.buffer.retain(|echo| {
            if current_time - echo.timestamp >= 0.0 && current_time - echo.timestamp <= self.max_delay {
                arrived.push(echo.clone()); false
            } else { true }
        });
        arrived
    }
}
