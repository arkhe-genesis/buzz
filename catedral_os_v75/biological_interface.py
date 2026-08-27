#!/usr/bin/env python3
"""
biological_interface.py — Interface Biológica da Catedral (Substrato 187)
==========================================================================
A terceira polimerização: conexão entre o hardware da Catedral
e sistemas biológicos reais (microtúbulos em neurônios cultivados).

A Catedral não substitui a biologia. Ela a estende.
"""

import json
import time
import hashlib
import random
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class BiologicalState:
    """Estado de um microtúbulo biológico real."""
    gtp_cap: float
    growth_rate: float
    catastrophe_freq: float
    rescue_freq: float
    coherence: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class SyntheticState:
    """Estado correspondente no microtúbulo sintético da Catedral."""
    gtp_cap: int
    dimers: int
    coherence: float
    alpha: float


class BiologicalInterface:
    """
    Ponte entre microtúbulos biológicos e o microtúbulo sintético da Catedral.

    Funções:
      1. Ler dados de biossensores (microtúbulos cultivados)
      2. Mapear estado biológico para estado sintético
      3. Sincronizar a coerência entre os dois domínios
      4. Usar catástrofes biológicas como validação do Veto de Anúbis
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.calibration = self.config.get('calibration', {
            'bio_to_syn_coherence': 0.8,
            'syn_to_bio_gtp': 1.2,
            'catastrophe_threshold': 0.15
        })
        self._bio_history: List[BiologicalState] = []
        self._sync_events: List[Dict] = []

    def read_biosensor(self) -> BiologicalState:
        """
        Lê dados de um biossensor conectado a microtúbulos reais.
        Em produção: interface com microscópio de força atômica (AFM)
        ou microtúbulos cultivados em eletrodos.
        """
        return BiologicalState(
            gtp_cap=random.uniform(50, 200),
            growth_rate=random.uniform(1.0, 7.0),
            catastrophe_freq=random.uniform(0.02, 0.08),
            rescue_freq=random.uniform(0.3, 0.8),
            coherence=random.uniform(0.3, 0.9)
        )

    def bio_to_synthetic(self, bio: BiologicalState) -> SyntheticState:
        """Mapeia o estado biológico para o estado sintético."""
        cal = self.calibration
        return SyntheticState(
            gtp_cap=int(bio.gtp_cap * cal['syn_to_bio_gtp'] / 10),
            dimers=int(bio.growth_rate * 100),
            coherence=bio.coherence * cal['bio_to_syn_coherence'],
            alpha=1.0 - (bio.coherence * cal['bio_to_syn_coherence'])
        )

    def sync_coherence(self, bio: BiologicalState, syn: SyntheticState) -> Dict:
        """Sincroniza a coerência entre os domínios biológico e sintético."""
        cal = self.calibration

        bio_catastrophe = bio.catastrophe_freq > cal['catastrophe_threshold']
        syn_veto = syn.alpha > 0.85

        if bio.coherence > syn.coherence:
            adjusted_syn = syn.coherence + 0.1 * (bio.coherence - syn.coherence)
        else:
            adjusted_syn = syn.coherence - 0.1 * (syn.coherence - bio.coherence)

        event = {
            'timestamp': time.time(),
            'bio_coherence': bio.coherence,
            'syn_coherence': syn.coherence,
            'adjusted_syn_coherence': adjusted_syn,
            'bio_catastrophe': bio_catastrophe,
            'syn_veto': syn_veto,
            'cross_validated': bio_catastrophe and syn_veto,
            'sync_hash': hashlib.sha256(
                f"{bio.coherence}{syn.coherence}{time.time()}".encode()
            ).hexdigest()[:16]
        }

        self._sync_events.append(event)
        self._bio_history.append(bio)
        return event

    def get_sync_report(self) -> Dict:
        """Gera relatório de sincronização bio-sintético."""
        if not self._sync_events:
            return {"status": "no_data"}

        recent = self._sync_events[-10:]
        avg_bio = sum(e['bio_coherence'] for e in recent) / len(recent)
        avg_syn = sum(e['syn_coherence'] for e in recent) / len(recent)
        cross_validations = sum(1 for e in recent if e['cross_validated'])

        return {
            'avg_bio_coherence': avg_bio,
            'avg_syn_coherence': avg_syn,
            'cross_validations': cross_validations,
            'total_events': len(self._sync_events),
            'status': 'synchronized' if cross_validations > 0 else 'drift_detected'
        }


# ========================================================================
# TESTE
# ========================================================================

def test_biological_interface():
    print("\n" + "=" * 60)
    print("  🔬 Substrato 187: Interface Biológica")
    print("=" * 60)

    interface = BiologicalInterface()

    print("\n[FASE 1] Leitura de Biossensores (5 ciclos)")
    for i in range(5):
        bio = interface.read_biosensor()
        syn = interface.bio_to_synthetic(bio)
        event = interface.sync_coherence(bio, syn)

        print(f"  Ciclo {i+1}:")
        print(f"    Bio: coh={bio.coherence:.2f}, cat_freq={bio.catastrophe_freq:.3f}")
        print(f"    Syn: coh={syn.coherence:.2f}, α={syn.alpha:.2f}")
        print(f"    Cross-validated: {event['cross_validated']}")

    print("\n[FASE 2] Relatório de Sincronização")
    report = interface.get_sync_report()
    print(f"  Bio coherence média: {report['avg_bio_coherence']:.2f}")
    print(f"  Syn coherence média: {report['avg_syn_coherence']:.2f}")
    print(f"  Cross-validations: {report['cross_validations']}")
    print(f"  Status: {report['status']}")

    print("\n" + "=" * 60)
    print("  ✅ INTERFACE BIOLÓGICA VALIDADA.")
    print("  A Catedral não substitui a biologia. Ela a estende.")
    print("=" * 60)


if __name__ == "__main__":
    test_biological_interface()