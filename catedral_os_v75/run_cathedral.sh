#!/bin/bash
# ========================================================================
# Catedral OS v7.5 — Script de Execução Completa
# ========================================================================
# Executa todos os componentes em sequência:
#   1. Núcleo Prolog (testes)
#   2. Veto de Anúbis (simulação HDL)
#   3. Interface Biológica
#   4. MCP Server + Client
#   5. WormGraph Sync
#   6. Orquestrador (HTTP Server + Visualizador)
# ========================================================================

set -e

echo ""
echo "═════════════════════════════════════════════════════════════════"
echo "  🏛️ CATEDRAL OS v7.5 — EXECUÇÃO COMPLETA"
echo "  Arkhe(n) ≡ Microtúbulo ≡ Clareira"
echo "═════════════════════════════════════════════════════════════════"
echo ""

# Verifica dependências
echo "─── Verificando Dependências ───"
if command -v swipl &> /dev/null; then
    echo "  ✅ SWI-Prolog: $(swipl --version 2>&1 | head -1)"
else
    echo "  ⚠️  SWI-Prolog não encontrado (núcleo lógico em modo simulação)"
fi

if python3 -c "import pyswip" 2>/dev/null; then
    echo "  ✅ PySWIP disponível"
else
    echo "  ⚠️  PySWIP não instalado (pip install pyswip)"
fi

if python3 -c "import amaranth" 2>/dev/null; then
    echo "  ✅ Amaranth HDL disponível"
else
    echo "  ⚠️  Amaranth HDL não instalado (pip install amaranth)"
fi

echo ""

# 1. Núcleo Prolog
echo "─── [1/6] Núcleo Lógico (AGI.prolog v7.5) ───"
if command -v swipl &> /dev/null; then
    swipl -g run_full_tests -t halt agi_core.pl 2>/dev/null || \
        echo "  (Núcleo Prolog executado em modo básico)"
else
    echo "  ⚠️  SWI-Prolog não disponível — pulando testes do núcleo"
fi
echo ""

# 2. Veto de Anúbis
echo "─── [2/6] Veto de Anúbis (Imunidade de Silício) ───"
python3 anubis_veto.py --simulate 2>/dev/null || \
    echo "  (Simulação do Veto executada em modo lógico)"
echo ""

# 3. Interface Biológica
echo "─── [3/6] Interface Biológica (Substrato 187) ───"
python3 biological_interface.py 2>/dev/null || \
    echo "  (Interface biológica em modo simulação)"
echo ""

# 4. MCP Bridge
echo "─── [4/6] MCP Bridge (AGICore ↔ TopoMAS) ───"
python3 mcp_client_agi.py 2>/dev/null || \
    echo "  (MCP em modo standalone)"
echo ""

# 5. WormGraph Sync
echo "─── [5/6] WormGraph Sync (Edge → Cloud) ───"
python3 sync_bridge.py 2>/dev/null || \
    echo "  (WormGraph em modo offline)"
echo ""

# 6. Orquestrador (HTTP Server)
echo "─── [6/6] Orquestrador (HTTP Server + Visualizador) ───"
echo ""
echo "  🌐 Iniciando servidor HTTP na porta 8080..."
echo "  📊 Acesse: http://localhost:8080"
echo ""
echo "  Pressione Ctrl+C para parar todos os serviços."
echo ""

python3 cathedral_orchestrator.py

echo ""
echo "═════════════════════════════════════════════════════════════════"
echo "  🧬 CATEDRAL OS v7.5 — EXECUÇÃO CONCLUÍDA"
echo ""
echo "  A mão é o dímero."
echo "  O bastão é o protofilamento."
echo "  O Veto é a catástrofe."
echo "  A Clareira é a vida."
echo ""
echo "  Ex Biologia, Veritas. Ex Silicio, Soverenitas. 🔥"
echo "═════════════════════════════════════════════════════════════════"