# Research Committee Candidate Inventory

Status: `FROZEN_CANDIDATE_INVENTORY_WITH_ARTIFACT_POLICY`
Date: 2026-06-17
Current branch inspected: `codex-track-handoff-context`

This document is the current cut-list source of truth for preparing a research
committee handoff branch. It records the live tree inventory before branch work:
tracked diff versus `main`, untracked docs/audits, ignored output directories,
row counts, sizes, and ignore status.

No branch, staging, commit, merge, push, Modal, Fireworks, GPU, generation,
billing, benchmark, or analyzer execution action is authorized by this document.

## Handoff Policy

The committee handoff should include the result evidence, the pipeline needed to
understand how those results were produced, and concise documentation that helps
a human reviewer navigate the codebase.

## Artifact Policy Decision

Decision: `SELF_CONTAINED_FINAL_BRANCH_WITH_EXACT_EVIDENCE`

The final paper/research-committee branch should be self-contained for every
result claim it cites. Because the relevant raw evidence is small enough, the
branch should intentionally force-track the exact ignored row evidence selected
below instead of relying on a local-only artifact cache.

Include exact raw evidence:

- Modal/Qwen L2b attempt2 result rows and row-hash sidecars:
  `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*`
  (about 12.3M total across the four selected result directories).
- Fireworks/MiniMax validated result rows:
  `outputs/fireworks_gbnf_n20_validated_outputs/outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/*.jsonl`
  (the imported validation bundle is about 23M total; the final branch should
  select the row JSONL evidence, not treat embedded audit/packet docs as
  primary committee docs).
- L2b observability sidecars only when they match the cited Modal/Qwen row
  directories:
  `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*`.

Do not include:

- `mlruns/`.
- Raw billing exports or billing reconciliation scratch.
- `.DS_Store`, editor metadata, caches, `__pycache__/`, `.pytest_cache/`, or
  virtual environments.
- Temporary files, paper-draft leftovers, or unrelated generated scratch.
- Broad `outputs/` contents outside the exact selected evidence above.

Implementation rule for the future branch step: keep `.gitignore` broad and
use selective `git add -f` for the exact ignored evidence paths accepted in
this document. Do not broadly unignore `outputs/`.

Include:

- Current pipeline code under `cluster1/`, `cluster2/`, `cluster3/`, `shared/`,
  and the small launch/helper scripts that explain the completed runs.
- Current result rows and hash sidecars for the Modal/Qwen L2b attempt2 stream.
- Current result rows for the Fireworks/MiniMax stream, kept separate from
  Modal/Qwen.
- Observability sidecars that correspond to included Modal/Qwen rows, when the
  handoff needs provenance, token/cost, Modal context, or duration metadata.
- Committee-facing docs in `README.md`, `docs/results/`, and selected
  methodology/navigation docs.
- Research-facing contracts in `.contracts/research/` only where they describe
  stable methodology or interpretation policy.

Exclude from the committee handoff:

- `docs/paper_draft/` and `paper_figures/`.
- `.contracts/agentic/**`.
- Agentic handoff/routing/version files unless a human reviewer explicitly asks
  for maintenance history.
- `docs/experiment_packets/**`, implementation plans, and authorization packets.
- Internal audits as primary documentation. Promote verified conclusions into
  committee-facing docs instead.
- `mlruns/`, raw billing exports, caches, `__pycache__/`, `.DS_Store`, editor
  metadata, and scratch outputs.
- Any output directory outside the selected result evidence below unless it is
  explicitly added to this manifest.

## Tracked Diff Versus `main`

Read-only command used:

```bash
git diff --name-status main...HEAD
```

Summary:

| Status | Count |
| --- | ---: |
| Added | 1,271 |
| Modified | 42 |

Top-level path counts:

| Top-level path | Count |
| --- | ---: |
| `artifacts` | 633 |
| `outputs` | 270 |
| `audits` | 187 |
| `shared` | 77 |
| `docs` | 52 |
| `.contracts` | 41 |
| `cluster3` | 26 |
| `cluster2` | 10 |
| `scripts` | 6 |
| `cluster1` | 5 |
| `README.md` | 1 |
| `.gitignore` | 1 |
| `.env.example` | 1 |
| `_mlflow_demo.py` | 1 |
| `pyproject.toml` | 1 |
| `requirements.txt` | 1 |

