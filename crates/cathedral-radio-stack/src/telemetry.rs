use rumqttc::{Client, MqttOptions, QoS};
use serde_json::json;

pub fn publish_telemetry(protocol_id: u8, rssi: f32, snr: f32, packet_len: usize) {
    // In a real system, we'd have a global MQTT client handle.
    let mut mqtt_opts = MqttOptions::new("node_1", "mqtt.broker.local", 1883);
    let (mut client, _) = Client::new(mqtt_opts, 10);
    let topic = format!("cathedral/telemetry/radio/{}", protocol_id);
    let payload = json!({
        "rssi": rssi,
        "snr": snr,
        "len": packet_len,
        "timestamp": 0, // get_current_tick(),
    });
    let _ = client.publish(&topic, QoS::AtLeastOnce, false, payload.to_string().as_bytes());
}
