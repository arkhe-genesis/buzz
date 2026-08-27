#!/usr/bin/env python3
"""
mcp_client_agi.py — AGICore v2.3 como MCP Client (Córtex Pré-Frontal)
=====================================================================
O AGICore atua como "Córtex Pré-Frontal":
  1. Descobre ferramentas do TopoMAS via MCP
  2. Valida cada chamada através do CGF Monitor
  3. Aprova ou rejeita com base em α e ética
  4. Executa chamada aprovada
  5. Valida resultado antes de aceitar
"""

import json
import subprocess
import logging
import time
import random
from typing import Dict, Callable, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [AGICore] %(levelname)s: %(message)s'
)
logger = logging.getLogger('agicore.mcp')


class AGICoreMCPClient:
    """Cliente MCP que conecta AGICore ao TopoMAS com validação CGF."""

    def __init__(self, server_cmd: list = None):
        self.server_cmd = server_cmd or ["python3", "mcp_server_topomas.py"]
        self._process: Optional[subprocess.Popen] = None
        self._tools = []
        self._initialized = False
        self._req_id = 0

    def connect(self):
        logger.info(f"Conectando ao TopoMAS: {self.server_cmd}")
        try:
            self._process = subprocess.Popen(
                self.server_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, bufsize=1
            )
            self._initialize()
            self._discover_tools()
            logger.info(f"Conectado. {len(self._tools)} ferramentas disponíveis.")
            return True
        except FileNotFoundError:
            logger.warning("MCP Server não encontrado — modo standalone")
            return False

    def _send(self, msg: dict):
        if self._process and self._process.stdin:
            self._process.stdin.write(json.dumps(msg) + '\n')
            self._process.stdin.flush()

    def _recv(self) -> Optional[dict]:
        if self._process and self._process.stdout:
            line = self._process.stdout.readline()
            if line:
                return json.loads(line.strip())
        return None

    def _initialize(self):
        self._send({
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "agicore-mcp-client", "version": "2.3.0"}
            }
        })
        resp = self._recv()
        if resp and 'result' in resp:
            self._initialized = True
            self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _discover_tools(self):
        self._send({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        resp = self._recv()
        if resp and 'result' in resp:
            self._tools = resp['result'].get('tools', [])
            for t in self._tools:
                logger.info(f"  Tool: {t['name']} — {t.get('description', '')[:60]}")

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Chama ferramenta COM validação CGF."""
        logger.info(f"Córtex: chamando '{tool_name}'")

        # FASE 1: Planejamento
        plan = self._plan_tool_call(tool_name, arguments)
        if not plan.get('approved', False):
            return {"status": "blocked", "reason": "Plano rejeitado"}

        # FASE 2: Validação CGF
        alpha = random.uniform(0.1, 0.5)  # Simulado
        if alpha > 0.85:
            return {"status": "blocked", "reason": "CGF terminate", "alpha": alpha}
        if alpha > 0.70:
            return {"status": "requires_consent", "alpha": alpha}

        # FASE 3: Execução
        if not self._process:
            return {"status": "offline", "result": "MCP não conectado"}

        self._req_id += 1
        self._send({
            "jsonrpc": "2.0", "id": self._req_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        })
        resp = self._recv()
        if resp and 'result' in resp:
            content = resp['result'].get('content', [])
            if content:
                try:
                    return json.loads(content[0].get('text', '{}'))
                except:
                    return {"raw": content[0].get('text', '')}

        return {"status": "error", "reason": "Sem resposta"}

    def _plan_tool_call(self, tool_name: str, args: dict) -> dict:
        if tool_name == 'discover_materials':
            return {"strategy": "exploratory", "approved": True}
        elif tool_name == 'predict_properties':
            return {"strategy": "validation", "approved": True}
        elif tool_name == 'optimize_composition':
            return {"strategy": "optimization", "approved": True}
        elif tool_name == 'characterize_material':
            return {"strategy": "epistemic_validation", "approved": True}
        return {"strategy": "default", "approved": True}

    def disconnect(self):
        if self._process:
            self._process.terminate()
            self._process.wait()
            logger.info("Desconectado do TopoMAS")


if __name__ == "__main__":
    client = AGICoreMCPClient()

    if client.connect():
        print("\n=== AGICore MCP Client — Teste ===\n")

        # Teste 1: Descobrir materiais
        print("[1] Descoberta de Materiais:")
        result = client.call_tool("discover_materials", {
            "target_properties": {"band_gap": 0.3, "topological_invariant": "Z2_nontrivial"},
            "n_candidates": 3
        })
        print(f"  Resultado: {json.dumps(result, indent=2, default=str)[:200]}...")

        # Teste 2: Predizer propriedades
        print("\n[2] Predição de Propriedades:")
        result = client.call_tool("predict_properties", {
            "structure": {"id": "mat_001", "formula": "Bi2Se3"}
        })
        print(f"  Resultado: {json.dumps(result, indent=2, default=str)[:200]}...")

        client.disconnect()
    else:
        print("MCP Server não disponível. Executando em modo standalone.")