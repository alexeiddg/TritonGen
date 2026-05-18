# Phase 4 Parse Reclassification Disposition

Date: 2026-05-18

## Summary

The first Phase 4 Modal baseline revalidation surfaced a uniform label drift:
all 180 frozen none-baseline rows moved from original canonical
`F0_BAD_SIGNATURE` to aligned-pipeline `F0_PARSE`.

This was not a compile-success regression and not a C1/C2 entrypoint
disagreement. All 180 frozen rows remained `compile_success=false`, and all
180 C1-entrypoint and C2-entrypoint evaluations agreed.

## Disposition

The drift is accepted as an expected parse reclassification. Every original
baseline row had legacy `compile_error_type="SignatureError"` while its
original error message contained a syntax-error wrapper:
`syntax error in generated source`. The aligned Phase 2/Phase 3.4 taxonomy
distinguishes true AST parse failures from launcher signature mismatches, so
these rows should canonicalize as `F0_PARSE`.

The code now canonicalizes legacy Cluster 1 compile labels with both
`compile_error_type` and `compile_error_msg`, preserving true signature
mismatches as `F0_BAD_SIGNATURE` while mapping syntax-wrapper rows to
`F0_PARSE`.

## Evidence

Post-fix evidence-bearing Modal L4 rerun:

```text
modal app id: ap-XarN6whc5xIivJQfSPZfMz
input: outputs/cluster1/baseline_repaired_l4_n20.jsonl
output: outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl
```

Verified artifact counts:

```text
total_rows: 180
original_compile_success=false: 180
new_compile_success=false: 180
compile_success_drift_count: 0
entrypoint_agreement_count: 180
entrypoint_disagreement_count: 0
original_canonical_failure_code=F0_PARSE: 180
new_canonical_failure_code=F0_PARSE: 180
cross_category_label_drift_count: 0
expected_legacy_to_canonical_mapping_count: 180
original messages containing syntax-error wrapper: 180
```

## Classification

`PHASE_4_MODAL_COMPLETED_WITH_EXPECTED_PARSE_RECLASSIFICATION`

This satisfies the Phase 4 baseline comparability question for compile success
and C1/C2 entrypoint identity. The project can proceed to the grammar hash
interlock before the Phase 5 final re-audit, assuming no later review finds an
unrelated issue.