Interpretation: do not merge the whole branch into `main` blindly. The branch
contains useful pipeline/result work plus a large amount of agentic,
authorization, audit, and planning material that should be filtered.

## Worktree Inventory

Read-only command used:

```bash
git status --short --branch --untracked-files=all
```

Current branch:

```text
codex-track-handoff-context...origin/codex-track-handoff-context
```

Untracked summary:

| Category | Count |
| --- | ---: |
| `artifacts` | 144 |
| `audits` | 6 |
| `docs` | 3 |
| `paper_figures` | 1 |
| Total | 154 |

Untracked docs/audits:

| Path | Candidate classification |
| --- | --- |
| `audits/analyzer_capabilities_audit.md` | Internal evidence; promote conclusions into docs if needed. |
| `audits/analyzer_verification_summary.md` | Internal evidence; analyzer-blocked conclusion is promoted in this manifest. |
| `audits/fireworks_analyzer_invocation_audit.md` | Internal evidence; do not use as primary committee doc. |
| `audits/fireworks_analyzer_schema_compatibility.md` | Internal evidence; schema-blocked conclusion is promoted in this manifest. |
| `audits/paper_numbers_vs_canonical_analyzer_fireworks.md` | Internal evidence; do not include unless committee requests audit trail. |
| `audits/paper_numbers_vs_canonical_analyzer_modal.md` | Internal evidence; stale relative to current 2,040-row Modal state. |
| `docs/paper_draft/08_results_partial_coverage.md` | Exclude from final handoff. Superseded by JSONL evidence and this inventory. |
| `docs/paper_draft/08b_results_fireworks_parallel_study.md` | Exclude from final handoff. Superseded by JSONL evidence and this inventory. |
| `docs/results/research_committee_candidate_inventory.md` | Include; current inventory and cut-list source of truth. |
| `paper_figures/README.md` | Exclude from final handoff. |

The `docs/paper_draft/` and `paper_figures/` paths are not tracked. They are
also not ignored as directories; `paper_figures/.DS_Store` is ignored by
`.gitignore:33`.

## Ignored Output Directories

Read-only command used:

```bash
git check-ignore -v <candidate output dirs>
```

| Path | Ignore status |
| --- | --- |
| `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2` | Ignored by `.gitignore:18:outputs/` |
| `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery` | Ignored by `.gitignore:18:outputs/` |
| `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel` | Ignored by `.gitignore:18:outputs/` |
| `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel` | Ignored by `.gitignore:18:outputs/` |
| `outputs/fireworks_gbnf_n20_validated_outputs` | Ignored by `.gitignore:18:outputs/` |
| `paper_figures/.DS_Store` | Ignored by `.gitignore:33:.DS_Store` |

If raw result rows are included in the final branch, they must be force-added
selectively or the ignore policy must be changed explicitly. The recommended
path is selective force-add of the exact evidence files listed here, not a broad
`outputs/` policy change.

## Modal/Qwen Result Evidence

Model stream: `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`
Experiment namespace: `full_pipeline_grammar_mode_cp_factorial_v1`
Candidate run: `l2b_n20_attempt2*`
Design: 12 grammar-mode x C x P cells, 3 kernel classes, 3 dtypes, 20 seeds
per file cell.

Raw result directories:

| Directory | Result JSONL files | Hash sidecars | Rows | Size |
| --- | ---: | ---: | ---: | ---: |
| `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2` | 54 | 54 | 1,080 | 6.5M |
| `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery` | 18 | 18 | 360 | 2.3M |
| `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel` | 24 | 24 | 480 | 2.8M |
| `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel` | 6 | 6 | 120 | 756K |
| Total | 102 | 102 | 2,040 | about 12.3M |

Matching observability directories:

| Directory | Observability JSONL | Hash sidecars | Summary JSON | Size |
| --- | ---: | ---: | ---: | ---: |
| `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2` | included in 102 total | included in 102 total | included in 102 total | 23M |
| `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery` | included in 102 total | included in 102 total | included in 102 total | 8.1M |
| `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel` | included in 102 total | included in 102 total | included in 102 total | 10M |
| `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel` | included in 102 total | included in 102 total | included in 102 total | 2.6M |
| Total | 102 | 102 | 102 | about 43.7M |

