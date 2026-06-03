# Agentic Transcript v1 A3 P-loop Integration Report

Version: 1.0.0
Date: 2026-06-02
Branch: `codex/llm-repair-memory-agentic-transcript-v1`
Worktree: `/private/tmp/tritongen-llm-repair-memory`
Baseline commit: `6c859b3317a41ad4adbc2cb4e9a4fc8cc1c6a198`
Classification: `A3_P_LOOP_INTEGRATION_COMPLETE_WITH_WORKTREE_CAVEATS`

## Executive Summary

A3 wires `agentic_transcript_v1` into Cluster 3 P repair as an opt-in policy
only. Default and explicit `last_attempt_only_v1` behavior remain legacy. The
agentic path renders structured public P history for eligible `F1_COMPILE`
repair attempts, records nullable/defaultable P metadata on generated rows,
fails closed on invalid config/rendering errors, and does not pass P transcripts
into C-loop prompts or C-loop config.

No Modal, GPU, generation-run, experiment-run, paper-scale, dependency,
lockfile, analyzer, output, Cluster 1, or Cluster 2 implementation work was
performed.

## Worktree Status

At checkpoint, the feature branch is ahead of origin by the committed A2
checkpoint and has uncommitted A3 implementation/report changes. The worktree
is intentionally not clean pending independent review and commit packaging.

Changed files at checkpoint:

```text
cluster3/experiments/run_cluster3_modal.py
cluster3/feedback/compile_error_repair.py
cluster3/feedback/trace.py
cluster3/results/dataclass.py
cluster3/tests/test_cluster3_schema.py
cluster3/tests/test_p_repair_loop.py
cluster3/tests/test_run_cluster3_modal_cli.py
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
audits/agentic_transcript_v1_a3_p_loop_integration_report.md
```

## Lease Status

The A3 launch packet and serialized-surface leases were already recorded in
`docs/handoff/experiment_change_orchestration_state.md` for:

- Cluster 3 P-loop repair policy integration.
- Cluster 3 runner/schema policy plumbing.

No conflicting owner was found in the state file.

## Files Changed

- `cluster3/feedback/compile_error_repair.py`
  - Adds `RepairHistoryConfig` plumbing to `run_p_repair_loop`.
  - Builds P-specific public `RepairAttemptEvidence` and in-memory source
    records for the A1 renderer.
  - Records terminal `PRepairPromptMetadata`.
- `cluster3/feedback/trace.py`
  - Adds compile-error excerpt hash and compile-error changed flags to P
    attempt summaries.
- `cluster3/experiments/run_cluster3_modal.py`
  - Adds CLI/config plumbing for policy, prompt budget, and latest-source flag.
  - Passes `repair_history_config` into the injected P loop.
  - Copies terminal P prompt metadata into generated row metadata.
- `cluster3/results/dataclass.py`
  - Adds nullable/defaultable P repair-history fields to
    `Cluster3GeneratedRowMetadata`.
  - Validates known policy labels, complete rendered agentic metadata, and
    metadata-to-P-trace source bindings.
- `cluster3/tests/test_p_repair_loop.py`,
  `cluster3/tests/test_cluster3_schema.py`, and
  `cluster3/tests/test_run_cluster3_modal_cli.py`
  - Add A3 positive and negative coverage.
- Handoff docs/register this checkpoint and pending-review status.

## P Policy/Config Plumbing Summary

Defaults remain `last_attempt_only_v1`. CLI/API config accepts:

- `--repair-history-policy` with known policy choices.
- `--repair-max-prompt-chars`.
- `--repair-include-latest-source`.

Invalid policy names are rejected by argparse. Invalid budget/latest-source
types or values fail during `Cluster3RunnerConfig` construction or
`RepairHistoryConfig` construction before any injected generation call.

## Legacy P Byte-Invariance Proof

`test_omitted_and_explicit_legacy_p_policy_prompt_bytes_match` verifies omitted
policy and explicit `last_attempt_only_v1` produce identical prompt bytes, and
that the bytes equal `build_p_feedback_prompt(...)` legacy output.

## Agentic P Rendering Path Summary

When explicitly selected and the latest P attempt is eligible `F1_COMPILE`,
the P loop renders A1 `agentic_transcript_v1` prompt text with:

