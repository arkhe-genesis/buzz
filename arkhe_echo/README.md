# Arkhe Echo Phase 0 — Honest Bayesian Inference Engine

**Version:** v2.0
**Date:** 2026-08-05
**Status:** Reference implementation — not a detection claim

---

## What this is

A corrected, reproducible Bayesian inference pipeline for testing whether IXPE
polarization data from the magnetar 1E 1547.0-5408 supports an oscillatory
modulation beyond smooth QED vacuum birefringence.  This is the **honest**
version of the Phase 0 analysis, incorporating all the corrections identified
in the code review.

## What this is NOT

- A claim of detection.  The embedded data is **mock** (approximated from
  Taverna et al. 2025), not real IXPE FITS files.
- A first-principles QED calculation.  The QED model is phenomenological.
- A Windows binary.  The build scripts are provided; you must run them on
  your own infrastructure.

---

## Corrections vs. Previous Version

| Issue | v1 (Previous) | v2 (This) |
|---|---|---|
| Bayes Factor | WAIC pseudo-formula (`lnK ≈ ΔWAIC/2`) | LOO-CV via `arviz.loo` |
| Null-test | Claimed but not implemented | Actually implemented |
| Physics | Invented power-law phase integral | Simplified Adler-type QED phase |
| Data | Smooth exponential mock | Mock matched to Taverna et al. (2025) |
| Log entries | Fabricated | Only computed outputs |
| Self-test | Missing | Included with tolerance checks |

---

## Quick Start

### 1. Install dependencies (CPU-only)

```bash
pip install -r requirements.txt
```

### 2. Run inference on embedded mock data

```bash
python arkhe_inference_v2.py --output results.json
```

### 3. Run null-test calibration (pilot: 100 sims)

```bash
python arkhe_inference_v2.py --null-test --null-sims 100 --output results.json
```

### 4. Self-test (verify reproducibility)

```bash
python arkhe_inference_v2.py --self-test
```

---

## Model Specification

### H0 — Pure QED (smooth decay)

```
PD(E) = amplitude × exp(-(E - 2.0) / e_folding)
```

Priors:
- `amplitude` ~ TruncatedNormal(0.65, 0.10, [0, 1])
- `e_folding` ~ TruncatedNormal(2.5, 1.0, [0.5, ∞])
- `sigma_extra` ~ HalfNormal(0.05)

### H1 — QED + Arkhe modulation

```
phase(E) = (7α / 90π) × (B_s / B_crit)² × (E / m_e c²) × geom_factor
PD(E)    = PD_QED(E) × (1 + cos(Δφ₀ + C × phase(E))) / 2
```

Additional priors:
- `C` ~ Beta(1, 1)  [coupling constant]
- `Δφ₀` ~ VonMises(0, 0.1)  [initial phase]
- `geom_factor` ~ LogNormal(0, 1)  [line-of-sight geometry]

