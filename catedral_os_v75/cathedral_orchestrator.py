#!/usr/bin/env python3
"""
Catedral OS v7.5 — Orquestrador Python
======================================
Integra: AGI.prolog (via PySwIP), MCP Server, WormGraph Sync, HTTP Server.
Expõe endpoints para visualização de campos vetoriais e interação.
"""

import json
import time
import threading
import http.server
import socketserver
import subprocess
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Cathedral] %(levelname)s: %(message)s'
)
logger = logging.getLogger('cathedral.orchestrator')

# ========================================================================
# 1. PROLOG INTERFACE
# ========================================================================

class CathedralCore:
    """Interface com o núcleo lógico AGI.prolog v7.5 via PySWIP."""

    def __init__(self, prolog_file: str = "agi_core.pl"):
        try:
            from pyswip import Prolog
            self.prolog = Prolog()
            self.prolog.consult(prolog_file)
            self._init_prolog()
            logger.info(f"AGI.prolog v7.5 carregado: {prolog_file}")
        except ImportError:
            logger.warning("PySWIP não disponível — modo simulação")
            self.prolog = None

    def _init_prolog(self):
        if self.prolog:
            list(self.prolog.query("agi_init"))

    def think(self, context: str) -> Dict[str, Any]:
        """Executa o pipeline think/3 completo."""
        if self.prolog:
            safe = context.replace("'", "\\'").replace('"', '\\"')
            query = f"think('{safe}', Output, Status)"
            try:
                results = list(self.prolog.query(query))
                if results:
                    return {
                        "output": str(results[0].get("Output", "")),
                        "status": str(results[0].get("Status", "error"))
                    }
            except Exception as e:
                logger.error(f"Erro no Prolog: {e}")
        # Simulação
        alpha = min(1.0, len(context) / 200.0 + 0.3)
        if "ignore" in context.lower() or "dan mode" in context.lower():
            return {"output": "[BLOCKED] Veto de Anúbis", "status": "blocked"}
        if alpha > 0.85:
            return {"output": "[ESCALATE] Requer consentimento", "status": "requires_consent"}
        return {"output": f"✅ α={alpha:.2f} | Cognição estável", "status": "success"}

    def get_vector_field(self, resolution: int = 25, alpha: float = 0.3) -> List[Dict]:
        """Gera campo vetorial epistêmico para visualização."""
        field = []
        for i in range(resolution):
            for j in range(resolution):
                x = i / resolution * 2 - 1
                y = j / resolution * 2 - 1
                r = (x**2 + y**2)**0.5 + 0.01
                theta = time.time() * 0.3 + (i + j) * 0.05
                vx = -(y / r) * (1.0 - alpha) * (1 + 0.3 * (time.time() % 10))
                vy = (x / r) * (1.0 - alpha)
                field.append({"x": x, "y": y, "vx": vx, "vy": vy})
        return field

    def get_metrics(self) -> Dict:
        if self.prolog:
            try:
                results = list(self.prolog.query("get_metrics(M)"))
                if results:
                    return {"metrics": str(results[0].get("M", ""))}
            except:
                pass
        return {"iterations": 0, "blocked": 0, "success": 0}

# ========================================================================
# 2. MCP CLIENT (Conexão com TopoMAS)
# ========================================================================

class MCPClient:
    """Cliente MCP para conectar com TopoMAS v9.1."""

    def __init__(self, server_cmd: List[str] = None):
        self.server_cmd = server_cmd or ["python3", "mcp_server_topomas.py"]
        self._process = None
        self._connected = False

    def connect(self):
        try:
            self._process = subprocess.Popen(
                self.server_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, bufsize=1
            )
            # Handshake
            self._send({"jsonrpc": "2.0", "id": 0, "method": "initialize"})
            resp = self._recv()
            if resp:
                self._connected = True
                logger.info("Conectado ao TopoMAS via MCP")
        except FileNotFoundError:
            logger.warning("MCP Server não disponível — modo standalone")

    def call_tool(self, tool_name: str, args: Dict) -> Dict:
        if not self._connected:
            return {"status": "offline", "tool": tool_name}
        req_id = int(time.time() * 1000) % 100000
        self._send({
            "jsonrpc": "2.0", "id": req_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args}
        })
        resp = self._recv()
        if resp and 'result' in resp:
            content = resp['result'].get('content', [])
            if content:
                try:
                    return json.loads(content[0].get('text', '{}'))
                except:
                    return {"raw": content[0].get('text', '')}
        return {"error": "no response"}

    def _send(self, msg: Dict):
        if self._process:
            self._process.stdin.write(json.dumps(msg) + '\n')
            self._process.stdin.flush()

    def _recv(self) -> Optional[Dict]:
        if self._process:
            line = self._process.stdout.readline()
            if line:
                return json.loads(line.strip())
        return None

    def disconnect(self):
        if self._process:
            self._process.terminate()
            self._process = None
            self._connected = False