- attempt 0 in history before attempt 1 generation;
- later attempts containing all prior compact P attempt history;
- best-anchor source in-memory only through `RepairSourceRecord`;
- prompt/history hashes and anchor/latest metadata;
- public compile-error evidence only.

## P Eligibility Preservation Proof

P remains `F1_COMPILE` only:

- non-eligible seed attempts are rejected;
- initial `F2_*` under P-only remains terminal and does not call P;
- post-P `F2_*` does not trigger another P prompt;
- `F0_*`, `F3_*`, and non-repairable terminal outcomes retain existing
  Cluster 3 stop semantics.

## F1_RUNTIME Terminal Proof

Tests cover both direct runner routing and P-loop terminal behavior:

- initial `F1_RUNTIME` is terminal and does not call P;
- post-P `F1_RUNTIME` terminates the P loop and does not render a second repair
  prompt.

## Metadata/Nullability Summary

Legacy/default rows record `p_history_policy="last_attempt_only_v1"` with
rendered prompt metadata fields unset.

Agentic rows with a rendered repair prompt record:

- `p_history_policy`;
- prompt template/renderer versions;
- anchor/latest attempt indexes;
- history attempt count;
- prompt sha256 and char count;
- max prompt budget and latest-source flag;
- anchor/latest source hashes;
- history summary sha256.

Agentic rows with no rendered P prompt, such as inactive rows or attempt-0
terminal cases, record the selected policy but no rendered prompt metadata.

## Fail-Closed Behavior Summary

The implementation fails before generation for:

- unsupported policy;
- invalid prompt budget;
- invalid latest-source flag type;
- prompt budget exhaustion;
- forbidden public P feedback terms;
- incomplete or inconsistent rendered agentic metadata.

No hidden fallback from explicit `agentic_transcript_v1` to legacy prompting is
implemented.

## C/P Separation Summary

The P transcript is not passed into C-loop prompt construction or C-loop config.
The existing C-loop handoff receives only the seed candidate source,
seed-candidate evaluation payload, and seed-candidate prompt hash/provenance.
No A4 P-to-C isolation behavior was implemented here.

## Tests Run

All commands used the baseline venv interpreter:
`/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python`.

```text
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest \
  shared/tests/test_repair_history_policies.py \
  shared/tests/test_repair_history_errors.py \
  shared/tests/test_repair_history_evidence.py \
  shared/tests/test_repair_history_ranking.py \
  shared/tests/test_repair_history_rendering.py -q
Result: 63 passed

/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest \
  cluster2/tests/test_feedback_prompts.py \
  cluster2/tests/test_repair_loop.py \
  cluster2/tests/test_results_logger.py \
  cluster2/tests/test_run_cluster2_modal.py \
  cluster2/tests/test_cluster2_boundary.py -q
Result: 209 passed, 1 skipped

/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest \
  cluster3/tests/test_p_prompts.py \
  cluster3/tests/test_p_repair_loop.py \
  cluster3/tests/test_cluster3_schema.py \
  cluster3/tests/test_run_cluster3_modal_cli.py \
  cluster3/tests/test_cluster3_imports.py -q
Result: 303 passed

/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -c "import cluster3.feedback.prompts; import cluster3.feedback.compile_error_repair; import cluster3.feedback.trace; import cluster3.results.dataclass; import cluster3.experiments.run_cluster3_modal; import shared.repair_history.rendering; print('a3_imports_ok')"
Result: a3_imports_ok
```

## Forbidden-Files Check

```text
git diff --name-only -- cluster1 cluster2/feedback cluster2/results cluster2/experiments shared/analysis outputs
Result: empty output
```

## Negative Scope Verification

```text
git diff --check
Result: passed with empty output
```

No Modal, output, generation-run, experiment-run, analyzer, dependency, or
lockfile changes were made.

## Unresolved Risks

- A2 and A3 both remain pending independent review before promotion.
- Full repository regression was not run; A1/A2/A3 focused suites passed.
- Worktree relies on the baseline venv interpreter outside the temporary
  feature worktree, matching the launch packet.

## Classification

`A3_P_LOOP_INTEGRATION_COMPLETE_WITH_WORKTREE_CAVEATS`

## Next-Step Recommendation

Run independent review for A2 and A3. If review is clean, commit A3 as its own
package. Start A4 only after A3 is preserved and the next launch packet/leases
are recorded.
