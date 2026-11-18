# COR versus SMOR: complete trajectory analysis

The full 7,817,235,449-byte supplied trajectory was analyzed: **10,001 frames, 8,232 atoms, 2,744 stable water-like groups**, steps 0-100000 with every interval equal to 10. The original trajectory and seven PDFs are preserved.

The centered finite-cell factor is **G_cell = 2.695802**. Integrals through **10,000 steps** are **3684.983 steps** (ordinary rank-one SMOR), **3096.300 steps** (connected self), and **4520.638 steps** (COR). They are **truncated integrals**. Full relaxation times and their ordering remain unresolved. The last 2,000 lag steps still add 282.90 and 413.86 steps to the ordinary SMOR and COR integrals, respectively.

Start with [the report](reports/final_report.pdf), [editable slides](reports/presentation.pptx), [result summary](results/summary.json), and [validation](results/validation.json). The report is also [readable Markdown](reports/final_report.md). [The submission manifest](submission/manifest.json) and `submission/COR_SMOR_submission.zip` collect deliverables without the multi-gigabyte source or environment.

## Environment (PowerShell, project directory)

The actual isolated interpreter is **CPython 3.12.16**. Installed packages and exact transitive versions are in `requirements.lock.txt`; scientific versions are also recorded in `results/summary.json` and `results/metadata.json`. Python 3.15 is not used. The local environment is `.venv`; portable interpreter and uv are under `tools/`. No system settings were changed.

With the existing environment, run commands directly; activation is unnecessary:

```powershell
& .venv/Scripts/python.exe -m pytest -q -ra
& .venv/Scripts/python.exe -m corsmor.cli all --config config/analysis.json
```

For a clean environment, download the official portable uv utility if absent. Run from this project folder. Do not delete the existing environment or caches to reproduce; a second environment can be named `.venv-reproduce` if desired.

```powershell
New-Item -ItemType Directory -Force tools | Out-Null
Invoke-WebRequest -Uri 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' -OutFile tools/uv.zip
Expand-Archive -LiteralPath tools/uv.zip -DestinationPath tools/uv -Force
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD 'tools/python'
$env:UV_CACHE_DIR = Join-Path $PWD 'tools/uv-cache'
& tools/uv/uv.exe venv --python 3.12.16 .venv
& tools/uv/uv.exe pip install --python .venv/Scripts/python.exe -r requirements.lock.txt
& tools/uv/uv.exe pip install --python .venv/Scripts/python.exe --no-deps -e .
& .venv/Scripts/python.exe -m corsmor.cli all --config config/analysis.json
```

Exact versions, rather than a floating package resolver, reproduce this run. Bootstrap network access downloads only software; trajectory data are not uploaded. The package sets a local `MPLCONFIGDIR` only if one is not already provided.

## Stages and checkpoints

```powershell
& .venv/Scripts/python.exe -m corsmor.cli convert --config config/analysis.json
& .venv/Scripts/python.exe -m corsmor.cli analyze --config config/analysis.json
& .venv/Scripts/python.exe -m corsmor.cli figures --config config/analysis.json
& .venv/Scripts/python.exe -m corsmor.cli documents --config config/analysis.json
& .venv/Scripts/python.exe -m corsmor.cli validate --config config/analysis.json
& .venv/Scripts/python.exe -m corsmor.cli package --config config/analysis.json
```

`all` executes these stages in order and fails if final validation fails. `validate` reruns scientific tests and writes `results/validation.json`; numerical success is distinct from physical metadata/convergence. `package` requires passing validation for current source/configuration. For a fresh report with a test-count line, first run `& .venv/Scripts/python.exe -c "from corsmor.validation import run_tests; run_tests()"`; the report otherwise points to the saved test log.

Conversion streams the raw binary file once and checkpoints every 250 complete frames to `cache/checkpoint.json`. An interruption resumes at the saved byte offset after matching source size/mtime and reconstruction configuration. Incomplete trailing cache rows are overwritten on resume. `cache/complete.json` is written only after every expected frame and clean EOF pass. Repeated `convert` calls reuse the complete cache; analysis-only settings (batch, lag, fits) do not force another raw scan. If changing source/reconstruction assumptions, use a **new cache directory** in a copied config. There is no cleanup command against the raw input.

The expected frame/atom/molecule counts and step range in `config/analysis.json` are assertions derived from the initial audit, fully verified by this run. The CLI targets the supplied orthorhombic, fully periodic, three-site format; it rejects triclinic, scaled-only coordinates, changing membership, malformed rows and nonuniform cadence. It resolves coordinates by column name and molecules by IDs, independent of row order. Geometry tolerances are configured in dump units and represent this tested proxy, not general chemistry rules. The primary retained record is all frames (`discard_frames=0`); the automatic first-10%-removed calculation supplies equilibration-cut sensitivity. Validation contains dataset-specific regression checks for this source.

## Scientific definitions

For each inferred central atom, reconstruct the two satellite bonds with the per-frame minimum-image convention. `u_i` is the normalized bond-vector sum; `U = sum_i u_i`. This is a geometric orientation proxy under the tested near-rigid, identical-dipole assumption.

