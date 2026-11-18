# COR and SMOR: a three-day course-project plan

Prepared 14 November 2026. Constraints: six students, three days, one laptop with an NVIDIA RTX 4050; online compute available if useful. The original simulation model, timestep, units, temperature, and dump-group selection are unknown.

## 1. Recommended project

**Title: Collective versus single-molecule orientational relaxation in a water-like molecular-dynamics trajectory: the role of intermolecular correlations.**

**Research question:** How does the relaxation of the summed molecular orientation differ from the orientation memory of individual molecules, and how much of that difference comes from correlations between different molecules?

Use the supplied trajectory as the main dataset and the supplied Maurya et al. 2021 paper as the methodological anchor. Deliver a correct, reproducible analysis with an explicit convergence assessment. Treat numerical comparison with literature as conditional on matching simulation metadata.

The essential result is a decomposition of collective relaxation into self and intermolecular contributions, supported by uncertainty estimates. A result that the trajectory is too short to establish a relaxation-time difference is scientifically valid if demonstrated clearly. Do not choose an expected ordering of COR and SMOR before analyzing the data.

### Minimum deliverables

1. A validated trajectory reader and compact orientation cache.
2. First-rank SMOR and COR curves on the same time axis.
3. Collective self/cross decomposition and a finite-cell orientational correlation factor.
4. Running relaxation integrals, block comparisons, and a clear statement of convergence.
5. A report of approximately 6–8 pages, 10–12 presentation slides, and reproducible scripts/configuration. Adjust lengths to the course rubric.

Choose at most one extension after these work: second-rank SMOR, hydrogen-bond-conditioned SMOR, or a separately documented reference simulation. New graphene droplets, hydrate nucleation, and a new implementation of HTR/HTR+ are outside the three-day core scope.

## 2. What is already available

The inspection results are recorded in [research/trajectory_audit.json](research/trajectory_audit.json). Seven frames were sampled; this was not a full integrity scan.

| Item | Observed evidence | Consequence |
| --- | --- | --- |
| File | `dumpr.lammpstrj`, 7,817,235,449 bytes, approximately 7.28 GiB | Read sequentially and cache only the required quantities. |
| Atoms | 8,232 in each sampled frame | Check this in every frame during conversion. |
| Molecules | First frame has 2,744 molecule IDs, each with two type-1 atoms and one type-2 atom | Consistent with three-site water; elemental identities remain inferred. |
| Coordinates | `x y z`, with `mol` and `id` available | Reconstruct each molecule using its IDs and minimum-image bond vectors. |
| Other fields | Velocities and forces; no charges or image flags | Orientations are accessible; absolute molecular dipoles require a model. |
| Box | Orthorhombic, `pp pp pp`; sampled side lengths approximately 43.5183 in dump units | Use the box from each frame; spatial homogeneity still needs checking. |
| Steps | Initial steps 0, 10, 20; final step 100000 | A cadence of 10 would imply 10,001 frames, but confirm every frame. |
| Geometry | First-frame inferred O–H distances approximately 1.0000; mean H–O–H angle approximately 109.47 degrees | If lengths are angstroms, this matches SPC/SPC/E geometry, without identifying the force field. |

