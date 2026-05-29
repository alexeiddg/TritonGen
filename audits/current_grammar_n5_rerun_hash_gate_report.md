# Current-Grammar n=5 Rerun Hash-Gate Report

## Executive summary

Classification: `STILL_BLOCKED`.

The old task-agnostic n=5 artifact remains a previous-grammar artifact and must not be used as current-grammar compatibility evidence or as the development baseline for n=20. A fresh n=5 task-agnostic G run was generated under the current `cluster1/grammar/triton_kernel_agnostic.gbnf` grammar on L4, but the new artifact failed current-grammar validation: 14/45 rows accepted and 31/45 rows rejected.

Because the fresh n=5 did not validate, the Phase -1 grammar hash was not re-recorded, no manifests were updated, and the hash gate remains blocked by design.

## Old n=5 legacy archival status

Old artifact:

- Path: `outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl`
- SHA256: `0efb88886ec0abca432835e66309e232155bce55f562de385d13d8f506e55d56`
- Row count: 45
- Observed `grammar_variant`: `task_agnostic`
- Prior audit result: incompatible with current grammar, with 31/45 current-grammar rejections.

Status: report-level legacy classification only. The active manifest/gate state was not edited in this reset attempt because the replacement current-grammar n=5 artifact failed validation. The old artifact should be treated as `legacy_grammar_version` and excluded from current-grammar analysis, but that archival metadata should be committed only together with a valid replacement or an explicit blocked-state contract update.

## Fresh n=5 run command

Command executed:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster1.experiments.run_cluster1_modal --condition G --kernel-class all --n 5 --grammar-variant task_agnostic --grammar-path cluster1/grammar/triton_kernel_agnostic.gbnf --modal-generation-gpu L4 --max-new-tokens 512 --output outputs/cluster1/task_agnostic_g_current_grammar_n5_l4.jsonl --overwrite
```

Result:

- Modal run completed.
- Rows written: 45
- Infrastructure failures: 0
- New artifact path: `outputs/cluster1/task_agnostic_g_current_grammar_n5_l4.jsonl`
- New sidecar path: `outputs/cluster1/task_agnostic_g_current_grammar_n5_l4.jsonl.meta.json`

## New artifact summary

- Artifact SHA256: `38c310329e80626c1788ab09674bc6b7a89ca3f88c280c5d87eee1c2d9d08744`
- Sidecar SHA256: `8d32dafbdb182fbe9394bff8e3bf9574583902c170b50c8d66b6a45f5c09542e`
- Total rows: 45
- Expected locked cells: 9 kernel/dtype cells
- Observed rows per locked cell: 5
- Observed kernel classes: `elementwise`, `reduction`, `matmul`
- Observed dtypes: `fp32`, `fp16`, `bf16`
- Observed `grammar_active`: `true`
- Observed `grammar_variant`: `task_agnostic`
- `template_upper_bound` rows: 0
- Generation seeds per cell: `[0, 1, 2, 3, 4]`
- Model id: `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`
- Model/tokenizer revisions: not recorded by the existing Cluster 1 Modal runner.

## Launcher completeness inspection

Six-row sample:

| row | kernel | dtype | seed | output allocation | grid | bracket launch | return output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | elementwise | fp32 | 0 | yes | yes | yes | yes |
| 2 | elementwise | fp32 | 1 | yes | yes | yes | yes |
| 16 | reduction | fp32 | 0 | no | no | no | no |
| 17 | reduction | fp32 | 1 | yes | yes | no | no |
| 31 | matmul | fp32 | 0 | yes | yes | yes | yes |
| 32 | matmul | fp32 | 1 | yes | yes | yes | yes |

The current run improves the five audited matmul fp32 rows relative to the legacy artifact: they now include output allocation, grid computation, bracket launch, and return statements. However, reduction rows still show systematic incomplete or malformed launchers, so the run is not a clean current-grammar development baseline.

## Masked-token-rate and compile-rate signal

- Compile successes: 1/45
- Compile success rate: 2.22%
- Compile error types: `RuntimeError` 43, `CompilationError` 1, no error 1
- Masked token rate count: 45/45
- Masked token rate min: 0.7266880639073022
- Masked token rate median: 0.7895958075929421
- Masked token rate max: 0.8518569552403374
- Unique solution hashes: 43/45
- Unique source hashes: 43/45

The masked-token rate did not approach template-upper-bound territory near 99%, and outputs did not collapse. The compile rate is nonzero but weak. The blocker is grammar validation and incomplete/malformed generated launchers, not a masked-token-rate spike.

## Grammar validation result

Current grammar hash:

- `cluster1/grammar/triton_kernel_agnostic.gbnf`
- SHA256: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`

