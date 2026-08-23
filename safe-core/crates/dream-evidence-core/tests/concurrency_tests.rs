use dream_evidence_core::{
    types::*,
    persistence::{PersistenceManager, ProtocolMeta},
    acquisition::Acquisition,
};
use std::sync::Arc;
use tempfile::tempdir;

#[tokio::test]
async fn test_persistence_concurrent_access() {
    let dir = tempdir().unwrap();
    let db_path = dir.path().join("test_db.redb");

    let pm = PersistenceManager::new(&db_path).unwrap();

    let meta = ProtocolMeta {
        next_packet_id: 42,
        next_epoch_id: 10,
        hardware_active: true,
        rem_window_start: Some(100),
        rem_window_end: Some(200),
        audit_chain_length: 5,
    };
    pm.save_meta(&meta).unwrap();

    let packet = DataPacket::new(100, SensorType::EEG, vec![1, 2], 0);
    pm.acquisition.insert("pkt:0", &packet).unwrap();

    let loaded_meta = pm.load_meta().unwrap();
    assert_eq!(loaded_meta.next_packet_id, 42);

    let loaded_packet = pm.acquisition.get("pkt:0").unwrap().unwrap();
    assert_eq!(loaded_packet.id, 0);
}
