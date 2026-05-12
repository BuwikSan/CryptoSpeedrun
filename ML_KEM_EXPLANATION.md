# ML-KEM (CRYSTALS-Kyber) — Kompletní Vysvětlení Kódu

Podrobný řádek-po-řádku přehled implementace ML-KEM-512 z `ml_kem.py`.

---

## 1. PARAMETRY A KONSTANTA (řádky 1–20)

```python
N    = 256   # stupeň polynomu (kolik koeficientů má každý polynom)
Q    = 3329  # modulus (všechny operace se dělají mod Q)
K    = 2     # "modul rank" (pro ML-KEM-512)
ETA1 = 3     # jak moc "hlučné" jsou s, e při keygenu
ETA2 = 2     # jak moc "hlučné" jsou e1, e2 při encryptu
```

### Vysvětlení

- **N = 256**: Polynom má 256 koeficientů. Pracujeme v polynomiálním kruhu **Z_Q[X]/(X^256 + 1)** — to je kruh polynomů stupně maximálně 255 s celočíselnými koeficienty mod Q.

- **Q = 3329**: Toto číslo je speciální! Je to `13·2^8 + 1`. 
  - Důvod: aby existoval **NTT (Number Theoretic Transform)** velikosti 256.
  - Potřebuješ primitivní kořen 512. odmocniny jednoty mod Q.
  - Číslo 17 je právě takový kořen mod 3329.

- **K = 2**: Modul má rozměr **2×2** (matice). Větší K = více bitů, silnější, ale pomalejší.
  - ML-KEM-768 má K=3, ML-KEM-1024 má K=4.

- **ETA1, ETA2**: Určují distribuci **šumu** (noise).
  - Menší = tichý, menší klíč, levnější
  - Větší = hlučný, větší klíč, bezpečnější
  - ETA1 se používá v keygenu, ETA2 v encryptu.

```python
EK_SIZE    = 384 * K + 32   # 800 bytes - velikost veřejného klíče
DK_PKE_SZ  = 384 * K        # 768 bytes - velikost s_hat v tajném klíči
```

### Výpočet

**Proč 384?** Protože máš K polynomů, každý s 256 koeficienty, každý kódovaný na **12 bitů**:
- 256 koeffic × 12 bits = 3072 bits = 384 bytes

EK se skládá z:
- K polynomů (t_hat) × 384 bytes = 768 bytes
- ρ (rho seed) = 32 bytes
- **Celkem: 800 bytes**

---

## 2. NTT SETUP (řádky 22–37)

```python
def _bit_rev7(x):
    r = 0
    for _ in range(7):
        r = (r << 1) | (x & 1)  # vezmi poslední bit z x, přidej do r zleva
        x >>= 1                   # posun x doprava
    return r
```

### Co to dělá?

Obrátí **spodních 7 bitů** čísla x (bitová reverze).

**Příklady:**
```
_bit_rev7(1)  = _bit_rev7(0b0000001) = 0b1000000 = 64
_bit_rev7(5)  = _bit_rev7(0b0000101) = 0b1010000 = 80
_bit_rev7(64) = _bit_rev7(0b1000000) = 0b0000001 = 1
```

**Kde se používá?** V NTT algoritmu — je to součást Cooley-Tukey FFT dekompozice.

```python
ZETAS  = [pow(17, _bit_rev7(i), Q) for i in range(128)]
GAMMAS = [pow(17, 2 * _bit_rev7(i) + 1, Q) for i in range(128)]
```

### Předpočítané konstanty

**ZETAS[i]** = 17^(BitRev7(i)) mod 3329

- Toto jsou **"twiddle faktory"** — čísla použitá v NTT butterfly operacích.
- 17 je primitivní 512-tá odmocnina jednoty mod 3329.
- Máš 128 hodnot (N/2 = 256/2).
- Například:
  - ZETAS[0] = 17^0 mod 3329 = 1
  - ZETAS[1] = 17^64 mod 3329 = nějaké číslo
  - ZETAS[127] = 17^(BitRev7(127)) = 17^1 = 17

**GAMMAS[i]** = 17^(2·BitRev7(i)+1) mod 3329

- Používá se při **base-case multiply** (násobení dvou polynomů v NTT doméně).
- Konkrétně: když násobíš dva malé polynomy modulo (X² - GAMMAS[i]).

