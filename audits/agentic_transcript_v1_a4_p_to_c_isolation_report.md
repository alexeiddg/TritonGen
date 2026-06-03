# Agentic Transcript v1 A4 P-to-C Isolation Report

Date: 2026-06-03
Status: complete with baseline-venv caveat
Classification: A4_P_TO_C_ISOLATION_COMPLETE_WITH_WORKTREE_CAVEATS

## Executive Summary

A4 adds a focused prompt-level isolation proof for the combined A2/A3 state.
The tests exercise the real Cluster 3 runner, real Cluster 3 P loop, and real
Cluster 3-to-Cluster 2 C adapter with local synthetic generation/correctness
callables. The post-P F2 C prompt uses the agentic C history path, contains the
C seed source and public C correctness evidence, while excluding P compile-error
text, P compile-error type, P attempt-history labels, P compile-error hashes, P
prompt/history hashes, and non-seed P source hashes.

A4 includes a narrow runner/adapter bridge patch so the Cluster 3 runner
forwards the resolved repair-history config to the C adapter, and the adapter
forwards that explicit config to the Cluster 2 repair loop. The adapter still
records `post_p_f2` metadata and rejects custom C feedback containing P compile
or private-eval markers before C generation.

## Worktree Status

- Worktree: `/private/tmp/tritongen-llm-repair-memory`
- Branch: `codex/llm-repair-memory-agentic-transcript-v1`
- Entry HEAD: `d2a9f2a A3: Integrate agentic transcript v1 P-loop repair memory`
- Current status: branch ahead of origin by 2 commits with only the A4
  isolation test, narrow Cluster 3 runner/adapter C-loop repair-history bridge,
  runner regression coverage, and A4 report/handoff docs changed.
- Baseline venv interpreter used for validation:
  `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python`
- No Modal, GPU, real generation, experiment execution/artifact, n=5, n=20,
  paper-scale, or `outputs/` mutation was performed.

## Files Changed

