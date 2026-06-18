# TritonGen

TritonGen is a research codebase for evaluating inference-time controls for
LLM-generated Triton GPU kernels. The current handoff target is a research
committee review of the repository, not a paper-draft bundle.

The experiment studies three binary controls in a factorial design:

| Factor | Meaning |
| --- | --- |
| `G` | Grammar-guided decoding using Triton GBNF/XGrammar style constraints. |
| `C` | Level-2 numerical-correctness feedback repair. |
| `P` | Level-1 compile-error feedback repair. |

The repository now contains two result streams:

| Stream | Evidence | Current status |
| --- | --- | --- |
| Modal / Qwen2.5-Coder-7B-AWQ | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*` | 2,040 / 2,160 rows on disk across the 12-cell grammar-mode x C x P design. Primary grammar-off plus task-agnostic rows are 1,360 / 1,440, with 0 functional successes. Template upper-bound diagnostic rows are 680 / 720, with 384 functional successes. |
| Fireworks / MiniMax M2 | `outputs/fireworks_gbnf_n20_validated_outputs/outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_all_waves_validated.jsonl` | 2,160 / 2,160 rows. This stream measures 15-shape compile-and-run success, not Level-2 numerical correctness. It is a separate evidence stream and must not be merged with Modal rates. |

The frozen candidate cut-list and current row-count evidence live in
`docs/results/research_committee_candidate_inventory.md`.

Artifact policy for the final branch: make it self-contained by selectively
force-tracking the exact result rows cited by the committee handoff. Keep
`.gitignore` broad; do not unignore all of `outputs/`.

## Current Result Caveats

- The Modal/Qwen primary task-agnostic stream is partial: the missing 80
  primary rows are the four `matmul__fp32/task_agnostic` C/P cells.
- The Modal template diagnostic stream is partial: the missing 40 template rows
  are the two `matmul__fp32/template_upper_bound` cells with `p_on`.
- The Modal primary stream has 0 / 1,360 Level-2 functional successes in the
  current on-disk candidate inventory.
- The Modal `template_upper_bound` grammar is diagnostic. It includes task
  structure and must not be reported as the primary grammar effect.
- The Fireworks/MiniMax stream is full coverage but shallower: `compile_success`
  means parse, signature, Triton compile, and 15-shape runtime smoke without
  exception. It is not `functional_success`.
- The canonical analyzer cannot currently produce a reportable output for these
  streams without schema work. Modal rows lack the replay-control metadata the
  paired analyzer requires; Fireworks rows lack Level-2 `functional_success` and
  replay-pair metadata.
- No performance, timing, profiling, fast@1, or speedup result is claimed.
- This README and the inventory do not authorize any Modal, Fireworks, GPU,
  generation, billing, or benchmark execution.

## Committee-Facing Docs

Use these files to navigate the repository for research review:

| Topic | Path |
| --- | --- |
| Current candidate inventory and cut-list | `docs/results/research_committee_candidate_inventory.md` |
| Project map and source-of-truth policy | `docs/00_project_map.md` |
| Cluster 3 methodology for the G/C/P factorial pipeline | `docs/04_methodology_cluster3.md` |
| Modal infrastructure and provenance | `docs/04_modal_infrastructure.md` |
| Failure taxonomy and evaluation ladder | `docs/06_failure_taxonomy_and_eval_ladder.md` |
| Analyzer/statistics semantics and current schema caveats | `docs/07_analysis_and_statistics.md` |
| Codebase navigation | `docs/handoff/codebase_handoff_guide.md` |
| Optional tracking notes | `docs/tracking/README.md` |

Older paper-draft and figure folders are not part of the committee handoff:

```text
docs/paper_draft/
paper_figures/
```

They are excluded from the candidate cut-list. Current result claims should be
made from the JSONL evidence and the committee inventory, not from those draft
files.

## Code Navigation

The main pipeline surfaces are:

| Area | Paths |
| --- | --- |
| Kernel tasks and grammar | `cluster1/data/kernels/`, `cluster1/grammar/` |
| Correctness feedback and Level-2 runner | `cluster2/feedback/`, `cluster2/modal/` |
| Full G/C/P pipeline | `cluster3/experiments/run_cluster3_modal.py`, `cluster3/feedback/`, `cluster3/modal/`, `cluster3/results/` |
| Factor and grammar-mode planning | `cluster3/planning/grammar_mode_matrix.py`, `shared/factors/grammar_modes.py` |
| Analysis and reporting primitives | `shared/analysis/factorial.py`, `shared/eval/` |
| Observability sidecars | `shared/observability/`, `artifacts/observability/` |
| Launch helpers for the Modal L2b waves | `scripts/run_l2b_n20_attempt2_waves*.sh` |

The Fireworks/MiniMax row evidence is present locally as an imported result
stream. The committee-facing inventory records that stream separately from the
Modal/Qwen pipeline.

## Source Of Truth

When sources disagree, use this hierarchy:

1. Current code and tests define implemented behavior.
2. Current JSONL output artifacts define observed results.
3. `docs/results/research_committee_candidate_inventory.md` defines the current
   candidate cut-list and row-count inventory.
4. Methodology docs in `docs/` define human-readable interpretation once they
   are aligned with current artifacts.
5. `.contracts/research/` contains research-facing constraints and policy.
6. `audits/` contains evidence and verification history.
7. `.contracts/agentic/`, `docs/experiment_packets/`, implementation plans, and
   agentic handoff files are internal execution context unless their conclusions
   are promoted into committee-facing docs.

Do not cite agentic notes, authorization packets, or implementation-plan specs
as final methodology. Promote their verified conclusions into `docs/` first.