---

## 3. NTT — SRDCE ALGORITMU (řádky 57–88)

```python
def ntt(f):
    """Forward NTT: seznam 256 koeficientů → NTT reprezentace"""
    f, k, length = list(f), 1, 128
```

### Inicializace

- `f` = kopie vstupního polynomu (seznam 256 čísel mod Q)
- `k = 1` — budeme indexovat do ZETAS pole (začínáme od ZETAS[1])
- `length = 128` — to je **šířka "bloku"** v prvním průchodu (N/2)

```python
    while length >= 2:
        for start in range(0, N, 2 * length):  # prochází bloky po 2*length
            z = ZETAS[k]; k += 1
            for j in range(start, start + length):
```

### Butterfly Operace (Cooley-Tukey)

Toto je jádro NTT. Graficky:

```
      f[j]              t                f[j]'
       |              /   \               |
       +--[+]----+         +--[+]-----  nový f[j]
       |         |               |
    f[j+len]   [*z]         f[j+len]'
       |              \   /     |
       +--[-]----+         +--[-]-----  nový f[j+len]
```

Vzorec:
```python
t             = z * f[j + length] % Q
f[j + length] = (f[j] - t) % Q
f[j]          = (f[j] + t) % Q
```

### Konkrétní Příklad

Když máš `f[0] = 100`, `f[128] = 50`, `z = ZETAS[1]`:
```
t             = z * 50 % Q          (třeba t = 200)
f[128] = (100 - 200) % Q = -100 % Q  (modulo Q, výsledek je kladný)
f[0]   = (100 + 200) % Q = 300
```

### Struktura NTT (7 vrstev)

NTT má **log₂(N) = log₂(256) = 8 vrstev**, ale pracuješ s **128 páry**:

| Vrstva | length | # bloků | # butterflů/blok | Celkem butterflů |
|--------|--------|---------|------------------|------------------|
| 1      | 128    | 1       | 128              | 128              |
| 2      | 64     | 2       | 64               | 128              |
| 3      | 32     | 4       | 32               | 128              |
| ...    | ...    | ...     | ...              | ...              |
| 7      | 2      | 64      | 2                | 128              |

Každá vrstva zpracovává všech 256 prvků, jen s různými kroky.

```python
    inv = pow(128, Q - 2, Q)   # 128^{-1} mod 3329 = 3303
    return [x * inv % Q for x in f]
```

**Finální normalizace:** Všechno se vynásobí 128^(-1).

- 128 = N/2
- Inverze se počítá pomocí **Fermatova malého teorému**: `a^(p-2) ≡ a^(-1) (mod p)` když p je prvočíslo.
- `pow(128, 3329-2, 3329)` = `pow(128, 3327, 3329)` = nějaké číslo
- Pro Q=3329 to je přesně 3303.

---

## 4. INVERSE NTT (řádky 90–108)

```python
def intt(f):
    """Inverse NTT: NTT reprezentace → polynomiální reprezentace"""
    f, k, length = list(f), 127, 2  # k začíná od 127 (konec ZETAS)!
    while length <= 128:
        for start in range(0, N, 2 * length):
            z = ZETAS[k]; k -= 1
            for j in range(start, start + length):
                t = f[j]
                f[j]          = (t + f[j + length]) % Q
                f[j + length] = z * (f[j + length] - t) % Q
        length *= 2
```

### Jak to funguje

Je to **skoro stejné jako NTT**, ale s malými rozdíly:

1. `k` počítáš od **127 dolů** (místo od 1 nahoru)
2. `length` **roste** (2, 4, 8, ... 128) místo aby klesala
3. Butterfly mají lehce **jinou strukturu** (+ je na jiném místě)
4. Na konci se to normalizuje (× 128^(-1))

### Matematika

Pokud udělíš `f_ntt = ntt(f)` a pak `f_back = intt(f_ntt)`, dostaneš zpět **přesně původní f**:

```python
f_original = [1, 2, 3, 4, ...]
f_ntt = ntt(f_original)
f_back = intt(f_ntt)
assert f_back == f_original  # ✓
```

---

## 5. NÁSOBENÍ V NTT DOMÉNĚ (řádky 110–118)

