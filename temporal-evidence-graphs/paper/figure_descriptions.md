# Descriptive figure text

1. **Architecture.** Immutable recording windows feed numerical feature extraction
   and a versioned evidence store. The store supplies scoped generation and direct
   validation. Evidence revisions propagate through dependencies into new display
   versions. Independent evaluation reads the immutable logs, and review actions
   occupy a separate workspace.
2. **Symbolic correction.** Two panels show a target increasing from 2 to 4 while
   an earlier value stays at 1. The derived difference changes from 1 to 3. Old
   direct and downstream claims are withdrawn. An OR claim remains supported by
   an independent value of 2, and the earlier-value claim remains supported.
3. **Reliability.** Six panels compare B0, B1, B2, M1, and B3 for synthetic,
   WESAD, and PPG-DaLiA sources. The upper row reports query-contract case violations and
   the lower row reports required-fact recall. Values and paired uncertainty
   intervals appear in the generated reliability and contrast tables.
4. **Correction.** Six panels show conditional correction completeness and
   collateral withdrawal for the same five methods and three sources. Undefined
   denominators are labeled n/a; underlying counts appear in the correction table.
5. **Streaming.** Four panels compare M1 and B3 at 1, 5, and 20 independently
   scheduled derived events per second. They display p95 flag latency, p95 generated
   candidate-completion latency, peak event backlog, and peak pending explanations.
   Every candidate lacks a required difference; these are not successful-repair times. Dotted
   horizontal lines mark the one- and five-second targets. The flag axis uses a
   logarithmic scale. Exact values and denominator counts are in the systems table.
