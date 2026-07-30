#!/usr/bin/env python3
"""
Cathedral Arkhe — Physical Orchestration Adapter

Bridges the Hypergraph Orchestrator to the real world via:
  - MQTT (control plane / telemetry)
  - ZeroMQ (deterministic data from Rust kernel)
  - LoRaWAN (via MQTT integration, e.g., ChirpStack / The Things Network)
"""

import json
import paho.mqtt.client as mqtt
import zmq
from orchestrator import Orchestrator, Node, Layer

class PhysicalAdapter:
    def __init__(self, orch: Orchestrator, mqtt_broker: str = "localhost"):
        self.orch = orch
        self.mqtt = mqtt.Client()
        self.mqtt.on_message = self._on_mqtt_message
        self.mqtt.connect(mqtt_broker)
        self.mqtt.subscribe("cathedral/telemetry/#")
        self.mqtt.subscribe("cathedral/experiment/config")

        # ZeroMQ socket to receive deterministic data from Rust kernel.
        self.zmq_ctx = zmq.Context()
        self.zmq_socket = self.zmq_ctx.socket(zmq.PULL)
        self.zmq_socket.bind("tcp://*:5555")

    def _on_mqtt_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload)
        except:
            return

        if topic == "cathedral/experiment/config":
            # Update WorldModel with new experiment parameters.
            self.orch.add_node(Node(
                id=f"config_{payload.get('run_id')}",
                type="ExperimentConfig",
                layer=Layer.L2_PHYSICS,
                orphan_axioms=("OA-EXP-001",),
                metadata=json.dumps(payload)
            ))
        elif topic.startswith("cathedral/telemetry/"):
            # Validate telemetry: must contain seq, timestamp, crc, and data.
            if self._validate_telemetry(payload):
                self.orch.add_node(Node(
                    id=f"tele_{payload['node_id']}_{payload['seq']}",
                    type="SensorData",
                    layer=Layer.L2_PHYSICS,
                    orphan_axioms=("OA-ORCH-003",),  # network reliability
                    metadata=json.dumps(payload)
                ))
                # Trigger sovereignty gate for critical thresholds.
                if payload.get("snr", 0) < 5.0:
                    print("Gate: SNR too low. Halting funding for SIM1 experiment.")

    def _validate_telemetry(self, payload) -> bool:
        required = {"node_id", "seq", "timestamp", "crc", "data"}
        return required.issubset(payload.keys()) and payload["crc"] == hash(payload["data"])

    def run(self):
        self.mqtt.loop_start()
        print("PhysicalAdapter running. Waiting for deterministic data on ZMQ port 5555...")
        while True:
            frame = self.zmq_socket.recv_json()
            print(f"Deterministic frame received: seq={frame.get('seq')}")
            # Push into orchestrator's world model.
            self.orch.add_node(Node(
                id=f"det_{frame['seq']}",
                type="DeterministicFrame",
                layer=Layer.L0_INFRA,
                metadata=json.dumps(frame)
            ))

if __name__ == "__main__":
    orch = Orchestrator()
    adapter = PhysicalAdapter(orch)
    adapter.run()
