# Agentic Transcript v1 A2 C-loop Integration Report

- Date: 2026-06-02
- Worktree: `/private/tmp/tritongen-llm-repair-memory`
- Branch: `codex/llm-repair-memory-agentic-transcript-v1`
- Baseline branch treated as main: `codex-track-handoff-context`
- Start commit: `e3ea1e795951e6844775ef007112fdf4865735f3`
- Prior package: A1 prompt core, commit `368a3c8`
- Classification: `A2_C_LOOP_INTEGRATION_COMPLETE_PENDING_REVIEW`

## Executive Summary

A2 wires the A1 `agentic_transcript_v1` prompt core into the Cluster 2 C repair
loop as an explicit opt-in policy. The default and explicit
`last_attempt_only_v1` path continue to use the existing Cluster 2 feedback
prompt builder. Explicit `agentic_transcript_v1` builds the next repair prompt
from structured public attempt history plus the selected best previous source.

The implementation adds runner/config plumbing and nullable/defaultable generated
row metadata for future analyzer grouping. It does not run Modal, generation,
n=5, n=20, paper-scale, or mutate `outputs/`.

## Files Changed

Implementation:

```text
cluster2/feedback/repair_loop.py
cluster2/experiments/run_cluster2_modal.py
cluster2/results/dataclass.py
```

Tests:

```text
cluster2/tests/test_repair_loop.py
cluster2/tests/test_results_logger.py
cluster2/tests/test_run_cluster2_modal.py
```

Checkpoint docs:

```text
audits/agentic_transcript_v1_a2_c_loop_integration_report.md
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
```

## Implementation Summary

- `run_repair_loop` now accepts an optional `RepairHistoryConfig`.
- Omitted config defaults to `last_attempt_only_v1`.
- Explicit `last_attempt_only_v1` preserves legacy prompt bytes.
- Explicit `agentic_transcript_v1` renders C repair prompts through A1
  `render_repair_history_prompt`.
- Agentic C history is built only from public evidence, source hashes, prompt
  hashes, and in-memory source records.
- Non-F2 failures still terminate without requesting repair generation.
- Malformed agentic evidence, invalid config, and over-budget agentic prompts
  fail closed before a follow-up repair generation is requested.
- `Cluster2RunnerConfig` exposes optional repair-history policy, prompt budget,
  and latest-source flags while preserving current defaults.
- `Cluster2GeneratedRowMetadata` records repair-history policy and nullable
  prompt/hash/anchor metadata; old generated rows missing the new policy field
  load as `last_attempt_only_v1`.

## Metadata Nullability Matrix

| Case | Policy metadata | Prompt/hash/anchor metadata |
|---|---|---|
| Omitted policy / default path | `last_attempt_only_v1` | null except legacy prompt-template label after a repair prompt is built |
| Explicit `last_attempt_only_v1` | `last_attempt_only_v1` | null anchor/hash fields; legacy prompt bytes unchanged |
| Explicit `agentic_transcript_v1`, repair attempt > 0 | `agentic_transcript_v1` | anchor/latest indices, attempt count, prompt SHA256, prompt char count, prompt budget, latest-source setting, anchor/latest source hashes, history summary SHA256 |
| Failed pre-generation agentic render | no normal generated row written by the local loop path; exception propagates before the next generation call |
| Attempt 0 success | selected policy label, no repair-history prompt metadata |
| Attempt 0 terminal non-repairable failure | selected policy label, no repair-history prompt metadata |
| Known legacy row missing policy | loads as `last_attempt_only_v1` through dataclass defaults |
| Unknown artifact row missing policy | deferred to A5 analyzer grouping/quarantine |

## Tests Added Or Updated

- C-loop default and explicit legacy byte-invariance.
- Agentic C prompt rendering with structured Attempt history and best-source
  anchor.
- Agentic later-attempt rendering with all prior compact history and latest
  attempt metadata.
- Agentic attempt 0 success and terminal non-repairable failures preserve
  policy-only metadata with no repair prompt fields.
- Agentic over-budget fail-closed behavior with no hidden legacy fallback.
- Agentic missing F2 `level_reached` fail-closed behavior.
- Typed config rejection before generation.
- Runner CLI default and explicit agentic policy parsing.
- Runner generated-row agentic metadata recording.
- Runner default legacy policy metadata.
- Generated-row metadata round-trip, malformed metadata rejection, incomplete
  rendered-agentic metadata rejection, and impossible anchor/latest index
  rejection.
- Agentic policy-only metadata rejection for repair rows and multi-entry repair
  traces where rendered prompt metadata is missing.
- Rendered-agentic generated-row metadata cross-checks against repair-trace
  length and anchor/latest source hashes.
- Legacy generated row missing `repair_history_policy` loading as
  `last_attempt_only_v1`.

## Validation Commands

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_repair_loop.py -v
```

Result: `42 passed in 0.08s`.

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_results_logger.py -v
```

Result: `59 passed in 0.16s`.

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_run_cluster2_modal.py -v
```

Result: `52 passed in 1.06s`.

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_feedback_prompts.py cluster2/tests/test_cluster2_boundary.py -v
```

Result: `56 passed, 1 skipped in 0.71s`.

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest shared/tests/test_repair_history_policies.py shared/tests/test_repair_history_errors.py shared/tests/test_repair_history_evidence.py shared/tests/test_repair_history_ranking.py shared/tests/test_repair_history_rendering.py -v
```

Result: `63 passed in 0.19s`.

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py -v
```

Result: `15 passed in 0.03s`.

Static and scope checks:

```bash
git diff --name-only
git diff --name-only -- cluster1 cluster3 shared/analysis outputs
git diff --check
git status --short --branch
```

Results: tracked diffs are confined to A2 allowed Cluster 2 files plus
state/registry docs; `git status --short --branch` also shows this new
untracked checkpoint report. Forbidden Cluster 1, Cluster 3, `shared/analysis`,
and `outputs` diff is empty; `git diff --check` passed for tracked diffs.

## Default-Invariance Proof

Tests prove omitted config and explicit `last_attempt_only_v1` produce identical
Cluster 2 repair prompt bytes. Runner defaults parse to:

```text
repair_history_policy = last_attempt_only_v1
repair_max_prompt_chars = 24000
repair_include_latest_source = False
```

Cluster 2 F2-only repair eligibility is unchanged: non-F2 failures terminate
without requesting repair generation.

## Scope Verification

- Modal/output mutation performed: no.
- Generation/experiment/n=5/n=20/paper-scale performed: no.
- `outputs/` modified: no.
- Cluster 1 modified: no.
- Cluster 3 modified: no.
- Analyzer modified: no.
- Shared prompt core modified: no.
- Dependency or lockfile modified: no.
- MLflow remains optional/no-op.

`git fetch origin` and `git pull --ff-only` were run only for the user-requested
checkout refresh before implementation. No dependency download, package install,
Modal API call, model/tokenizer download, billing query, or external service
operation was run.

## Unresolved Risks

- Independent review is still required before promotion because A2 touches the
  C repair loop, runner config, and result metadata.
- A3 P-loop integration, A4 P-to-C isolation, A5 analyzer grouping/quarantine,
  and A6 A/B gates remain not started.
- Analyzer behavior is intentionally unchanged, so mixed-policy artifact
  quarantine is still deferred to A5.

## Classification

`A2_C_LOOP_INTEGRATION_COMPLETE_PENDING_REVIEW`

## Next-Step Recommendation

Run independent review on the A2 diff. Apply any review fixes as a separate A2
review patch before committing or promoting; then start A3 only after taking the
P-loop and Cluster 3 runner leases.
