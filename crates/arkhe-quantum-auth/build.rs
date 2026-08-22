use std::env;

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-env-changed=ARKHE_QUANTUM_AUTH_FORCE_NO_STD");

    let target_arch = env::var("CARGO_CFG_TARGET_ARCH").unwrap_or_default();
    let target_os = env::var("CARGO_CFG_TARGET_OS").unwrap_or_default();

    // Detect hardware crypto acceleration
    if target_arch == "x86_64" || target_arch == "x86" {
        println!("cargo:rustc-cfg=target_has_aesni");
    }
    if target_arch == "aarch64" {
        println!("cargo:rustc-cfg=target_has_neon_aes");
    }

    // Validate mutually exclusive features
    let features: Vec<String> = env::vars()
        .filter(|(k, _)| k.starts_with("CARGO_FEATURE_"))
        .map(|(k, _)| k.strip_prefix("CARGO_FEATURE_").unwrap().to_lowercase())
        .collect();

    if features.iter().any(|s| s == "std") && features.iter().any(|s| s == "no_std") {
        println!("cargo:warning=arkhe-quantum-auth: cannot enable both `std` and `no_std` features. Defaulting to std.");
    }

    // no_std builds require an allocator
    if features.iter().any(|s| s == "no_std") && !features.iter().any(|s| s == "alloc") {
        panic!("arkhe-quantum-auth: `no_std` feature requires `alloc`");
    }

    // Warn if building for unknown no_std target without custom getrandom
    if features.iter().any(|s| s == "no_std") && target_os != "none" && target_os != "linux" {
        println!("cargo:warning=Building no_std for target_os={}. Ensure custom getrandom impl is provided.", target_os);
    }

    // If arkhe-pea feature is enabled, verify arkhe-core is available
    if features.iter().any(|s| s == "arkhe_pea") && !features.iter().any(|s| s == "arkhe_core") {
        println!("cargo:warning=arkhe-pea integration recommended with arkhe-core DID types");
    }
}