```python
def _mul_ntt(f, g):
    """Dvě polynomy v NTT doméně násobíme "base-case"""
    h = [0] * N
    for i in range(128):
        a0, a1 = f[2*i], f[2*i+1]      # dva koeficienty z f
        b0, b1 = g[2*i], g[2*i+1]      # dva koeficienty z g
        gm = GAMMAS[i]
        
        h[2*i]   = (a0*b0 + a1*b1*gm) % Q
        h[2*i+1] = (a0*b1 + a1*b0)    % Q
    return h
```

### Matematika

Pracuješ s **lokálním polynomiálním kruhem** pro každou i-tou double:

```
f_local = a0 + a1·X
g_local = b0 + b1·X
```

Chceš je násobit **modulo (X² - gm)**, takže:

```
(a0 + a1·X)(b0 + b1·X) = a0·b0 + (a0·b1 + a1·b0)·X + a1·b1·X²

Ale X² ≡ gm (mod X² - gm), takže:
       = (a0·b0 + a1·b1·gm) + (a0·b1 + a1·b0)·X
```

**Výsledek:**
- Koef. u X⁰: `a0*b0 + a1*b1*gm`
- Koef. u X¹: `a0*b1 + a1*b0`

### Proč po 2 koeficienty?

NTT transformuje 256-rozměrný polynom na 256 výstupních hodnot. Ty se přirozeně párují do **128 "quad blocks"** — v každém máš 2 koeficienty, které se chují jako lokální polynomialní kruh.

---

## 6. SAMPLING — REJECTION (řádky 127–145)

```python
def _sample_ntt(seed):
    """Z XOF seedu vygeneruješ 256 hodnot v [0, Q)"""
    a, i = [], 0
    while len(a) < N:  # dokud nemáš 256 hodnot
        if i + 3 > len(seed):
            seed = hashlib.shake_128(seed).digest(len(seed) + 168)
```

### Inicializace

Seed je obvykle 840 bytů z `XOF(rho, i, j)` (SHAKE-128).

Když dojdeš na konec seedu, rozšíříš ho pomocí SHAKE-128 o dalších 168 bytů.

```python
        d1 = seed[i] + 256 * (seed[i+1] % 16)
        d2 = (seed[i+1] // 16) + 16 * seed[i+2]
        i += 3
```

Z každých **3 bytů** vytvoříš **2 kandidáty**:

| Bitový layout |  |
|---|---|
| Byte 0: `XXXXXXXX` |  |
| Byte 1: `YYYYZZZZ` |  |
| Byte 2: `TTTTTTTT` |  |

```
d1 = XXXXXXXX YYYY = 8 + 4 bitů = 12 bitů číslo v [0, 4095]
d2 = ZZZZ TTTTTTTT = 4 + 8 bitů = 12 bitů číslo v [0, 4095]
```

```python
        if d1 < Q:                a.append(d1)
        if d2 < Q and len(a) < N: a.append(d2)
```

### Rejection Sampling

Jestli je kandidát < Q (3329), přidáš ho. Jinak ho zahodíš.

**Proč?** Q není mocnina 2 (není 4096). Kdybysi vybral všechny 12-bitové hodnoty, měly by nerovnoměrné rozdělení modulo Q. Rejection sampling zajišťuje **uniformitu** — každé číslo v [0, Q) má stejnou pravděpodobnost.

**Statistika:** 
- Kandidátů: 2^12 = 4096
- Validních: Q = 3329
- Pravděpodobnost: 3329/4096 ≈ 81.3%
- Průměrně: 256 / 0.813 ≈ 314 kandidátů na 256 výsledků

S 840 byty máš ~560 kandidátů (840×3/3×2), což je víc než dost.

---

## 7. CENTERED BINOMIAL SAMPLING (řádky 147–161)

```python
def _sample_cbd(eta, prf_bytes):
    """Z PRF bytů vygeneruješ 256 hodnot z CBD(eta)"""
    f, bits = [0] * N, []
    for byte in prf_bytes[:64 * eta]:
        for b in range(8):
            bits.append((byte >> b) & 1)  # rozpakuj bit po bitu
```

### Bit-level Rozpakování

Máš `64*eta` bytů = `512*eta` bitů. Rozpakuješ je jeden po jednom:

