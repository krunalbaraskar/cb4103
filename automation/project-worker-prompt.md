# Authorized unattended COR/SMOR project

The user explicitly asked to schedule this project after 7:44 AM India time on 15 November 2026 and to work on it end to end. You are the scheduled worker starting at or after 7:45 AM. Perform the work, do not merely propose another plan. The scheduling turn intentionally did not start scientific implementation before this time.

Workspace: `F:\Sem 7\CB4103\PROJECT`.

Read `PROJECT_PLAN.md`, `research/LITERATURE_REVIEW.md`, `research/trajectory_audit.json`, and any applicable AGENTS.md. If present, read `WORK_LOG.md`, `automation/status.json`, and existing source/results before acting. Continue from checkpoints; preserve user edits and the raw trajectory and supplied PDFs. The six student roles in the plan are organizational context: you must complete all necessary implementation and deliverables yourself. Do not spawn other agents unless the user later explicitly authorizes it.

## Context and scientific limits

- Course project: collective orientational relaxation (COR) versus single-molecule orientational relaxation (SMOR).
- The user has a team of six, approximately three days, and a laptop with NVIDIA RTX 4050. Online compute is possible, but do not provision paid resources or make purchases. CPU analysis of the existing dataset is the primary path.
- `dumpr.lammpstrj` is 7,817,235,449 bytes. Initial inspection found 8,232 atoms, 2,744 water-like groups of two type-1 atoms and one type-2 atom, wrapped Cartesian coordinates, molecule IDs, a periodic orthorhombic box, sampled steps 0/10/20 through 100000. The first frame's inferred bond geometry is approximately 1.0 length unit and 109.47 degrees. Full integrity, frame count, cadence, chemistry, and stationarity must be verified.
- The user confirmed they do NOT know the original water model, units, integration timestep, temperature, or whether this dump is a subset of a larger system. Do not ask for these again as a prerequisite. Do not invent them. Use simulation-step lag units and state assumptions. Treat constant identical dipoles following the molecular bisector as a tested assumption/proxy, not proven force-field provenance. SPC-like geometry alone does not establish SPC/E.
- The supplied 2021 Maurya et al. graphene-water PDF is the anchor, especially Section III.C, Eqs. 2-11, Figs. 10-12, Table IV. It uses TIP4P/2005 and different geometry; do not claim exact reproduction of its numerical results. All seven supplied PDFs and extracted text are under `Papers/Papers` and `research/paper_text`. HTR/HTR+ hydrate classification is optional future context, not required core scope.
- Distinguish ordinary first-rank SMOR, connected molecular self correlation, collective COR, and collective-normalized self/cross terms. Keep the same collective denominator for the decomposition, allow negative cross terms, and disclose centering sensitivity. Do not infer relaxation ordering from a static factor alone. Never call a truncated/noisy integral a converged full relaxation time.

## Required end-to-end outcome

1. Implement a documented, reusable local analysis package/CLI and configuration. Create an isolated environment with compatible versions, recording actual dependencies. Use an available supported Python version if the default Python 3.15 lacks scientific wheels. Check available disk/RAM. Use streaming input, compact memory-mapped orientation arrays, batching, and float64 accumulation; do not load the full text trajectory into RAM or repeatedly scan it unnecessarily.
2. Validate every frame's headers, box interpretation, IDs, molecule mapping, membership, finite data, cadence, and truncation. Reconstruct intramolecular minimum-image bond vectors by molecule/atom ID. Cache steps, orientations, stable molecule ordering, box lengths, and provenance. Preserve enough metadata/geometry diagnostics for an independent assessment. Complete the full existing dataset, not only a tiny demonstration.
3. Calculate ordinary first-rank SMOR, connected self correlations, centered collective COR, collectively normalized self/cross contributions, the explicitly defined finite-cell factor, running integrals, and supported fit estimates. Implement direct and zero-padded FFT estimators with correct origin-count normalization. Inspect centering effects, spatial profiles, trajectory halves/blocks, lag-cutoff sensitivity, and sampling limits. Optional rank-two SMOR may be added only after the core is complete.
4. Write meaningful tests for scientific correctness: periodic reconstruction, unsorted IDs/molecules, malformed frames, known orientation cases, FFT/direct agreement, explicit small-system pair-sum agreement, normalization/decomposition, actual frame cadence, and estimator/centering behavior. Run them and fix failures. Preserve test output and validation details. Do not use tests that merely duplicate the implementation or fabricate data as empirical results.
5. Run the real analysis to completion and produce clear, properly labeled PNG figures (plus SVG/PDF where useful). Include molecular/geometry/spatial diagnostics, SMOR versus COR, the self/cross decomposition, and running-integral/convergence plots. Show uncertainty only when justified; otherwise show block variation and explicitly mark unresolved quantities. Use simulation steps throughout unless independently verified metadata becomes available. Do not claim temperature or energy equilibration without logs.
6. Write a complete course-project report grounded in actual generated results, with methods, figures, tables, literature citations, validation, limitations, and interpretation. Separate published benchmark numbers from measured results. Deliver both readable Markdown and a well-formatted PDF, and an editable PowerPoint presentation. Inspect representative rendered pages/slides if practical. Include a six-person presentation/task allocation and likely viva questions. Avoid filler and invented findings.
7. Write a top-level README with exact environment/setup/run/test/reproduce commands and artifact locations. Save a machine-readable result summary and validation report. Include a submission-ready deliverables folder or manifest without copying the multi-gigabyte raw trajectory. Update `WORK_LOG.md` continuously with completed work, decisions, commands/results, remaining steps, and any real limitations.

Required final artifact paths:

- `README.md`
- `results/metadata.json`
- `results/correlations.csv`
- `results/summary.json`
- `results/validation.json`
- `reports/final_report.md`
- `reports/final_report.pdf`
- `reports/presentation.pptx`
- `figures/` with the real diagnostic and result figures
- reusable analysis source, configuration, and meaningful tests

`results/validation.json` must contain boolean `overall_pass`, true only after real tests and required checks passed, plus the actual commands/results and material scientific limitations. Passing numerical checks does not mean physical metadata or relaxation convergence is established; report those independently. An unresolved physical relaxation time is acceptable if analyzed rigorously and explained.

## Autonomous execution

Continue across dependency problems, numerical failures, and routine implementation choices. Ask no optional questions that would stop unattended work. Keep all credentials private. Do not publish, email, message teammates, upload private data, or change unrelated user settings. Do not use destructive filesystem cleanup against the raw inputs. Use temporary files/environments within the project when practical.

The scheduler has a lock and records each worker invocation. At checkpoints, make the work resumable from project files. A wrapper can launch a continuation if necessary; do not assume that launching a process or creating a plan satisfies the project. Return status `complete` only when all required deliverables exist, the real full-data analysis has run, and validation passed. If a genuine blocker remains, finish all independent work and describe it concretely in `WORK_LOG.md` and the structured final response. Otherwise keep working to completion in this invocation.

Your final response must match the supplied output schema: status (`complete`, `incomplete`, or `blocked`), summary, completed_deliverables, remaining_work, validation, and needs_user_input. Never return `complete` just to stop a long run.
