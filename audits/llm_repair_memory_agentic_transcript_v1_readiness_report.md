# LLM Repair Memory Agentic Transcript v1 Readiness Report

- Date: 2026-06-01
- Branch: `codex/llm-repair-memory-agentic-transcript-v1`
- Worktree: `/private/tmp/tritongen-llm-repair-memory`
- Source branch: `codex-track-handoff-context`
- Source commit: `aa4d20f1f5c64932e72b488d131244542e44459f`
- Scope: prepare the repository and documentation for opt-in
  `agentic_transcript_v1` implementation
- Modal/output mutation performed: no
- Network/dependency download performed: no

## Summary

The isolated worktree was created successfully from the current
`codex-track-handoff-context` tree. The existing repository already had a
strategy document for LLM repair memory:

```text
docs/13_agentic_repair_memory_strategy.md
```

That document is design guidance, not an implementation spec. Before this
readiness pass, the repo was missing the A-stream implementation contract
equivalent to the existing O and S implementation specs:

```text
docs/16_observability_sidecar_implementation_spec.md
docs/17_structural_task_analyzer_metadata_implementation_spec.md
```

This branch adds:

```text
docs/18_agentic_transcript_v1_implementation_spec.md
```

and routes it through the project map, document hub, document version registry,
orchestration contract, and live orchestration state.

## Baseline Code Findings

Current C and P repair behavior is still `last_attempt_only_v1`.

Relevant C surfaces:

```text
cluster2/feedback/prompts.py
cluster2/feedback/repair_loop.py
cluster2/tests/test_feedback_prompts.py
cluster2/tests/test_repair_loop.py
```

Relevant P surfaces:

```text
cluster3/feedback/prompts.py
cluster3/feedback/compile_error_repair.py
cluster3/constants.py
cluster3/tests/test_p_repair_loop.py
cluster3/tests/test_p_prompts.py
```

Observed current facts:

- C prompt rendering uses Base task, Previous source, Failure code, Feedback,
  Public details, and Instruction.
- P prompt rendering uses Base task, Previous source, Failure code, Feedback,
  Compile error, and Instruction.
- `cluster3.constants.P_HISTORY_POLICY_V1` is still
  `"last_attempt_only_v1"`.
- No `agentic_transcript_v1` runtime implementation exists yet.

## Documentation Findings

Before this pass:

- `docs/13_agentic_repair_memory_strategy.md` defined the desired policy,
  ranking ideas, boundaries, metadata, rollout gates, and golden prompt shape.
- `docs/15_experiment_change_orchestration_contract.md` required the agentic
  policy to stay opt-in.
- `docs/handoff/experiment_change_orchestration_state.md` still had open
  D-AGENT decisions for prompt budget, latest-source inclusion, and P-to-C
  provenance wording.
- No dedicated `agentic_transcript_v1` implementation spec was present.

This pass resolves the missing-spec gap by adding
`docs/18_agentic_transcript_v1_implementation_spec.md`.

The new spec records these implementation decisions:

- default `agentic_transcript_v1` rendered prompt budget is 24000 UTF-8
  characters, with explicit positive overrides;
- required prompt sections fail closed if they do not fit;
- latest full source is excluded by default when it differs from the selected
  best anchor;
- full latest source can be included only with explicit config and within
  budget;
- P-to-C handoff does not include P compile logs or a P provenance note in C
  prompt text in v1;
- `agentic_transcript_v1` remains opt-in and must be labeled separately from
  `last_attempt_only_v1`.

A follow-on hardening pass updated the spec to v0.1.1 and added explicit
implementation guardrails for:

- evidence completeness by failure level;
- in-memory source records and duplicate source/prompt hashes;
- seed-candidate attempt 0 handling;
- resume semantics and output-path separation;
- prompt-injection fixtures and final-instruction precedence;
- typed fail-closed errors;
- sanitizer ownership boundaries;
- prompt hash versus history-summary hash definitions;
- artifact mixing and analyzer quarantine;
- metadata fields for prompt budget and latest-source inclusion.