```python
    for i in range(N):
        a_s = sum(bits[2*i*eta     : 2*i*eta + eta])
        b_s = sum(bits[2*i*eta+eta : 2*i*eta + 2*eta])
        f[i] = (a_s - b_s) % Q
```

Pro každý koef. i:
1. Vezmeš prvních **eta** bitů a sečteš je → `a_s` ∈ [0, eta]
2. Vezmeš dalších **eta** bitů a sečteš je → `b_s` ∈ [0, eta]
3. Koef. = `a_s - b_s` ∈ [-eta, eta]

### CBD = Centered Binomial Distribution

**Příklad pro eta=3:**

- Máš 3 náhodné bity → jejich suma je v {0,1,2,3}
  - 0 jedniček: suma = 0
  - 1 jednička: suma = 1
  - 2 jedničky: suma = 2
  - 3 jedničky: suma = 3
- Máš 3 náhodné bity → jejich suma je v {0,1,2,3}
- Rozdíl `-3` až `+3`

**Distribuční tvar:** Symetrická kolem 0, binomiální tvar (více hodnot blíž k 0).

### Jaký smysl?

- Používá se pro **šum** (`s`, `e`, `e1`, `e2`) v ML-KEM.
- Čím větší eta, tím větší šum.
- Větší šum = více bezpečnosti, ale větší klíč.

---

## 8. ENCODE / DECODE (řádky 163–183)

```python
def _byte_encode(f, d):
    """N koeficientů × d bitů → 32d bytů"""
    out = bytearray(32 * d)
    for i in range(N):
        c = int(f[i]) & ((1 << d) - 1)  # vezmi spodních d bitů
        for j in range(d):
            p = i * d + j                # globální bit position
            out[p >> 3] |= ((c >> j) & 1) << (p & 7)
```

### Co to dělá?

Zasuneš N koeficientů (každý d-bitový) do `32*d` bytů.

**Bitový layout pro i-tý koef.:**

```
Koef. 0: bity 0–(d-1)       → byty 0–(d/8)
Koef. 1: bity d–(2d-1)      → byty (d/8)–(2d/8)
Koef. 2: bity 2d–(3d-1)     → byty (2d/8)–(3d/8)
```

**Konkrétní příklad pro ML-KEM-512, d=12:**

```
Koef. 0: bity 0–11          → byty 0–1
Koef. 1: bity 12–23         → byty 1–2
Koef. 2: bity 24–35         → byty 3–4
```

```python
def _byte_decode(b, d):
    """32d bytů → N koeficientů × d bitů"""
    f = [0] * N
    for i in range(N):
        for j in range(d):
            p = i * d + j
            f[i] |= ((b[p >> 3] >> (p & 7)) & 1) << j
    return f
```

Obrácená operace — vytahuješ bity zpátky do koeficientů.

```python
def _compress(f, d):
    """Hodnoty v [0, Q) → [0, 2^d) (zmenšení)"""
    m = 1 << d
    return [round(x * m / Q) % m for x in f]

def _decompress(f, d):
    """Hodnoty v [0, 2^d) → [0, Q) (zvětšení)"""
    return [round(x * Q / (1 << d)) % Q for x in f]
```

### Komprese = Zmenšení Přesnosti

Místo posílat všech 12 bitů, pošleš jen d bitů. Kompresní vzorec:

```
compress_q(x, d) = round(x · 2^d / Q) mod 2^d
```

**Příklad pro d=10:**

```
x = 3000 (v [0, 3329])
compress_q(x, 10) = round(3000 * 1024 / 3329) mod 1024
                  = round(921.4) mod 1024
                  = 921
```

**Dekomprese:**

```
decompress_q(y, 10) = round(y · Q / 2^d) mod Q
                    = round(921 * 3329 / 1024) mod 3329
                    ≈ 3000
```

Není to přesné, ale "dostatečně blízko" — chyba je < 1 LSB.

---

## 9. PKE KEYGEN (řádky 195–225)

```python
def _pke_keygen(d):
    rho, sigma = _G(d + bytes([K]))
```

Vezmeš 32 random bytů `d`, přidáš jednobytový module rank `K=2`, hashuješ **SHA3-512** a rozděliš na dvě 32bytové semínka:
- `rho` — seed pro matici A
- `sigma` — seed pro šum (s, e)

