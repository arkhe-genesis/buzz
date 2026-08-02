use tokio::net::UdpSocket;
use tokio::time::{sleep, Duration};
use std::collections::HashMap;
use std::net::SocketAddr;
use serde::{Serialize, Deserialize};
use crate::{EchoSignal, TimeBlock, PlasmaConfig, EvoField};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NetworkMessage {
    Heartbeat { node_id: u64, field_hash: [u8; 32], phase_time: f64 },
    Echo { echo: EchoSignal, block: TimeBlock },
    BlockRequest { height: u64 },
}

pub struct PeerInfo {
    pub node_id: u64,
}

impl PeerInfo {
    pub fn new(node_id: u64) -> Self {
        Self { node_id }
    }
}

pub struct P2PNode {
    socket: UdpSocket,
    node_id: u64,
    peers: HashMap<SocketAddr, PeerInfo>,
    config: PlasmaConfig,
    field: EvoField,
}

impl P2PNode {
    pub async fn new(addr: SocketAddr, config: PlasmaConfig) -> Self {
        let socket = UdpSocket::bind(addr).await.unwrap();
        let node_id = rand::random();
        let field = EvoField::harris_sheet(config);
        Self { socket, node_id, peers: HashMap::new(), config, field }
    }

    pub async fn broadcast_echo(&self, echo: EchoSignal, block: TimeBlock) {
        let packet = NetworkMessage::Echo { echo: echo.clone(), block };
        let serialized = bincode::serialize(&packet).unwrap();

        for (peer_addr, _info) in self.peers.iter() {
            let delay = 0.1; // Placeholder for frequency-based delay
            let data = serialized.clone();
            let target = *peer_addr;
            // Simplified broadcast for simulation purposes
            let _ = self.socket.send_to(&data, target).await;
        }
    }

    pub async fn run(&mut self) {
        let mut buf = [0u8; 65536];
        loop {
            let (len, src) = self.socket.recv_from(&mut buf).await.unwrap();
            let packet: NetworkMessage = bincode::deserialize(&buf[..len]).unwrap();
            self.handle_message(packet, src).await;
        }
    }

    async fn handle_message(&mut self, msg: NetworkMessage, src: SocketAddr) {
        match msg {
            NetworkMessage::Echo { echo, block } => {
                self.process_echo(echo, block).await;
            }
            NetworkMessage::Heartbeat { node_id, field_hash: _, phase_time: _ } => {
                self.peers.entry(src).or_insert(PeerInfo::new(node_id));
            }
            _ => {}
        }
    }

    async fn process_echo(&mut self, _echo: EchoSignal, _block: TimeBlock) {
        // Placeholder for echo processing logic
    }
}
