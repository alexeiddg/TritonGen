# L2b n20 Partial Wave 1 Launch Surface Blocker Report

## Executive Summary

This report archives the failed partial L2b n20 Wave 1 launch attempt from
baseline `430c342e9743c969fbeb627576a80dcdd7b97a8e`. The run wrote a small
create-only provenance record under the authorized `l2b_n20` namespace, but did
not complete Wave 1 and must not be continued. The next clean launch must use a
fresh signed namespace, proposed as `l2b_n20_attempt2`.

classification: `L2B_N20_PARTIAL_WAVE1_ARCHIVED_LAUNCH_SURFACE_GAP`

## Signed Authorization Reference

- Packet: `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n20_full_coverage_authorization_packet.md`
- Token:
  `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1`
- Baseline: `430c342e9743c969fbeb627576a80dcdd7b97a8e`
- Namespace: `l2b_n20`
- Write policy: create-only, no overwrite, no retry, no resume

## Partial Artifact Summary

```text
result_jsonl_files: 3
actual_rows_detected_by_read_only_validator: 13
content_hash_sidecars: 3
observability_jsonl_files: 3
observability_hash_sidecars: 3
observability_summary_sidecars: 0
completed_waves: 0
analyzer_report_billing_run: no
```

Partial result files:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/elementwise__bf16/grammar_off__c_off__p_off.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/elementwise__fp16/grammar_off__c_off__p_off.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/elementwise__fp32/grammar_off__c_off__p_off.jsonl
```

Partial observability files:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/elementwise__bf16/grammar_off__c_off__p_off.observability.jsonl
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/elementwise__fp16/grammar_off__c_off__p_off.observability.jsonl
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/elementwise__fp32/grammar_off__c_off__p_off.observability.jsonl
```

## Partial Cells

```text
elementwise__fp32/grammar_off__c_off__p_off
elementwise__fp16/grammar_off__c_off__p_off
elementwise__bf16/grammar_off__c_off__p_off
```

## Launch Surface Blockers

The foreground launcher did not complete Wave 1. After interruption, it failed
with an `AttributeError` at `cluster3/experiments/run_cluster3_modal.py:1798`
because the top-level print path assumed a signed run always returned a
`Cluster3RunResult`.

The original packet validation command also referenced
`.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage` before that
module existed in the checkout.

## Launcher Patch

`cluster3/experiments/run_cluster3_modal.py` now fails closed when a signed run
returns no result, using the explicit classification
`L2B_N20_RUN_FAILED_INTERRUPTED_OR_MISSING_RUN_RESULT`. The patch preserves
partial artifacts and does not imply validation success, retry, or resume.

## Validator Surface Reconciliation

`cluster3.analysis.validate_l2b_full_coverage` now exists as a read-only local
validator. It supports post-wave and combined validation, per-shard row counts,
duplicate logical key detection, missing logical key detection, content-hash
sidecar checks, and observability event/hash/summary sidecar checks. It does not
generate rows.

Read-only validation of the archived partial Wave 1 namespace returns
`L2B_FULL_COVERAGE_VALIDATION_FAIL` with 13 actual rows versus 720 expected rows,
0 duplicate logical keys, and 707 missing logical keys.

## Relaunch Strategy

The existing `l2b_n20` roots now exist, so create-only rerun semantics forbid
reusing them. The future clean relaunch namespace is proposed as
`l2b_n20_attempt2`. That namespace is recorded in planning constants but is not
authorized for execution by this report.

Future relaunch requires a separate signed packet or amended packet with exact
attempt2 command surfaces.

## No Execution Proof

This archive and repair phase ran no Modal command, GPU job, generation command,
experiment execution command, analyzer/report command, billing query, Fireworks
command, retry, resume, overwrite, or cleanup command.

## Protected Mutation Proof

This phase did not mutate `mlruns`, `docs/preliminary_report`, dependency files,
or lockfiles. Existing partial `l2b_n20` output and observability artifacts were
preserved as provenance.

## Next Step Recommendation

Prepare a separate signed relaunch packet for `l2b_n20_attempt2`, including
attempt2 output/observability/analysis/report/billing namespaces, then run a new
preflight that proves the attempt2 target roots are absent before any launch.