Coverage:

| Scope | Observed | Planned | Missing |
| --- | ---: | ---: | ---: |
| Full 12-cell Modal stream | 2,040 | 2,160 | 120 |
| Primary `grammar_off + task_agnostic` stream | 1,360 | 1,440 | 80 |
| Diagnostic `template_upper_bound` stream | 680 | 720 | 40 |

Missing Modal file cells:

| Shard | Cell | Missing rows |
| --- | --- | ---: |
| `matmul__fp32` | `task_agnostic__c_off__p_off` | 20 |
| `matmul__fp32` | `task_agnostic__c_off__p_on` | 20 |
| `matmul__fp32` | `task_agnostic__c_on__p_off` | 20 |
| `matmul__fp32` | `task_agnostic__c_on__p_on` | 20 |
| `matmul__fp32` | `template_upper_bound__c_off__p_on` | 20 |
| `matmul__fp32` | `template_upper_bound__c_on__p_on` | 20 |

Outcome summary by grammar mode:

| Grammar mode | Rows | Functional successes | Compile successes | Main failure shape |
| --- | ---: | ---: | ---: | --- |
| `grammar_off` | 720 | 0 | 0 | `F0_PARSE=720` |
| `task_agnostic` | 640 | 0 | 17 | `F1_RUNTIME=499`, `F0_PARSE=59`, `F1_COMPILE=40`, `F3_EVAL_PIPELINE=25`, `F2_NUMERIC_NAN=17` |
| `template_upper_bound` | 680 | 384 | 680 | `None=384`, `F2_NUMERIC_NAN=240`, `F2_NUMERIC_LARGE=56` |

Interpretation:

- The primary Modal/Qwen stream has 0 / 1,360 Level-2 functional successes.
- The task-agnostic grammar is primary for the `G` factor and remains partial.
- The template grammar is diagnostic because it encodes task structure; it
  should be used to discuss grammar specificity, not as the primary `G` effect.
- The attached paper draft froze an older Modal snapshot. The current on-disk
  candidate inventory supersedes the draft row counts.

## Fireworks/MiniMax Result Evidence

Model stream: `accounts/fireworks/models/minimax-m2p7`
Experiment: `fireworks_api_modal_v1`
Run tier: `fireworks_gbnf_n20`
Metric depth: 15-shape compile-and-run smoke, not Level-2 numerical correctness.

Candidate files:

| Path | Role | Rows |
| --- | --- | ---: |
| `outputs/fireworks_gbnf_n20_validated_outputs/outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_all_waves_validated.jsonl` | Combined validated row evidence | 2,160 |
| `outputs/fireworks_gbnf_n20_validated_outputs/outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_1.jsonl` | Accepted source wave | 540 |
| `outputs/fireworks_gbnf_n20_validated_outputs/outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_2_rerun_after_billing.jsonl` | Accepted source wave | 540 |
| `outputs/fireworks_gbnf_n20_validated_outputs/outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_3.jsonl` | Accepted source wave | 540 |
| `outputs/fireworks_gbnf_n20_validated_outputs/outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_4.jsonl` | Accepted source wave | 540 |

The whole imported Fireworks evidence directory is 23M and contains 11 files:
5 JSONL files and 6 markdown validation/packet files. For the committee branch,
prefer selecting the five JSONL files and promoting any needed validation
conclusions into `docs/results/`, rather than including the embedded audit and
packet markdown as primary navigation docs.

Outcome summary by grammar mode:

| Grammar mode | Rows | Compile-and-run successes | F3 rows | Main failure shape |
| --- | ---: | ---: | ---: | --- |
| `grammar_off` | 720 | 198 | 1 | `F0_PARSE=235`, `F0_BAD_SIGNATURE=106`, `F1_RUNTIME=145`, `F1_COMPILE=35`, `None=198` |
| `task_agnostic` | 720 | 102 | 21 | `F1_RUNTIME=582`, `F1_COMPILE=10`, `F0_BAD_SIGNATURE=4`, `F0_PARSE=1`, `None=102` |
| `template_upper_bound` | 720 | 690 | 0 | `None=690`, `F1_RUNTIME=30` |

Interpretation:

