# Fix tlm clippy
sed -i 's/epoch: Instant,/_epoch: Instant,/g' crates/arkhe-soc-tlm/src/lib.rs
sed -i 's/epoch: Instant::now()/_epoch: Instant::now()/g' crates/arkhe-soc-tlm/src/lib.rs
sed -i 's/clock: ClockDomain,/_clock: ClockDomain,/g' crates/arkhe-soc-tlm/src/sram.rs
sed -i 's/clock: clock,/_clock: clock,/g' crates/arkhe-soc-tlm/src/sram.rs
sed -i 's/for i in 0..DOMAIN_NODES {/for (i, result) in results.iter_mut().enumerate().take(DOMAIN_NODES) {/g' crates/arkhe-soc-tlm/src/qpl.rs
sed -i 's/results\[i\] = QplResult { node: i, input, output };/*result = QplResult { node: i, input, output };/g' crates/arkhe-soc-tlm/src/qpl.rs
sed -i 's/for i in 0..DOMAIN_NODES {/for (i, val) in values.iter_mut().enumerate().take(DOMAIN_NODES) {/g' crates/arkhe-soc-tlm/src/soc.rs
sed -i 's/values\[i\] = self.sram.read_domain_d(i as u8).unwrap_or(0.0);/*val = self.sram.read_domain_d(i as u8).unwrap_or(0.0);/g' crates/arkhe-soc-tlm/src/soc.rs

cat << 'EOF2' > patch_soc.py
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
EOF2
python3 patch_soc.py

sed -i 's/for i in 0..DOMAIN_NODES {/for (i, weight) in weights.iter().enumerate().take(DOMAIN_NODES) {/g' crates/arkhe-soc-tlm/src/sram.rs
sed -i 's/let weight = f64::from(weights\[i\]) \/ 100.0;/let weight = f64::from(*weight) \/ 100.0;/g' crates/arkhe-soc-tlm/src/sram.rs

cat << 'EOF2' > patch_bin.py
with open("crates/arkhe-soc-tlm/src/bin/main.rs", "r") as f:
    text = f.read()
text = text.replace("    let overhead = ((per_iter_us / REFERENCE_SOL_US) - 1.0) * 100.0;", "    let _overhead_wall = ((per_iter_us / REFERENCE_SOL_US) - 1.0) * 100.0;")
with open("crates/arkhe-soc-tlm/src/bin/main.rs", "w") as f:
    f.write(text)
EOF2
python3 patch_bin.py

# Ignore security vulnerabilities
cargo update -p nostr-relay-pool@0.44.1
cargo update -p webbrowser
