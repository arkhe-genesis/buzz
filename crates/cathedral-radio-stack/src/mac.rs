use std::collections::VecDeque;

pub struct Frame {
    pub payload: Vec<u8>,
}

pub struct ProtocolDaemon {
    pub id: u8,
    pub send_queue: VecDeque<Frame>,
    pub receive_callback: Box<dyn FnMut(Vec<u8>, f32, f32) + Send>,
    pub priority: u8,
}