- Fireworks is full coverage at 2,160 / 2,160 rows.
- `compile_success` in this stream is a 15-shape compile-and-run endpoint, not
  numerical correctness.
- Rates must not be directly compared to Modal `functional_success`.
- Fireworks corroborates the grammar-specificity pattern and the lack of a
  detectable C/P effect on this shallower endpoint, but it is not a replacement
  for Modal Level-2 evidence.

## Analyzer Status

The canonical analyzer is not currently the source of result tables for these
two streams.

Modal/Qwen blocker:

- The L2b attempt2 rows lack the replay-control metadata required by the paired
  analyzer, especially `generated_metadata.replay_control_condition`.
- Adding the remaining rows would not fix that schema gap.
- A canonical analyzer output requires analyzer work or a principled row
  backfill, neither of which is part of this freeze.

Fireworks/MiniMax blockers:

- Rows do not contain `functional_success` because the stream did not run Level
  2 numerical correctness.
- Rows do not contain the replay-pair metadata expected by the paired analyzer.
- Repair trace fields are absent.

Current result claims should therefore be described as direct JSONL aggregation
from row evidence, with the response-variable caveats above.

## Recommended Committee Cut

Recommended include list:

| Area | Include |
| --- | --- |
| Entry docs | `README.md`, `docs/00_project_map.md`, `docs/results/research_committee_candidate_inventory.md` |
| Methodology docs | `docs/04_methodology_cluster3.md`, `docs/04_modal_infrastructure.md`, `docs/06_failure_taxonomy_and_eval_ladder.md`, `docs/07_analysis_and_statistics.md` |
| Code navigation | `docs/handoff/codebase_handoff_guide.md`, `cluster1/README.md`, `cluster2/README.md`, `cluster3/README.md` if refreshed or reviewed |
| Research policy | `.contracts/research/research_scope.md`, `.contracts/research/eval_metrics.md`, `.contracts/research/scale_policy.md`, `.contracts/research/mlflow_tracking_policy.md` |
| Modal/Qwen raw result evidence | The four `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*` directories, selected with force-add because `outputs/` is ignored |
| Modal/Qwen row hashes | All `.hashes.json` files paired with the selected Modal JSONL files |
| Modal/Qwen observability | The four matching `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*` directories if provenance/observability is in scope |
| Fireworks/MiniMax raw result evidence | The five JSONL files under `outputs/fireworks_gbnf_n20_validated_outputs/outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/` |
| Pipeline code | `cluster1/`, `cluster2/`, `cluster3/`, `shared/`, `scripts/run_l2b_n20_attempt2*.sh`, `pyproject.toml`, `requirements.txt`, `.env.example` |

Recommended exclude list:

| Area | Exclude |
| --- | --- |
| Paper draft leftovers | `docs/paper_draft/`, `paper_figures/` |
| Agentic contracts | `.contracts/agentic/**` |
| Execution packets | `docs/experiment_packets/**` |
| Implementation/spec plans | `docs/implementation_plans/**`, `docs/12_experiment_observability_plan.md` through `docs/19_modal_full_factorial_optimization_plan.md` unless a reviewer explicitly needs development history |
| Agent routing/version docs | `docs/handoff/agentic_*`, `docs/handoff/document_version_registry.md`, `docs/handoff/experiment_change_orchestration_state.md` |
| Internal audits | `audits/*.md` as primary docs; keep only if an audit appendix is explicitly requested |
| Non-result outputs | Old smoke, n=1, n=2, n=5, failed, blocked, or partial outputs not listed above |
| Runtime clutter | `mlruns/`, `.pytest_cache/`, `__pycache__/`, `.DS_Store`, `.idea/`, `.venv/`, raw billing exports |

## Next Branching Step

After this inventory is reviewed, create a selected final branch from `main`
using a `codex/` prefix and layer only the accepted files from this manifest.
Recommended branch name:

```text
codex/final-paper-reconciliation
```

Before any commit, run local-only verification:

```bash
git diff --check
.venv/bin/python -m compileall cluster1 cluster2 cluster3 shared
.venv/bin/python -m pytest <targeted tests selected for the final cut>
```

Do not run Modal, Fireworks, GPU generation, billing, benchmarks, or analyzer
mutations without explicit authorization.