```python
    A = [[_sample_ntt(_XOF(rho, i, j)) for j in range(K)] for i in range(K)]
```

Vygeneruješ K×K matici polynomů v **NTT doméně**.
-每 polynomiální prvek: `A[i][j] = SampleNTT(XOF(rho, i, j))`
- XOF = SHAKE-128, generuje pseudonáhodné byty
- SampleNTT = rejection-sample polynom do NTT reprezentace

```python
    s_hat = [ntt(_sample_cbd(ETA1, _PRF(ETA1, sigma, i))) for i in range(K)]
    e_hat = [ntt(_sample_cbd(ETA1, _PRF(ETA1, sigma, K + i))) for i in range(K)]
```

Vygeneruješ tajný vektor **s** a chybu **e** (oba K polynomů):
1. Vzorkuješ z **CBD** (centered binomial)
2. Transformuješ do **NTT domény** (aby ses později dal snadněji násobit)

PRF index se liší:
- `s[i]` z PRF(sigma, i)
- `e[i]` z PRF(sigma, K+i)

```python
    t_hat = []
    for i in range(K):
        ti = [0] * N
        for j in range(K):
            ti = _add(ti, _mul_ntt(A[i][j], s_hat[j]))
        t_hat.append(_add(ti, e_hat[i]))
```

Vypočítáš **t = A·s + e** (v NTT doméně).

Řádka i vektoru t:
```
t[i] = sum_j (A[i][j] * s[j]) + e[i]
```

Konkrétně:
- `ti = A[i][0] * s[0] + A[i][1] * s[1] + e[i]` (pro K=2)

```python
    ek = b''.join(_byte_encode(t_hat[i], 12) for i in range(K)) + rho
    dk = b''.join(_byte_encode(s_hat[i], 12) for i in range(K))
    return ek, dk
```

Kódování:
- **ek** (veřejný klíč) = `t[0] (384B) || t[1] (384B) || rho (32B)` = **800 bytů**
- **dk** (tajný klíč v PKE) = `s[0] (384B) || s[1] (384B)` = **768 bytů**

---

## 10. PKE ENCRYPT (řádky 227–260)

```python
def _pke_encrypt(ek, m, r):
    t_hat = [_byte_decode(ek[384*i : 384*(i+1)], 12) for i in range(K)]
    rho   = ek[384*K:]
    A     = [[_sample_ntt(_XOF(rho, i, j)) for j in range(K)] for i in range(K)]
```

Dekóduj veřejný klíč:
- `t_hat[i]` = dekóduj polynom z pozice 384i do 384(i+1)
- `rho` = posledních 32 bytů

Regeneruj matici A (je veřejná, máš rho).

```python
    r_hat = [ntt(_sample_cbd(ETA1, _PRF(ETA1, r, i))) for i in range(K)]
    e1    = [_sample_cbd(ETA2, _PRF(ETA2, r, K + i)) for i in range(K)]
    e2    = _sample_cbd(ETA2, _PRF(ETA2, r, 2 * K))
    mu    = _decompress(_byte_decode(m, 1), 1)
```

Vzorkuješ z randomness `r` (32 bytů):
- `r_hat[i]` = vektor K polynomů (transformován do NTT), ETA1
- `e1[i]` = vektor K polynomů, ETA2 (menší šum)
- `e2` = jeden polynom, ETA2
- `mu` = dekóduj 32bytovou zprávu m (1 bit/koef.) a decompressuj

```python
    u = []
    for j in range(K):
        uj = [0] * N
        for i in range(K):
            uj = _add(uj, _mul_ntt(A[i][j], r_hat[i]))
        u.append(_add(intt(uj), e1[j]))
```

Vypočítáš **u = A^T · r + e1** (v spatial doméně, ne NTT):

Algoritmus:
1. Pro každou pozici j v u:
2. Sečti všechny `A[i][j] * r_hat[i]` (násobení v NTT doméně)
3. Transformuj zpátky (`intt`)
4. Přidej `e1[j]`

Konkrétně pro K=2:
```
u[0] = intt(A[0][0]*r_hat[0] + A[1][0]*r_hat[1]) + e1[0]
u[1] = intt(A[0][1]*r_hat[0] + A[1][1]*r_hat[1]) + e1[1]
```