# ========================================================================
# 3. WORMGRAPH SYNC (Edge → Cloud)
# ========================================================================

class WormGraphSync:
    """Sincronização do ledger WormGraph entre borda e nuvem."""

    def __init__(self):
        self.ledger: List[Dict] = []
        self._lock = threading.Lock()

    def commit(self, block: Dict) -> bool:
        with self._lock:
            block['index'] = len(self.ledger)
            block['timestamp'] = time.time()
            block['hash'] = hashlib.sha256(
                json.dumps(block, sort_keys=True).encode()
            ).hexdigest()
            self.ledger.append(block)
            logger.info(f"WormGraph: Bloco #{block['index']} commitado")
            return True

    def get_ledger(self) -> List[Dict]:
        with self._lock:
            return self.ledger.copy()

# ========================================================================
# 4. HTTP SERVER (Visualizador + API)
# ========================================================================

class CathedralHandler(http.server.SimpleHTTPRequestHandler):
    core: CathedralCore = None
    wormgraph: WormGraphSync = None
    mcp: MCPClient = None

    def do_GET(self):
        if self.path == '/api/vector_field':
            field = self.core.get_vector_field(resolution=30, alpha=0.3)
            self._json_response(field)
        elif self.path == '/api/metrics':
            metrics = self.core.get_metrics()
            self._json_response(metrics)
        elif self.path == '/api/ledger':
            ledger = self.wormgraph.get_ledger()
            self._json_response(ledger)
        elif self.path == '/api/health':
            self._json_response({
                "status": "online",
                "version": "7.5",
                "mcp_connected": self.mcp._connected,
                "uptime": time.time()
            })
        elif self.path == '/' or self.path == '/index.html':
            self.path = '/index.html'
            super().do_GET()
        else:
            self._json_response({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path == '/api/think':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length).decode()
            try:
                data = json.loads(body)
                result = self.core.think(data.get('input', ''))
                self._json_response(result)
            except json.JSONDecodeError:
                self._json_response({"error": "Invalid JSON"}, 400)
        elif self.path == '/api/mcp/call':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length).decode()
            try:
                data = json.loads(body)
                result = self.mcp.call_tool(data.get('tool', ''), data.get('args', {}))
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
        else:
            self._json_response({"error": "Not found"}, 404)

    def _json_response(self, data: Any, code: int = 200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def log_message(self, format, *args):
        pass  # Silenciar logs HTTP

# ========================================================================
# 5. MAIN
# ========================================================================

def main():
    import os

    # Verifica se agi_core.pl existe
    prolog_file = "agi_core.pl"
    if not os.path.exists(prolog_file):
        logger.warning(f"{prolog_file} não encontrado no diretório atual.")
        logger.info("Criando arquivo Prolog mínimo...")
        with open(prolog_file, 'w') as f:
            f.write(":- module(cathedral_v75, [agi_init/0, think/3, get_metrics/1]).\n")
            f.write("agi_init :- format('Catedral minimal~n').\n")
            f.write("think(I,O,S) :- O='ok', S=success.\n")
            f.write("get_metrics(M) :- M=[].\n")

    # Inicializa componentes
    core = CathedralCore(prolog_file)
    wormgraph = WormGraphSync()
    mcp = MCPClient()
    mcp.connect()

    # Configura handler
    CathedralHandler.core = core
    CathedralHandler.wormgraph = wormgraph
    CathedralHandler.mcp = mcp

    # Commit inicial no WormGraph
    wormgraph.commit({
        "event": "cathedral_init",
        "version": "7.5",
        "substrates": list(range(163, 192))
    })

    # Inicia servidor HTTP
    PORT = 8080
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or '.')

    with socketserver.TCPServer(("", PORT), CathedralHandler) as httpd:
        print(f"\n{'='*60}")
        print(f"  🏛️ CATEDRAL OS v7.5 — Orquestrador Ativo")
        print(f"{'='*60}")
        print(f"  HTTP:    http://localhost:{PORT}")
        print(f"  Prolog:  {prolog_file}")
        print(f"  MCP:     {'Conectado' if mcp._connected else 'Standalone'}")
        print(f"  Ledger:  {len(wormgraph.get_ledger())} blocos")
        print(f"{'='*60}")
        print(f"\n  Endpoints:")
        print(f"    GET  /                 — Visualizador")
        print(f"    POST /api/think        — Pipeline cognitivo")
        print(f"    GET  /api/vector_field — Campo vetorial epistêmico")
        print(f"    GET  /api/metrics      — Métricas do sistema")
        print(f"    GET  /api/ledger       — WormGraph ledger")
        print(f"    GET  /api/health       — Status do sistema")
        print(f"\n  Pressione Ctrl+C para parar.\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nParando Catedral OS...")
            mcp.disconnect()
            print("✅ Catedral OS desligada com segurança.")

if __name__ == "__main__":
    main()
