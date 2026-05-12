# ML-KEM — 5-Minute Quick Overview

**Čas na přečtení:** ~5 minut  
**Cíl:** Pochopit, co ML-KEM dělá, jak pracuje a jaké kryptografické finty používá.

---

## 🎯 Co je ML-KEM?

**ML-KEM** (Module-Lattice-Based Key Encapsulation Mechanism) je **postkvantový algoritmus** standardizovaný NIST v roce 2024 (FIPS 203). 

- **Cíl:** Bezpečně sdílit tajný klíč (32 bajtů) mezi dvěma stranami, a to způsobem, který **odolá i budoucím kvantovým počítačům**.
- **Klasické algoritmy:** RSA, ECDH — jsou náchylné na Shorův algoritmus (kvantový útok)
- **ML-KEM:** Postaven na mřížkách (lattice problems) — nejlepší známý útok je klasický (nikoliv kvantový)

---

## 🔑 Jak ML-KEM funguje — 3 kroky

### 1️⃣ **KeyGen** — Generování páru klíčů

```
Alice chce přijímat šifrované zprávy.

1. Vygeneruje veřejnou matici A (náhodná, známá všem)
2. Vygeneruje tajný vektor s (malý, tajný)
3. Spočítá t = A·s + e  (přidá maličký šum e pro bezpečnost)

Výstup:
  - Veřejný klíč (ek) = [t || ρ]   (800 bytů) — Alice publikuje
  - Tajný klíč (dk) = [s || ...]   (1632 bytů) — Alice tajně uschová
```

**Klíčová idea:** Opačný problém (obnovit `s` z `t`) je těžký → **Module-LWE problém**.

---

### 2️⃣ **Encaps** — Zapouzdření klíče

```
Bob chce poslat Alici tajný klíč K (32 bajtů).

1. Bob vygeneruje náhodnou zprávu m (32 bajtů)
2. Spočítá: K, r = G(m || H(ek))   (hashovací trik)
3. Zašifruje m pomocí Alicina ek → ciphertext c (768 bajtů)

Výstup:
  - K (sdílený tajný klíč — Bob a Alice jej budou mít stejný)
  - c (ciphertext — Bob pošle Alici)

Bob pošle Alici ciphertext `c` (ostatní vidí, ale bez tajného klíče `dk` jej nemohou dešifrovat).
```

---

### 3️⃣ **Decaps** — Rozmotání klíče

```
Alice přijmula od Boba ciphertext c a chce obnovit K.

1. Alice pomocí svého tajného klíče dk dešifruje c → m'
2. Znovu spočítá: K', r' = G(m' || H(ek))  (znovu vygeneruje K')
3. Znovuencrypt — spočítá c' = Encrypt(ek, m', r')
4. KONTROLA (Fujisaki-Okamoto trik):
   - Pokud c == c'  →  vrátí K'      ✓ (ciphertext byl validní)
   - Pokud c ≠ c'  →  vrátí fake K   ✗ (ciphertext byl zmanipulován)

Alice obdrží **stejné K jako Bob** (pokud si nikdo nepohrál s c).
```

---

## 🔐 Klíčové kryptografické "finty"

### 1. **Number Theoretic Transform (NTT)** ⚡

**Problém:** Násobení polynomů stupně 255 je pomalé (O(n²) = 256² operací).

**Řešení:** NTT je obdoba FFT, ale nad tělesem Z₃₃₂₉ (nikoliv komplexní čísla).
- **Čas:** O(n log n) místo O(n²)
- **Modul q = 3329:** Zvolen speciálně, aby existovala 256bodová NTT
- **Výsledek:** Všechna násobení polynomů běží ~100× rychleji

```python
# Bez NTT: f * g = O(256²) ≈ 65k operací
# S NTT:   ntt(f) * ntt(g) = O(256·log₂(256)) ≈ 2k operací
```

---

### 2. **Centered Binomial Distribution (CBD)** 🎲

**Problém:** Jak vygenerovat "malý" šum e ∈ [-η, η]?

**Řešení:** CBD — vezmi η bitů, vezmi dalších η bitů, sečti je a odečti:

```
e_i = Σ(b₀) - Σ(b₁),  kde b₀, b₁ jsou náhodné bity

Výsledek: e_i je rovnoměrně distribuován v [-η, η]
Rychlost: Velmi jednoduchá na hardware (bez odmocnin, bez logaritmů)
```

**Proč to funguje?** Rozdíl dvou binomických rozdělení dává centrované rozdělení. Přidání šumu zabraňuje útokům na diskrétní algoritmus.

---

### 3. **Compression & Decompression** 📦

**Problém:** Polynomy v Zq mají koeficienty v [0, 3328], což vyžaduje 12 bitů per koeficient.

**Řešení:** Smažeme přesnost (redundantní bity) — zmenšujeme z 12 bitů na 10 či 4 bity:

```
Compression (12 → 10 bitů):
  c = round(f · 2¹⁰ / 3329) mod 2¹⁰
  
Decompression (10 → 12 bitů zpět):
  f' = round(c · 3329 / 2¹⁰) mod 3329
```

