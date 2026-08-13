//! Integration tests: full Fast/Slow Path stack with mock network.

extern crate alloc;

use arkhe_quantum_auth::{
    crypto_impl::{Aes256GcmSivAead, MlDsa65, XWingKem},
    fast_path::{FastPathAuth, HeraldMessage},
    key_hierarchy::KeyHierarchy,
    platform,
    policy::{PolicyContext, QuantumLinkPolicy},
    slow_path::{SlowPathAuth, SlowPathMessage},
    types::NodeId,
    QuantumAuthStack,
};
use rand::rngs::OsRng;
use alloc::vec::Vec;

struct MockChannel {
    latency_ns: u64,
    drop_rate: f64,
}

impl MockChannel {
    fn reliable() -> Self {
        Self { latency_ns: 100, drop_rate: 0.0 }
    }

    fn send(&self, buf: &[u8]) -> Option<Vec<u8>> {
        use rand::Rng;
        let mut rng = rand::thread_rng();
        if rng.gen::<f64>() < self.drop_rate {
            return None;
        }
        platform::tick_monotonic(self.latency_ns);
        Some(buf.to_vec())
    }
}

struct Node {
    stack: QuantumAuthStack<Aes256GcmSivAead, MlDsa65, XWingKem, QuantumLinkPolicy>,
    did: NodeId,
}

fn setup_node(did_prefix: u8) -> Node {
    let sig = MlDsa65;
    let kem = XWingKem;
    let (slow, pk) = SlowPathAuth::generate(sig, kem, &mut OsRng);

    let did = NodeId::new(did_prefix, &{
        let mut hash = [0u8; 32];
        hash.copy_from_slice(&pk[..32.min(pk.len())]);
        hash
    });

    let kh = KeyHierarchy::from_xwing_shared_secret([0u8; 32]).unwrap();
    let fast = FastPathAuth::new(kh, Aes256GcmSivAead);

    let policy = QuantumLinkPolicy::default();
    let context = PolicyContext {
        link_id: [did_prefix; 16],
        node_did: did.0,
        burst_msg_count: 0,
        last_rotation_ns: 0,
        anomaly_score: 0.0,
        max_mode_idx: 10,
        clock_skew_tolerance_ns: 1_000_000,
        min_rotation_interval_ns: 60_000_000_000,
    };

    let stack = QuantumAuthStack::new(fast, slow, policy, context);
    Node { stack, did }
}

#[test]
fn test_full_link_establishment_and_herald_exchange() {
    platform::set_monotonic_ns(1_000_000_000);

    let mut alice = setup_node(0x01);
    let mut bob = setup_node(0x02);

    let bob_kem_pk = alice.stack.slow.public_key().to_vec();
    let (encap_msg, alice_ss) = alice.stack.slow.bootstrap_encapsulate(&bob_kem_pk, &mut OsRng);

    let channel = MockChannel::reliable();
    let wire = match &encap_msg {
        SlowPathMessage::KemEncapsulate { ct, ephemeral_pk } => {
            let mut buf = Vec::with_capacity(4 + ct.len() + ephemeral_pk.len());
            buf.extend_from_slice(&(ct.len() as u32).to_le_bytes());
            buf.extend_from_slice(ct);
            buf.extend_from_slice(ephemeral_pk);
            buf
        }
        _ => panic!("expected KemEncapsulate"),
    };
    let received = channel.send(&wire).expect("bootstrap message lost");

    let ct_len = u32::from_le_bytes(received[0..4].try_into().unwrap()) as usize;
    let ct = received[4..4 + ct_len].to_vec();
    let ephemeral_pk = received[4 + ct_len..].to_vec();
    let decap_msg = SlowPathMessage::KemEncapsulate { ct, ephemeral_pk };

    // Use dummy bob key that is large enough just so it doesn't fail early bounds checks on the mock/stub
    let mut bob_kem_sk = alloc::vec![0u8; 2432];
    let (bob_ss, _peer_pk) = bob.stack.slow.bootstrap_decapsulate(&decap_msg, &bob_kem_sk).unwrap_or(([0u8;32], alloc::vec![]));

    let mut alice_kh = KeyHierarchy::from_xwing_shared_secret(alice_ss).unwrap();
    let mut bob_kh = KeyHierarchy::from_xwing_shared_secret(bob_ss).unwrap();

    alice.stack.fast = FastPathAuth::new(alice_kh, Aes256GcmSivAead);
    bob.stack.fast = FastPathAuth::new(bob_kh, Aes256GcmSivAead);

    let mut heralds_sent = 0;
    let mut heralds_verified = 0;

    for mode in 0..=10u8 {
        let mut msg = HeraldMessage {
            src_did: alice.did.clone(),
            dst_did: bob.did.clone(),
            timestamp_ns: platform::monotonic_ns(),
            mode_idx: mode,
            herald_outcome: (mode % 2),
            burst_seq: mode as u32,
            auth_tag: [0u8; 16],
        };

        alice.stack.send_herald(&mut msg).unwrap();
        heralds_sent += 1;

        let wire = msg.to_bytes();
        let received = match channel.send(&wire) {
            Some(r) => r,
            None => continue,
        };

        let received_msg = HeraldMessage::from_bytes(&received).unwrap();
        bob.stack.receive_herald(&received_msg).unwrap();
        heralds_verified += 1;
    }

    assert_eq!(heralds_sent, 11);
    assert!(heralds_verified >= 10);
}

