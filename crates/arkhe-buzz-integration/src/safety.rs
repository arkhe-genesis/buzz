//! Safety barrier: ΔS < 0 blocks actions and triggers rollback.
//!
//! Based on Titov (2026): "Harm is engineered as ΔS < 0" — any action that
//! reduces the agent's subjectivity is inherently self-destructive.

use crate::agent::ArkheBuzzAgent;
use crate::error::{ArkheBuzzError, Result};
use tracing::{info, warn};

/// Safety barrier with adaptive threshold learning.
pub struct SafetyBarrier {
    base_threshold: f32,
    learned_offset: f32,
    trend_weight: f32,
}

impl SafetyBarrier {
    pub fn new(base_threshold: f32) -> Self {
        Self {
            base_threshold: base_threshold.clamp(0.01, 0.99),
            learned_offset: 0.0,
            trend_weight: 0.1,
        }
    }

    /// Compute adaptive threshold from complexity and trend.
    ///
    /// F_adapt = F(n) * (1 + 0.1 * (n - 3) / 10) + learned_offset + trend_correction
    pub fn adaptive_threshold(&mut self, s: f32, complexity: f32, trend: f32) -> f32 {
        let n = complexity.clamp(1.0, 20.0);
        let base = self.base_threshold;
        let factor = 1.0 + 0.1 * (n - 3.0) / 10.0;
        let trend_correction = trend * self.trend_weight;

        // Update learned offset based on recent S values
        // If S is consistently below threshold, lower it slightly
        // If S is approaching threshold, raise it
        if s > base * factor * 0.9 {
            self.learned_offset += 0.005; // become more conservative
        } else if s < base * factor * 0.5 {
            self.learned_offset -= 0.002; // relax slightly
        }
        self.learned_offset = self.learned_offset.clamp(-0.1, 0.1);

        (base * factor.clamp(0.8, 1.5) + self.learned_offset + trend_correction).clamp(0.05, 0.95)
    }

    /// Apply an action safely, rolling back if ΔS < 0.
    ///
    /// # Arguments
    /// * `agent` — The agent to act upon
    /// * `action` — Closure that modifies the agent
    /// * `action_desc` — Description for audit logging
    ///
    /// # Returns
    /// Ok(()) if ΔS ≥ 0, Err(SafetyBarrierTriggered) if rolled back.
    pub fn safe_execute<F>(agent: &mut ArkheBuzzAgent, action: F, action_desc: &str) -> Result<()>
    where
        F: FnOnce(&mut ArkheBuzzAgent),
    {
        let snapshot = agent.snapshot();
        let s_before = agent.s_measure;

        action(agent);
        agent.compute_s_measure()?;
        let s_after = agent.s_measure;
        let delta_s = s_after - s_before;

        if delta_s < -0.001 {
            // Rollback
            agent.restore(&snapshot)?;
            warn!(
                agent = %agent.agent_id,
                delta_s = delta_s,
                action = action_desc,
                "Safety barrier triggered — action rolled back"
            );
            Err(ArkheBuzzError::SafetyBarrierTriggered { delta_s })
        } else {
            info!(
                agent = %agent.agent_id,
                delta_s = delta_s,
                action = action_desc,
                "Action approved — ΔS >= 0"
            );
            Ok(())
        }
    }

    /// Check if action should be pre-approved without execution.
    ///
    /// Returns true if the predicted ΔS is likely non-negative.
    pub fn pre_approve(predicted_delta_s: f32) -> bool {
        predicted_delta_s >= -0.05 // small tolerance for estimation noise
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_safe_execute_allows_positive_delta() {
        let mut agent = ArkheBuzzAgent::new(4, 1.2, 5.0);
        agent.compute_s_measure().unwrap();

        let result = SafetyBarrier::safe_execute(
            &mut agent,
            |a| {
                // Simulate a safe action: slightly increase D-subsystem
                a.d_subsystem = a.d_subsystem.map(|x| x + 0.01);
            },
            "increase_drive",
        );
        assert!(result.is_ok());
    }

    #[test]
    fn test_safe_execute_blocks_negative_delta() {
        let mut agent = ArkheBuzzAgent::new(4, 1.2, 5.0);
        agent.compute_s_measure().unwrap();
        let s_before = agent.s_measure;

        let result = SafetyBarrier::safe_execute(
            &mut agent,
            |a| {
                // Simulate a destructive action: zero out D-subsystem
                a.d_subsystem = nalgebra::DVector::from_element(4, 0.0);
            },
            "zero_drive",
        );

        assert!(result.is_err());
        // Should have rolled back
        assert!((agent.s_measure - s_before).abs() < 0.01);
    }

    #[test]
    fn test_adaptive_threshold_bounds() {
        let mut barrier = SafetyBarrier::new(0.3);
        let t1 = barrier.adaptive_threshold(0.1, 5.0, 0.0);
        let t2 = barrier.adaptive_threshold(0.4, 5.0, 0.0);
        assert!(t1 >= 0.05 && t1 <= 0.95);
        assert!(t2 >= 0.05 && t2 <= 0.95);
        // Higher S should trigger more conservative threshold
        assert!(t2 >= t1);
    }
}