Toto je vlastně `u = A^T · r + e1`.

```python
    v_hat = [0] * N
    for i in range(K):
        v_hat = _add(v_hat, _mul_ntt(t_hat[i], r_hat[i]))
    v = _add(_add(intt(v_hat), e2), mu)
```

Vypočítáš **v = t^T · r + e2 + mu**:

Stejný postup, ale jen jedna výstupní hodnota (ne vektor).

```python
    c1 = b''.join(_byte_encode(_compress(u[i], DU), DU) for i in range(K))
    c2 = _byte_encode(_compress(v, DV), DV)
    return c1 + c2
```

Kódování ciphertextu:
- Kompresuj `u` na **DU=10** bitů, kóduj → K × 320 bytů = 640 bytů
- Kompresuj `v` na **DV=4** bity, kóduj → 1 × 128 bytů = 128 bytů
- **Ciphertext c = c1 || c2 = 768 bytů**

---

## 11. PKE DECRYPT (řádky 262–276)

```python
def _pke_decrypt(dk, c):
    u     = [_decompress(_byte_decode(c[32*DU*i : 32*DU*(i+1)], DU), DU) for i in range(K)]
    v     = _decompress(_byte_decode(c[32*DU*K:], DV), DV)
    s_hat = [_byte_decode(dk[384*i : 384*(i+1)], 12) for i in range(K)]
```

Dekóduj ciphertext a tajný klíč:
- `u[i]` = decompressuj vektor
- `v` = decompressuj skalár
- `s_hat[i]` = dekóduj tajné polynomy

```python
    w = list(v)
    for i in range(K):
        w = _sub(w, intt(_mul_ntt(s_hat[i], ntt(u[i]))))
    return _byte_encode(_compress(w, 1), 1)
```

Vypočítáš **w = v - s^T · u**:

Algoritmus:
1. Začni s `w = v`
2. Pro každý index i: `w -= s[i] * u[i]` (v spatial doméně)
3. Kompresuj w na 1 bit, vrátí 32 bytů

Matematika:
```
Původně jsme šifrovali:
v = t^T · r + e2 + mu
u = A^T · r + e1

Nyní:
w = v - s^T · u
  = (t^T · r + e2 + mu) - s^T · (A^T · r + e1)
  = t^T · r + e2 + mu - s^T · A^T · r - s^T · e1
  = (As+e)^T · r + e2 + mu - s^T · A^T · r - s^T · e1
  = s^T · A^T · r + e^T · r + e2 + mu - s^T · A^T · r - s^T · e1
  = e^T · r + e2 + mu - s^T · e1

Pokud jsou všechny chyby malé, to je **přibližně** mu (s nějakými zbytky chyby).
```

Bity mu jsou původně v compression-expanded formě — zaokrouhlíš na 1 bit a dostaneš zpět původní m.

---

## 12. ML-KEM VRSTVA — KEYGEN (řádky 287–300)

```python
def keygen():
    d, z = os.urandom(32), os.urandom(32)
    rho, sigma = _G(d + bytes([K]))
```

Vygeneruješ dvě 32-bytová náhodná čísla:
- `d` — seed pro PKE keygen
- `z` — seed pro **implicit rejection** (decryption failure pseudorandomness)

```python
    ek_pke, dk_pke = _pke_keygen(d)
    ek = ek_pke
    dk = dk_pke + ek + _H(ek) + z
```

Zavoláš PKE keygen (vytvoří základní veřejný a tajný klíč):

Potom vytvoříš **ML-KEM klíče**:
- **ek** (ML-KEM encapsulation key) = `ek_pke` = 800 bytů
- **dk** (ML-KEM decapsulation key) = 4 části concatenované:
  1. `dk_pke` = 768 bytů (PKE tajný klíč)
  2. `ek` = 800 bytů (PKE veřejný klíč — pro re-encryption check)
  3. `H(ek)` = 32 bytů (hash veřejného klíče)
  4. `z` = 32 bytů (implicit rejection seed)
  - **Celkem: 1632 bytů**

**Proč H(ek)?** V decapsu se ověřuje, že máš správný ek (chrání před key substitution útoky).

**Proč z?** Pokud decryption selže (ciphertext je poškozený/útok), vrátíš J(z, c) místo signalizovat chybu.

