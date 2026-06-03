# Agentic Transcript v1 A5 Analyzer Grouping Report

Date: 2026-06-03
Status: complete with baseline-venv caveat
Classification: A5_ANALYZER_GROUPING_COMPLETE_WITH_WORKTREE_CAVEATS

## Executive Summary

A5 adds a narrow analyzer safety layer for repair-history policy metadata. The
factorial analyzer now classifies missing, explicit legacy, explicit agentic,
unknown, mixed, and incomplete agentic repair-history policy states; extends
factorial summary grouping with repair-history policy/template/renderer/budget
keys; and quarantines mixed or incomplete inputs before they can enter headline
paired comparisons or model output.

No metric formula, prompt builder, C-loop behavior, P-loop behavior, runner
execution path, Modal code, output artifact, generation run, n=5 run, n=20 run,
or paper-scale behavior was changed.

## Worktree Status

- Worktree: `/private/tmp/tritongen-llm-repair-memory`
- Branch: `codex/llm-repair-memory-agentic-transcript-v1`
- Entry HEAD: `d1c8196 A4: Prove agentic transcript P-to-C isolation`
- Baseline sequence: `6c859b3` A2 -> `d2a9f2a` A3 -> `d1c8196` A4
- Baseline venv interpreter used for validation:
  `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python`
- No Modal, GPU, real generation, experiment execution/artifact, n=5, n=20,
  paper-scale, MLflow runtime artifact, or `outputs/` mutation was performed.

## Files Changed

- `shared/analysis/factorial.py`
- `shared/tests/test_factorial_analysis.py`
- `shared/tests/fixtures/factorial/*.jsonl`
- `audits/agentic_transcript_v1_a5_analyzer_grouping_report.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/experiment_change_orchestration_state.md`

## Analyzer Surface Identified

The implemented analyzer entry point is `shared/analysis/factorial.py`.

Relevant surfaces:

- `load_results` and `load_result_paths` read JSONL artifacts and call
  `normalize_result_rows`.
- `normalize_result_rows` owns row normalization and now attaches canonical
  repair-history policy classification columns.
- `analyze_factorial` owns paired comparisons, condition rates, and model
  output, and now rejects mixed repair-history analysis groups before those
  outputs are computed.
- `factorial_summary` owns grouped secondary compile diagnostics and now groups
  by repair-history policy/template/renderer/budget/latest-source keys.

## Policy Classification Behavior

Rows are classified as:

- `known_legacy_missing_policy` for missing/null policy when the artifact is
  loaded under the default known-legacy compatibility mode.
- `explicit_last_attempt_only` for explicit
  `repair_history_policy="last_attempt_only_v1"`.
- `explicit_agentic_transcript` for explicit
  `repair_history_policy="agentic_transcript_v1"` with complete required
  metadata.
- `unknown_policy` for unsupported explicit policies or missing-policy artifacts
  loaded with `missing_repair_history_policy_artifact_kind="unknown"`.
- `mixed_policy_artifact` for mixed policy states within one artifact.
- `incomplete_agentic_metadata` for explicit agentic rows missing required
  policy/template/anchor/latest/prompt/source/history metadata.

Cluster 3 `p_` and `c_` repair-history metadata aliases are normalized into the
same analyzer grouping columns as Cluster 2 common repair-history metadata.

## Grouping-Key Behavior

The existing factorial summary grouping keys are preserved. When repair-history
columns are present, `factorial_summary` also groups by:

- `repair_history_policy`
- `repair_prompt_template_version`
- `repair_prompt_renderer_version`
- `repair_max_prompt_chars`
- `repair_include_latest_source`

`analyze_factorial` records the homogeneous repair-history grouping in metadata
and rejects multi-group inputs rather than aggregating legacy and agentic rows
as one headline comparison.

## Quarantine Behavior

The analyzer raises before headline analysis for:

