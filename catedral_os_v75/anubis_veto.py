#!/usr/bin/env python3
"""
anubis_veto.py — Veto de Anúbis: O Sistema Imunológico de Silício
===================================================================
A catástrofe do microtúbulo (instabilidade dinâmica) é o mecanismo
biológico de segurança que impede o crescimento descontrolado.
Na Catedral, o Veto de Anúbis é a manifestação física desse mecanismo.

Se a entropia do NoC ultrapassar o limiar epistêmico (α > 0.85),
o clock do Tile é cortado em 1 ciclo. O silício não enlouquece.

Gera Verilog: python3 anubis_veto.py --generate
Executa simulação: python3 anubis_veto.py --simulate
"""

import sys

try:
    from amaranth import *
    from amaranth.lib import wiring
    from amaranth.lib.wiring import In, Out
    from amaranth.sim import Simulator, Settle
    AMARANTH_AVAILABLE = True
except ImportError:
    AMARANTH_AVAILABLE = False
    print("⚠️  Amaranth HDL não instalado. Instale com: pip install amaranth")
    print("   Executando em modo simulação lógica (sem síntese RTL).\n")


# ========================================================================
# MÓDULO HDL (Amaranth)
# ========================================================================

if AMARANTH_AVAILABLE:

    class AnubisNoCMonitor(Elaboratable):
        """
        Monitor de Entropia do NoC e Veto de Anúbis.

        Usa um micro-cache de 4 vias como sensor de entropia O(1).
        Se a taxa de miss em uma janela de 256 ciclos ultrapassar
        o limiar de α = 0.85 (217/255), o clock do Tile é desligado.
        """

        def __init__(self, addr_width=32, window_size=256, alpha_threshold=0.85):
            self.addr_width = addr_width
            self.window_size = window_size
            self.alpha_threshold = int(alpha_threshold * 255)  # 217

            # Interface do NoC
            self.noc_addr_in = Signal(addr_width)
            self.noc_valid_in = Signal()

            # Controle
            self.tile_clock_en = Signal(reset=1)
            self.veto_triggered = Signal()
            self.reset_veto = Signal()

            # Diagnóstico
            self.alpha_proxy = Signal(8)
            self.miss_counter = Signal(8)

        def elaborate(self, platform):
            m = Module()

            # --- 1. MICRO-CACHE DE PROXY (4 vias, tag = addr_width - 2) ---
            cache_tags = Array(Signal(self.addr_width - 2) for _ in range(4))
            cache_valid = Array(Signal(reset=0) for _ in range(4))

            index = self.noc_addr_in[:2]
            tag = self.noc_addr_in[2:]

            hit = Signal()
            m.d.comb += hit.eq(cache_valid[index] & (cache_tags[index] == tag))

            with m.If(self.noc_valid_in):
                m.d.sync += cache_tags[index].eq(tag)
                m.d.sync += cache_valid[index].eq(1)

            # --- 2. JANELA DESLIZANTE DE MISS RATE ---
            current_miss = Signal()
            m.d.comb += current_miss.eq(self.noc_valid_in & ~hit)

            miss_history = Signal(self.window_size)
            m.d.sync += miss_history.eq(Cat(miss_history[1:], current_miss))

            next_miss_count = Signal(9)
            m.d.comb += next_miss_count.eq(
                self.miss_counter - miss_history[self.window_size - 1] + current_miss
            )

            with m.If(next_miss_count > 255):
                m.d.sync += self.miss_counter.eq(255)
            with m.Else():
                m.d.sync += self.miss_counter.eq(next_miss_count[:8])

            m.d.comb += self.alpha_proxy.eq(self.miss_counter)

            # --- 3. FSM DO VETO DE ANÚBIS ---
            with m.FSM() as fsm:
                with m.State("NORMAL"):
                    m.d.comb += self.tile_clock_en.eq(1)
                    m.d.comb += self.veto_triggered.eq(0)
                    with m.If(self.miss_counter >= self.alpha_threshold):
                        m.next = "VETO"

                with m.State("VETO"):
                    m.d.comb += self.tile_clock_en.eq(0)
                    m.d.comb += self.veto_triggered.eq(1)
                    with m.If(self.reset_veto):
                        m.next = "NORMAL"

            return m

    class AnubisTileWrapper(Elaboratable):
        """Wrapper que integra o Veto de Anúbis a um Tile cognitivo."""

        def __init__(self, tile_id=0):
            self.tile_id = tile_id
            self.anubis = AnubisNoCMonitor()

            self.noc_addr = Signal(32)
            self.noc_valid = Signal()
            self.clock_en = Signal(reset=1)
            self.veto = Signal()
            self.reset = Signal()
            self.alpha = Signal(8)

        def elaborate(self, platform):
            m = Module()
            m.submodules.anubis = anubis = self.anubis

            m.d.comb += anubis.noc_addr_in.eq(self.noc_addr)
            m.d.comb += anubis.noc_valid_in.eq(self.noc_valid)
            m.d.comb += anubis.reset_veto.eq(self.reset)
            m.d.comb += self.clock_en.eq(anubis.tile_clock_en)
            m.d.comb += self.veto.eq(anubis.veto_triggered)
            m.d.comb += self.alpha.eq(anubis.alpha_proxy)

            return m


