use serde::{Deserialize, Serialize};
use std::fs; use std::path::PathBuf;
use crate::shadow::Shadow;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShadowSnapshot { pub height: u64, pub shadow: Shadow, pub timestamp: f64 }

pub struct ShadowStore { pub dir: PathBuf }
impl ShadowStore {
    pub fn new(dir: PathBuf) -> Self { fs::create_dir_all(&dir).unwrap(); Self { dir } }
    pub fn save(&self, snapshot: &ShadowSnapshot) -> Result<(), std::io::Error> {
        let path = self.dir.join(format!("shadow_{}.bin", snapshot.height));
        fs::write(path, bincode::serialize(snapshot).unwrap())
    }
    pub fn load(&self, height: u64) -> Result<ShadowSnapshot, std::io::Error> {
        let bytes = fs::read(self.dir.join(format!("shadow_{}.bin", height)))?;
        Ok(bincode::deserialize(&bytes).unwrap())
    }
}