- unknown repair-history policy values;
- missing-policy artifacts explicitly classified as unknown;
- mixed missing-policy and explicit legacy rows in one artifact;
- mixed legacy and agentic rows in one artifact;
- mixed repair-history groups across one `analyze_factorial` input;
- explicit agentic rows missing required metadata;
- inconsistent `repair_prompt_template_version`;
- inconsistent `repair_prompt_renderer_version`;
- inconsistent `repair_max_prompt_chars`;
- inconsistent `repair_include_latest_source`.

`factorial_summary` remains usable for diagnostic separation of multiple
homogeneous artifacts because its grouping keys keep those rows separate.

## Legacy Compatibility Behavior

Existing legacy rows without repair-history policy continue to analyze under the
default known-legacy compatibility mode. They normalize to effective
`last_attempt_only_v1` with state `known_legacy_missing_policy`. Existing
four-cell pairing behavior is preserved by regression coverage.

Explicit `last_attempt_only_v1` rows normalize to the same effective policy but
retain state `explicit_last_attempt_only`, which lets mixed explicitness inside
one artifact be quarantined.

## Fixture Coverage

New fixtures under `shared/tests/fixtures/factorial/` cover:

- all missing policy legacy artifact;
- explicit `last_attempt_only_v1` artifact;
- explicit complete `agentic_transcript_v1` artifact;
- explicit `agentic_transcript_v1` no-render terminal artifact with nullable
  prompt metadata;
- explicit legacy no-render plus rendered terminal artifact proving nullable
  no-render prompt metadata shares the policy group;
- mixed missing-policy plus explicit legacy artifact;
- mixed legacy plus agentic artifact;
- unknown policy artifact;
- explicit agentic missing required prompt/hash metadata;
- inconsistent template version;
- inconsistent max prompt chars;
- inconsistent include-latest-source setting.

## Tests Run

- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -v`
  - Result: 91 passed, 4 skipped
- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest shared/tests/test_repair_history_policies.py shared/tests/test_repair_history_errors.py shared/tests/test_repair_history_evidence.py shared/tests/test_repair_history_ranking.py shared/tests/test_repair_history_rendering.py -v`
  - Result: 63 passed
- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_feedback_prompts.py cluster2/tests/test_repair_loop.py cluster2/tests/test_results_logger.py cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_cluster2_boundary.py -v`
  - Result: 209 passed, 1 skipped
- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_p_repair_loop.py cluster3/tests/test_cluster3_schema.py cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_cluster3_imports.py cluster3/tests/test_p_to_c_isolation.py -v`
  - Result: 300 passed
- `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -c "import shared.analysis.factorial; import shared.repair_history.policies; print('a5_imports_ok')"`
  - Result: `a5_imports_ok`

## Forbidden-Files Check

The A5 implementation does not touch Cluster 1, Cluster 2 feedback/experiments/
results, Cluster 3 feedback/experiments/results, Modal code, or `outputs/`.

Completed command:

```text
git diff --name-only -- cluster1 cluster2/feedback cluster2/experiments cluster2/results cluster3/feedback cluster3/experiments cluster3/results outputs
```

Result: empty output.

## Negative Scope Verification

A5 changed only the analyzer, analyzer tests/fixtures, and handoff/audit docs.
It did not add statistical lift, pass@k, paper-scale, performance, profiler,
timing, speedup, or result-claim logic. It did not modify raw artifacts or run
any experiment.

`git diff --check` passed with empty output.

The trailing-whitespace scan over the analyzer, factorial tests/fixtures, A5
report, and handoff docs returned no matches.

## Unresolved Risks

- The feature worktree continues to use the baseline repository venv at
  `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python`.
- A2/A3/A4/A5 remain pending independent review before promotion.
- A6 run gates are not implemented in A5; no run packet is approved by this
  report.

## Classification

A5_ANALYZER_GROUPING_COMPLETE_WITH_WORKTREE_CAVEATS

## Next-Step Recommendation

Request independent review of the A5 analyzer grouping/quarantine diff. If
accepted, move to A6 run-packet gating only; do not execute Modal, generation,
n=5, n=20, paper-scale, or output-mutating work without a fresh approval packet.