---

## 13. ML-KEM ENCAPS (řádky 302–312)

```python
def encaps(ek):
    m = os.urandom(32)
    K_key, r = _G(m + _H(ek))
```

Encapsulace sdíleného tajemství:

1. Vygeneruješ náhodnou 32bytovou **zprávu** `m`
2. Hashneš ji spolu s `H(ek)` (SHA3-512) a rozdělíš:
   - `K_key` = sdílené tajemství (32 bytů) — **toto je klíč**
   - `r` = randomness pro PKE encrypt (32 bytů)

**Proč H(ek)?** Domain separation — aby se m nevyskytlo identicky pro různé veřejné klíče.

```python
    c = _pke_encrypt(ek, m, r)
    return K_key, c
```

Encryptuješ zprávu `m` pod veřejným klíčem `ek` s randomness `r`:
- Dostaneš ciphertext `c` (768 bytů)

**Vrácené hodnoty:**
- `K_key` = 32bytový sdílený klíč
- `c` = 768bytový ciphertext

---

## 14. ML-KEM DECAPS (řádky 314–332)

```python
def decaps(dk, c):
    dk_pke = dk[:DK_PKE_SZ]
    ek     = dk[DK_PKE_SZ        : DK_PKE_SZ + EK_SIZE]
    h      = dk[DK_PKE_SZ + EK_SIZE     : DK_PKE_SZ + EK_SIZE + 32]
    z      = dk[DK_PKE_SZ + EK_SIZE + 32:]
```

Rozparsuj `dk` na čtyři komponenty:
1. `dk_pke` = bajtů 0–767 (PKE tajný klíč)
2. `ek` = bajtů 768–1567 (PKE veřejný klíč)
3. `h` = bajtů 1568–1599 (hash H(ek))
4. `z` = bajtů 1600–1631 (implicit rejection seed)

```python
    m_prime      = _pke_decrypt(dk_pke, c)
    K_prime, r_p = _G(m_prime + h)
    c_prime      = _pke_encrypt(ek, m_prime, r_p)
```

**Decapsulace — Fujisaki-Okamoto transformace:**

1. Decryptuješ ciphertext `c` pomocí `dk_pke` → dostaneš `m_prime`
2. Opět hashuješ `m_prime + h` a dostaneš (K_prime, r_p)
3. Znovuencryptuješ `m_prime` s `ek` a `r_p` → dostaneš `c_prime`

```python
    return K_prime if c == c_prime else _J(z, c)
```

**Klíčová logika — Implicit Rejection:**

Pokud se `c_prime` **shoduje** s původním `c`:
- Znamená to, že decryption byl správný a encapsulation se zdařil
- Vrátíš `K_prime` (správný klíč)

Pokud se `c_prime` **neshoduje** s `c`:
- Útok, poškozená data, nebo špatný klíč
- Vrátíš `J(z, c)` = pseudonáhodné číslo odvozené z tajného `z`
- **Nikdy nehlásíš chybu** — útočník neví, zda to selhalo

**Proč je to důležité?** Bez tohoto by útočník mohl dělat:
```
Pokud decrypt vrací chybu   → vím, že klíč je špatný
Pokud decrypt vrací OK      → vím, že klíč je správný
```

To by byl **decryption oracle** — pomocí něj by útočník mohl prolomit IND-CCA2 bezpečnost. FO transformace to znemožňuje.

---

## 15. TEXT ENCRYPTION (řádky 334–357)

```python
def encrypt_text(ek, plaintext: str) -> tuple:
    K_key, c_kem = encaps(ek)
    pt = plaintext.encode('utf-8')
    ks = hashlib.shake_256(K_key).digest(len(pt))
    ct = bytes(a ^ b for a, b in zip(pt, ks))
    return c_kem, ct
```

**Hybrid encryption — KEM + stream cipher:**

1. Encapsuluješ ML-KEM a dostaneš `K_key` (32 bytů) a `c_kem` (768 bytů)
2. Převedeš plaintext na UTF-8 byty
3. Generuješ keystream z `K_key` pomocí SHAKE-256 (stejné délky jako plaintext)
4. XORuješ plaintext s keystreamem → `ct`

