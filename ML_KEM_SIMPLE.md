# ML-KEM PRO IDIOŤÁKA (Opravdu Jednoduché Vysvětlení)

Zapomeň na všechnu tu matematiku. Tady je vysvětlení bez blbostí.

---

## JAK FUNGUJE POSÍLÁNÍ TAJEMSTVÍ MEZI DVĚMA LIDMI?

Představ si, že chceš poslat svému kamarádovi **tajné číslo** (klíč pro šifrování zpráv).

**Problém:** Pokud mu ho pošleš normálně, ostatní to můžou odchytit.

**Řešení:** ML-KEM je jako trezor.

```
Kamarád si vytvoří dva klíče:
├─ VEŘEJNÝ klíč  (nalepí ho na dveře trezoru → všichni vidí)
└─ TAJNÝ klíč    (schová si ho → jen on zná)

Ty:
1. Vezmeš veřejný klíč
2. Vyjmneš tajné číslo (1, 2, 3, ... cokoliv)
3. Zabališ ho do trezoru s tím veřejným klíčem
4. Trezor se zamkne
5. Pošleš mu trezor (ciphertext)

On:
1. Vezme trezor
2. Otevře ho svým tajným klíčem
3. Vytáhne tajné číslo

Teď oba znáte stejné číslo → můžete jím šifrovat zprávy.
```

---

## CO JE ML-KEM KONKRÉTNĚ?

**ML-KEM** je technika, jak:
1. Vytvořit takový "trezor" (šifrování)
2. Aby ho byl schopný otevřít jen ten, kdo má správný klíč
3. Aby to byla bezpečné i proti budoucím super-počítačům

---

## PARAMETRY — CO VŠECHNY TA ČÍSLA ZNAMENAJÍ?

```python
N    = 256   # Polynom má 256 "součástí" (můžeš si představit 256 kol na trezoru)
Q    = 3329  # Největší číslo, co se používá (kolem 3000)
K    = 2     # Velikost trezoru (2 = mid-size, 3 = větší, 4 = obří)
ETA1 = 3     # Kolik "šumu" (chyby) přidáš při tvorbě klíče (víc = bezpečnější)
ETA2 = 2     # Kolik "šumu" při zamykání trezoru
```

**Laicky:**
- Větší K = bezpečnější, ale pomalejší a větší klíč
- Větší ETA = bezpečnější, ale větší chyby (těžší rozluštit)

---

## NTT — "MAGIC TRICK" PRO RYCHLÉ NÁSOBENÍ

Představ si, že potřebuješ vynásobit dvě čísla, která jsou OBROVSKÁ.

**Tuplý způsob:** Vezmeš tužku a papír a děláš klasické násobení. Trvá věčnost.

**Chytrý způsob (NTT):**
1. Obě čísla "přeformátuješ" na jinou reprezentaci (trochu jako převedeš desítky na dvacetiny)
2. Vynásobíš je v téhle nové reprezentaci (je to super rychlé!)
3. Převedeš výsledek zpátky na normální formu

```
Normální čísla:  [1, 2, 3, 4, 5, ...]
       NTT ↓
NTT forma:       [100, 200, 300, ...]
       Násobení je tady snadné!
       NTT ↓
Výsledek:        [5, 10, 15, 20, 25, ...]
```

**Proč to funguje?** Protože matematika je chytrá. Je to jako když vezmeš kalkulačku místo papíru — stejný výsledek, ale 1000× rychleji.

---

## SAMPLING — "NÁHODNÝ ŠUM"

Když vytváříš trezor, přidáš do něj malý "šum" — random chybu.

**Proč?** Aby ho nebyl nikdo schopný "uhodnout" či "prolomit" matematicky.

```
Normální šum:    [0, 0, 0, 0, 0, 1000, 0, 0]  ← problém: je vidět kde je
Dobrý šum:       [1, -1, 1, 1, -1, 1, -1, 1]  ← rozptýlený, těžko vidět
```

**Rejection Sampling** = když vyrobíš random číslo, které je příliš velké, zahodíš ho a vygeneruješ nové.

```
if random_number < 3329:
    ✓ Použij ho
else:
    ✗ Zahoď, vygeneruj nové
```

Proč? Aby byla distribuce **rovnoměrná** — každé číslo má stejnou šanci.

---

## ENCODE / DECODE — BALENÍ DO BYTŮ

Představ si, že máš seznam 256 čísel (polynom).

```
[1, 2, 3, 4, 5, ...]  ← 256 čísel
     Encode (zabal do bytů)
         ↓
[10101010, 11001100, ...]  ← 384 bytů (12 bitů na číslo)
```

**Encode** = vezmi čísla, konvertuj na bity, zabal do bytů (malé balíčky)
**Decode** = vezmi byty, rozpakuj na bity, získej zpět čísla

**Proč je to důležité?** Aby se to dalo poslat přes internet/síť. Čísla nejdou poslat tak jednoduše, ale byty ano.