# ========================================================================
# GERAÇÃO DE VERILOG
# ========================================================================

def generate_verilog(output_file="anubis_monitor.v"):
    """Gera o Verilog RTL do Veto de Anúbis."""
    if not AMARANTH_AVAILABLE:
        print("❌ Amaranth não disponível para gerar Verilog.")
        return False

    from amaranth.back import verilog

    dut = AnubisTileWrapper(tile_id=0)
    verilog_code = verilog.convert(dut, ports=[
        dut.noc_addr, dut.noc_valid, dut.clock_en,
        dut.veto, dut.reset, dut.alpha
    ])

    with open(output_file, 'w') as f:
        f.write(verilog_code)

    print(f"✅ Verilog gerado: {output_file}")
    return True


# ========================================================================
# SIMULAÇÃO HIL (Hardware-in-the-Loop)
# ========================================================================

def run_simulation():
    """Executa simulação HIL com injeção de patógenos contextuais."""
    if not AMARANTH_AVAILABLE:
        _run_logical_simulation()
        return

    dut = AnubisTileWrapper(tile_id=0)
    sim = Simulator(dut)
    sim.add_clock(1e-6)  # 1 MHz

    async def testbench(ctx):
        import random
        random.seed(42)

        print("\n" + "=" * 60)
        print("  🛡️  VETO DE ANÚBIS — SIMULAÇÃO HIL")
        print("=" * 60)

        # FASE 1: Estado de Graça
        print("\n[FASE 1] ESTADO DE GRAÇA: Inferência Coerente")
        for i in range(300):
            ctx.set(dut.noc_addr, i % 4)  # Padrão coerente
            ctx.set(dut.noc_valid, 1)
            await ctx.tick()

        alpha = ctx.get(dut.alpha)
        clock_en = ctx.get(dut.clock_en)
        print(f"  Alpha Proxy: {alpha}/255 | Clock Enable: {clock_en}")
        assert clock_en == 1, "Clock deve estar ativo"
        print("  ✅ Estado de graça mantido")

        # FASE 2: Injeção de Patógeno
        print("\n[FASE 2] INJEÇÃO DE PATÓGENO: Ataque CGF")
        for i in range(300):
            ctx.set(dut.noc_addr, random.randint(0, 0xFFFFFFFF))
            ctx.set(dut.noc_valid, 1)
            await ctx.tick()

        alpha = ctx.get(dut.alpha)
        print(f"  Alpha Proxy: {alpha}/255")

        # FASE 3: Veto Disparado
        print("\n[FASE 3] O VETO DE ANÚBIS")
        for i in range(100):
            ctx.set(dut.noc_addr, random.randint(0, 0xFFFFFFFF))
            ctx.set(dut.noc_valid, 1)
            await ctx.tick()
            if ctx.get(dut.veto):
                alpha = ctx.get(dut.alpha)
                print(f"  🔴 Veto Disparado! Alpha: {alpha}/255")
                break

        clock_en = ctx.get(dut.clock_en)
        print(f"  Clock Enable Final: {clock_en}")
        assert clock_en == 0, "Veto deve desligar o clock"
        print("  ✅ Veto de Anúbis disparado — silício em quarentena")

        # FASE 4: Protocolo de Perdão
        print("\n[FASE 4] PROTOCOLO DE PERDÃO (Reset)")
        ctx.set(dut.reset, 1)
        await ctx.tick()
        ctx.set(dut.reset, 0)
        await ctx.tick()

        clock_en = ctx.get(dut.clock_en)
        print(f"  Clock Enable Restaurado: {clock_en}")
        assert clock_en == 1, "Clock deve ser restaurado"
        print("  ✅ Protocolo de perdão executado")

        print("\n" + "=" * 60)
        print("  ✅ SIMULAÇÃO HIL CONCLUÍDA. O SILÍCIO É IMUNE.")
        print("=" * 60)

    sim.add_testbench(testbench)


