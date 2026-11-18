# Slide 1: How does a molecular sum forget its orientation?

Introduce the question. All results are from a geometric molecular-bisector proxy. The complete trajectory passed audit; metadata and full relaxation convergence remain separate limitations.

# Slide 2: Individual rotation and collective memory ask different questions

Anchor: Maurya et al. 2021, Section III.C, equations 2-11, figures 10-12 and Table IV. TIP4P/2005 at graphene is a methodological reference, not the identity of this supplied dataset.

# Slide 3: Every saved frame was audited

The original 7.817 GB source is preserved. Full streaming parser validates every frame, not sampled prefixes. IDs and molecule membership are stable even if atom row order changes. No original model, time step, units or temperature is supplied.

# Slide 4: Use one consistent centering and denominator

Define u as the normalized sum of two minimum-image bond vectors. Means are per molecule over the same segment. Ordinary SMOR is uncentered; connected self is A/A0. COR is B/B0. Cross can be negative. The identity is exact at every lag.

# Slide 5: Check the science independently of the fast estimator

Describe analytic rotation and persistent-mean cases, explicit ordered cross-pair sums, zero-padding and F-k origin normalization, then full-data cadence and membership. Synthetic test fixtures are validation, not empirical findings.

# Slide 6: Geometry supports a proxy, not a force-field assignment

The geometry envelope includes every molecule in every frame. Spatial profiles are projections in fractional coordinates, compared across quarters. Matching SPC-like geometry does not prove SPC/E, charges, or omitted species.

# Slide 7: Compare ordinary self, connected self and centered COR

All F-k origins are included. Ordinary and connected self differ because of finite-sample molecular means. Full curves extend to 10000 lag steps, one tenth of retained duration. Describe the observed curves without claiming a converged time ratio.

# Slide 8: Cross contributions change the collective signal

G_cell=2.69580; self zero-lag=0.37095; cross zero-lag=0.62905. Both terms use B0, so they are not separately unit-normalized. Negative dynamic values are allowed. Static amplitude alone does not establish relaxation ordering.

# Slide 9: Report finite-cutoff integrals, not full relaxation times

Running integrals use the trapezoidal rule. Discuss drift, sign changes and the cutoff table in the report. Fixed-window exponential fits are secondary descriptions with residual screens, not validation of the full tail.

# Slide 10: One trajectory gives block variation, not many independent replicas

Quarters are nonoverlapping and use means estimated within each segment. Their reporting lags are no more than one tenth of their durations. Halves provide integral comparisons. Do not call curves confidence intervals. Temperature and energy equilibration cannot be checked without logs.

# Slide 11: Centering and saved cadence are part of the result

Subtracting noisy molecular means changes connected self; total mean subtraction changes collective relaxation. Every-second-frame analysis tests saved-cadence sensitivity but does not recover fast unsaved motion. Initial 10% removal is not claimed to be a thermal equilibration cutoff.

# Slide 12: What the supplied data establish

Close with the strongest supported statements: complete audit, numerically validated geometric orientation correlations, exact cross decomposition, and quantified sensitivity. Missing metadata and independent longer sampling are concrete next steps, not presumed facts.

# Slide 13: Six-person speaking and review allocation

These roles allocate presentation and review. Everyone should understand the exact decomposition and principal limitations. The complete reusable implementation is shared across the team.

# Slide 14: Prepare to defend definitions and limitations

Why can COR differ from SMOR? The correlation of a sum includes distinct-molecule cross terms.
Why is each contribution not normalized to one? Both use B(0), so self(0)=1/G_cell and cross(0)=1-1/G_cell.
Can a cross term be negative? Yes. Anticorrelated orientations can cancel self contributions.
Why no picoseconds or model name? The integration timestep, units and charge model are unavailable; geometry is not provenance.
Why subtract molecular means? It gives an exact connected decomposition, but finite-record means can bias the long tail; ordinary SMOR is also shown.
Why zero-pad and divide by F-k? To avoid circular wraparound and account for fewer origins at larger lag.
Does G_cell determine time ordering? No. Dynamic cross terms and convergence are also needed.
Why is full tau unresolved? Finite cutoffs, mean estimation and segment variation do not establish a stable full-time integral or tail.
Are 2,744 molecules independent COR samples? No. COR has one summed vector per saved frame and temporally overlapping origins.