# TritonGen

TritonGen is a research codebase for studying how inference-time controls affect
LLM-generated Triton GPU kernels. The project generates candidate Triton kernels,
validates them through parse, compile, runtime, and numerical-correctness stages,
and stores row-level evidence for later analysis.

The current experiments focus on three controls:

| Factor | Control | Meaning |
| --- | --- | --- |
| `G` | Grammar guidance | Constrained decoding with Triton-oriented grammar variants. |
| `C` | Correctness feedback | Level-2 numerical-correctness feedback and repair. |
| `P` | Compile feedback | Level-1 compile-error feedback and repair. |

The main experimental surface is a factorial pipeline over grammar mode,
correctness feedback, and compile feedback. The repository includes both the
pipeline code and the row evidence needed to inspect the current results.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `cluster1/` | Kernel tasks, grammar variants, baseline generation, grammar-guided generation, and compile validation. |
| `cluster2/` | Correctness evaluation, replay controls, and `C` repair logic. |
| `cluster3/` | Full `G`/`C`/`P` pipeline, Modal runner, row schema, durable logger, replay pairing, and validation helpers. |
| `shared/` | Shared evaluation ladder, failure taxonomy, Modal harness, factor definitions, tracking hooks, observability, and repair-history utilities. |
| `outputs/` | Selected raw JSONL result evidence and row-hash sidecars. Most generated outputs remain ignored unless explicitly selected. |
| `artifacts/observability/` | Selected observability sidecars matching the included Modal/Qwen result rows. |
| `docs/` | Methodology, artifact registry, analysis caveats, infrastructure notes, and navigation documents. |
| `.contracts/research/` | Stable research constraints, scale policy, and metric definitions. |

Start with these documents:

| Topic | Path |
| --- | --- |
| Project map | `docs/00_project_map.md` |
| Cluster 1 methodology | `docs/02_methodology_cluster1.md` |
| Cluster 2 methodology | `docs/03_methodology_cluster2.md` |
| Cluster 3 methodology | `docs/04_methodology_cluster3.md` |
| Modal infrastructure and provenance | `docs/04_modal_infrastructure.md` |
| Artifact and result registry | `docs/05_artifacts_and_results_registry.md` |
| Failure taxonomy and evaluation ladder | `docs/06_failure_taxonomy_and_eval_ladder.md` |
| Analysis and statistics caveats | `docs/07_analysis_and_statistics.md` |
| Current result inventory | `docs/results/research_committee_candidate_inventory.md` |
| Onboarding notes | `docs/ONBOARDING.md` |

## Current Evidence

There are two result streams in this repository. They answer related but not
identical questions, so their rates should not be merged.