The final planning addendum updated the spec to v0.1.2 and added:

- a spec-only checkpoint before any code work;
- an A0.5 preflight between policy constants and prompt-core implementation;
- a fixture-first A1 gate;
- legacy and migration policy-classification fixtures;
- implementation stop triggers;
- an A1 review checkpoint before C/P loop integration.

An implementation-gap hardening pass updated the spec to v0.1.3 after a
targeted public research cross-check against Reflexion, Self-Refine, OWASP
LLM01:2025 prompt-injection guidance, and OpenAI structured-output guidance.
No scope expansion was added. The pass tightened the coding contract with:

- explicit `RepairHistoryConfig` validation and no fallback after explicit
  `agentic_transcript_v1` selection;
- canonical prompt serialization grammar, exact section spacing, compact
  history line format, and source/failure evidence delimiters;
- public-evidence-only attempt records and anchor ranking;
- `public_eval_shapes_passed` naming to avoid hidden/private eval leakage;
- active repair eligibility rules proving C renders only eligible F2 repair
  prompts and P renders only eligible `F1_COMPILE` repair prompts;
- success/non-repairable latest-attempt handling that writes no repair prompt
  metadata;
- additional A1 tests for config validation, canonical rendering, private
  evidence rejection, private-signal ranking rejection, and non-rendered prompt
  metadata.

A final plan-hardening addendum updated the spec to v0.1.4 and added:

- an A1 fixture acceptance manifest with expected anchor/latest attempts,
  prompt/history hashes, latest-source setting, render error code, and legacy
  byte-invariance expectation;
- A1 legacy C/P byte-invariance snapshots for `last_attempt_only_v1`;
- A1 prompt-core import isolation against provider, tokenizer, Modal, Torch,
  Triton, Transformers, XGrammar, CUDA helper, generation-client, and runner
  imports;
- an A2/A3 metadata nullability matrix for legacy/default, explicit legacy,
  explicit agentic, failed pre-generation render, attempt 0 success, attempt 0
  non-repairable terminal failure, known legacy missing-policy rows, and
  unknown missing-policy rows;
- A2/A3 CLI/API/default tests for omitted, explicit legacy, explicit agentic,
  invalid policy, invalid budget, and invalid latest-source settings;
- an A5 mixed-policy analyzer fixture proving headline metrics are quarantined
  when `last_attempt_only_v1` and `agentic_transcript_v1` rows are present in
  the same diagnostic artifact.

An implementation-discipline addendum updated the spec to v0.1.5 and added:

- a commit/package slicing contract that keeps docs-only, A0, A0.5, A1, A2,
  A3, A4, A5, and A6 independently reviewable;
- a commit-message template with scope, invariance, validation, and risk
  sections;
- a per-package exit checklist covering files changed, tests/checks run,
  default-invariance proof, forbidden-files check, no Modal/output mutation,
  unresolved risks, and the next blocked package or gate;
- a rollback rule requiring each package to remain revertible without
  invalidating earlier packages;
- fixed A2/A3 configuration precedence:
  direct API argument, CLI flag, config default, then legacy default;
- a no-opportunistic-cleanup rule for nearby prompt, loop, result, runner,
  analyzer, and documentation code.

The ready-to-implement kickoff state was then recorded in
`docs/handoff/experiment_change_orchestration_state.md` v1.5.6. It names:

- branch: `codex/llm-repair-memory-agentic-transcript-v1`;
- worktree: `/private/tmp/tritongen-llm-repair-memory`;
- spec: `docs/18_agentic_transcript_v1_implementation_spec.md` v0.1.5;
- first package: A0 policy constants;
- A0 allowed files and forbidden actions;
- A0 required default-invariance proof;
- the current targeted local C/P prompt-loop and docs-consistency validation
  command.

After recording the kickoff state, the targeted validation slice was rerun:

```text
137 passed in 0.66s
```

## Validation

Local dependency observations:

```text
/Users/alexeidelgado/miniconda3/bin/python imports torch 2.9.0
/Users/alexeidelgado/miniconda3/bin/python cannot import triton
```

