# Learning guide: COR versus SMOR in this project

This guide teaches you what this project did and why, from the physics to the code to the numbers. It is written for the six team members preparing the report, presentation and viva. Read it once from the top. Then go back to the part you own (Section 10).

You do **not** need the 7.3 GB trajectory for anything in this guide. The exercises run on toy data with the project's own code.

**Contents**

1. [The one-paragraph story](#1-the-one-paragraph-story)
2. [Background you need](#2-background-you-need)
3. [From atoms to orientation vectors](#3-from-atoms-to-orientation-vectors)
4. [Time correlation functions](#4-time-correlation-functions)
5. [SMOR, COR and the self/cross decomposition](#5-smor-cor-and-the-selfcross-decomposition)
6. [From curves to relaxation times](#6-from-curves-to-relaxation-times)
7. [How the code does it](#7-how-the-code-does-it)
8. [Reading our results and figures](#8-reading-our-results-and-figures)
9. [What we can and cannot claim](#9-what-we-can-and-cannot-claim)
10. [Study plan by role](#10-study-plan-by-role)
11. [Hands-on exercises](#11-hands-on-exercises)
12. [Self-test and viva practice](#12-self-test-and-viva-practice)
13. [Glossary](#13-glossary)
14. [Further reading](#14-further-reading)

---

## 1. The one-paragraph story

We have a molecular-dynamics (MD) movie of 2,744 water-like molecules: 10,001 saved snapshots ("frames"), one every 10 simulation steps. We ask two questions about it. **How quickly does one molecule forget which way it was pointing?** That is single-molecule orientational relaxation, **SMOR**. **How quickly does the sum of all molecular orientations forget its direction?** That is collective orientational relaxation, **COR**. They differ because molecules are not independent: neighbours tend to point in related directions. We split the collective signal exactly into a **self** part (each molecule with its own past) and a **cross** part (each molecule with every other molecule). We found strong positive cross correlation (G_cell ≈ 2.70), and COR stays above SMOR over the whole window we can trust. But the curves have not decayed to zero by the end of that window, so we report **truncated** integrals and say honestly that the full relaxation times are not resolved.

---

## 2. Background you need

### 2.1 Molecular dynamics in two minutes

An MD simulation integrates Newton's equations for every atom, one small time step at a time. Every few steps it writes positions (and here also velocities and forces) to a **dump file**. Our file, `dumpr.lammpstrj`, is a LAMMPS text dump. Each frame looks like this:

```text
ITEM: TIMESTEP
100
ITEM: NUMBER OF ATOMS
8232
ITEM: BOX BOUNDS pp pp pp
0.0 43.518276
...
ITEM: ATOMS id mol type x y z vx vy vz fx fy fz
1 1 2 12.3 4.5 6.7 ...
```

- `id` is the atom, `mol` is the molecule, `type` is the atom type (here 2 = central atom, likely oxygen; 1 = satellite, likely hydrogen).
- `pp pp pp` means the box is **periodic** in x, y and z. An atom leaving one face re-enters on the opposite face.
- Coordinates are **wrapped** into the box. So the two hydrogens of one molecule can be stored on opposite sides of the box even though they are bonded.

### 2.2 What we know and do not know about the data

| Known (verified on every frame) | Unknown (no input file or log was supplied) |
| --- | --- |
| 10,001 frames, steps 0 to 100,000, every 10 steps | Water model (SPC? SPC/E? something else?) |
| 8,232 atoms = 2,744 groups of (1 centre + 2 satellites) | Unit style and integration timestep, so no picoseconds |
| Cubic periodic box, side 43.518 length units | Temperature, ensemble, charges |
| Bond length 1.000 and angle 109.47° in every molecule | Whether the dump contains the whole system |

The geometry (1.0 length, 109.47°) matches SPC and SPC/E water. But those two models share their geometry and differ only in charges. **Geometry alone does not identify the model.** This is why the whole project uses "simulation steps" as the time unit and never says "ps".

### 2.3 Why orientation relaxation matters

Water molecules carry an electric dipole along the bisector of the H–O–H angle. How fast dipoles reorient controls dielectric response, spectroscopy line shapes and hydrogen-bond dynamics. The anchor paper (Maurya et al. 2021) showed that putting water on graphene barely changes how fast **one** molecule rotates but changes **collective** relaxation dramatically. The difference comes entirely from cross correlations between molecules. That is the mechanism our project measures.

---

## 3. From atoms to orientation vectors

### 3.1 Minimum-image convention (MIC)

To get a bond vector we subtract positions. Because coordinates are wrapped, a raw difference can be almost a whole box length too long. The fix, applied separately for x, y and z with box length $L$:

$$
d_{\text{MIC}} = d - L\,\operatorname{round}(d/L)
$$

Example: box 43.5, O at x = 43.2, H at x = 0.3. Raw difference = −42.9. Then round(−42.9/43.5) = −1, so MIC difference = −42.9 + 43.5 = 0.6. Correct.

In our data about **6.1 %** of molecules need this correction in a typical frame. Without MIC their orientations would be garbage.

### 3.2 The orientation vector

For molecule $i$ with bond vectors $\mathbf b_{i1}, \mathbf b_{i2}$ (O→H1, O→H2 after MIC):

$$
\mathbf u_i = \frac{\mathbf b_{i1}+\mathbf b_{i2}}{|\mathbf b_{i1}+\mathbf b_{i2}|}
$$

This is a unit vector along the H–O–H bisector. For a rigid, symmetric three-site water with equal hydrogen charges, the dipole is exactly proportional to it. So **if** every molecule has the same constant dipole, normalized correlations computed with $\mathbf u_i$ equal the dipole correlations. The unknown dipole size cancels. We tested the rigidity part: the bisector magnitude varies by less than 0.05 % across all molecules and frames. We cannot test the charge part, so we call $\mathbf u_i$ a **geometric orientation proxy**.

### 3.3 The collective vector

$$
\mathbf U(t) = \sum_{i=1}^{N} \mathbf u_i(t)
$$

If molecules pointed at random and independently, $|\mathbf U|^2$ would average to about $N$. If neighbours tend to align, it is bigger. If they tend to anti-align, it is smaller.

---

## 4. Time correlation functions

### 4.1 The idea

A time autocorrelation function asks: "If I know the value now, how much do I still know a lag $\tau$ later?"

$$
C(\tau) = \frac{\langle x(t)\,x(t+\tau)\rangle_t}{\langle x(t)^2\rangle_t}
$$

It starts at 1 and decays toward 0 as memory is lost. For vectors, use the dot product. A simple model is $C(\tau) = e^{-\tau/\tau_r}$, where $\tau_r$ is the relaxation time.

### 4.2 Averaging over time origins

We have $F$ frames. At lag $k$ frames there are exactly $F-k$ valid pairs $(t, t+k)$. The estimator divides by **$F-k$**, not by $F$:

$$
\hat C(k) = \frac{1}{F-k}\sum_{t=0}^{F-k-1} x(t)\,x(t+k)
$$

Large lags have few pairs and are noisy. So we only report lags up to **10 % of the record**: 1,000 frames = 10,000 steps out of 100,000.

### 4.3 Doing it fast with the FFT

The direct sum costs $F^2$ operations per molecule. The Wiener–Khinchin theorem gives the same result in $F\log F$: Fourier-transform the signal, take $|X(\omega)|^2$, inverse transform. One trap: the plain FFT treats the signal as periodic, so the end wraps onto the start ("circular correlation"). The fix is to **zero-pad to at least $2F-1$ points** before transforming. The code does exactly this and then divides by $F-k$. A test checks the FFT result against the direct sum. They agree to $10^{-16}$.

### 4.4 Centering

Subtracting the mean first ($v = x - \bar x$) gives a **connected** correlation that decays to 0 even if $x$ has a permanent offset. With a finite record the mean is itself estimated with noise, and subtracting it pushes the long-lag tail down slightly. For centered data the identity $F\,A(0) + 2\sum_{k>0}(F-k)A(k) = 0$ holds when all lags are included. So centering always forces some negative area somewhere. This is why the project reports both centered and uncentered versions.

---

## 5. SMOR, COR and the self/cross decomposition

This is the core of the project. Learn these definitions exactly.

### 5.1 Definitions (as implemented)

Let $\mathbf v_i = \mathbf u_i - \overline{\mathbf u_i}$ (each molecule's own time mean removed) and $\delta\mathbf U = \mathbf U - \overline{\mathbf U} = \sum_i \mathbf v_i$.

| Name | Formula | Starts at | Meaning |
| --- | --- | --- | --- |
| Ordinary SMOR | $R(k)/N$, with $R = \sum_i\langle \mathbf u_i(t)\cdot\mathbf u_i(t+k)\rangle$ | 1 | Average single-molecule memory, no centering |
| Connected self | $A(k)/A(0)$, with $A = \sum_i\langle \mathbf v_i(t)\cdot\mathbf v_i(t+k)\rangle$ | 1 | Same, after removing each molecule's mean |
| COR | $B(k)/B(0)$, with $B = \langle \delta\mathbf U(t)\cdot\delta\mathbf U(t+k)\rangle$ | 1 | Memory of the total orientation |
| Collective self | $A(k)/B(0)$ | $1/G_{cell}$ | Self part of COR |
| Collective cross | $[B(k)-A(k)]/B(0)$ | $1-1/G_{cell}$ | Cross part of COR (can be negative) |
| Finite-cell factor | $G_{cell} = B(0)/A(0)$ | | Static measure of orientational correlation |

### 5.2 Why the decomposition is exact

Expand the dot product of two sums:

$$
B(k) = \Big\langle \sum_i \mathbf v_i(t)\cdot \sum_j \mathbf v_j(t+k)\Big\rangle
= \underbrace{\sum_i \langle \mathbf v_i(t)\cdot\mathbf v_i(t+k)\rangle}_{A(k)\ \text{(self, } i=j)}
+ \underbrace{\sum_{i\neq j}\langle \mathbf v_i(t)\cdot\mathbf v_j(t+k)\rangle}_{B(k)-A(k)\ \text{(cross)}}
$$

Divide by $B(0)$:

$$
\text{COR}(k) = \frac{A(k)}{B(0)} + \frac{B(k)-A(k)}{B(0)}
$$

Three points to remember:

1. **Both parts share the same denominator $B(0)$.** Neither starts at 1. At lag 0 they add to 1.
2. **We never compute the $N^2$ pair sum in production.** We get the cross term by subtraction, $B-A$. A test on a small subset computes the pairs explicitly and checks they match ($4\times10^{-16}$ error).
3. **Cross can be negative.** If neighbours anti-align, they cancel each other in $\mathbf U$.

### 5.3 What $G_{cell}$ tells you

| $G_{cell}$ | Meaning |
| --- | --- |
| ≈ 1 | Molecules are orientationally uncorrelated |
| > 1 | Molecules tend to point the same way (positive cross) |
| < 1 | Molecules tend to cancel each other (negative cross) |

Ours is **2.70**: strong positive correlation. For comparison, the anchor paper reports 3.23 for bulk TIP4P/2005 water and 0.24 for a graphene droplet. **Do not call ours a Kirkwood factor or a dielectric constant.** It depends on the finite cell, the boundary conditions, and our centering convention. And our charges are unknown.

### 5.4 Why COR is not simply $G_{cell}$ times SMOR

It is tempting to write $\tau_{COR} = G\,\tau_{SMOR}$. That holds only if the cross correlations decay at the same rate as the self ones. In general they do not. The anchor paper keeps a dynamic correction factor for exactly this reason. A static number cannot tell you which relaxation is faster; you need the dynamic curves.

---

## 6. From curves to relaxation times

### 6.1 Running integral

The most general definition of a relaxation time is the area under the normalized curve:

$$
\tau(T) = \int_0^{T} C(t)\,dt
$$

For $e^{-t/\tau_r}$ this tends to $\tau_r$ as $T\to\infty$. In practice you plot $\tau(T)$ against the cutoff $T$ and look for a **plateau**. Our curves have no plateau: in the last 2,000 steps of the window, the SMOR integral still grows by 283 steps and COR by 414 steps. So every integral we report is **truncated** at a stated cutoff.

### 6.2 Exponential fits

A secondary description is a fit of $a\,e^{-t/\tau_{fit}}$ over a declared window (100–2,500 steps). The code accepts a fit only if all of these hold:

- the data are positive throughout the window;
- the curve decays by at least 0.05;
- RMSE < 0.03 and R² > 0.95;
- the fitted τ is at most twice the window width.

The last rule stops us from claiming a τ far beyond what the window shows. COR's fit (5,311 steps) fails it and is **rejected**. Fit scales are descriptive; they are not full relaxation times. Residuals are correlated in time, so no standard error is quoted.

### 6.3 Uncertainty: why blocks, not error bars

There is only **one** collective vector per frame, and successive frames overlap in memory. So 2,744 molecules do **not** give 2,744 independent COR samples. The project splits the record into halves and quarters and shows the spread. That spread is variation, not a confidence interval. Bootstrapping single frames would be wrong, because frames are correlated.

---

## 7. How the code does it

All code is in `src/corsmor/` (about 1,200 lines). The pipeline is a chain of stages:

```text
dumpr.lammpstrj ──convert──► cache/*.npy ──analyze──► results/*.csv,json
                                              │
                         figures ◄────────────┤
                         documents ◄──────────┤  (report .md/.pdf, slides .pptx)
                         validate ◄───────────┤  (tests + checks → validation.json)
                         package  ◄───────────┘  (submission zip + manifest)
```

Run any stage with `python -m corsmor.cli <stage> --config config/analysis.json`, or `all` to run every stage.

### 7.1 Module map

| File | Key functions | What to understand |
| --- | --- | --- |
| `trajectory.py` | `read_frame`, `molecule_mapping`, `reconstruct`, `convert` | Streams the 7 GB text file **once**. Validates every header, ID, membership and step. Maps each molecule to (centre, H1, H2) by ID, not by row order. Applies MIC (`raw - L*np.rint(raw/L)`). Writes a float32 memory-mapped array `orientations.npy` of shape (10001, 2744, 3). Checkpoints every 250 frames so an interruption resumes. |
| `correlation.py` | `autocorrelation_fft`, `autocorrelation_direct`, `correlations`, `running_integral`, `fit_decay` | The science. Read `correlations` line by line: it loops over molecules in batches of 64, builds R (uncentered), A (centered), and U, then B, and returns every curve in Section 5.1. |
| `analysis.py` | `analyze`, `empirical_checks` | Runs `correlations` on the full record, halves, quarters, the record with the first 10 % removed, and every second frame. Writes `results/`. |
| `plotting.py` | `make_figures` | The eight figure families. |
| `documents.py` | `build_documents`, `build_presentation` | Generates the report and slides **from the result files**, so numbers in documents can never drift from the analysis. |
| `validation.py` | `run_tests`, `validate`, `package` | Runs pytest and numerical checks, and writes `overall_pass`. Packaging is refused unless validation passed. |
| `cli.py` | `main` | Command-line entry point. |

### 7.2 The heart of `correlations()` (annotated)

```python
for first in range(0, N, batch):                 # 64 molecules at a time to save RAM
    x = u[:, first:first+batch].astype(float64)  # (F, 64, 3), accumulate in float64
    U += x.sum(axis=1)                           # build the collective vector
    R += ac(x, max_lag)                          # ordinary self, uncentered
    mean = x.mean(axis=0)                        # each molecule's own time mean
    A += ac(x - mean, max_lag)                   # connected self
delta = U - U.mean(axis=0)
B = ac(delta, max_lag)                           # collective, centered
G = B[0] / A[0]
cross = (B - A) / B[0]                           # exact, no pair loop
```

`ac` sums the autocorrelation over every channel it is given (all molecules × 3 components). So one call returns the summed self term for the whole batch.

### 7.3 Tests worth reading (`tests/test_science.py`)

- A vector rotating at a known rate must give $\cos(\omega k)$.
- An exponential process must give the known integral.
- A constructed anti-aligned pair must give a negative cross term.
- The explicit $i\ne j$ pair sum must equal $B-A$.
- FFT must equal direct.
- Molecules split across the box, shuffled IDs, reordered columns, truncated frames, NaNs, changed membership and wrong cadence must all be handled or rejected.
- On the real cache, every frame interval must be 10 steps. This is the test that is skipped when the trajectory is absent.

Run them: `python -m pytest -q -ra`.

---

## 8. Reading our results and figures

### 8.1 Key numbers (all lags in simulation steps)

| Quantity | Value |
| --- | --- |
| $A(0)$, $B(0)$ | 2518.30, 6788.83 |
| $G_{cell}$ (full record) | **2.696** |
| $G_{cell}$ range over quarters | 1.762 – 2.697 |
| Collective self(0) / cross(0) | 0.371 / 0.629 |
| At lag 2,500: ordinary SMOR / connected self / COR | 0.511 / 0.466 / 0.605 |
| At lag 2,500: collective self / cross | 0.173 / 0.432 |
| At lag 10,000: ordinary SMOR / COR | 0.116 / 0.148 |
| Truncated integral to 10,000: SMOR / connected self / COR | 3685 / 3096 / 4521 |
| Fit τ (100–2,500 window): SMOR / connected self / COR | 4349 ✓ / 3794 ✓ / 5311 ✗ rejected |
| Every-second-frame change: SMOR / COR | ≤ 1.2×10⁻⁵ / ≤ 2.7×10⁻⁴ |

**How to say the main result in one breath:** "63 % of the zero-lag collective fluctuation comes from correlations between different molecules. Over the 10,000-step window COR stays above SMOR, with a larger truncated integral (4521 vs 3685 steps). Neither has converged, so we do not claim full relaxation times or their ratio."

### 8.2 Figure guide

| Figure | What it shows | What to say |
| --- | --- | --- |
| `01_geometry` | Schematic of the proxy; bond and angle envelopes over all frames | Molecules are rigid to 4 decimal places. This supports the proxy but does not prove the charges. |
| `02_spatial_profiles` | Centre-atom counts along x, y, z per quarter | Within about 1.4 % of uniform: no obvious slab or interface. This does not prove bulk. |
| `03_collective_stationarity` | $U_x, U_y, U_z$ over time; prefix $G_{cell}$ | The collective vector wanders slowly (quarter means of $U_y$ go from +28 to −72). These are slow modes, sampled only a few times. |
| `04_smor_cor` | Ordinary SMOR, connected self, COR | COR lies above both self curves. The early-time panel shows the fast initial drop. |
| `05_decomposition` | COR = collective self + collective cross | The cross term starts at 0.63 and dominates throughout. |
| `06_running_integrals` | τ(T) for each curve | Still rising at 10,000 steps: no plateau, so the times are truncated. |
| `07_block_variation` | Quarters and halves | COR varies a lot between blocks; SMOR is stable. Collective statistics are the weak point. |
| `08_sensitivity` | Centering, cadence, first-10 % removal | Cadence does not matter. Centering shifts self curves by up to 0.08. |

---

## 9. What we can and cannot claim

**We can say:**

- Every frame was checked, and molecules were reconstructed correctly across periodic boundaries.
- Our estimators are numerically exact: FFT = direct, pair sum = $B-A$, decomposition error 10⁻¹⁶.
- There is strong positive static orientational correlation ($G_{cell}$ ≈ 2.7) in this cell under our centering convention.
- Over 0–10,000 steps, COR stays above SMOR, and cross terms carry most of the collective signal.

**We must not say:**

- Anything in picoseconds, or "SPC/E water", or "300 K".
- That 2.7 is the Kirkwood factor or gives a dielectric constant.
- That we measured the full relaxation times, or that τ_COR/τ_SMOR = 1.23 (4521/3685). That is a ratio of truncated integrals.
- That the system is equilibrated. We have no energy or temperature logs.
- That the quarter spread is a 95 % confidence interval.
- That we reproduced Maurya et al.'s numbers. Different model, conditions and units.

---

## 10. Study plan by role

Everyone: read Sections 1, 5 and 9 and do Exercise 2. Then focus on your part.

| Person | Role | Read | Do | Be ready to explain |
| --- | --- | --- | --- | --- |
| 1 | Question, literature, provenance | §2, anchor paper §III.C + Table IV, `research/LITERATURE_REVIEW.md` | Make a one-slide comparison of published vs measured, kept separate | Why we cannot use ps; why SPC geometry ≠ SPC/E |
| 2 | Reader and reconstruction | §3, §7.1, `trajectory.py` | Exercise 3 (MIC) | How a split molecule is fixed; what is validated per frame; why checkpoints |
| 3 | SMOR and connected self | §4, §6, `correlation.py` | Exercise 1 and 4 | Why divide by F−k; why centering matters; why no plateau |
| 4 | COR and cross terms | §5 | Exercise 2 and 5 | The decomposition derivation on a whiteboard; why cross(0) = 1 − 1/G |
| 5 | Validation and sampling | §6.3, §7.3, `results/validation.json` | Run `pytest`; read `numerical_checks.json` | Why blocks are not error bars; what `overall_pass` does and does not mean |
| 6 | Figures and reproducibility | §7, §8.2, `README.md` | Install the env, run tests, regenerate figures from results | Walk through every figure in one sentence each |

**Suggested schedule (about 6 hours each):**

- **Hour 1:** Sections 1–2. Skim the anchor paper's Section III.C.
- **Hours 2–3:** Sections 3–6, with pen and paper. Derive the decomposition yourself.
- **Hour 4:** Exercises.
- **Hour 5:** Your role's files and figures.
- **Hour 6:** Self-test (Section 12) in pairs, out loud.

---

## 11. Hands-on exercises

### Setup (once)

Any OS, Python 3.11–3.14:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install numpy scipy matplotlib pytest reportlab python-pptx pymupdf psutil
pip install --no-deps -e .
python -m pytest -q -ra     # expect 23 passed, 1 skipped without the trajectory
```

For the exact pinned Windows environment, see `README.md`.

### Exercise 1: FFT versus direct (10 min)

```python
import numpy as np
from corsmor.correlation import autocorrelation_fft, autocorrelation_direct
x = np.random.default_rng(0).normal(size=(200, 5))
print(np.max(np.abs(autocorrelation_fft(x, 20) - autocorrelation_direct(x, 20))))  # ~1e-16
```

Now change `next_fast_len(2*F-1)` to `F` inside a copy of `autocorrelation_fft`. Does it still agree? Why not? (Hint: circular wraparound.)

### Exercise 2: Build a toy liquid and watch cross terms appear (20 min)

Each "molecule" has a fast private rotation plus a slow motion shared with everyone. Weight `w` controls how much they share.

```python
import numpy as np
from corsmor.correlation import correlations, running_integral
rng = np.random.default_rng(0)

def ou(shape, tau):  # random walk with memory time tau (frames)
    out = np.empty(shape); out[0] = rng.normal(size=shape[1:]); a = np.exp(-1/tau)
    for t in range(1, shape[0]):
        out[t] = a*out[t-1] + np.sqrt(1-a*a)*rng.normal(size=shape[1:])
    return out

F, N = 4000, 50
lag = np.arange(401)
for w in [0.0, 0.3, 0.6]:
    own = ou((F, N, 3), 20.0)      # fast, private
    shared = ou((F, 1, 3), 200.0)  # slow, common to all molecules
    v = own + w*shared
    u = v/np.linalg.norm(v, axis=2, keepdims=True)
    r = correlations(u, 400)
    print(f"w={w}: G_cell={r['stats']['G_cell']:.2f}  "
          f"tau_self={running_integral(r['connected_self'], lag)[-1]:.0f}  "
          f"tau_COR={running_integral(r['cor'], lag)[-1]:.0f}  "
          f"cross(0)={r['collective_cross'][0]:.2f}")
```

Expected output (seed 0):

```text
w=0.0: G_cell=0.96  tau_self=13  tau_COR=13  cross(0)=-0.05
w=0.3: G_cell=3.83  tau_self=23  tau_COR=110  cross(0)=0.74
w=0.6: G_cell=11.14  tau_self=41  tau_COR=132  cross(0)=0.91
```

Questions:

- With no sharing, why is $G$ ≈ 1 and COR ≈ self?
- With sharing, why is COR much slower than self? Which time scale does COR inherit?
- Is $\tau_{COR} = G\,\tau_{self}$ here? (Check: no. This is Section 5.4 in action.)

### Exercise 3: Minimum image by hand (10 min)

```python
import numpy as np
L = 43.518276
O = np.array([43.2, 10.0, 10.0]); H = np.array([0.3, 10.5, 10.6])
raw = H - O
print(raw, raw - L*np.rint(raw/L), np.linalg.norm(raw - L*np.rint(raw/L)))
```

The corrected bond should be about 1 length unit. Explain to a teammate what goes wrong without the correction.

### Exercise 4: Truncated integral of a known exponential (10 min)

```python
import numpy as np
from corsmor.correlation import running_integral
t = np.arange(0, 10001, 10.0); tau = 4000
I = running_integral(np.exp(-t/tau), t)
print(I[-1], tau*(1-np.exp(-10000/tau)))   # ~3672 vs true full tau 4000
```

Even a perfect exponential with τ = 4,000 gives only about 3,670 by 10,000 steps. Compare this with our SMOR value of 3,685. What does it tell you about how far from converged we are?

### Exercise 5: Negative cross term (10 min)

Make molecule 2 always point opposite to molecule 1 (`u[:,1] = -u[:,0]`) in a two-molecule system, plus a little noise. Run `correlations` and look at `G_cell` and `collective_cross[0]`. You should get G_cell close to 0 and a large negative cross(0) (it equals 1 − 1/G). Explain the sign. Why can cross(0) go far below −1 when G is small?

### Exercise 6: Explore the real results (15 min)

```python
import json, numpy as np
s = json.load(open('results/summary.json'))
print(s['full']['G_cell'], s['quarter_G_range'])
c = np.genfromtxt('results/correlations.csv', delimiter=',', names=True)
print(c.dtype.names)
```

Find the lag where ordinary SMOR first drops below 0.5. Then find the same for COR.

---

## 12. Self-test and viva practice

Answer out loud, without notes. Model answers are below. Hide them first.

1. Define SMOR and COR in one sentence each.
2. Write the decomposition of COR and say why it is exact.
3. Why does the collective self term start at 0.371 and not at 1?
4. What does G_cell = 2.70 mean physically? What does it **not** mean?
5. Why is the time axis in steps and not ps?
6. What is the minimum-image convention and why did 6 % of molecules need it?
7. Why do we divide by F−k? Why zero-pad the FFT?
8. Why do we report "truncated integrals"? How would you know a time had converged?
9. Why was the COR exponential fit rejected?
10. Can the cross term be negative? Give a physical example.
11. Why are the four quarters not four independent measurements with error bars?
12. If someone gave you the LAMMPS input file tomorrow, what would change in the report?
13. Does G_cell > 1 prove τ_COR > τ_SMOR?
14. What would you do with a longer simulation, or with five independent ones?

<details>
<summary>Model answers</summary>

1. SMOR: the average memory each molecule keeps of its own orientation. COR: the memory the sum of all orientations keeps of its own direction.
2. COR = A/B(0) + (B−A)/B(0). Expanding the correlation of a sum gives exactly the i=j terms (A) plus the i≠j terms (B−A). It is algebra, not approximation. It holds at every lag because the same means and the same origins are used everywhere.
3. Because it is divided by B(0), not A(0). Its zero-lag value is A(0)/B(0) = 1/G_cell.
4. Molecules in this cell tend to orient alike: the total fluctuates 2.7 times more than independent molecules would. It is not a macroscopic Kirkwood factor or a dielectric constant. It depends on cell size, boundary conditions and centering, and our charges are unknown.
5. The timestep and unit style are unknown, so no conversion from steps to time is justified.
6. Subtract the nearest periodic image so bond vectors are short. Wrapped coordinates put about 6 % of molecules across a box face in a typical frame.
7. There are only F−k pairs at lag k, so dividing by F gives a biased estimate. Without zero-padding the FFT computes a circular correlation, wrapping the end onto the start.
8. The running integrals are still rising at the cutoff (by 283 and 414 steps over the last 2,000). Convergence would need a plateau that is stable across cutoffs, segments and centering, ideally confirmed by independent runs.
9. Its fitted τ (5,311) exceeds twice the window width, so it extrapolates far beyond the data.
10. Yes. In anti-aligned neighbours (for example, an antiparallel dipole arrangement) the dipoles cancel in the sum. The graphene droplet in the anchor paper has G ≈ 0.24, so its cross term is strongly negative.
11. Each quarter is one continuous piece of the same trajectory, with slow collective modes that span quarters. There are also only four, so a standard error would be meaningless. We show the spread only.
12. The time axes could be converted to ps. Temperature and model could be stated. Charges would confirm or refute the identical-dipole proxy. The analysis code itself would not change.
13. No. Dynamic cross correlations can decay faster or slower than self ones. See the toy in Exercise 2 and the anchor paper's dynamic correction.
14. Extend the lag window until the integrals plateau, and use independent runs for real confidence intervals. Then report converged times and their ratio.

</details>

---

## 13. Glossary

| Term | Meaning |
| --- | --- |
| Frame | One saved snapshot of all atoms |
| Cadence | Steps between saved frames (10 here) |
| Lag | Time separation between the two frames being compared |
| Origin | Starting frame of a pair; F−k origins exist at lag k |
| MIC | Minimum-image convention for periodic boxes |
| Proxy | A quantity standing in for another under a stated assumption (bisector for dipole) |
| Connected correlation | Correlation of fluctuations after removing the mean |
| Self / cross | Same-molecule / different-molecule contributions |
| G_cell | B(0)/A(0), the finite-cell static correlation factor used here |
| Kirkwood factor | Macroscopic analogue of G, linked to the dielectric constant; not what we computed |
| Running integral | Area under C(t) up to cutoff T |
| Truncated | Measured only up to a cutoff; not the full value |
| Block variation | Spread of a quantity across sub-segments of one trajectory |
| Memory map | Array stored on disk and read on demand, so 330 MB never sits fully in RAM |

---

## 14. Further reading

In order of importance:

1. **Maurya, Metya, Singh & Saito (2021)**, *J. Chem. Phys.* 154, 164704 — the anchor. Read Section III.C, Eqs. 2–11, Figs. 10–12 and Table IV. The PDF is in `Papers/Papers/`. https://doi.org/10.1063/5.0046817
2. **This repo's report** — `reports/final_report.pdf`, then `research/LITERATURE_REVIEW.md` for the other six supplied papers and how they relate.
3. **LAMMPS docs**: the dump format (https://docs.lammps.org/dump.html) and SPC/SPC/E (https://docs.lammps.org/Howto_spc.html).
4. **Textbook background on time correlation functions**: Allen & Tildesley, *Computer Simulation of Liquids* (2nd ed.), the chapter on time-dependent properties and correlation functions. Or McQuarrie, *Statistical Mechanics*, the chapter on time correlation functions.
5. **Optional, more advanced**: Alvarez et al. (2023), *J. Chem. Phys.*, on self and cross dipolar relaxation in water (https://doi.org/10.1063/5.0168588).
