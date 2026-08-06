# Arkhe Echo Phase 0 — Deterministic Build Environment
# Base: Debian Bookworm with Python 3.11
# Build command: docker build -t arkhe-echo-builder .

FROM python:3.11.9-slim-bookworm

# Prevent interactive prompts during apt
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=0

# Install system dependencies for JAX/NumPyro and Nuitka
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy and install Python dependencies FIRST (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Nuitka (build-time only)
RUN pip install --no-cache-dir nuitka==2.6.9

# Copy source code
COPY arkhe_inference_v2.py .

# Build flags for reproducibility:
#   --standalone      : bundle the Python interpreter
#   --onefile         : single executable
#   --windows-console-mode=disable : no console window (GUI mode)
#   --no-pyi-file     : no type-stub generation
#   --disable-ccache  : disable ccache for deterministic builds
#   --lto=yes         : link-time optimization
#   --jobs=4          : parallel compilation
#
# NOTE: This Dockerfile targets Linux.  For Windows PE output, you need
#       a Windows host or cross-compilation (not supported by Nuitka).
#       The command below produces a Linux ELF binary.

RUN python -m nuitka \
    --standalone \
    --onefile \
    --no-pyi-file \
    --disable-ccache \
    --lto=yes \
    --jobs=4 \
    --output-dir=dist \
    arkhe_inference_v2.py

# The binary will be at /build/dist/arkhe_inference_v2.bin
# (Linux ELF).  For Windows, see build_windows.sh.
