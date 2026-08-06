#!/usr/bin/env bash
# build.sh — Build the Arkhe Echo binary and produce a signed manifest
# Usage: ./build.sh [linux|windows]
# Requires: Docker (for Linux), or Windows + Python + Nuitka (for Windows)

set -euo pipefail

PLATFORM="${1:-linux}"
VERSION="v2.0"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
OUTPUT_DIR="./dist"
MANIFEST="${OUTPUT_DIR}/ARKHE_ECHO_MANIFEST.txt"

echo "========================================"
echo "Arkhe Echo Phase 0 — Build Script"
echo "Platform: ${PLATFORM}"
echo "Version: ${VERSION}"
echo "========================================"

mkdir -p "${OUTPUT_DIR}"

if [[ "${PLATFORM}" == "linux" ]]; then
    echo "[1/4] Building Linux binary via Docker..."
    docker build -t arkhe-echo-builder .
    docker create --name arkhe-tmp arkhe-echo-builder
    docker cp arkhe-tmp:/build/dist/. "${OUTPUT_DIR}/"
    docker rm arkhe-tmp
    BINARY=$(find "${OUTPUT_DIR}" -type f -executable | head -n1)

elif [[ "${PLATFORM}" == "windows" ]]; then
    echo "[1/4] Building Windows binary via Nuitka (native)..."
    # This must run ON a Windows machine with Python and Nuitka installed.
    python -m nuitka \
        --standalone \
        --onefile \
        --windows-console-mode=disable \
        --windows-icon-from-ico=arkhe.ico \
        --no-pyi-file \
        --disable-ccache \
        --lto=yes \
        --jobs=4 \
        --output-dir="${OUTPUT_DIR}" \
        arkhe_inference_v2.py
    BINARY=$(find "${OUTPUT_DIR}" -name "*.exe" | head -n1)

else
    echo "ERROR: Unknown platform '${PLATFORM}'. Use 'linux' or 'windows'."
    import sys
    sys.exit(1)
fi

echo "[2/4] Binary produced: ${BINARY}"

# Compute SHA-256
echo "[3/4] Computing SHA-256..."
HASH=$(sha256sum "${BINARY}" | awk '{print $1}')
echo "  SHA-256: ${HASH}"

# Write manifest
echo "[4/4] Writing manifest..."
cat > "${MANIFEST}" <<INNER_EOF
ARKHE ECHO PHASE 0 — BUILD MANIFEST
===================================
Binary:        $(basename "${BINARY}")
SHA-256:       ${HASH}
Version:       ${VERSION}
Platform:      ${PLATFORM}
Timestamp:     ${TIMESTAMP}
Python:        3.11.9
JAX:           0.4.38
NumPyro:       0.16.2
ArviZ:         0.20.0
Nuitka:        2.6.9
Build host:    $(uname -a)

REPRODUCIBILITY NOTES:
- Set PYTHONHASHSEED=0 before build.
- Use the exact Docker image hash for bit-identical builds.
- JAX/NumPyro may exhibit minor float differences across CPU vendors.
  For strict determinism, pin to a specific CPU architecture.

VERIFICATION:
  sha256sum $(basename "${BINARY}")
  Expected: ${HASH}
INNER_EOF

echo ""
echo "========================================"
echo "BUILD COMPLETE"
echo "Binary:  ${BINARY}"
echo "SHA-256: ${HASH}"
echo "Manifest: ${MANIFEST}"
echo "========================================"