- Ordinary rank-one SMOR: `R(k)/N`, where `R = sum_i <u_i(t) dot u_i(t+k)>`.
- Molecular centering: `v_i = u_i - mean(u_i)` over the retained segment.
- Connected self: `A(k)/A(0)`, where `A = sum_i <v_i(t) dot v_i(t+k)>`.
- Centered COR: `B(k)/B(0)`, where `B = <(U-mean(U))(t) dot (U-mean(U))(t+k)>`.
- Collective self: `A(k)/B(0)`; collective cross: `[B(k)-A(k)]/B(0)`.
- Finite-cell factor: `G_cell = B(0)/A(0)`. Raw and centered-over-N alternative factors are separately recorded.

All origin averages use **F-k** valid pairs. FFTs are zero-padded to at least 2F-1 and accumulate in float64. Both decomposition terms use B(0); neither is separately normalized to one, and cross terms may be negative. The package also supplies direct estimators and explicit ordered-pair validation. Means are reestimated within every half/block. This convention is exact algebraically but sensitive to finite sampling; ordinary SMOR and raw collective alternatives are shown.

Primary lag: 0-10000 steps, at most one tenth of retained duration. Half/quarter windows are similarly restricted. Every-second-frame analysis tests saved-cadence sensitivity, while first-10% removal tests initial-cut sensitivity. Four quarters show variation only; they do not justify confidence intervals. Fits use a declared 100-2500 step exponential window and saved residual/adequacy screens. A fit scale does not establish a full integral time. No rank-two axis or hydrate classifier is mixed into the core analysis.

The water model, units, integration timestep, temperature, charge sites, electrostatics and dump-group completeness are unknown. **Do not convert axes to ps, identify SPC/E from geometry, assign the anchor paper's 300 K conditions, or interpret G_cell as a macroscopic dielectric constant.** Molecular means may reflect finite sampling, orientational order, or an unknown environment. Spatial projections and collective traces cannot establish thermal equilibration without logs.

Methods follow the supplied [Maurya et al. 2021 paper](https://doi.org/10.1063/5.0046817), especially Section III.C and Eqs. 2-11. Its TIP4P/2005 graphene droplets are a published comparison, not this dataset's identity. The [LAMMPS dump reference](https://docs.lammps.org/dump.html) establishes coordinate/box semantics; [SPC/SPC/E documentation](https://docs.lammps.org/Howto_spc.html) explains their shared geometry. All seven supplied papers are contextualized in the report and `research/LITERATURE_REVIEW.md`.

## Artifact map

| Location | Contents |
| --- | --- |
| `src/corsmor/` | Reader/cache, FFT/direct estimators, analysis, figures, documents, validation/packaging, CLI |
| `config/analysis.json` | Input assertions, reconstruction assumptions, batching, lag/cutoff/fit settings |
| `tests/test_science.py` | Analytic and adversarial scientific tests; full actual-cache cadence check |
| `cache/orientations.npy` | Float32 `(10001,2744,3)` memory map, 329,313,056 bytes including header |
| `cache/steps.npy`, `molecule_ids.npy` | Actual saved steps and stable molecule ordering |
| `cache/atom_membership.npy`, `groups.npy` | Sorted atom IDs/molecule IDs/types and center/satellite index map |
| `cache/box_lengths.npy`, `box_lower.npy` | Every frame's box geometry in dump units |
| `cache/geometry.npy` | Per-frame all-molecule geometry ranges/moments; column names in metadata |
| `cache/spatial_counts.npy` | `(frames,3,24)` central-site fractional-position bin counts |
| `cache/frame_sha256.npy` | SHA256 of each complete raw frame; aggregate convention in metadata |
| `results/metadata.json` | Full input audit, provenance, geometry, unknowns, resources and software |
| `results/correlations.csv` | All primary curves, lag steps, origin counts and cumulative integrals |
| `results/summary.json` | Static factors, fits, cutoffs, segment results, centering, versions, limitations |
| `results/half_*.csv`, `quarter_*.csv` | Segment curves and integrals with local centering |
| `results/discard_first_10_percent.csv`, `downsample_2.csv` | Sensitivity analyses |
| `results/prefix_factor.csv` | Accumulated factor with prefix means |
| `results/numerical_checks.json` | Actual-data FFT/direct and explicit ordered-pair discrepancies |
| `results/pytest.log`, `pytest.xml`, `test_results.json` | Actual test output, JUnit results and command/return status |
| `results/validation.json` | Boolean `overall_pass`, actual commands/checks and independent scientific limits |
| `figures/01_...` through `08_...` | Geometry, spatial profiles, stationarity, SMOR/COR, decomposition, integrals, blocks, sensitivities; PNG/SVG/PDF |
| `reports/final_report.md`, `.pdf` | Complete actual-results report with tables, citations and limitations |
| `reports/presentation.pptx` | Editable 14-slide deck: 12-slide narrative + team/viva appendices; speaker notes |
| `reports/presentation_layout_preview.pdf` | Companion layout rendering; native Office renderer unavailable |
| `reports/previews/`, `results/document_inspection.json` | Representative actual PDF renders and slide layout inspection |
| `reports/presentation_notes.md` | Editable speaker notes, six-person allocation and viva preparation |
| `research/input_manifest.json` | Original supplied-PDF identities and full trajectory content-fingerprint convention |
| `submission/` | Manifest and compact ZIP, excluding raw trajectory, PDF inputs, caches and environment |
| `WORK_LOG.md` | Decisions, commands/results, checkpoints and final completion audit |

Initial resources: 16.37 GB total RAM, about 4.34 GB available at conversion; about 15.21 GB free disk. Conversion took about 302 seconds. Cache plus diagnostics is approximately 336 MB; batching limits FFT workspace. No GPU, cloud provisioning or additional MD run was required.