**Important:** H0 is nested inside H1 at C = 0.  This means a proper Bayes
Factor should penalize H1 for its extra parameters (Occam's razor).  LOO-CV
handles this automatically by measuring out-of-sample predictive accuracy.

---

## Model Comparison

We use **Pareto-smoothed importance-sampling LOO-CV** (PSIS-LOO) via ArviZ,
the modern standard for Bayesian model comparison.

The key metric is:

```
Δelpd = elpd_loo(H1) - elpd_loo(H0)
```

Interpretation (following Vehtari et al.):
- Δelpd > 2 × SE  → H1 preferred
- Δelpd < -2 × SE → H0 preferred
- |Δelpd| < 2 × SE → Inconclusive

**We do NOT report a Bayes Factor.**  LOO-CV is more robust than marginal
likelihood estimation for models with weak priors or misspecified likelihoods.

---

## Null-Test Protocol

The null-test generates synthetic datasets under H0 (pure QED) with realistic
Gaussian noise, fits both H0 and H1 to each, and records the Δelpd distribution.
This calibrates the false-positive rate.

**Computational cost:**
- 100 simulations × 2 models × 4 chains × 3000 steps ≈ 100 CPU-hours
- 1000 simulations ≈ 1000 CPU-hours (as noted in the original directive)

**Usage:**
```bash
# Pilot (100 sims)
python arkhe_inference_v2.py --null-test --null-sims 100

# Production (1000 sims — run on a cluster)
python arkhe_inference_v2.py --null-test --null-sims 1000
```

---

## Determinism & Reproducibility

### PARS Seed

The PRNG key is derived from the SHA-256 hash of a metadata string:

```python
key = pars_seed("IXPE_1E1547_5408_2025_Taverna")
```

This ensures identical chain initialization across runs.

### Limitations on Determinism

Even with fixed seeds, **bit-identical floating-point results are NOT
guaranteed** across:
- Different CPU vendors (Intel vs. AMD vs. ARM)
- Different JAX/XLA versions
- Different BLAS libraries (OpenBLAS vs. MKL)
- Parallel execution ordering

For strict reproducibility, pin:
- CPU architecture
- JAX/XLA version (done in requirements.txt)
- `JAX_PLATFORMS=cpu`
- `XLA_FLAGS=--xla_cpu_multi_thread_eigen=false`

---

## Building a Standalone Binary

### Linux (via Docker)

```bash
./build.sh linux
```

Produces `dist/arkhe_inference_v2.bin` (ELF) + manifest.

### Windows (native)

```bash
# On a Windows machine with Python 3.11 and Nuitka installed:
.\build.sh windows
```

Produces `dist/arkhe_inference_v2.exe` + manifest.

### Known Issues with Nuitka + JAX

JAX uses XLA (Accelerated Linear Algebra) which compiles operations at
runtime.  Nuitka's static analysis may not capture all dynamic imports.
If the binary fails at runtime:

1. Try PyInstaller instead of Nuitka:
   ```bash
   pip install pyinstaller
   pyinstaller --onefile arkhe_inference_v2.py
   ```

2. Or use `jax2tf` to convert the model to TensorFlow SavedModel, then
   bundle with TensorFlow Lite.

3. Or accept that a Python script + `requirements.txt` is more reliable
   than a bundled binary for JAX-based code.

---

## File Structure

```
arkhe_echo/
├── arkhe_inference_v2.py   # Main inference engine
├── requirements.txt        # Pinned dependencies
├── Dockerfile              # Linux build environment
├── build.sh                # Build script (Linux + Windows)
└── README.md               # This file
```

---

## References

1. Taverna et al. (2025). "X-ray polarimetry of 1E 1547.0-5408 with IXPE."
   *Astronomy & Astrophysics* (in press).
   Reports PD ~65% at 2 keV, dropping to ~20% at 4–6 keV.

2. Abu-Ajamieh (2026). "Detectability of QED vacuum birefringence using
   IXPE and eXTP."  Uses Adler integral for time-delay estimation.

3. Lai & Ho (2003). "Resonant conversion of photon modes in a magnetized
   vacuum." *Physical Review D*, 68, 104005.  Foundation for QED VB in
   magnetar magnetospheres.

4. Vehtari, Gelman, & Gabry (2017). "Practical Bayesian model evaluation
   using leave-one-out cross-validation and WAIC." *Statistics and Computing*.

5. Xiao et al. (2024). "Non-determinism of deterministic LLM settings."
   Documents sources of floating-point non-determinism in ML inference.

---

## License & Attribution

This is a reference implementation for reproducibility research.  If you use
this code, cite:

```
Arkhe Echo Phase 0 — Honest Bayesian Inference Engine (2026)
https://github.com/arkhe-project/echo-phase0
```

**No detection claims are made by this software.**  Any inference of a
"membrane" or "coupling constant" from real data requires:
- Access to actual IXPE FITS files
- Proper null-test calibration (≥1000 simulations)
- Peer review by the astrophysics community
- Comparison against first-principles atmospheric codes (e.g., MAGTHOMSCATT)

---

**Seal:** `ARKHE-ECHO-v2.0-HONEST-2026-08-05`
**Score:** N/A
