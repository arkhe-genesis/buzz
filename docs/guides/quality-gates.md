# Quality Gates & ASI-Grade Verification Strategy v2.0

This document outlines the commands and procedures used to verify Cathedral ARKHE ecosystem.

## Tooling Installation

To run the full suite locally, you need the following Cargo plugins:

```bash
cargo install cargo-llvm-cov cargo-insta cargo-deny cargo-audit cargo-semver-checks cargo-deadlinks cargo-sbom
```

## Running Checks Locally

### Pre-commit Checks

Run these before opening a Pull Request:

```bash
cargo xtask pre-commit
```

This includes formatting, code compilation checks, strict clippy lints, dependency checks (cargo deny + cargo audit), and fast unit test coverage.

### Snapshot Reviews

When running tests that use snapshot testing, if they fail because the snapshot needs to be updated, use:

```bash
cargo insta review
```

### CI and Full Audits

Run the full CI pipeline (including benchmarks, semver checks, full coverage, and snapshot tests):

```bash
cargo xtask ci
```

Run the exhaustive release audit:

```bash
cargo xtask full-audit
```

## Reading Coverage Reports

`cargo llvm-cov` generates LCOV files (`lcov.info`). You can visualize them using various LCOV tools or generate HTML directly:

```bash
cargo llvm-cov --workspace --html --output-dir target/coverage
```
