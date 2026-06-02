# Agentic Transcript v1 A1 Prompt Core Report

- Date: 2026-06-02
- Worktree: `/private/tmp/tritongen-llm-repair-memory`
- Branch: `codex/llm-repair-memory-agentic-transcript-v1`
- Baseline branch treated as main: `codex-track-handoff-context`
- Prior package: A0.5 constants preflight, commit `8d441a29062aaae6c15987f0068e7a619ab12cae`
- Classification: `A1_PROMPT_CORE_COMPLETE_WITH_WORKTREE_CAVEATS`

## Executive Summary

A1 implemented the pure local `agentic_transcript_v1` prompt core without
wiring it into Cluster 2 or Cluster 3 loops. The package adds typed local
fail-closed errors, explicit policy config validation, public/source-free
attempt evidence, in-memory source records, deterministic anchor ranking,
byte-stable transcript rendering, prompt/history SHA256 metadata, budget
handling, golden fixtures, prompt-injection containment fixtures, import
isolation tests, and legacy C/P `last_attempt_only_v1` prompt snapshots.

Default behavior remains unchanged because A1 does not edit C/P prompt
builders, repair loops, runners, schemas, analyzers, Modal code, or outputs.

## Worktree Status

Pre-report changed paths were confined to A1 implementation surfaces:

```text
shared/repair_history/
shared/tests/test_repair_history_errors.py
shared/tests/test_repair_history_evidence.py
shared/tests/test_repair_history_policies.py
shared/tests/test_repair_history_ranking.py
shared/tests/test_repair_history_rendering.py
shared/tests/fixtures/repair_history/
```

This report and handoff-state/registry updates are documentation-only A1
checkpoint additions.

## Files Changed

Implementation:

```text
shared/repair_history/__init__.py
shared/repair_history/errors.py
shared/repair_history/evidence.py
shared/repair_history/policies.py
shared/repair_history/ranking.py
shared/repair_history/rendering.py
```

Tests and fixtures:

```text
shared/tests/test_repair_history_errors.py
shared/tests/test_repair_history_evidence.py
shared/tests/test_repair_history_policies.py
shared/tests/test_repair_history_ranking.py
shared/tests/test_repair_history_rendering.py
shared/tests/fixtures/repair_history/manifest.json
shared/tests/fixtures/repair_history/c_later_regression.txt
shared/tests/fixtures/repair_history/include_latest_source.txt
shared/tests/fixtures/repair_history/legacy_c_last_attempt_only_v1.txt
shared/tests/fixtures/repair_history/legacy_p_last_attempt_only_v1.txt
shared/tests/fixtures/repair_history/normal_c_transcript.txt
shared/tests/fixtures/repair_history/p_repeated_f1_compile.txt
shared/tests/fixtures/repair_history/prompt_injection_source_text.txt
shared/tests/fixtures/repair_history/repeated_source_hash.txt
```

Checkpoint docs:

```text
audits/agentic_transcript_v1_a1_prompt_core_report.md
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
```

## Evidence Model Summary

`RepairAttemptEvidence` carries source-free prompt-visible public evidence.
`RepairSourceRecord` carries in-memory source text and enforces that
`source_hash` matches exact source text SHA256. Evidence validation rejects
malformed indexes, hashes, failure codes, non-contiguous rendered histories,
F2 records without Level 2/public summaries, P `F1_COMPILE` records without
public compile evidence, and forbidden private/performance/token/billing
signals in prompt-visible fields.

## Config Validation Summary

`RepairHistoryConfig` defaults to `last_attempt_only_v1`, `max_prompt_chars =
24000`, and `include_latest_source = False`. Validation rejects unknown policy
names, bool/non-positive/non-int prompt budgets, and non-bool
`include_latest_source`. Explicit invalid `agentic_transcript_v1` config raises
a typed local error and does not fall back to legacy behavior.

The A1 package also includes a small policy-classification helper covering
explicit legacy, explicit agentic, known missing legacy, unknown missing legacy,
and mixed-policy rows for later analyzer migration work.

## Ranking Summary

Anchor selection is deterministic, uses only public attempt evidence, preserves
repeated source hashes as separate attempts, and uses later attempt only as the
final tie-break. C ranking prefers better public F2 evidence, repair/public eval
counts when present, lower public numeric diffs, non-NaN evidence, and
shape-correct evidence. P ranking prefers compile-success/post-compile progress,
changed compile error class, and specific public compile evidence.

## Rendering Summary

The renderer produces byte-stable sections in this order:

```text
Base task
Repair objective
Attempt history
Best previous source to repair from
optional Latest failed source
Latest failure details
Instruction
```

Sections use `<Section name>:` headers and exactly one blank line between
sections. Full source and failure details use the required delimiters. The
default final instruction is:

```text
Produce a corrected complete Triton Python module. Do not explain. Do not concatenate prior attempts. Use the history only to avoid repeated mistakes.
```

## Fixture Manifest Summary

`shared/tests/fixtures/repair_history/manifest.json` records fixture id, loop
kind, policy, expected anchor/latest attempt, exact prompt SHA256, exact history
summary SHA256, latest-source setting, render error code, and legacy
byte-invariance expectation.

Fixture cases cover normal C transcript, C later regression, repeated source
hashes, P repeated `F1_COMPILE`, prompt-injection source text, optional latest
source inclusion, over-budget fail-closed rendering, and legacy C/P snapshots.