| Stream | Model / service | Evidence | Status |
| --- | --- | --- | --- |
| Modal/Qwen L2b | `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` on Modal | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*` | 2,040 / 2,160 rows. This is the primary Level-2 correctness evidence for the Modal pipeline, but it is partial. |
| Fireworks/MiniMax | `accounts/fireworks/models/minimax-m2p7` | `outputs/fireworks_gbnf_n20_validated_outputs/outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/*.jsonl` | 2,160 / 2,160 rows. This stream measures a 15-shape compile-and-run endpoint, not Level-2 numerical correctness. |

Modal/Qwen coverage:

| Scope | Observed | Planned | Missing |
| --- | ---: | ---: | ---: |
| Full grammar-mode x C x P stream | 2,040 | 2,160 | 120 |
| Primary `grammar_off + task_agnostic` stream | 1,360 | 1,440 | 80 |
| Diagnostic `template_upper_bound` stream | 680 | 720 | 40 |

The missing Modal/Qwen rows are all in `matmul__fp32` cells:

- `task_agnostic__c_off__p_off`
- `task_agnostic__c_off__p_on`
- `task_agnostic__c_on__p_off`
- `task_agnostic__c_on__p_on`
- `template_upper_bound__c_off__p_on`
- `template_upper_bound__c_on__p_on`

Important interpretation boundaries:

- The primary Modal/Qwen stream currently has 0 / 1,360 Level-2 functional
  successes.
- `template_upper_bound` is diagnostic because it encodes task structure. It is
  useful for grammar-specificity analysis, but it is not the primary `G` effect.
- Fireworks/MiniMax `compile_success` is not equivalent to Modal/Qwen
  `functional_success`.
- The canonical analyzer does not currently produce a reportable output for the
  Modal/Qwen or Fireworks/MiniMax streams. Current summaries come from direct
  JSONL aggregation with the metric caveats above.
- This repository does not claim timing, profiling, speedup, or performance
  results.

## Local Setup

Use Python 3.11 or newer.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

If editable install is not desired, install the pinned runtime requirements:

```bash
pip install -r requirements.txt
```

Optional MLflow tracking support is off by default:

```bash
pip install "tritongen[tracking]"
```

## Local Verification

These checks do not run remote jobs or spend GPU/API resources:

```bash
.venv/bin/python -m compileall cluster1 cluster2 cluster3 shared
.venv/bin/python -m pytest
```

To inspect the current evidence without rerunning experiments, read the JSONL
rows directly or start from:

```text
docs/results/research_committee_candidate_inventory.md
```

That inventory records selected result paths, row counts, sizes, ignored-output
status, and the exact include/exclude policy for result artifacts.

## Reproducing Experiments

There are two different replication levels:

1. Reproduce local validation and analysis logic from checked-in code and JSONL
   rows.
2. Rerun remote generation/evaluation jobs through Modal or provider APIs.

For the first level, use local tests, row validation helpers, and the checked-in
evidence under `outputs/` and `artifacts/observability/`.

For the second level, inspect the run entrypoints and scripts before executing
anything:

| Purpose | Entry point |
| --- | --- |
| Cluster 3 Modal runner | `cluster3/experiments/run_cluster3_modal.py` |
| Grammar-mode matrix planning | `cluster3/planning/grammar_mode_matrix.py` |
| L2b coverage validation | `cluster3/analysis/validate_l2b_full_coverage.py` |
| L2b rescue validation | `cluster3/analysis/validate_l2b_two_lane_rescue_union.py` |
| Modal infrastructure notes | `docs/04_modal_infrastructure.md` |

Remote replication requires Modal credentials, provider credentials, model access,
and intentional GPU/API spend. The Modal Hugging Face secret hook is documented
in `shared/modal_harness/secrets.py`; the expected environment variable is
`TRITONGEN_MODAL_HF_SECRET`.

Before any remote rerun, verify the active command against the current code and
record a new artifact-registration pass. Historical launch scripts were removed
from the research handoff because they reflected old branch and coverage
assumptions; reconstruct reruns from the current runner, planner, and artifact
inventory instead.

## Analysis Status

The implemented analyzer primitives live in `shared/analysis/factorial.py`.
Earlier 2^2 artifacts have a registered analyzer output, documented in
`docs/05_artifacts_and_results_registry.md` and
`docs/07_analysis_and_statistics.md`.

The current Modal/Qwen and Fireworks/MiniMax streams are not analyzer-ready:

- Modal/Qwen rows lack replay-control metadata required by the paired analyzer.
- Fireworks/MiniMax rows use a shallower endpoint and do not contain
  `functional_success` or replay-pair metadata.

Until that schema work is done, result statements for these streams should cite
raw JSONL aggregation and preserve the response-variable caveats.

## What Not To Treat As Results

The following paths are useful history or local scratch, but they are not result
sources for the current repository state:

```text
docs/paper_draft/
paper_figures/
docs/experiment_packets/
.contracts/agentic/
```

Audits in `audits/` are evidence history. Use them to trace decisions, but cite
the promoted conclusions in `docs/`, checked-in JSONL rows, and source code when
describing the current methodology.

## Source Of Truth

When files disagree, use this order:

1. Current source code and tests define implemented behavior.
2. Current JSONL rows and hash sidecars define observed result evidence.
3. `docs/results/research_committee_candidate_inventory.md` defines the current
   selected result inventory and artifact policy.
4. Methodology docs in `docs/` define interpretation and caveats.
5. `.contracts/research/` defines research constraints and scale policy.
6. `audits/` and historical packets provide traceability, not primary results.