**Výsledek:**
- Zmenšíme ciphertext z 1024 bajtů na 768 bajtů (~25% ušetřeno)
- Zavedeme říditelnou chybu (max ~3 jednotky na koeficient)
- Šum to maskuje — bezpečnost zůstane

---

### 4. **Fujisaki-Okamoto Transform (FO)** 🛡️

**Problém:** Symetrické šifrování (ML-KEM bez FO) je náchylné na **CCA2 útoky** — útočník může normalizovat ciphertexty a zjišťovat, zda se dekapsulace podařila či nikoliv.

**Řešení:** FO transformace — **re-enkrypce s kontrolou**:

```
decaps(dk, c):
  1. Dešifruj c → m'
  2. Znovu zašifruj m' pod ek s odvozením r
  3. Jestliže se ciphertext shoduje (c == c'):
       → vrátí SPRÁVNÝ klíč K'
     Jinak:
       → vrátí FAKE klíč J(z, c)   [pomocí tajného semínka z]

Efekt: Útočník nemůže rozlišit, zda měl klíč správný či špatný.
       To eliminuje CCA2 útoky.
```

---

### 5. **Domain Separation s H(ek)** 🔗

**Problém:** Vázanost všech operací na veřejný klíč.

**Řešení:** Vždy se používá **H(ek)** (hash veřejného klíče) spolu s ostatními vstupy:

```
K, r = G(m || H(ek))     ← Domain separation
```

**Proč to funguje?**
- Zabraňuje **útokům záměnou klíče** (key substitution attack)
- Zajistí, že každý veřejný klíč má "vlastní" prostor sdílených tajemství
- Běžná chyba: Zapomenutí H(ek) → CCA2 zranitelnost

---

## 📊 Shrnutí — Co se to děje pod kapotou?

| Operace | Matematika | Čas | Finty |
|---------|-----------|------|-------|
| **KeyGen** | A ∈ Z_q^{k×k}, s,e malé → t = As+e | ~10ms | NTT, CBD, domain separation |
| **Encaps** | u = A^T·r+e₁, v = t^T·r+e₂+m | ~1ms | NTT, compression, hashovací trik |
| **Decaps** | w = v - s^T·u, re-encrypt check | ~5ms | NTT, FO transform, implicit rejection |
| **Velikost** | ek=800B, dk=1632B, c=768B | — | Compression, module lattice |

---

## 🎯 Proč je ML-KEM bezpečný?

### Klasická bezpečnost (dnes)
- **Nejlepší útok:** BKZ algoritmus na mřížkách
- **Složitost:** ~2¹¹⁸ klasických operací (mimo dosah)
- **Důvod:** Module-LWE problém nemá žádnou speciální strukturu

### Kvantová bezpečnost (v budoucnu)
- **Shorův algoritmus:** NELZE aplikovat (žádná grupos tructura)
- **Groverův algoritmus:** Poskytuje pouze √-zrychlení (~2⁶⁴ místo 2¹²⁸)
- **Prakticky:** ML-KEM-512 zůstane bezpečný i pro kvantové počítače

---

## 🚀 Praktická doporučení

1. **Nikdy nepoužívejte stejné `m`** — každý `encaps` musí mít jiné náhodné semínko
2. **Udržujte `dk` v tajnosti** — kompromitování = ztráta všech budoucích relací
3. **Kombinujte s klasickým algoritmem** — během přechodu použijte hybridní mód (ML-KEM + X25519)
4. **Rotujte klíče** — maximálně 2³² encapsulations na jeden pár klíčů
5. **Ověřujte velikosti** — odmítejte podezřelě krátké/dlouhé klíče (downgrade attack)

---

## 📚 Kde se to používá?

- ✅ **TLS 1.3** — post-quantum variant se připravuje
- ✅ **SSH** — OpenSSH experimenty se ML-KEM
- ✅ **Signal, Wire** — messaging apps postupně migrují
- ✅ **VPN** — WireGuard, OpenVPN plánují podporu
- ✅ **Email (PGP)** — draft standard pro post-quantum OpenPGP

---

## 🎓 Klíčové termíny

| Termín | Vysvětlení |
|--------|-----------|
| **LWE** | Learning With Errors — těžký problém |
| **MLWE** | Module-LWE — vyšší dimenzionalita v polynomu |
| **NTT** | Number Theoretic Transform — rychlé násobení |
| **FO** | Fujisaki-Okamoto — konverze CPA → CCA2 |
| **CBD** | Centered Binomial Distribution — vzorkování šumu |
| **Implicit rejection** | Návrátit fake klíč místo chyby při útoku |
| **Domain separation** | Vázanost na konkrétní kontext (H(ek)) |

---

## 💡 Shrnutí v jedné větě

**ML-KEM je postkvantový algoritmus pro bezpečné sdílení tajného klíče, který používá těžkost mřížkových problémů, NTT pro rychlost, CBD pro šum, kompresi pro velikost a Fujisaki-Okamoto pro zajištění bezpečnosti proti útokům s orakuly.**

🎉 **To je vše za 5 minut!**
