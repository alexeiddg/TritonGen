# C3 n20 Metric-Family-Gated Packet Report

- Version: 1.0.1
- Date: 2026-06-05
- Branch: `codex/c3-n20-metric-family-gated-packet`
- Baseline: `d015862 Audit structural task S4 promotion`
- Scope: experiment packet only / no execution authorized
- Classification: `C3_N20_PACKET_REVIEW_PASS_COMMIT_ALLOWED`

## Executive Summary

Created a draft Cluster 3 n20 metric-family-gated experiment packet at
`docs/experiment_packets/c3_n20_metric_family_gated_packet.md`.

The packet preregisters how a possible future Cluster 3 n20 launch must declare
structural/code-surface, task/functional, mixed diagnostic, planned-deferred,
future-only, and benchmarkable/performance metrics before any launch approval,
output mutation, analyzer refresh, report refresh, performance sidecar use, or
paper-scale claim.

Packet review passed locally under
`C3_N20_PACKET_REVIEW_PASS_COMMIT_ALLOWED`. The packet remains
non-authorizing and is not a launch packet.

This packet does not create new scientific evidence. It does not run Modal,
GPU, generation, experiments, benchmarks, profilers, timing, or speedup work. It
does not mutate raw JSONL, `outputs/`, `artifacts/`, analyzer output, generated
report assets, result schemas, dependencies, lockfiles, analyzer code, report
builder code, runner code, or Modal harness code.

## Docs Inspected

- `docs/15_experiment_change_orchestration_contract.md`
- `docs/17_structural_task_analyzer_metadata_implementation_spec.md`
- `docs/14_structural_vs_task_outcome_reporting_plan.md`
- `docs/07_analysis_and_statistics.md`
- `docs/04_methodology_cluster3.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`
- `cluster3/README.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/scale_policy.md`

## Packet File Created

`docs/experiment_packets/c3_n20_metric_family_gated_packet.md`

The repository does not currently contain `.contracts/experiment_packets/`, so
the packet uses the allowed fallback directory under `docs/experiment_packets/`.

## Metric-Family Declarations

The packet declares required registry-style fields for each metric:

```text
metric_name
outcome_family
level_gate
metric_gate
reportability
current_status
evidence_source
denominator_policy
claim_boundary
```

Declared metric families and status categories:

- `structural_code_surface`: `level1_compile_success_rate`,
  `grammar_valid_rate`, `compile_pass_at_k`, `syntax_valid_rate`.
- `task_functional`: `level2_functional_success_rate`,
  `correctness_pass_at_k`.
- `mixed_diagnostic`: `terminal_failure_distribution`,
  `diagnostics.level_reach_rates`, `diagnostics.feedback_activation`,
  `diagnostics.metric_availability`.
- `benchmarkable_performance`: `benchmarkable_pass_at_k`,
  `speedup_or_performance_metric`.
- `planned_deferred`: all future Cluster 3 row-derived metrics that lack
  compatible evidence in this packet.
- `future_only`: benchmarkable/performance metrics that require later Level 4
  sidecar authorization and evidence.

The packet records the experiment as intended for a future launch, but keeps
metric `current_status` values registry-compatible as `planned_deferred` or
`future_only` until execution evidence exists.

## Denominator And Eligibility Policy

The packet requires intent-to-treat denominators over generated rows unless an
existing analyzer policy explicitly defines a metric-specific exception.

Required preservation rules:

- Do not drop F0/F1 rows merely because C did not activate.
- Do not drop non-F1_COMPILE rows merely because P did not activate.
- Preserve F0_PARSE, F1_COMPILE, F1_RUNTIME, F2 functional failures, F3, and
  success terminal states distinctly.
- Treat eligible-set and loop-fired analyses as diagnostics, not replacements
  for primary condition comparisons.
- P repairs only `F1_COMPILE`.
- `F1_RUNTIME` remains terminal in Cluster 3 v1.
- C repairs only F2 numerical or shape correctness failures.
- Direct initial-F2 C paths must be labeled separately from post-P F2 paths when
  both exist.

## Claim-Boundary Policy

The packet explicitly does not authorize:

- paper-scale claims;
- Modal or GPU execution;
- output mutation;
- analyzer output refresh;
- raw JSONL rewrite;
- performance or speedup claims;
- causal claim language;
- P lift, C lift, G lift, interaction effects, or all-condition 2^3 completion
  claims.

