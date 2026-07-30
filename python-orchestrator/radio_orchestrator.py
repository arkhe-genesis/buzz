#!/usr/bin/env python3
"""
Cathedral Arkhe — Radio Protocol Orchestrator

Manages multiple protocol daemons (Meshtastic, Reticulum, Bitchat)
via the Rust MAC scheduler. Sends configuration commands over MQTT.
"""

import json
import paho.mqtt.client as mqtt
from orchestrator import Orchestrator, Node, Layer

class RadioOrchestrator:
    def __init__(self, orch: Orchestrator, mqtt_broker: str = "localhost"):
        self.orch = orch
        self.mqtt = mqtt.Client()
        self.mqtt.on_message = self._on_mqtt_message
        self.mqtt.connect(mqtt_broker)
        self.mqtt.subscribe("cathedral/radio/config")
        self.mqtt.subscribe("cathedral/radio/telemetry/#")

    def _on_mqtt_message(self, client, userdata, msg):
        topic = msg.topic
        payload = json.loads(msg.payload)
        if topic == "cathedral/radio/config":
            # Command to enable/disable a protocol daemon.
            daemon_id = payload.get("daemon")
            enabled = payload.get("enabled", True)
            # Send command to Rust MAC scheduler (via ZeroMQ).
            self.orch.add_node(Node(
                id=f"daemon_{daemon_id}_{int(enabled)}",
                type="RadioConfig",
                layer=Layer.L0_INFRA,
                metadata=json.dumps(payload)
            ))
            # Publish the schedule change.
            self.mqtt.publish("cathedral/radio/schedule", json.dumps({
                "daemons": self._get_active_daemons()
            }))
        elif topic.startswith("cathedral/radio/telemetry/"):
            # Forward telemetry to the hypergraph.
            self.orch.add_node(Node(
                id=f"radio_tele_{payload['node_id']}_{payload['seq']}",
                type="RadioTelemetry",
                layer=Layer.L2_PHYSICS,
                metadata=json.dumps(payload)
            ))

    def _get_active_daemons(self) -> list:
        # Query the orchestrator state to get currently enabled daemons.
        return ["Meshtastic", "Reticulum", "Bitchat"]  # stub

if __name__ == "__main__":
    orch = Orchestrator()
    radio = RadioOrchestrator(orch)
    # Start MQTT loop, then wait for commands.
    radio.mqtt.loop_forever()