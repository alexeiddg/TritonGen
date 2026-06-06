# L1b n=5 Execution Authorization Report

date_utc: 2026-06-06

branch: `codex-track-handoff-context`

baseline_commit: `bc77e9b Audit L1a analyzer patch and golden drift`

authorization_source: operator `/goal` prompt attached at
`/Users/alexeidelgado/.codex/attachments/4ba7d790-c5d6-407d-b0b5-82697b0e0fb5/pasted-text.txt`

AUTHORIZES_EXECUTION: YES - L1b n=5 `grammar_mode_cp_12cell` only.

## Scope

This authorization is limited to the L1b development-scale 12-cell
`grammar_mode x C x P` selector:

- `grammar_mode in {grammar_off, template_upper_bound, task_agnostic}`
- `C in {off, on}`
- `P in {off, on}`
- 12 total cells
- `n=5` per cell
- 60 total planned rows
- `kernel_class=elementwise`
- `dtypes=fp32`
- `scale_tier=development`
- `TRITONGEN_MLFLOW=0`

No L2, n=20, paper-scale, profiler, benchmark, speedup, performance comparison,
runtime MLflow tracking, preliminary-report refresh, or output writes outside the
L1b namespaces are authorized by this report.

## Authorized Namespaces

Output namespace:

`outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5`

Observability namespace:

`artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5`

Post-run analysis/report/billing namespaces:

- `artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5*`
- `artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5*`
- `artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5*`

L1a artifacts are read-only for this phase.

## Command Surface

Required execution-plan command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier development --n 5 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Authorized execution command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier development --n 5 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1B_N5_AUTHORIZATION_GOAL_20260606 --overwrite
```

## Preflight Evidence

- `git status --short --branch`: branch aligned with
  `origin/codex-track-handoff-context` before selector patch.
- `git log --oneline -10`: includes baseline `bc77e9b`.
- L1b target namespace scan:
  `find outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1 artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1 artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1 artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1 artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1 -maxdepth 2 -name '*l1b_n5*' -print`
  returned empty output before the first L1b launch.
- Execution plan returned:
  - `authorization_profile: L1b n=5 development`
  - `cell_count: 12`
  - `planned_rows: 60`
  - `scale_tier: development`
  - `n: 5`
  - `output_root: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5`
  - `observability_root: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5`
  - `signed_authorization_option: --signed-l1b-authorization`

## Limits

- Max fresh L1b launch attempts: 3.
- Max attempts that reach Modal/GPU allocation: 2.
- Max rows: 60.
- Max generation attempts: 360.
- Max correctness calls: 360.
- Max wall-clock: 6h.
- Max estimated cost: USD 75.
- Max reconciled billing cap: USD 125.
- No resume of partially written L1b target paths unless a signed, deterministic,
  artifact-safe resume protocol is already documented.

## Status

AUTHORIZED_L1B_N5_ONLY_PRELAUNCH
