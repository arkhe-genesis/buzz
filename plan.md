1. **Analyze User Request**: The user wants to integrate a provided Rust crate (`arkhe-vision`) into the existing monorepo. This involves creating a new crate inside `crates/arkhe-vision`.
2. **Setup Crate**:
    - `crates/arkhe-vision/Cargo.toml` with the specified dependencies (e.g., `ort`, `tch`, `image`, etc.).
    - `crates/arkhe-vision/src/lib.rs` with the provided code.
    - Add `crates/arkhe-vision` to the workspace `Cargo.toml`.
3. **Fix Compilation Errors**:
    - The provided code was outdated regarding the `ort`, `ndarray`, and `tch` APIs.
    - Update `Cargo.toml` to compatible versions (`ort 2.0.0-rc.9`, `ndarray 0.17`, `tch 0.14`).
    - Adjust `tch::Tensor` methods (`from_slice` instead of `of_slice`, `forward_ts` instead of `forward`, `Cuda(0)` instead of `Cuda`).
    - Adjust `ort` API calls (e.g., `Value::from_array`, `session.run(inputs)`).
    - Handle asynchronous borrowing (`Mutex` instead of raw refs) for `ort::Session`.
    - Fix prometheus metric instantiations.
    - Add custom `bytes` serializer `bytes_serde` for `SegmentationMask`.
4. **Pre-commit Checks**: Run tests `cargo test -p arkhe-vision` and any monorepo linting to ensure it works cleanly. Run `pre_commit_instructions` and follow them.
5. **Submit Code**: Commit the changes.