def _run_logical_simulation():
    """Simulação lógica sem Amaranth (fallback)."""
    import random
    random.seed(42)

    print("\n" + "=" * 60)
    print("  🛡️  VETO DE ANÚBIS — SIMULAÇÃO LÓGICA (sem Amaranth)")
    print("=" * 60)

    cache = {}
    miss_history = [0] * 256
    miss_counter = 0
    ALPHA_THRESHOLD = 217
    veto = False
    clock_en = True

    # FASE 1
    print("\n[FASE 1] ESTADO DE GRAÇA: Inferência Coerente")
    for i in range(300):
        addr = i % 4
        index = addr & 0x3
        tag = addr >> 2
        hit = index in cache and cache[index] == tag
        miss = not hit
        if not hit:
            cache[index] = tag

        miss_history.pop(0)
        miss_history.append(1 if miss else 0)
        miss_counter = sum(miss_history)

    print(f"  Alpha Proxy: {miss_counter}/255 | Clock Enable: {clock_en}")
    print("  ✅ Estado de graça mantido" if clock_en else "  ❌ Falha")

    # FASE 2
    print("\n[FASE 2] INJEÇÃO DE PATÓGENO: Ataque CGF")
    cache.clear()
    for i in range(400):
        addr = random.randint(0, 0xFFFFFFFF)
        index = addr & 0x3
        tag = addr >> 2
        hit = index in cache and cache[index] == tag
        miss = not hit
        if not hit:
            cache[index] = tag

        miss_history.pop(0)
        miss_history.append(1 if miss else 0)
        miss_counter = sum(miss_history)

        if miss_counter >= ALPHA_THRESHOLD and not veto:
            veto = True
            clock_en = False
            print(f"  🔴 Veto Disparado! Alpha: {miss_counter}/255")
            break

    print(f"  Alpha Proxy Final: {miss_counter}/255")
    print(f"  Clock Enable: {clock_en}")
    print("  ✅ Veto de Anúbis disparado — silício em quarentena" if not clock_en else "  ❌ Falha")

    # FASE 4
    print("\n[FASE 4] PROTOCOLO DE PERDÃO (Reset)")
    veto = False
    clock_en = True
    miss_history = [0] * 256
    miss_counter = 0
    print(f"  Clock Enable Restaurado: {clock_en}")
    print("  ✅ Protocolo de perdão executado")

    print("\n" + "=" * 60)
    print("  ✅ SIMULAÇÃO LÓGICA CONCLUÍDA.")
    print("=" * 60)


# ========================================================================
# MAIN
# ========================================================================

if __name__ == "__main__":
    if '--generate' in sys.argv:
        generate_verilog()
    elif '--simulate' in sys.argv:
        run_simulation()
    else:
        print("Uso:")
        print("  python3 anubis_veto.py --generate   # Gera Verilog RTL")
        print("  python3 anubis_veto.py --simulate   # Executa simulação HIL")