#!/bin/bash
# scripts/verify.sh — Executa todos os harnesses do SafeSail

set -e

echo "🔍 Verificando SafeSail com Kani..."

# Executar todos os harnesses
cd arkhe-safe-sail
cargo kani --harness s1_pressure_bounded_by_one
cargo kani --harness s2_boundary_condition
cargo kani --harness s3_pressure_monotonic
cargo kani --harness s4_pressure_non_negative
cargo kani --harness s5_temporal_stability
cargo kani --harness s6_rate_reduction_never_increases_pressure
cargo kani --harness s7_zero_pressure_always_safe
cargo kani --harness s8_max_capacity_always_safe
cargo kani --harness s9_capacity_construction_no_overflow
cargo kani --harness s10_metrics_construction_no_panic

echo "✅ Todos os harnesses verificados com sucesso!"