---

## COMPRESS / DECOMPRESS — ZMENŠENÍ VELIKOSTI

Trezor je OBROVSKÝ. Aby se dal poslat, musíš ho zmenšit.

```
Původní číslo:    1000  (4 bity = 16 možných hodnot)
Kompres:          1      (1 bit = jen 0 nebo 1)
Dekompres:        999    (vrátíš se přibližně zpátky)
```

**Ztrata:** Není to přesné, ale "dostatečně blízko". Je to jako JPEG fotografie — zmenšíš ji, ztratíš detail, ale pořád je poznáš.

---

## PKE — ZÁKLADNÍ "TREZOR"

PKE je jednoduchá verze. Má 3 věci:

### 1. KeyGen — Vytvoř trezor

```
1. Vygeneruješ náhodné čísla (A, s, e)
2. Spočítáš: t = A×s + e (věc, která určuje trezor)
3. Veřejný klíč = (t, A)   ← Všichni vidí
   Tajný klíč  = s          ← Jen ty
```

**Analogie:** Trezor je uzamčen zámkem (t, A), který otevřeš klíčem s.

### 2. Encrypt — Zamkni zprávu do trezoru

```
1. Vezmeš veřejný klíč (t, A)
2. Vezmeš zprávu m (co chceš poslat)
3. Generuješ random údaje (r, e1, e2)
4. Vypočítáš:
   u = A×r + e1
   v = t×r + e2 + m
5. Trezor = (u, v) ← Zašifrovaná zpráva
```

**V angličtině:** u a v jsou zamčené kousky tvé zprávy.

### 3. Decrypt — Otevři trezor tajným klíčem

```
1. Vezmeš tajný klíč s
2. Vezmeš trezor (u, v)
3. Spočítáš: m = v - s×u
4. Vytáhneš zprávu m
```

**Proč to funguje?** Protože matematika je šikovná:
```
v - s×u = (t×r + e2 + m) - s×(A×r + e1)
        ≈ m  (šum se zruší, protože je malý)
```

---

## ML-KEM — UPGRADE NA "BEZPEČNÝ" TREZOR

PKE je základní. ML-KEM přidá bezpečnost.

### Problém se PKE:

Útočník se může chovat jako "doručovatel":
```
Útočník: "Ahoj, poslal jsem ti zprávu!"
Ty: [Snažíš se otevřít, ale není to pro tebe]
Útočník: "Aha! To znamená, že dekryption selhalo!"

→ Útočník získal INFORMACI jen tím, že viděl, co se stalo
  Tím si může postupně "uhodnout" klíč
```

### Řešení: "Potichu odseknutí"

ML-KEM přidá sekvenci:

```
Když se pokusíš otevřít trezor:
1. Pokusíš se dekryptovat (m_prime = v - s×u)
2. Znovuencryptuješ m_prime a zkontroluješ: "Je to totožné s původním trezorem?"
3. Pokud ANO:
   ✓ Vrátíš správný klíč
4. Pokud NE:
   ✗ Vrátíš FAKE klíč (na první pohled stejný, ale není to on)

→ Útočník nemá ŽÁDNOU informaci
  Jestli to selhalo nebo ne — nemůže rozlišit!
```

Toto je **Fujisaki-Okamoto transformace** — "potichu odseknutí" (implicit rejection).

---

## KEYGEN — VYTVOŘENÍ PÁRU KLÍČŮ

```python
1. Vygeneruješ 2 náhodná čísla: d a z

2. Použiješ d pro PKE.KeyGen:
   → Dostaneš (ek_pke, dk_pke)

3. Vytvoříš veřejný klíč:
   ek = ek_pke  (800 bytů)

4. Vytvoříš tajný klíč:
   dk = dk_pke + ek + Hash(ek) + z  (1632 bytů)
   
   Proč všechno tam dáš?
   ├─ dk_pke    → potřebuješ pro decryption
   ├─ ek        → potřebuješ pro re-encryption check
   ├─ Hash(ek)  → chrání před "key substitution" útoky
   └─ z         → seed pro fake klíč (když selhá decryption)
```

---

## ENCAPS — VYTVOŘENÍ TAJNÉHO ČÍSLA A TREZORU

```python
1. Vygeneruješ náhodné číslo: m  (to bude tvé "tajné číslo")

2. Hashneš m + Hash(ek):
   → Dostaneš klíč K a randomness r

3. Zamkneš m do trezoru s r:
   c = PKE.Encrypt(ek, m, r)

4. Vrátíš:
   - K  = tvé tajné číslo (32 bytů) ← TOTO je klíč na šifrování zpráv
   - c  = trezor (768 bytů) ← TOTO pošleš kamarádovi
```

**Celý proces:** Vezmeš náhodné číslo, zamkneš ho, pošleš trezor.

---

## DECAPS — OTEVŘENÍ TREZORU