The targeted C/P prompt-loop validation below avoids Triton imports. Full
GPU/Triton regression is not available in this local environment until Triton is
installed or a Modal-approved validation path is used.

Initial test runner checks:

```text
python -m pytest ...
```

Result:

```text
zsh:1: command not found: python
```

System Python check:

```text
python3 -m pytest ...
```

Result:

```text
/opt/homebrew/opt/python@3.14/bin/python3.14: No module named pytest
```

Bundled Codex runtime check:

```text
/Users/alexeidelgado/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest ...
```

Result:

```text
No module named pytest
```

Conda Python has pytest, but pytest startup segfaulted when importing macOS
`readline` from pytest's capture initialization. The successful validation used
an in-memory `readline` stub before calling `pytest.main`.

Initial targeted command:

```bash
/Users/alexeidelgado/miniconda3/bin/python -c "import sys, types, pytest; sys.modules['readline'] = types.ModuleType('readline'); sys.exit(pytest.main(['cluster2/tests/test_feedback_prompts.py','cluster2/tests/test_repair_loop.py','cluster3/tests/test_p_repair_loop.py','cluster3/tests/test_condition_adapters.py','cluster3/tests/test_cluster3_imports.py']))"
```

Result:

```text
123 passed in 0.82s
```

After adding and routing the implementation spec, the validation slice was
expanded to include Cluster 3 docs consistency:

```bash
/Users/alexeidelgado/miniconda3/bin/python -c "import sys, types, pytest; sys.modules['readline'] = types.ModuleType('readline'); sys.exit(pytest.main(['cluster2/tests/test_feedback_prompts.py','cluster2/tests/test_repair_loop.py','cluster3/tests/test_p_repair_loop.py','cluster3/tests/test_condition_adapters.py','cluster3/tests/test_cluster3_imports.py','cluster3/tests/test_docs_consistency.py']))"
```

Result:

```text
137 passed in 0.72s
```

The validated slice covers current C prompt construction, C repair-loop
boundaries, P repair-loop behavior, C/P condition adapters, Cluster 3 cheap
import/constants behavior, and Cluster 3 documentation consistency.

After the v0.1.3 implementation-gap hardening pass, the same targeted
validation slice was rerun:

```bash
/Users/alexeidelgado/miniconda3/bin/python -c "import sys, types, pytest; sys.modules['readline'] = types.ModuleType('readline'); sys.exit(pytest.main(['cluster2/tests/test_feedback_prompts.py','cluster2/tests/test_repair_loop.py','cluster3/tests/test_p_repair_loop.py','cluster3/tests/test_condition_adapters.py','cluster3/tests/test_cluster3_imports.py','cluster3/tests/test_docs_consistency.py']))"
```

Result:

```text
137 passed in 0.65s
```

Additional hygiene checks after v0.1.3:

```bash
git diff --check
```

Result:

```text
no output
```

After the v0.1.4 plan-hardening addendum, the targeted validation slice was
rerun:

```bash
/Users/alexeidelgado/miniconda3/bin/python -c "import sys, types, pytest; sys.modules['readline'] = types.ModuleType('readline'); sys.exit(pytest.main(['cluster2/tests/test_feedback_prompts.py','cluster2/tests/test_repair_loop.py','cluster3/tests/test_p_repair_loop.py','cluster3/tests/test_condition_adapters.py','cluster3/tests/test_cluster3_imports.py','cluster3/tests/test_docs_consistency.py']))"
```

Result:

```text
137 passed in 0.86s
```

Additional hygiene checks after v0.1.4:

```bash
git diff --check
```

Result:

```text
no output
```

After the v0.1.5 implementation-discipline addendum, the targeted validation
slice was rerun:

```bash
/Users/alexeidelgado/miniconda3/bin/python -c "import sys, types, pytest; sys.modules['readline'] = types.ModuleType('readline'); sys.exit(pytest.main(['cluster2/tests/test_feedback_prompts.py','cluster2/tests/test_repair_loop.py','cluster3/tests/test_p_repair_loop.py','cluster3/tests/test_condition_adapters.py','cluster3/tests/test_cluster3_imports.py','cluster3/tests/test_docs_consistency.py']))"
```

