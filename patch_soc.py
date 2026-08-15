with open("crates/arkhe-soc-tlm/src/soc.rs", "r") as f:
    text = f.read()
text = text.replace("""        let mut c = PerformanceCounters::default();
        c.qpl_cycles = self.qpl.counters.qpl_cycles;
        c.expand_cycles = self.qpl.counters.expand_cycles;
        c.power_mw = self.power.estimate_power_mw();
        c""", """        PerformanceCounters {
            qpl_cycles: self.qpl.counters.qpl_cycles,
            expand_cycles: self.qpl.counters.expand_cycles,
            power_mw: self.power.estimate_power_mw(),
            ..Default::default()
        }""")
with open("crates/arkhe-soc-tlm/src/soc.rs", "w") as f:
    f.write(text)