```python
1. Vezmeš trezor c a svůj tajný klíč dk

2. Pokusíš se otevřít:
   m_prime = PKE.Decrypt(dk, c)

3. Znovuencryptuješ a zkontrolovoluješ:
   m_prime_again = PKE.Encrypt(ek, m_prime, r_prime)
   Shoduje se s c?

4. Pokud ANO:
   ✓ K_prime = Hash(m_prime + Hash(ek))
   ✓ Vrátíš K_prime (správný klíč)

5. Pokud NE:
   ✗ K_fake = Hash(z + c)  ← fake klíč z tvého seedu z
   ✗ Vrátíš K_fake (vypadá stejně, ale není to on)

→ NIKDY neřekneš "selhalo" — oba případy vypadají stejně!
```

---

## TEXT ENCRYPTION — POSÍLÁNÍ ZPRÁV

Teď máte oba stejný klíč K.

```python
# Abys poslal zprávu "Ahoj":

1. Vezmeš K a vygeneruješ "keystream" (pseudonáhodný proud bytů):
   keystream = SHAKE256(K)
   
2. XORuješ zprávu s keystreamem:
   zašifrováno = "Ahoj" XOR keystream
   
3. Pošleš trezor c a zašifrovanou zprávu

# On ji dešifruje:

1. Otevře trezor c svým klíčem → dostane K
2. Vygeneruje stejný keystream
3. XORuje zpět:
   "Ahoj" = zašifrováno XOR keystream
```

**XOR:** Je to super jednoduchá operace (bitová negace). Když XORuješ 2×, vrátíš se zpátky:
```
A XOR B XOR B = A  ✓
```

---

## WRONG KEY DEMO — CO SE STANE, JestliŽE ZMĚNÍŠ KLÍČ

```
Správný klíč:   "secret_key_12345"
Špatný klíč:    "secret_key_12346"  (změníl jsem poslední číslo)

SHAKE256(správný):   [10, 20, 30, 40, ...]
SHAKE256(špatný):    [99, 88, 77, 66, ...]

"Ahoj" XOR [10, 20, 30, 40]:  = [asdf, ghjk, ...]
"asdf..." XOR [99, 88, 77, 66] = [chaos, nonsense, garbage]

→ Výsledek je úplný garbáž
```

**Tady je magičnost:** Ani jedno bito nebylo chybně — je to jen XOR s úplně jinými čísly. Výsledek je random.

---

## PROČ JE ML-KEM BEZPEČNÝ?

### Proti klasickým útokům:
```
Útočník zná:  ek (veřejný klíč), c (trezor)

Aby rozluštil:  Musel by vyřešit Module Learning With Errors
                To znamená: "Vezmi matici A a vektor v,
                            kde v = A×s + malá chyba
                            Najdi s"

Je to stejně těžké jako:  Rozložit 2000bitové číslo na prvočinitele
                          (nebo vyřešit diskrétní logaritmus)
```

### Proti kvantovým útokům:
```
Běžná čísla (RSA): Kvantový počítač je prolomí za MINUTY
ML-KEM (mřížky):  Kvantový počítač potřebuje MILIONY LET

(A ani to není garantované — je to jen nejlepší známý útok)
```

### Proti útokům "vidím, zda selhalo":
```
Bez implicit rejection:
  "Selhalo?" → NE  = klíč je správný (útočník si prosí pozor!)
  "Selhalo?" → ANO = klíč je špatný (útočník si vezme lepší guess)

S implicit rejection (ML-KEM):
  "Selhalo?" → FAKE KLÍČ (kterou jsem sám vytvořil)
  Útočník neví, zda to selhalo, takže se nemůže zlepšovat!
```

---

## SHRNUTÍ V TŘECH VĚTÁCH

1. **ML-KEM vytváří "elektronický trezor"** — veřejným klíčem ho zamkneš, tajným ho otevřeš.

2. **Bezpečnost:** Trezor je založen na problému (mřížky), který je těžký, i pro kvantové počítače.

3. **Chytrý trik:** Když otevření selhane, vrátíš falešný klíč místo aby ses omluvil — útočník nevěděl, že selhalo.

---

## ČŮRÁ ANALOGIE NA ZÁVĚR

```
Klasická kryptografie (RSA):
  Jako mít svěrák z ocele — funguje super,
  dokud ho nedemolujete motorovou pilou (kvantový počítač)

ML-KEM:
  Jako mít svěrák z unobtainia — ne vědci nejsou si jistí,
  jestli vůbec existuje motorová pila, která by ho rozřezala,
  a když vám vyběhne návštěva, vy tvrdíte, že je to jiný svěrák
  (takže návštěva nemůže poznat, co se stalo)
```

---

## HOTOVO

Teď bys měl rozumět:
- ✓ Co je ML-KEM
- ✓ Jak funguje (bez matematiky)
- ✓ Proč je bezpečný
- ✓ Co se stane, když něco selže

Nejsi už idiot. Jsi jen člověk, který chápe ML-KEM bez PhD z matematiky.