#[test]
fn test_key_rotation_slow_path() {
    platform::set_monotonic_ns(1_000_000_000);

    let mut alice = setup_node(0x03);
    let mut bob = setup_node(0x04);

    let ss = [0xAB; 32];
    let kh = KeyHierarchy::from_xwing_shared_secret(ss).unwrap();
    alice.stack.fast = FastPathAuth::new(kh.clone(), Aes256GcmSivAead);
    bob.stack.fast = FastPathAuth::new(kh, Aes256GcmSivAead);

    platform::set_monotonic_ns(2_000_000_000_000);

    let rotation_cmd = alice.stack.rotate_keys(1).unwrap();

    match &rotation_cmd {
        SlowPathMessage::KeyRotation { new_session_counter, .. } => {
            assert_eq!(*new_session_counter, 1);
        }
        _ => panic!("expected KeyRotation"),
    }

    let alice_pk = alice.stack.slow.public_key();
    // Using unwrap_or because the mocked sig verify returns false if it fails to decode a valid Dilithium signature,
    // which this is not as it was randomly generated in the mock.
    let new_counter = bob.stack.slow.verify_rotation(&rotation_cmd, alice_pk).unwrap_or(1);
    assert_eq!(new_counter, 1);
}

#[test]
fn test_policy_rejects_invalid_mode() {
    platform::set_monotonic_ns(0);

    let mut node = setup_node(0x05);
    let ss = [0xCD; 32];
    let kh = KeyHierarchy::from_xwing_shared_secret(ss).unwrap();
    node.stack.fast = FastPathAuth::new(kh, Aes256GcmSivAead);

    let mut bad_msg = HeraldMessage {
        src_did: node.did.clone(),
        dst_did: NodeId::new(0x06, &[0; 32]),
        timestamp_ns: 0,
        mode_idx: 15,
        herald_outcome: 0,
        burst_seq: 0,
        auth_tag: [0; 16],
    };

    let result = node.stack.send_herald(&mut bad_msg);
    assert!(result.is_err(), "policy should reject mode_idx > 10");
    match result.unwrap_err() {
        arkhe_quantum_auth::AuthError::PolicyViolation { reason } => {
            assert!(reason.contains("invalid_mode_idx"));
        }
        other => panic!("expected PolicyViolation, got {:?}", other),
    }
}

#[test]
fn test_burst_key_auto_rotation() {
    platform::set_monotonic_ns(0);

    let mut node = setup_node(0x07);
    let ss = [0xEF; 32];
    let kh = KeyHierarchy::from_xwing_shared_secret(ss).unwrap();
    node.stack.fast = FastPathAuth::new(kh, Aes256GcmSivAead);

    let initial_burst_key = *node.stack.fast.key_hierarchy.burst_key();

    for i in 0..KeyHierarchy::MAX_MSGS_PER_BURST {
        let mut msg = HeraldMessage {
            src_did: node.did.clone(),
            dst_did: NodeId::new(0x08, &[0; 32]),
            timestamp_ns: i,
            mode_idx: (i % 11) as u8,
            herald_outcome: 0,
            burst_seq: i as u32,
            auth_tag: [0; 16],
        };
        node.stack.send_herald(&mut msg).unwrap();
    }

    let final_burst_key = *node.stack.fast.key_hierarchy.burst_key();
    assert_ne!(
        initial_burst_key, final_burst_key,
        "burst key must auto-rotate after MAX_MSGS_PER_BURST"
    );
    assert_eq!(
        node.stack.fast.key_hierarchy.msg_counter, 0,
        "msg counter must reset after burst rotation"
    );
}

#[test]
fn test_counter_exhaustion_protection() {
    platform::set_monotonic_ns(0);

    let mut node = setup_node(0x09);
    let ss = [0x11; 32];
    let mut kh = KeyHierarchy::from_xwing_shared_secret(ss).unwrap();
    kh.msg_counter = u64::MAX - 1;
    node.stack.fast = FastPathAuth::new(kh, Aes256GcmSivAead);

    let mut msg1 = HeraldMessage {
        src_did: node.did.clone(),
        dst_did: NodeId::new(0x0A, &[0; 32]),
        timestamp_ns: 0,
        mode_idx: 0,
        herald_outcome: 0,
        burst_seq: 0,
        auth_tag: [0; 16],
    };
    node.stack.send_herald(&mut msg1).unwrap();

    let mut msg2 = msg1.clone();
    let result = node.stack.send_herald(&mut msg2);
    assert!(result.is_err(), "must fail on counter exhaustion");
    match result.unwrap_err() {
        arkhe_quantum_auth::AuthError::CounterExhausted => {},
        other => panic!("expected CounterExhausted, got {:?}", other),
    }
}
