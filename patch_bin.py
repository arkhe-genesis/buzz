with open("crates/arkhe-soc-tlm/src/bin/main.rs", "r") as f:
    text = f.read()
text = text.replace("    let overhead = ((per_iter_us / REFERENCE_SOL_US) - 1.0) * 100.0;", "    let _overhead_wall = ((per_iter_us / REFERENCE_SOL_US) - 1.0) * 100.0;")
with open("crates/arkhe-soc-tlm/src/bin/main.rs", "w") as f:
    f.write(text)