SPC and SPC/E share geometry but have different charges. Geometry alone does not establish the model. See the [official LAMMPS SPC/SPC/E description](https://docs.lammps.org/Howto_spc.html).

The dump might contain only a selected atom group. Its water-like composition and periodic box do not prove that the underlying simulation was homogeneous bulk water or that no substrate/solute was present outside the dumped group.

### Working without the original input/log

Proceed with orientation-based quantities and label the horizontal axis **lag in simulation steps**. For a complete, uniformly sampled file, lag index `k` corresponds to `10 k` steps. Do not label steps as femtoseconds or picoseconds.

For illustration only, 100000 steps would span 100 ps at a 1 fs timestep or 200 ps at a 2 fs timestep. Neither timestep is established here. LAMMPS permits different unit styles and timesteps: [units documentation](https://docs.lammps.org/units.html).

State the central assumption: **each inferred water molecule represents an identical rigid molecular dipole whose direction follows the molecular bisector**. Verify nearly constant geometry across the trajectory. Under this assumption, a common unknown dipole magnitude cancels from normalized SMOR, COR, and the correlation factor. Otherwise label the result a geometric orientation analysis, rather than a complete dielectric analysis.

Do not report absolute dipoles, a dielectric constant, temperature dependence, or physical relaxation times from the supplied dump alone. If metadata becomes available later, update the configuration and regenerate the outputs.

## 3. How the papers support the project

The direct reference is [Maurya et al., JCP 154, 164704 (2021)](https://doi.org/10.1063/5.0046817), supplied in `Papers/Papers/`. Read Section III.C, Eqs. (2)–(11), Figs. 10–12, and Table IV first. It uses dipole autocorrelations for SMOR, total-dipole fluctuations for COR, and self/cross terms to explain their difference. Its TIP4P/2005 graphene-droplet calculations are a reference for the method and mechanism, not an exact match to this uncharacterized trajectory.

The paper reports bulk-water SMOR/COR times of 5.37/11.86 ps, versus 5.43/0.90 ps for its usual graphene–water interaction. These illustrate that collective and individual relaxation can change in different directions. Keep these values in a separate **published results** table, never in the project's measured-results column. [Source: Table IV](https://doi.org/10.1063/5.0046817).

More recent research reinforces the emphasis on intermolecular contributions: [Alvarez et al. (2023)](https://doi.org/10.1063/5.0168588) separate self and cross-dipolar relaxation in liquid water, while [Nakano and Tanaka (2026)](https://pubs.rsc.org/en/content/articlelanding/2026/cp/d5cp03962b/unauth) investigate their spatial distribution. These motivate the question; this project does not attempt their simulation scale.

The other supplied papers have distinct roles. HTR (2022) and HTR+ (2024) concern hydrate structural identification; the methane-hydrate interface paper supplies possible future interface context. The molten-carbonate, electrolyte-diffusion, and polymer-pressure papers provide broader MD background. Their methods are not prerequisites for COR/SMOR. The polymer-pressure PDF is a **2000** paper despite its `2020_` filename. See [the literature notes](research/LITERATURE_REVIEW.md) for the complete reading order.

## 4. Mathematical specification

### Molecular orientation

For molecule `i`, reconstruct the vectors from the inferred oxygen to its two hydrogens:

\[
\mathbf b_{ia}=\operatorname{MIC}(\mathbf r_{H_a}-\mathbf r_O),\qquad
\mathbf u_i=\frac{\mathbf b_{i1}+\mathbf b_{i2}}{|\mathbf b_{i1}+\mathbf b_{i2}|}.
\]

For each periodic orthorhombic direction, `MIC(d) = d - L round(d/L)`. Use molecule IDs and atom IDs; do not rely on row order or on every three consecutive rows belonging to a molecule. Check that the two bond lengths and angle remain plausible after reconstruction. The dump fields are documented in the [LAMMPS dump reference](https://docs.lammps.org/dump.html).

For a neutral, symmetric three-site water model with equal hydrogen charges, the physical dipole is proportional to `b1 + b2`. A rigid identical-dipole model therefore permits normalized correlations using `u` alone. Virtual charge sites, flexible geometry, or polarization require model-specific treatment; [LAMMPS explicitly distinguishes TIP4P dipole computation](https://docs.lammps.org/compute_dipole.html).

### SMOR and collective orientation

The ordinary first-rank SMOR is

\[
C_1^{s}(t)=\frac1N\sum_i\langle\mathbf u_i(t_0)\cdot\mathbf u_i(t_0+t)\rangle_{t_0}.
\]

Form `U(t) = sum_i u_i(t)`. To obtain an exact fluctuation decomposition, define `v_i = u_i - <u_i>` and `delta U = sum_i v_i = U - <U>`, with one consistent set of means and time-origin rules. Then define

\[
A(t)=\sum_i\langle\mathbf v_i(t_0)\cdot\mathbf v_i(t_0+t)\rangle,\quad
B(t)=\langle\delta\mathbf U(t_0)\cdot\delta\mathbf U(t_0+t)\rangle.
\]

\[
C_s(t)=A(t)/A(0),\qquad C_{COR}(t)=B(t)/B(0).
\]

`C_s` is the connected self correlation. In an isotropic equilibrated system with vanishing molecular mean orientations it agrees with `C_1^s`. Compute the ordinary SMOR as well and inspect the effect of centering. On a short trajectory, subtracting separate noisy molecular means can bias long-time behavior; report that sensitivity rather than hiding it. A persistent mean may also indicate orientational order, an interface, an external field, or insufficient sampling.

### Self/cross decomposition

\[
C_{COR}(t)=\underbrace{A(t)/B(0)}_{C_{self}^{coll}(t)}+
\underbrace{[B(t)-A(t)]/B(0)}_{C_{cross}^{coll}(t)}.
\]

Both contributions use the **same collective denominator**. They do not each start at one. The cross term may be negative. Compute it by subtraction; an explicit all-pairs molecular loop is unnecessary for the total contribution.

Define a finite-cell fluctuation factor

\[
G_{cell}=B(0)/A(0).
\]

It follows that the zero-lag collective self and cross contributions are `1/G_cell` and `1 - 1/G_cell`. For identical rigid dipoles with negligible means, this is the finite-cell dipolar factor used in the anchor paper. Label the convention explicitly: boundary conditions matter when comparing finite-cell factors with macroscopic Kirkwood factors.

Do not impose `tau_COR = G_cell tau_SMOR` as an exact identity. The anchor paper retains a dynamic correction, and positive static cross-correlation alone does not establish the ordering of relaxation times.

### Relaxation times

Use the running integral as the primary diagnostic:

\[
\tau_X(t_{max})=\int_0^{t_{max}}C_X(t)\,dt.
\]

With the current metadata, the integral has units of **simulation steps**. Plot its dependence on the upper cutoff. Report a converged integral only if there is a stable region before the noise-dominated tail. If there is no plateau, report a truncated integral with its cutoff and label the full time unresolved.

As a secondary description, fit a visibly exponential decay region to `a exp(-t/tau_fit)` and disclose the fit window and residuals. A tail-fit time and a full integral time need not agree. Avoid fitting a stretched or multi-exponential model just because it has more parameters. Compare `tau_COR/tau_s` only using consistent definitions and only when both estimates are resolved.

Second-rank SMOR, `C_2^s = <[3(u(0).u(t))^2 - 1]/2>`, is optional. Label it separately. A rank-two curve, or an O–H-axis correlation used for spectroscopy, is not interchangeable with first-rank molecular-dipole SMOR.

## 5. Implementation and validation

Use Python with NumPy, SciPy, and Matplotlib; MDAnalysis is optional. The current default Python has none of these installed. Create an isolated analysis environment using a Python/package combination with available wheels, then record actual versions. Paper text was extracted separately using a temporary PDF-reader environment.

### Shared data contract: agree in the first two hours

| Artifact | Contract |
| --- | --- |
| `metadata.json` | Source file, inferred atom mapping, unknown fields as null, assumptions, exclusions, retained step range, software versions. |
| `steps.npy` | Actual integer timestep of every retained frame; never reconstruct the sequence before validating it. |
| `orientations.npy` | Shape `(frames, molecules, 3)`, stable molecule order, float32 cache; use float64 for sums/correlations. |
| `molecule_ids.npy` | Explicit ordering corresponding to the molecule axis. |
| `box_lengths.npy` | Shape `(frames, 3)`; reject unexpected triclinic formats rather than applying the orthorhombic formula silently. |
| `correlations.csv` | Lag steps, ordinary SMOR, connected self, COR, collective self, collective cross, number of contributing origins. |
| `summary.json` | Correlation-factor convention, fit/integral settings, block variation, results, and unresolved quantities. |

For 10,001 frames and 2,744 molecules, the float32 orientation array is approximately **314 MiB** before overhead. Cache generation should stream the 7.28 GiB text input once. The parser must detect duplicate/missing IDs, inconsistent molecule composition, incomplete frames, changing membership, and nonuniform or repeated steps.

Use FFT-based autocorrelation with zero padding to at least `2F-1` samples and divide each lag sum by its actual origin count `F-k`. Batch molecules to limit temporary memory. Keep the direct time-domain calculation for a small independent validation subset. Do not use circular correlation inadvertently.

### Required checks before interpreting curves

- Molecular geometry and unit-vector norms remain sensible, including molecules split across periodic boundaries.
- SMOR and COR equal one at zero lag within numerical precision, and the collective decomposition reconstructs COR at every lag.
- On a small subset, explicitly summing `i != j` cross terms agrees with `B-A`. This independently checks the decomposition.
- FFT and direct calculations agree on a short trace with matching centering and normalization.
- Plot `U_x`, `U_y`, and `U_z`; compare means, variances, geometry, and spatial number profiles across time blocks. These can reveal problems but cannot establish temperature/energy equilibration without the original logs.
- Repeat core results for trajectory halves and, only if sufficiently long, several blocks. Block lengths must greatly exceed the decay time being estimated. Overlapping origins and 2,744 molecules do not create 2,744 independent measurements of the collective signal.
- Use a conservative reporting lag, initially at most one tenth of the retained duration. Examine cutoff sensitivity rather than extending the curve until only a few origins remain.
- Compare original cadence with a modestly downsampled analysis. Preserve short-time resolution if early-time motion is discussed.

If blocks are too short or too few for defensible intervals, show block-to-block variation and call the uncertainty preliminary. Do not bootstrap individual frames as independent observations. Do not assume the first saved frame is equilibrated; document any removal and its sensitivity.

## 6. Six-person allocation

These are team assignments for the students, with fixed interfaces so work can proceed in parallel.

| Person | Ownership | First handoff | Final responsibility |
| --- | --- | --- | --- |
| 1 | Scientific lead, literature, metadata and assumptions | Equations, source table, unknown-metadata statement by hour 3 | Integrate report; keep published and measured results distinct. |
| 2 | Streaming reader and molecular reconstruction | Small validated cache by hour 4; complete cache by hour 12 | Dataset manifest, parser checks, reproducible conversion. |
| 3 | SMOR analysis | Direct implementation on the sample cache by hour 6 | Ordinary/connected self curves and relaxation integrals; optional C2. |
| 4 | COR and self/cross analysis | COR on the sample cache by hour 6 | Decomposition, G_cell, collective relaxation estimates. |
| 5 | Independent validation and uncertainty | Independent small-system direct calculation by hour 8 | Audit conventions, frame integrity, centering, blocks, fits, and convergence. |
| 6 | Figures, slides, and reproducibility | Figure templates and report/slide outline by hour 4 | Consistent axes/captions, final plots, run instructions, presentation rehearsal. |

Person 5 should verify definitions independently rather than only rerunning Persons 3 and 4's code. Persons 1 and 6 can draft introduction, methods, and limitations before numerical results arrive. Name one integration owner for each script to avoid competing edits.

## 7. The 72-hour schedule

Hours are elapsed time from project kickoff, not an assumed submission time. Plan normal rest and use unattended jobs overnight.

| Window | Work and handoffs | Exit criterion |
| --- | --- | --- |
| 0–4 h | Read anchor Section III.C; agree definitions/data contract; inspect geometry and spatial profiles; establish analysis environment. | Small cache loads correctly; scope and assumptions are written. |
| 4–12 h | Stream full trajectory, validate IDs/steps, implement direct pilot SMOR/COR/decomposition; begin figure templates. | Full cache and first correctly normalized curves. |
| 12–24 h | Complete efficient correlation calculations; cross-check direct/FFT results; assess centering, block variability, and integrals. | Core figures exist; decide whether the data resolve relaxation. |
| 24–40 h | Improve uncertainty analysis and compare methods with the anchor paper. Run one optional extension only if the core is stable. | Analysis settings and scientific scope are frozen by hour 40. |
| 40–54 h | Finalize plots, tables, methods, discussion, and limitations; cross-review calculations. | Report draft, slides, and scripts form a consistent package. |
| 54–64 h | Reproduce final outputs from the saved cache/config; audit citations, units, and claims. | One teammate can regenerate the reported numbers. |
| 64–72 h | Rehearse, fix presentation problems, and package submission. | Final report/slides/code/data manifest; retain a submission buffer. |

**At hour 12:** if conversion is slow, profile a small prefix and simplify parsing; do not have six people repeatedly scan the raw file.

**At hour 24:** if COR has no stable relaxation estimate, make the main finding an observed self/cross decomposition plus a quantified sampling limitation. A well-explained limitation is preferable to a precise-looking extrapolation from noise.

## 8. When additional compute helps

The main workload is text parsing and correlations on a compact array. Start with the laptop CPU and available RAM; the RTX 4050 is not required to complete the core analysis. Verify RAM and free disk space before conversion. GPU-specific analysis code would add setup work and is unnecessary unless profiling shows a material benefit.

Because the original model and run conditions are unknown, **a new run cannot honestly be called an extension or exact reproduction of this trajectory**. If the core analysis is complete by hour 24 and a functioning MD installation is already available, one teammate may run a separately labeled, fully documented reference case, such as periodic SPC/E water at 300 K with long-range electrostatics. The [LAMMPS model documentation](https://docs.lammps.org/Howto_spc.html) supplies starting parameters; record the final complete input, equilibration procedure, constraints, thermostat, box, timestep, and output cadence.

For that optional case, benchmark a short run, extrapolate runtime including output, and require equilibration checks before production. Aim initially for at least about 1 ns of production, extending only if time and convergence permit; this is a planning target, not a guarantee of converged COR. Save a compact molecular-orientation/dipole trace frequently enough for the intended lag range rather than velocities and forces for every atom.

Use online compute only if the benchmark predicts that a useful completed reference run will miss the analysis freeze on the laptop. Select resources based on a working LAMMPS build and measured throughput; do not assume GPU availability alone provides acceleration. Transfer the small input/reference output as needed, not the 7.28 GiB trajectory unless necessary. Do not make cloud setup a dependency for submission.

## 9. Final figures and report claims

| Figure | Content | What it establishes |
| --- | --- | --- |
| 1 | Molecular bisector diagram, geometry check, and representative spatial number profiles | What is measured and whether the assumed molecular mapping is plausible. |
| 2 | Ordinary/connected first-rank SMOR and COR, with available block variation | Whether individual and collective orientation memory differ over the sampled range. |
| 3 | COR, collective self, and collective cross on one scale | The sign, amplitude, and time dependence of intermolecular contributions. |
| 4 | Running integrals plus half/block comparisons | Which timescales or truncated measures are supported by the trajectory. |

The results table should list dataset identity, lag unit, retained duration in steps, assumed model class, G_cell, relaxation estimator/cutoff, estimates or 'unresolved', and uncertainty method. Put literature values in a separate table with their model, temperature, geometry, and definition.

A useful report sequence is: question and literature; dataset/provenance; correlation definitions; implementation/validation; results; interpretation; limitations and next experiment. Explain why collective cross terms matter without claiming that correlation curves alone prove a unique hydrogen-bond rearrangement mechanism.

### Optional scientific extension

The lowest-risk extension is second-rank SMOR. A more physical extension is hydrogen-bond-conditioned SMOR if units and molecular identities are established. Define the geometry criterion and classify molecules at the time origin; explicitly distinguish this from requiring molecules to remain in a class, which biases the sample toward long residence times. Full HTR/HTR+ cage classification requires a suitable hydrate dataset and independent validation, so leave it as future work here.

### Completion checklist

- [ ] Every retained frame has validated membership, box interpretation, and step spacing.
- [ ] The molecular bisector and constant-dipole assumptions are stated.
- [ ] Time is in simulation steps unless independently verified metadata establishes physical units.
- [ ] Ordinary SMOR, connected self, COR, and collective self/cross are labeled correctly.
- [ ] Direct and efficient calculations agree on an independent small case.
- [ ] Relaxation estimates disclose windows/cutoffs and convergence limits.
- [ ] The supplied trajectory is distinguished from the TIP4P/2005 graphene system in the anchor paper.
- [ ] All final numerical claims can be regenerated from scripts, configuration, and cached arrays.
- [ ] Each teammate can explain the central decomposition and the largest limitation.

## 10. Suggested proposal abstract

We will compare collective and single-molecule orientational relaxation using an existing molecular-dynamics trajectory containing 2,744 water-like molecules. Molecular orientations will be reconstructed from minimum-image intramolecular vectors and analyzed through first-rank self correlations and the autocorrelation of the summed orientation. An exact self/cross decomposition will quantify the contribution of intermolecular orientation correlations. Running relaxation integrals, direct-versus-FFT comparisons, and time-block analysis will assess numerical accuracy and sampling limits. The methods follow the orientational analysis of Maurya et al. (2021), while recognizing that the supplied trajectory's original model and run conditions are unavailable. Results will therefore be reported in simulation-step units under an explicit rigid, identical-dipole assumption. The project will establish which differences between collective and individual relaxation are supported by the available data and identify the additional metadata or sampling needed for quantitative dielectric interpretation.
