sed -i 's/clock: _clock,/_clock: clock,/g' crates/arkhe-soc-tlm/src/sram.rs
sed -i 's/aotb::{AotbEncoderHw, AotbVerifierHw}/aotb::AotbEncoderHw/g' crates/arkhe-soc-tlm/src/soc.rs
