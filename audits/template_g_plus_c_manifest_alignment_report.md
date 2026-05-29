# Template G+C Manifest Alignment Report

## 1. Executive summary

Phase 1 status: `ALIGNMENT_READY`.

The current-pipeline template G artifact at `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` was verified locally and registered in `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` as `g_template_upper_bound_current_pipeline_n20_l4`.

The explicit `template_upper_bound` diagnostic replay route now selects the current-pipeline template G artifact. The legacy template artifact `g_template_upper_bound_n20_l4` remains registered but is no longer selected for this diagnostic route. Task-agnostic G registration and selected task-agnostic G+C replay behavior were not altered.

Minimal alignment fixes were made because the template G+C smoke verification requires current replay-source identity in generated rows:

- `cluster2/modal/generation.py` maps `template_upper_bound` hash-gate verification to `g_template_upper_bound_current_pipeline_n20_l4`.
- `cluster2/results/dataclass.py` and `cluster2/experiments/run_cluster2_modal.py` expose `cluster1_artifact_id` and `replay_source` in generated-row metadata.
- `cluster2/validation/generated_metadata.py` accepts those fields when validating legacy flat generated metadata.
- Related tests were updated to expect the current-pipeline template replay artifact.

## 2. Template G artifact verification

Verified with `.venv/bin/python`:

| Check | Result |
| --- | --- |
| Path exists | yes |
| Valid JSONL rows | 180 |
| Bad JSON lines | 0 |
| `grammar_variant` | `template_upper_bound` on 180/180 |
| `grammar_path` | `cluster1/grammar/triton_kernel.gbnf` on 180/180 |
| `grammar_sha` | `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82` on 180/180 |
| `compile_success` | true on 180/180 |
| Model/tokenizer revision | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` on 180/180 |
| Modal provenance | `modal_image_sha=im-tU3VQyAbFvrusOxtlwspCN`; `modal_image_provenance_sha256=82fb2024879bf2db36d75995b0704ade1a9c32dc2d3d3aff6207332995dc7535` |
| Cell coverage | 20 rows for every kernel-class/dtype cell |

Known row-shape caveat: rows are flat Cluster 1 rows and omit row-level `condition`, `scale_tier`, `base_seed`, `sample_index`, and `max_new_tokens`; the sidecar records `condition=G`, `scale_tier=paper`, and `max_new_tokens=2048`.

## 3. Manifest registration details

Registered artifact:

| Field | Value |
| --- | --- |
| Artifact ID | `g_template_upper_bound_current_pipeline_n20_l4` |
| Path | `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` |
| Rows | 180 |
| Intended rows | 180 |
| Coverage policy | `EXACT_COVERAGE` |
| Grammar variant | `template_upper_bound` |
| Grammar SHA | `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82` |
| Scale tier | `paper` |
| Diagnostic only | true |
| Primary analysis | false |

The selected template controls are now:

```text
none_baseline_n20_l4
g_template_upper_bound_current_pipeline_n20_l4
```

The legacy template artifact remains in the manifest as `g_template_upper_bound_n20_l4` for historical diagnostic evidence but is not selected for the current-pipeline template diagnostic route.

`docs/05_artifacts_and_results_registry.md` was updated to record the replay artifact ID and diagnostic-only replay registration.

## 4. Grammar/hash status

Local grammar hash:

```text
cluster1/grammar/triton_kernel.gbnf
0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82
```

This matches the artifact row metadata and the manifest entry.

The frozen Cluster 1 manifest hash recorded in `cluster2/contracts/phase_minus1_manifest.json` was updated because the existing Cluster 2 hash gate verifies that contract before G+C generation. No grammar file was modified.

## 5. Tests run

Required:

```bash
.venv/bin/python -m pytest cluster2/tests/test_replay_manifest.py -v
```

Result: 13 passed.

```bash
.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py -q
```

Result: 76 passed.

```bash
.venv/bin/python -m pytest shared/tests -k "factorial or template" -v
```

Result: 107 passed, 465 deselected.

Additional targeted checks:

```bash
.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py::test_g_plus_c_hash_gate_uses_current_task_agnostic_n20_artifact cluster2/tests/test_results_logger.py::test_generated_rows_preserve_c2_generation_hash_semantics -q
```

Result: 2 passed.

## 6. Alignment classification

`ALIGNMENT_READY`

## 7. Remaining gaps

No Phase 1 alignment gaps remain.

This does not create or imply a template G+C n=20 artifact. The template path remains diagnostic/non-primary, and the primary analyzer output was not modified.

## 8. Next recommendation

Proceed to Phase 2 n=1 Modal smoke for explicit `template_upper_bound` G+C using:

```text
outputs/cluster2/template_g_plus_c_smoke_n1.jsonl
```
