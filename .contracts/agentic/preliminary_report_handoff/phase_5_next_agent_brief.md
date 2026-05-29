# Phase 5 Next Agent Brief

## Next Phase

Phase 6 - Modal Infrastructure And Provenance Documentation

Expected file:

- `docs/04_modal_infrastructure.md`

## Use As Inputs

- `docs/00_project_map.md`
- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`

## Required Direction

- Explain Modal as methodology and reproducibility infrastructure, not as a research result.
- Document generation, evaluation, provenance, and durable row-writing roles.
- Document provenance fields such as model revision, tokenizer revision, Modal image SHA, package versions, XGrammar version, and grammar SHA where applicable.
- Preserve known provenance caveats: G has `modal_image_sha=unknown`, none has legacy schema/provenance limitations, and C lacks raw top-level `compile_success`.
- Document durable row writing as a protection against long-run data loss and connect it to Cluster 2 completed/partial-run history.
- Preserve the analyzer `metadata.reportable=false` caveat.
- Do not recommend or run new Modal jobs.

## Must Not Do

- Do not edit outputs.
- Do not edit grammar files.
- Do not edit source code.
- Do not edit README.md.
- Do not edit `.contracts/research/*`.
- Do not run Modal, GPU jobs, generation, or experiments.
- Do not write the preliminary report.

## Carry Forward Caveats

- Current scope is 2^2: none, G, C, G+C.
- Cluster 3/P is deferred.
- G and G+C are 177/180, not 180/180.
- Missing G/G+C rows are matmul/fp32/base_seed=5 and matmul/bf16/base_seed=0,18.
- G+C has five `F3_EVAL_PIPELINE` rows.
- Analyzer output exists but `metadata.reportable=false`.
- Cluster 1 functional success is unproven because Level 2 was not run.
