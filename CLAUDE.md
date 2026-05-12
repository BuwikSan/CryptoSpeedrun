# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running Code

No build step. Run directly with Python 3.x:

```bash
# ML-KEM demo
python code/src/ml_kem.py

# Hill cipher demo
python code/src/Hill_Cypher.py

# Jupyter notebooks
jupyter notebook code/ML_KEM_Demo.ipynb
jupyter notebook code/Hill_Cypher_Demo.ipynb
```

Dependencies:
- `ml_kem.py` — stdlib only (`hashlib`, `os`)
- `Hill_Cypher.py` — `numpy`, `sympy`

## Architecture

### ML-KEM (`code/src/ml_kem.py`)

From-scratch NIST FIPS 203 ML-KEM-512 impl. Two-layer design:

**Layer 1 — K-PKE** (IND-CPA): Internal encryption primitive. `_pke_keygen / _pke_encrypt / _pke_decrypt`. Operates on module vectors of polynomials in `Z_3329[X]/(X^256+1)`.

**Layer 2 — ML-KEM** (IND-CCA2): Public API wrapping K-PKE via Fujisaki-Okamoto transform. `keygen / encaps / decaps`. `decaps` never signals failure — returns `J(z, c)` on mismatch (implicit rejection).

**Polynomial arithmetic**: All poly multiplication goes through NTT (`ntt` / `intt` / `_mul_ntt`). ZETAS and GAMMAS are precomputed twiddle factors using `17` as primitive 512th root of unity mod 3329.

**Key layout** (K=2 / ML-KEM-512):
- `ek` (encapsulation key): 800 B = `t_hat[0..K]` (384B each) + `rho` (32B)
- `dk` (decapsulation key): 1632 B = `dk_pke` (768B) + `ek` (800B) + `H(ek)` (32B) + `z` (32B)
- Ciphertext: 768 B = `c1` (640B, compressed at DU=10 bits) + `c2` (128B, DV=4 bits)

**Text encryption** (`encrypt_text / decrypt_text`): Hybrid scheme — ML-KEM key agreement + SHAKE-256 stream cipher.

### Hill Cipher (`code/src/Hill_Cypher.py`)

Czech-alphabet Hill cipher (43-char alphabet: diacritics + space + period). `Hills_cypher` supports multiple rounds, arbitrary key length. Keys inverted mod 43 via sympy `Matrix.inv_mod`. Padding uses `Q`; length tracked in `self.padding_length` so `decypher` trims correctly.

## Documentation

All `ML_KEM_*.md` files in Czech:
- `ML_KEM_SIMPLE.md` — conceptual overview
- `ML_KEM_EXPLANATION.md` — line-by-line walkthrough
- `ML_KEM_MATH.md` — math foundations (ring theory, NTT derivation)
