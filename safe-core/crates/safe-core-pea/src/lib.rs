use safe_core_identity::ArkheDid;

#[derive(Debug, Clone)]
pub enum TaskState {
    Pending,
    Running,
    Completed,
    Failed,
}

#[derive(Debug, Clone)]
pub struct Intent {
    pub root_hash: blake3::Hash,
    pub did: ArkheDid,
    pub action: String,
    pub data: Vec<u8>,
    pub state: TaskState,
}

impl Intent {
    pub fn new_root(root_hash: &blake3::Hash, did: ArkheDid, action: &str, data: &[u8]) -> Self {
        Self {
            root_hash: *root_hash,
            did,
            action: action.to_string(),
            data: data.to_vec(),
            state: TaskState::Pending,
        }
    }

    pub fn advance_state(&mut self, state: TaskState, _ctx: &()) -> Result<(), ()> {
        self.state = state;
        Ok(())
    }
}

pub struct PolicyEngine {}