**Vrácené hodnoty:**
- `c_kem` = 768bytový KEM ciphertext
- `ct` = encrypted text (stejné délky jako plaintext)

```python
def decrypt_text(dk, c_kem: bytes, ct: bytes) -> str:
    K_key = decaps(dk, c_kem)
    ks    = hashlib.shake_256(K_key).digest(len(ct))
    pt    = bytes(a ^ b for a, b in zip(ct, ks))
    try:
        return pt.decode('utf-8')
    except UnicodeDecodeError:
        return f'[DECRYPTION FAILED — garbage bytes]: {pt[:40].hex()}...'
```

**Decryption:**

1. Decapsuluješ `c_kem` pomocí `dk` → `K_key`
2. Generuješ stejný keystream (SHAKE-256)
3. XORuješ ciphertext s keystreamem → plaintext byty
4. Dekóduj UTF-8
5. Pokud dekódování selhá (špatný klíč, poškozená data) → vrátí hex dump garbage

---

## SHRNUTÍ — CELKOVÝ TOKOVÝ DIAGRAM

```
┌──────────────────────────────────────────────────────────────┐
│                 ML-KEM-512 ARCHITECTURE                      │
└──────────────────────────────────────────────────────────────┘

┌─ KeyGen() ──────────────────────────────────────────────────┐
│  d, z ← random(32)                                           │
│  ─→ PKE.KeyGen(d) ──→ (ek_pke, dk_pke)                      │
│                       │                                      │
│  ek = ek_pke                                                │
│  dk = dk_pke || ek || H(ek) || z                           │
└──────────────────────────────────────────────────────────────┘

┌─ Encaps(ek) ────────────────────────────────────────────────┐
│  m ← random(32)                                             │
│  (K, r) = G(m || H(ek))                                    │
│  c ← PKE.Encrypt(ek, m, r)                                 │
│  return (K, c)                                             │
└──────────────────────────────────────────────────────────────┘

┌─ Decaps(dk, c) ─────────────────────────────────────────────┐
│  m' = PKE.Decrypt(dk_pke, c)                              │
│  (K', r') = G(m' || H(ek))                                │
│  c' = PKE.Encrypt(ek, m', r')                             │
│  return (c' == c) ? K' : J(z, c)                          │
│         (re-encryption check — Fujisaki-Okamoto)          │
└──────────────────────────────────────────────────────────────┘
```

---

## KLÍČOVÉ MATEMATICKÉ KONCEPTY

| Koncept | Vysvětlení |
|---------|-----------|
| **NTT** | Fast polynomial multiplication (O(n log n) místo O(n²)) |
| **Module-LWE** | Security premise: hard even for quantum computers |
| **CBD** | Noise distribution: symmetric binomial around 0 |
| **Rejection Sampling** | Ensures uniform distribution in [0, Q) |
| **Compression** | Reduce ciphertext size at cost of small rounding error |
| **Fujisaki-Okamoto** | Transform IND-CPA encryption to IND-CCA2 KEM |
| **Implicit Rejection** | No error signal on decryption failure → no oracle attacks |
| **Domain Separation** | H(ek) prevents key substitution attacks |

---

## DŮLEŽITÉ VLASTNOSTI ML-KEM

✓ **IND-CCA2 Bezpečnost** — ochrana proti chosen-ciphertext útokům
✓ **Post-Quantum** — bezpečné i proti kvantovým počítačům
✓ **Efektivní NTT** — rychlá polynomiální aritmetika
✓ **Kompaktní klíče** — ek=800B, ciphertext=768B
✓ **Constant-Time Možné** — vhodné pro hardware
✓ **Deterministické Encaps** — stejná zpráva m+ek → stejný ciphertext (ne random)

---

## ČÍM SE LIŠÍ OD KLASICKÉ KRYPTOGRAFIE?

| Vlastnost | RSA/ECDH | ML-KEM |
|-----------|----------|--------|
| **Hardost** | Factorization / DLP | Learning With Errors |
| **Quantum** | ✗ Shor (polynomial) | ✓ Nejznámější=BKZ (~2^118) |
| **Klíč** | 2048-4096 bitů | 800-1600 bytů |
| **Postup** | Jeden krásný vzorec | Homomorfní šum + renormalizace |
| **Znovuencryption** | Složité | Elegantní (FO) |