Future paper-facing output must fail closed or mark the affected metric
diagnostic-only if an unknown `metric_registry` major schema appears, family or
reportability fields are missing, deferred/future metrics are presented as
current, compile-only evidence is presented as task/functional correctness, or
benchmarkable/performance claims lack approved performance sidecar evidence.

## Sidecar Policy

The packet requires future launch packets to state exact sidecar paths and
join-key policy before launch. Scientific JSONL rows remain the source of truth
for outcomes.

Performance/timing/speedup values remain sidecar-only and future-only unless a
later signed packet authorizes performance evidence and attaches compatible
Level 2 correctness prerequisites, device, dtype, shape, baseline, timing
method, sidecar path, and join-key policy.

Performance sidecar authorization status for this packet: not authorized.

## Launch Prerequisites

A future launch packet must specify:

- exact branch and commit;
- exact model and decoding config;
- exact conditions and `n` per condition;
- kernel classes and problem IDs;
- dtype and shape policy;
- Modal image digest policy;
- output JSONL paths;
- hash sidecar paths;
- observability sidecar paths;
- performance sidecar paths if separately authorized;
- analyzer version expectation;
- metric registry schema expectation;
- outcome family schema expectation;
- registry provenance expectation;
- no raw artifact rewrite policy;
- retry and repair budgets;
- seed policy;
- failure stop conditions;
- post-run validation commands.

Missing launch prerequisites keep execution blocked.

## No-Execution Proof

This branch is docs/audit/packet only. It does not invoke Modal, GPU jobs,
generation, experiments, benchmarks, profilers, timing collection, speedup
computation, billing, external APIs, package installation, dependency
downloads, model downloads, or tokenizer downloads.

## No-Output-Mutation Proof

This branch does not edit or write raw JSONL, `outputs/`, `artifacts/`,
`docs/preliminary_report/_report_data.json`, `docs/preliminary_report/index.html`,
`docs/preliminary_report/index.es.html`, analyzer outputs, report outputs,
result schemas, dependency files, lockfiles, or MLflow runtime state.

Ignored preliminary-report previews remain excluded unless a later explicit
review decision force-adds them.

## Validation Commands

Required local validation:

```bash
git diff --check
git status --short --branch
git diff --name-only -- shared/analysis shared/tests docs/preliminary_report outputs artifacts cluster1 cluster2 cluster3 shared/modal_harness pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
positive execution-authorization scan for Modal/GPU/generation/experiment/benchmark/profiler/output/paper-scale YES flags over docs/handoff, docs/experiment_packets, and this audit report
metric-family declaration scan for outcome-family fields, gate fields, status fields, diagnostic fields, and required metric names over docs/handoff, docs/experiment_packets, and this audit report
claim-boundary scan for pass-at-k wording, compile-vs-correctness wording, deferred syntax/performance wording, paper-scale claims, causal claims, performance claims, and speedup wording over docs/handoff, docs/experiment_packets, and this audit report
```

Results:

- `git diff --check`: pass.
- `git status --short --branch`: branch
  `codex/c3-n20-metric-family-gated-packet` with only the packet/audit/handoff
  docs changed.
- Forbidden code/output diff scan: empty output.
- Positive execution-authorization scan: empty output, exit code 1 for no
  matches.
- Metric-family declaration scan: required hits present in the packet and audit
  report.
- Claim-boundary scan: hits are prohibitions, gate-qualified pass@k wording,
  deferred/future-only wording, non-authorization text, or fail-closed
  claim-boundary language.
- Ignored preview status remained:
  - `!! docs/preliminary_report/_report_data.json`
  - `!! docs/preliminary_report/index.es.html`
  - `!! docs/preliminary_report/index.html`
- `.contracts/experiment_packets/` is absent, so validation used the allowed
  fallback packet path under `docs/experiment_packets/`.

## Review Classification

`C3_N20_PACKET_REVIEW_PASS_COMMIT_ALLOWED`

## Next-Step Recommendation

Commit the reviewed packet branch. Do not run Modal, GPU jobs, generation,
experiments, benchmarks, profilers, timing, speedup, analyzer refresh, output
mutation, raw JSONL rewrite, report refresh, or paper-scale work from this
packet alone.