Result:

```text
137 passed in 0.70s
```

Additional hygiene checks after v0.1.5:

```bash
git diff --check
```

Result:

```text
no output
```

```bash
awk '/[ \t]$/ {print FILENAME ":" FNR ": trailing whitespace"}' docs/18_agentic_transcript_v1_implementation_spec.md audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md docs/handoff/document_version_registry.md docs/handoff/experiment_change_orchestration_state.md
```

Result:

```text
no output
```

```bash
rg -n "[^[:ascii:]]" docs/18_agentic_transcript_v1_implementation_spec.md audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md
```

Result:

```text
no output
```

```bash
awk '/[ \t]$/ {print FILENAME ":" FNR ": trailing whitespace"}' docs/18_agentic_transcript_v1_implementation_spec.md audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md docs/handoff/document_version_registry.md docs/handoff/experiment_change_orchestration_state.md
```

Result:

```text
no output
```

```bash
awk '/[ \t]$/ {print FILENAME ":" FNR ": trailing whitespace"}' docs/18_agentic_transcript_v1_implementation_spec.md audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md
```

Result:

```text
no output
```

```bash
rg -n "[^[:ascii:]]" docs/18_agentic_transcript_v1_implementation_spec.md audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md
```

Result:

```text
no output
```

## Claim And Boundary Scans

The orchestration-contract scan over docs/audits/Cluster 3 README found many
expected historical caveat references to speedup, timing, profiler, pass@k,
paper-scale, and P/C lift. No new Modal run, output mutation, or result claim
was made by this branch.

Focused scans over the agentic strategy, orchestration contract, and live state
showed the expected guardrail language around private eval data, hidden details,
profiling, timing, and speedup. These references are boundary statements, not
new result claims.

After the v0.1.4 plan-hardening addendum, focused scans over the A-spec,
readiness audit, registry, and live state again found only expected guardrail
or historical-version language:

```bash
rg -n "0\.1\.3|v0\.1\.3|1\.41\.0|v1\.41\.0" docs/18_agentic_transcript_v1_implementation_spec.md docs/handoff/document_version_registry.md docs/handoff/experiment_change_orchestration_state.md audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md
```

Result: only the historical v0.1.3/v1.41.0 changelog/audit entries.

```bash
rg -i "paper-scale complete|n=20 complete|pass@k result|P lift|C lift|improves correctness|performance improvement|speedup|profiler result|timing result|full 2\\^3 complete|statistically significant" docs/18_agentic_transcript_v1_implementation_spec.md audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md docs/handoff/document_version_registry.md docs/handoff/experiment_change_orchestration_state.md
```

Result: only boundary and scan-command text; no new result claim.

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing|allclose" docs/18_agentic_transcript_v1_implementation_spec.md audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md docs/handoff/document_version_registry.md docs/handoff/experiment_change_orchestration_state.md
```

Result: only prompt-boundary, private-data exclusion, and scan-command text.

After the v0.1.5 implementation-discipline addendum, the same focused scans
were rerun over the A-spec, readiness audit, registry, and live state.

Stale-version scan result:

```text
Only historical v0.1.4/v1.42.0 changelog and audit entries remain.
```

Unsupported-claim scan result:

```text
Only boundary and scan-command text; no new result claim.
```

Private-eval scan result:

```text
Only prompt-boundary, private-data exclusion, and scan-command text.
```

## Next Implementation Steps

The next safe work packages are:

1. A0 policy constants: add policy-name constants and tests proving
   `last_attempt_only_v1` remains the default.
2. A1 prompt core: add attempt evidence, best-anchor ranking, transcript
   rendering, golden prompt tests, prompt-hash tests, and budget fail-closed
   tests.
3. A2/A3 integration only after A1 passes and the required loop/runner leases
   are recorded.

No paid, Modal, n=5, n=20, paper-scale, or output-mutating run is authorized by
this readiness pass.