Validation of `outputs/cluster1/task_agnostic_g_current_grammar_n5_l4.jsonl` with `cluster1.grammar.triton_kernel_validator.accepts_source(..., TASK_AGNOSTIC_GBNF_PATH)`:

- Rows with source: 45
- Accepted: 14
- Rejected: 31

Rejection classes:

| rejection class | count |
| --- | ---: |
| `parser_launcher_missing_bracket_launch_return_output` | 10 |
| `parser_launcher_missing_grid_computation_bracket_launch_return_output` | 1 |
| `parser_launcher_missing_output_allocation_grid_computation_bracket_launch_return_output` | 4 |
| `semantic_launcher_missing_return_output` | 4 |
| `semantic_other` | 12 |

The fresh n=5 artifact therefore fails the required compatibility gate.

## Hash re-record result

Not performed.

Reason: the fresh current-grammar n=5 artifact failed grammar validation. Re-recording the grammar hash now would convert a failed compatibility reset into a silent provenance update, which is exactly what the Phase -1 gate is meant to prevent.

## Hash gate verification result

The active hash gate remains blocked, as expected because no hash was re-recorded.

Command:

```bash
.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py::test_remote_generator_generate_one_hash_matches_phase_minus_1 -v
```

Result: failed with the expected mismatch:

- Expected old hash: `756f46a76e8fc6e208a263a69678873ecbbe7327d1c3c7ee9fe6a902fb96600f`
- Current grammar hash: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`

## Compatibility check result

Smoke fixtures:

```bash
.venv/bin/python -m pytest cluster1/tests/test_grammar_acceptance.py -v
```

Result: 215 passed.

Fresh n=5 output compatibility:

- Artifact: `outputs/cluster1/task_agnostic_g_current_grammar_n5_l4.jsonl`
- Result: failed, 14/45 accepted and 31/45 rejected.

The old artifact was not used as current-grammar compatibility evidence.

## Go/no-go recommendation for n=20 task-agnostic G

No-go for n=20 task-agnostic G.

The current grammar fixtures pass, but the current generation path is not producing a fully grammar-valid n=5 baseline. Before n=20 planning, diagnose why Modal constrained generation can emit rows rejected by the local validator. The highest-priority classes are reduction launcher truncation/malformed wrapper generation and semantic validator rejections of generated launchers that include bracket launch but return non-canonical output variable names.

## Files modified

Generated by this reset attempt:

- `outputs/cluster1/task_agnostic_g_current_grammar_n5_l4.jsonl`
- `outputs/cluster1/task_agnostic_g_current_grammar_n5_l4.jsonl.meta.json`
- `audits/current_grammar_n5_rerun_hash_gate_report.md`

Not modified:

- `cluster1/grammar/triton_kernel_agnostic.gbnf`
- `cluster2/contracts/phase_minus1_manifest.json`
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`
- `cluster2/modal/generation.py`
- frozen Cluster 1 paper artifacts
- old n=5 artifact contents

## Remaining risks

- The replacement n=5 artifact is not valid under the current validator.
- The old n=5 artifact remains a legacy artifact by audit classification, but its archival metadata was not committed because the replacement failed.
- The existing Cluster 1 Modal runner does not record model revision or tokenizer revision in the artifact sidecar.
- Some current generated rows reach remote compile but still fail the local grammar validator, so the Modal constrained-decoding grammar path and local validator need alignment/debugging before any provenance refresh.
