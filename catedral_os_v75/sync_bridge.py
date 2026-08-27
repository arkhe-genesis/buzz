#!/usr/bin/env python3
"""
sync_bridge.py — Ponte de Sincronização Edge → Cloud (WormGraph Sync)
====================================================================
Versão 2.0: Compressão de Merkle, Pruning e Consenso Multi-Cloud.
"""

import json
import time
import hashlib
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import urllib.request
import urllib.error
import random

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [WGS] %(levelname)s: %(message)s'
)
logger = logging.getLogger('wormgraph.sync')


@dataclass
class EdgeState:
    session: str
    context_hash: str
    alpha: float
    level: int
    flags: int
    nonce: int
    timestamp: float


class WormGraphSyncBridge:
    """Ponte de sincronização com compressão e consenso multi-cloud."""

    def __init__(self, config: Dict = None):
        config = config or {}
        self.cloud_endpoints = config.get('cloud_endpoints', [
            'http://localhost:8080/api/ledger'
        ])
        self.max_pending = config.get('max_pending', 100)
        self.commit_interval = config.get('commit_interval', 30.0)
        self._running = False
        self._pending: List[EdgeState] = []

    def add_state(self, state: EdgeState):
        self._pending.append(state)
        if len(self._pending) > self.max_pending:
            self._prune()

    def _prune(self):
        self._pending.sort(key=lambda s: s.alpha, reverse=True)
        self._pending = self._pending[:self.max_pending // 2]

    def _compute_merkle_root(self, states: List[EdgeState]) -> str:
        hashes = [hashlib.sha256(json.dumps(s.__dict__).encode()).hexdigest() for s in states]
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])
            hashes = [hashlib.sha256((hashes[i]+hashes[i+1]).encode()).hexdigest()
                      for i in range(0, len(hashes), 2)]
        return hashes[0] if hashes else "0"*64

    def _build_commit(self, states: List[EdgeState]) -> Dict:
        merkle_root = self._compute_merkle_root(states)
        block_data = f"{merkle_root}|{len(states)}|{states[0].nonce}|{states[-1].nonce}"
        return {
            'merkle_root': merkle_root,
            'n_states': len(states),
            'nonce_range': [states[0].nonce, states[-1].nonce],
            'block_hash': hashlib.sha256(block_data.encode()).hexdigest(),
            'timestamp': time.time()
        }

    def _send_to_endpoint(self, endpoint: str, block: Dict) -> bool:
        try:
            data = json.dumps(block).encode()
            req = urllib.request.Request(endpoint, data=data,
                                         headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read()).get('status') == 'committed'
        except Exception as e:
            logger.warning(f"Falha no endpoint {endpoint}: {e}")
            return False

    def sync_cycle(self) -> bool:
        if not self._pending:
            return True

        states = self._pending[:self.max_pending]
        block = self._build_commit(states)

        successes = 0
        required = len(self.cloud_endpoints) // 2 + 1
        for ep in self.cloud_endpoints:
            if self._send_to_endpoint(ep, block):
                successes += 1

        if successes >= required:
            logger.info(f"Bloco commitado ({successes}/{len(self.cloud_endpoints)})")
            self._pending = self._pending[len(states):]
            return True
        return False

    def run(self):
        self._running = True
        logger.info(f"Sync Bridge iniciado. Endpoints: {len(self.cloud_endpoints)}")
        while self._running:
            try:
                self.sync_cycle()
                time.sleep(self.commit_interval)
            except KeyboardInterrupt:
                self._running = False
            except Exception as e:
                logger.error(f"Erro: {e}")
                time.sleep(5)


if __name__ == "__main__":
    # Demo: gera estados e sincroniza
    bridge = WormGraphSyncBridge({
        'cloud_endpoints': ['http://localhost:8080/api/ledger'],
        'max_pending': 50,
        'commit_interval': 5.0
    })

    print("\n=== WormGraph Sync Bridge — Demo ===\n")
    for i in range(10):
        bridge.add_state(EdgeState(
            session="demo", context_hash=hash(str(i)),
            alpha=random.uniform(0.1, 0.9), level=random.randint(0, 4),
            flags=0, nonce=i, timestamp=time.time()
        ))
    print(f"Estados pendentes: {len(bridge._pending)}")
    success = bridge.sync_cycle()
    print(f"Sincronização: {'✅ Sucesso' if success else '⚠️ Offline (sem cloud)'}")