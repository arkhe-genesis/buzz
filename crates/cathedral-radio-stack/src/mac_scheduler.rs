//! MAC Scheduler – FreeRTOS task implementation.
//! Uses `freertos-rust` crate for task management and queues.

use freertos_rust::*;
use crate::sx1262::RadioPhy;
use crate::mac::{ProtocolDaemon, Frame};

/// Scheduler configuration received over MQTT.
#[derive(Debug, Clone)]
pub struct SchedulerConfig {
    pub slot_duration_ms: u32,
    pub enabled_daemons: Vec<u8>, // protocol IDs
}

/// MAC scheduler state.
pub struct MacScheduler<PHY: RadioPhy> {
    phy: PHY,
    daemons: Vec<ProtocolDaemon>,
    config: SchedulerConfig,
    current_slot: usize,
    slot_start_ticks: TickType,
}

impl<PHY: RadioPhy> MacScheduler<PHY> {
    pub fn new(phy: PHY) -> Self {
        Self {
            phy,
            daemons: Vec::new(),
            config: SchedulerConfig {
                slot_duration_ms: 100,
                enabled_daemons: vec![1, 2, 3], // Meshtastic, Reticulum, Bitchat
            },
            current_slot: 0,
            slot_start_ticks: 0,
        }
    }

    /// Register a protocol daemon.
    pub fn register_daemon(&mut self, mut daemon: ProtocolDaemon) {
        // Ensure the daemon has a send channel (queue) for outgoing frames.
        self.daemons.push(daemon);
    }

    /// Update configuration (called from MQTT callback).
    pub fn update_config(&mut self, config: SchedulerConfig) {
        self.config = config;
        // If the enabled set changes, rebuild daemon list (filter).
        // For simplicity, we assume all registered daemons are always enabled.
    }

    /// The main FreeRTOS task.
    pub fn task_entry(mut self) -> ! {
        // Initialize the radio
        self.phy.set_frequency(868.0).unwrap();
        self.phy.set_modulation(9, 125_000, 5).unwrap();

        let mut current_slot = 0;
        self.slot_start_ticks = get_current_tick();

        loop {
            let now = get_current_tick();
            let elapsed = (now - self.slot_start_ticks) as u32;
            if elapsed >= self.config.slot_duration_ms {
                // Switch to next slot
                if !self.daemons.is_empty() {
                    current_slot = (current_slot + 1) % self.daemons.len();
                }
                self.slot_start_ticks = now;
                self.current_slot = current_slot;
            }

            // Get the active daemon
            if let Some(daemon) = self.daemons.get_mut(current_slot) {
                // Check if daemon has a frame to send (from its queue)
                if let Some(frame) = daemon.send_queue.pop_front() {
                    // Add protocol ID to front of payload
                    let mut packet = vec![daemon.id];
                    packet.extend_from_slice(&frame.payload);
                    let _ = self.phy.transmit(&packet);
                }

                // Receive any incoming frame
                if let Ok(Some(rx)) = self.phy.receive() {
                    if let Some(proto) = rx.first() {
                        // Deliver to the daemon with matching ID
                        if let Some(target) = self.daemons.iter_mut().find(|d| d.id == *proto) {
                            let rssi = self.phy.get_rssi();
                            let snr = self.phy.get_snr();
                            (target.receive_callback)(rx.clone(), rssi, snr);
                            // Also forward telemetry to orchestrator
                            crate::telemetry::publish_telemetry(*proto, rssi, snr, rx.len());
                        }
                    }
                }
            }

            // Yield to other tasks
            delay_ticks(1);
        }
    }
}

/// Create and start the FreeRTOS task.
pub fn start_scheduler<PHY: RadioPhy + Send + 'static>(phy: PHY) {
    let scheduler = MacScheduler::new(phy);
    // Wrap in a task handle
    let _task = Task::new()
        .stack_size(2048)
        .priority(TaskPriority(2))
        .start(move |_| { scheduler.task_entry(); })
        .unwrap();
    // Store task handle if needed
}

// Mock functions for FreeRTOS bindings.
fn get_current_tick() -> TickType { 0 }
fn delay_ticks(_t: TickType) { }
type TickType = u32;