## Prompt/Hash Summary

`repair_prompt_sha256` is SHA256 over the exact rendered full prompt text.
`repair_history_summary_sha256` is SHA256 over the exact compact Attempt history
section body. The include-latest-source fixture intentionally changes the prompt
hash while preserving the history-summary hash.

## Budget Behavior Summary

The renderer defaults to a 24000-character budget. If
`include_latest_source=True` causes the prompt to exceed budget, only the
optional latest-source section is dropped and the prompt is recomputed. Required
sections are never dropped. If required sections exceed budget, rendering raises
`PromptBudgetExceededError` with code `prompt_budget_exceeded`.

## Prompt-Injection Fixture Behavior

The prompt-injection fixture includes fake section headers, fake source/failure
delimiters, and an instruction to ignore later instructions inside source text.
Those strings remain evidence inside the delimited source section and do not
move the final `Instruction:` section or change renderer section order.

## Legacy Byte-Invariance Evidence

Legacy snapshot hashes:

```text
legacy C last_attempt_only_v1 prompt: 7a76f125b522ae0494101c4460ae67ab6bceb1bad0f8863df6e0ee4db3ac050a
legacy P last_attempt_only_v1 prompt: 1b90c50c3ed99ad9279737fbd495869905b19afd3f6d88dcad728cd98855d9ef
```

Tests prove omitted policy and explicit `last_attempt_only_v1` both preserve
the current C and P legacy prompt bytes.

## Import Isolation Proof

Focused tests and standalone import smoke prove `shared/repair_history/*` does
not import or load Modal, Torch, Triton, Transformers, XGrammar, tokenizer
packages, generation clients, runner modules, or C/P prompt builders. The shared
prompt core imports only standard-library modules, A0 policy constants from
`cluster2.constants`, and other `shared.repair_history` modules.

Standalone smoke output:

```text
forbidden_imports []
```

## Tests Run

Focused A1 tests:

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest shared/tests/test_repair_history_policies.py shared/tests/test_repair_history_errors.py shared/tests/test_repair_history_evidence.py shared/tests/test_repair_history_ranking.py shared/tests/test_repair_history_rendering.py -v
```

Result:

```text
63 passed in 0.13s
```

Existing focused default-drift tests:

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_cluster2_boundary.py -v
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py -v
```

Results:

```text
cluster2: 26 passed, 1 skipped in 0.63s
cluster3: 15 passed in 0.04s
```

Standalone import isolation:

```text
forbidden_imports []
```

## Forbidden-Files Check

Final changed paths:

```text
audits/agentic_transcript_v1_a1_prompt_core_report.md
docs/handoff/document_version_registry.md
docs/handoff/experiment_change_orchestration_state.md
shared/repair_history/__init__.py
shared/repair_history/errors.py
shared/repair_history/evidence.py
shared/repair_history/policies.py
shared/repair_history/ranking.py
shared/repair_history/rendering.py
shared/tests/fixtures/repair_history/c_later_regression.txt
shared/tests/fixtures/repair_history/include_latest_source.txt
shared/tests/fixtures/repair_history/legacy_c_last_attempt_only_v1.txt
shared/tests/fixtures/repair_history/legacy_p_last_attempt_only_v1.txt
shared/tests/fixtures/repair_history/manifest.json
shared/tests/fixtures/repair_history/normal_c_transcript.txt
shared/tests/fixtures/repair_history/p_repeated_f1_compile.txt
shared/tests/fixtures/repair_history/prompt_injection_source_text.txt
shared/tests/fixtures/repair_history/repeated_source_hash.txt
shared/tests/test_repair_history_errors.py
shared/tests/test_repair_history_evidence.py
shared/tests/test_repair_history_policies.py
shared/tests/test_repair_history_ranking.py
shared/tests/test_repair_history_rendering.py
```

Static diff check:

```bash
git diff --check
```

Result: passed.

Pre-report forbidden implementation surfaces were clean:

```bash
git status --short -- cluster1 cluster2/feedback cluster2/experiments cluster2/results cluster3/feedback cluster3/experiments cluster3/results shared/analysis outputs
git diff --name-only -- cluster1 cluster2/feedback cluster2/experiments cluster2/results cluster3/feedback cluster3/experiments cluster3/results shared/analysis outputs
```

Both produced empty output.

## Negative Scope Verification

A1 did not edit Cluster 1, C repair-loop integration, P repair-loop integration,
runners, result schemas, analyzers, Modal code, prompt builders, or outputs.
No Modal, GPU, generation, experiment, n=5, n=20, or paper-scale command was
run.

## Unresolved Risks

- A1 is not wired into Cluster 2 or Cluster 3 loops by design; A2/A3 remain
  blocked until this checkpoint is preserved and the relevant leases are taken.
- The feature worktree still relies on the baseline venv interpreter
  `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python`.
- Tokenizer-derived budget accounting remains out of scope for v1; A1 uses the
  specified deterministic character budget.

## Classification

`A1_PROMPT_CORE_COMPLETE_WITH_WORKTREE_CAVEATS`

## Next-Step Recommendation

Preserve A1 as its own reviewable commit. Then start A2 C-loop integration only
after taking the C-loop/Cluster 2 runner lease, or start A3 P-loop integration
only after taking the P-loop/Cluster 3 runner lease.