- `cluster3/tests/test_p_to_c_isolation.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/feedback/c_loop_adapter.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `audits/agentic_transcript_v1_a4_p_to_c_isolation_report.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/experiment_change_orchestration_state.md`

## P-to-C Handoff Path Identified

The P-to-C handoff path is:

1. `cluster3.experiments.run_cluster3_modal._run_generated_cell`
2. `cluster3.experiments.run_cluster3_modal._call_c_loop`
3. `cluster3.feedback.c_loop_adapter.run_cluster3_c_loop_from_f2`
4. `cluster2.feedback.repair_loop.run_repair_loop`

For post-P F2, Cluster 3 passes the P terminal source and public F2 result as
the C seed candidate with `c_loop_source="post_p_f2"`. The adapter now accepts
an explicit repair-history config for C prompt rendering, and the Cluster 3
runner forwards its resolved config into the adapter. The C handoff still does
not accept P repair history, P repair trace objects, or P compile transcript
text.

## C Prompt Isolation Proof

`test_post_p_f2_c_prompt_excludes_p_compile_history_text_and_hashes` runs a
synthetic `C+P` row where:

- initial evaluation returns `F1_COMPILE` with a unique A4 compile sentinel;
- explicit `agentic_transcript_v1` renders the P prompt;
- the P attempt returns `F2_NUMERIC_LARGE`;
- the integrated Cluster 3 runner calls the real C adapter, which builds an
  explicit agentic C repair prompt from the post-P F2 seed.

The test proves the P prompt contains the sentinel, P compile type, and P
attempt history, while the C prompt contains the agentic C repair objective, C
attempt-0 history, the C seed source, C failure code, and public C correctness
summary.

## P Transcript Exclusion Proof

The same test asserts the C prompt excludes:

- P compile-error excerpt text;
- P compile-error type;
- `p_compile_error_type=` and `p_compile_error_changed=` history labels;
- `Compile error excerpt` text;
- the P repair objective text;
- P-specific attempt-history labels;
- non-seed P source hashes;
- P feedback hashes;
- P compile-error excerpt hashes;
- P prompt hash and P history summary hash.

The post-P seed source hash may appear as the C attempt-0 source hash because
the P terminal F2 source becomes the public C seed. The row's generated C repair
trace remains disjoint from P repair-attempt source hashes. C seed provenance may
also record the post-P seed source hash as metadata.

## Direct Initial-F2 C Path Proof

`test_initial_f2_c_prompt_uses_public_c_evidence_without_p_transcript` proves
the direct initial-F2 route with explicit `agentic_transcript_v1`:

- does not fire P;
- records `c_loop_source="initial_f2"`;
- builds an agentic C prompt containing C attempt history, the initial source,
  F2 failure code, and public C correctness summary;
- excludes all P compile sentinel text, P compile type, and P history labels.

## Post-P F2 C Path Proof

The post-P path is covered by the end-to-end prompt test and by
`test_adapter_records_post_p_source_without_rendering_p_logs_to_c_prompt`.
Together they prove the adapter records `c_loop_source="post_p_f2"` and
`seed_source_hash` metadata while keeping P compile evidence out of prompt text.

## Fail-Closed Behavior

No new fail-closed code was needed. Existing adapter behavior is covered by
`test_adapter_rejects_p_compile_markers_from_custom_c_feedback_before_generation`,
which injects P compile sentinel text through a custom C feedback builder and
asserts that the adapter raises before any C generation call.

## Legacy Byte-Invariance Proof

`test_legacy_post_p_c_prompts_match_default_and_explicit_legacy` compares the
post-P P prompt and subsequent C prompt for omitted policy versus explicit
`last_attempt_only_v1`. Both prompt strings remain byte-identical.

The existing A1 shared suite also re-verifies legacy C and P prompt snapshot
byte invariance.

## Tests Run

- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest shared/tests/test_repair_history_policies.py shared/tests/test_repair_history_errors.py shared/tests/test_repair_history_evidence.py shared/tests/test_repair_history_ranking.py shared/tests/test_repair_history_rendering.py -v`
  - Result: 63 passed
- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_feedback_prompts.py cluster2/tests/test_repair_loop.py cluster2/tests/test_results_logger.py cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_cluster2_boundary.py -v`
  - Result: 209 passed, 1 skipped
- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_p_repair_loop.py cluster3/tests/test_cluster3_schema.py cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_cluster3_imports.py -v`
  - Result: 293 passed
- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_p_to_c_isolation.py -v`
  - Result: 7 passed
- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -v`
  - Result: 96 passed
- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -c "import cluster2.feedback.repair_loop; import cluster3.feedback.compile_error_repair; import shared.repair_history.rendering; print('a4_imports_ok')"`
  - Result: `a4_imports_ok`

## No-Run Boundary Check

Completed command:

```text
git diff --name-only -- cluster1 cluster2/experiments cluster2/results cluster3/results shared/analysis outputs
```

Result: empty output.

`cluster3/tests/test_c_loop_adapter.py` does not exist, so there was no
additional adapter test file to include.

## Negative Scope Verification

A4 changed only the focused Cluster 3 isolation test, the narrow Cluster 3
runner/adapter C-loop repair-history config bridge, one Cluster 3 runner
regression assertion, and handoff/report docs. It did not modify Cluster 1,
Cluster 2 runtime/results/experiments, Cluster 3 results, shared analyzers,
outputs, Modal app/image/function definitions, dependency files, or lockfiles.

`git diff --check` passed with empty output. A trailing-whitespace scan over the
touched A4 runner/adapter/test/report/handoff docs also returned no matches.

## Unresolved Risks

- The feature worktree continues to use the baseline repository venv at
  `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python`.
- A2/A3/A4 remain pending independent review before promotion.

## Classification

A4_P_TO_C_ISOLATION_COMPLETE_WITH_WORKTREE_CAVEATS

## Next-Step Recommendation

Request independent review of the A4 test proof before moving to A5 analyzer
policy grouping.
