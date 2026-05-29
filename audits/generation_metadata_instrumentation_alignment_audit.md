# Generation Metadata Instrumentation Alignment Audit

Audit scope: current unstaged implementation in `/Users/alexeidelgado/Desktop/TritonGen`.

Rules honored during this audit:

- Used `.venv/bin/python` for all validation.
- Did not invoke Modal.
- Did not run generation, GPU checks, n=5, or n=20 experiments.
- Did not edit Python code, manifests, artifacts, or grammar files.
- Only this requested audit report was updated.

## 1. Executive Summary

Overall classification: **MOSTLY_ALIGNED_WITH_MINOR_GAPS**.

The implementation is aligned with the methodology-critical row-level evidence requirements by static code-path inspection and local tests:

- C1 durable rows, C1 Modal wire rows, C2 generated metadata, and C2 Modal payloads carry the required metadata fields.
- `grammar_active` is treated as attempted constrained decoding / condition routing, not G acceptance evidence.
- `grammar_valid` is enforced as `gbnf_parse_valid and semantic_valid`.
- C1 and C2 Modal generation code paths compute grammar SHA and split validation inside the remote generation runtime before returning payloads.
- Local revalidation is used as an audit gate after grammar SHA comparison, not as a replacement for Modal-returned evidence.
- Legacy rows load with defaults and fail paper-scale metadata gates.
- Analyzer/reporting paths use `grammar_valid` for grammar acceptance while preserving compile and functional metrics.
- Focused and broad local tests passed.

n=20 remains blocked. The implementation is ready for a **Modal n=1 smoke only**, but actual Modal runtime values remain **UNKNOWN** until that smoke produces an artifact. n=5 and n=20 should not run until n=1 smoke artifacts pass the metadata gate and the planned tiered progression.

Minor gaps remain:

- C1 run sidecars record `generation_metadata_schema_version` but do not yet summarize observed grammar SHA values, runtime versions, Modal image provenance, grammar validation counts, rejection-layer counts, or stop-reason counts as requested in the plan.
- Current runtime paths populate smoke/development rows, but strict write-time metadata enforcement is automatic only for `scale_tier="paper"` and for grammar-active current-schema invariants. Legacy/non-paper baseline or C payloads can still default to legacy-like values unless the stricter metadata gate is requested.
- Actual Modal-side behavior is statically aligned but not runtime-proven locally because Modal execution was forbidden for this audit.

## 2. Plan Alignment Matrix

| requirement | expected behavior | observed implementation | status | evidence |
|---|---|---|---|---|
| Phase A: schema additions | Add defaulted metadata fields to C1/C2 dataclasses and Modal schemas | Implemented across C1 row, C1 wire, C2 generated metadata, and C2 wire result schemas | PASS | `cluster1/results/dataclass.py:41`; `shared/modal_harness/schemas.py:98`; `cluster2/results/dataclass.py:245`; `cluster2/modal/schemas.py:241` |
| Phase A: legacy defaults | Old rows load without new fields | C1 deserialization fills defaults; C2 generated metadata fields are defaulted | PASS | `cluster1/results/dataclass.py:364`; `cluster2/results/dataclass.py:245`; tests `cluster1/tests/test_results.py:202`, `cluster1/tests/test_validate_cluster1_results.py:271` |
| Phase B: raw grammar SHA helper | SHA-256 over raw file bytes | Implemented with `Path(path).read_bytes()` | PASS | `cluster1/generation/provenance.py:44`; test `cluster1/tests/test_generation_provenance.py::test_sha256_file_reads_raw_bytes` |
| Phase B: runtime versions | Collect xgrammar/transformers/tokenizers versions with safe fallback | Implemented using `importlib.metadata.version`, fallback `"unknown"` | PASS | `cluster1/generation/provenance.py:71`; test `cluster1/tests/test_generation_provenance.py::test_runtime_versions_do_not_raise` |
| Phase B: model/tokenizer revisions | Extract observed revisions best-effort, else explicit/request fallback or unknown | Implemented for C1 loaded model/tokenizer and C2 loaded/requested revisions | PASS | `cluster1/generation/provenance.py`; `shared/modal_harness/generation.py:82`; `cluster2/modal/generation.py:291`; test `cluster2/tests/test_modal_generation_c2.py::test_c2_generation_rows_record_observed_model_and_tokenizer_revisions` |
| Phase B: Modal image provenance | Record stable Modal image SHA or deterministic fallback | Implemented with stable SHA env lookup plus stored fallback digest/components | PASS | `cluster1/generation/provenance.py:169`; tests `cluster1/tests/test_generation_provenance.py`, `cluster2/tests/test_modal_generation_c2.py:457` |
| Phase C: layered validator | Public helper distinguishes GBNF parse, Python AST, semantic validator, runtime errors | Implemented | PASS | `cluster1/grammar/triton_kernel_validator.py:404`; tests `cluster1/tests/test_generation_provenance.py:261`, `:285`, `:312`, `:322` |
| Phase C: `accepts_source` compatibility | Preserve existing boolean API | `accepts_source(...)` delegates to `validate_source_layers(...).grammar_valid` | PASS | `cluster1/grammar/triton_kernel_validator.py:397` |
| Phase C: local/Modal consistency gate | After Modal SHA match, local revalidation mismatch blocks | Implemented for C1 and C2 Modal conversions | PASS | `cluster1/experiments/run_cluster1_modal.py:886`; `cluster2/experiments/run_cluster2_modal.py:1254`; tests `cluster1/tests/test_run_cluster1_modal.py:483`, `cluster2/tests/test_run_cluster2_modal.py:395` |
| Phase D: C1 Modal instrumentation | Compute grammar SHA, validation fields, runtime versions, revisions, image provenance in Modal generation runtime | Implemented inside `RemoteGenerator.generate_one(...)`, after runtime grammar path resolution | PASS by static inspection | `shared/modal_harness/generation.py:82` |
| Phase D: C2 G+C Modal instrumentation | Same metadata evidence for C2 G+C path | Implemented inside `run_c2_generation_with_loaded_model(...)`, after runtime grammar path resolution | PASS by static inspection | `cluster2/modal/generation.py:291` |
| Phase D: payload propagation | Preserve Modal-returned fields through local conversion and durable rows | Implemented for C1 conversion and C2 generated metadata extraction/building | PASS | `cluster1/experiments/run_cluster1_modal.py:803`; `cluster2/experiments/run_cluster2_modal.py:1158`; `cluster2/results/dataclass.py:710`; tests `cluster1/tests/test_run_cluster1_modal.py:483`, `cluster2/tests/test_run_cluster2_modal.py:171` |
| Phase E: analyzer updates | Add grammar acceptance, rejection-layer, stop-reason summaries using `grammar_valid` | Implemented for C1 and shared factorial diagnostics | PASS | `cluster1/experiments/analyze_cluster1.py:516`; `shared/analysis/factorial.py`; tests `cluster1/tests/test_analysis.py`, `shared/tests/test_factorial_analysis.py` |
| Phase E: preserve compile/functional semantics | Do not redefine compile or functional success | Compile summaries remain based on `compile_success`; factorial primary response remains `functional_success` | PASS | `cluster1/experiments/analyze_cluster1.py`; `shared/analysis/factorial.py`; tests `shared/tests/test_factorial_analysis.py` |
| Phase F: tests | Cover schemas, provenance, validator split, round-trip, analyzers, gates, Modal payload propagation | Implemented and passing locally | PASS | Local validation section |
| Phase G: docs/runbooks | Document final semantics and n=20 gating | Research docs and C1/C2 READMEs use `grammar_valid` semantics and lowercase rejection layers | PASS | `.contracts/research/eval_metrics.md`; `.contracts/research/scale_policy.md`; `cluster1/README.md:33`; `cluster2/README.md` |
| Artifact serialization: JSONL rows | New fields serialize to durable JSONL rows | C1 serializes dataclass via `asdict`; C2 serializes `Cluster2EvalRow.to_json()` | PASS | `cluster1/results/logger.py:13`; `cluster2/results/logger.py:80`; tests `cluster1/tests/test_results.py:504`, `cluster2/tests/test_results_logger.py:205` |
| Artifact serialization: C1 sidecar summaries | C1 sidecars include schema version and run-level metadata summaries | Schema version exists; requested run-level summaries are not implemented | PARTIAL | `cluster1/experiments/run_cluster1_modal.py:221`; plan `.contracts/agentic/generation_metadata_instrumentation_plan.md:558` |
| Metadata gate | Paper-scale rows reject missing/unknown required metadata while legacy rows still load | Implemented for C1 and C2 paper-scale gates; non-paper strictness remains weaker | PASS for paper, PARTIAL for smoke/dev strictness | `cluster1/results/dataclass.py:162`; `cluster1/experiments/validate_cluster1_results.py`; `cluster2/results/dataclass.py:989`; tests `cluster1/tests/test_validate_cluster1_results.py:271`, `cluster2/tests/test_run_cluster2_modal.py:677` |
| Actual Modal artifact evidence | Confirm real Modal container emits fields | Not run by audit rule | UNKNOWN | Evidence missing: n=1 Modal smoke artifact |

## 3. Required Field Coverage Matrix

| field | C1 durable row | C1 Modal wire schema | C2 generated metadata | C2 Modal payload | serialization | tests | status |
|---|---|---|---|---|---|---|---|
| `grammar_sha` | `GenerationResult` | `RemoteGenerationResult` | `Cluster2GeneratedRowMetadata` | `RemoteC2GenerationResult` plus `generation_identity` | C1 JSONL, C2 JSONL | schema, conversion, SHA mismatch tests | PASS |
| `grammar_path` | yes | yes | yes | result plus `generation_identity` | yes | variant/path tests | PASS |
| `grammar_variant` | yes | request/result | yes | request/result plus identity | yes | variant routing tests | PASS |
| `gbnf_parse_valid` | yes | yes | yes | result plus identity | yes | validator and payload tests | PASS |
| `semantic_valid` | yes | yes | yes | result plus identity | yes | validator and payload tests | PASS |
| `grammar_valid` | yes, joint invariant | yes, joint invariant | yes, joint invariant | yes, joint invariant | yes | analyzer and schema tests | PASS |
| `rejection_layer` | yes | yes | yes | result plus identity | yes | validator-layer tests | PASS |
| `stop_reason` | yes | yes | yes | result plus identity | yes | stop-reason tests | PASS |
| `xgrammar_version` | yes | yes | yes | result plus `runtime_identity` | yes | provenance/schema tests | PASS |
| `transformers_version` | yes | yes | yes | result plus `runtime_identity` | yes | provenance/schema tests | PASS |
| `tokenizers_version` | yes | yes | yes | result plus `runtime_identity` | yes | provenance/schema tests | PASS |
| `model_revision` | yes | yes | yes | result plus `model_identity` | yes | revision propagation tests | PASS |
| `tokenizer_revision` | yes | yes | yes | result plus `model_identity` | yes | revision propagation tests | PASS |
| `modal_image_sha` | yes | yes | yes | result plus `runtime_identity` | yes | image SHA tests | PASS |
| `modal_image_provenance_sha256` | yes | yes | yes | result plus `runtime_identity` | yes | fallback digest tests | PASS |

Additional observation: `modal_image_provenance_components` is also present and serialized, which makes the fallback digest reconstructable even though the user-required field list only names `modal_image_provenance_sha256`.

## 4. Semantics Audit

### `grammar_active`

Confirmed behavior: `grammar_active` is attempted constrained decoding / condition routing. It is not used as acceptance evidence in the updated acceptance summaries.

Evidence:

- C1 generation only loads/applies grammar when `grammar_active=True`: `cluster1/generation/constrained_gen.py`.
- C1 analyzer condition labels use `grammar_active`, but acceptance metrics use `grammar_valid`: `cluster1/experiments/analyze_cluster1.py:516`.
- Shared factorial condition reconstruction can infer condition from `grammar_active` when explicit `condition` is absent, but grammar acceptance uses `grammar_valid`: `shared/analysis/factorial.py`.

### `grammar_valid`

Confirmed behavior: `grammar_valid` is the joint G acceptance field and is enforced as `gbnf_parse_valid and semantic_valid`.

Evidence:

- C1 invariant: `cluster1/results/dataclass.py:131`.
- C1 Modal schema invariant: `shared/modal_harness/schemas.py:98`.
- C2 generated metadata invariant: `cluster2/results/dataclass.py`.
- C2 Modal schema invariant: `cluster2/modal/schemas.py:241`.
- Tests: `cluster1/tests/test_results.py:161`, `cluster2/tests/test_results_logger.py:245`.

### `gbnf_parse_valid` and `semantic_valid`

Confirmed behavior: the validator returns split fields. `semantic_valid=True` only after GBNF parse and Python AST parsing succeed and the semantic validator accepts.

Evidence:

- `cluster1/grammar/triton_kernel_validator.py:404`.
- Tests: `cluster1/tests/test_generation_provenance.py:261`, `:285`, `:312`, `:322`.

### `rejection_layer`

Confirmed behavior: `rejection_layer` is null only for `grammar_valid=True`; invalid grammar rows require a layer. Allowed values are lowercase: `gbnf_parse`, `python_ast`, `semantic_validator`, `runtime_error`, and `unknown`.

Evidence:

- Constants: `shared/generation_metadata.py`.
- C1 invariant: `cluster1/results/dataclass.py:137`.
- C2 result tests: `cluster2/tests/test_results_logger.py:245`.
- C1 README uses lowercase examples: `cluster1/README.md:33`.

### `stop_reason`

Confirmed behavior: `stop_reason` is carried through decoded kernels, Modal schemas, durable rows, and C2 payloads. It is not silently inferred as `grammar_final_state`.

Evidence:

- Classification helper: `cluster1/generation/provenance.py:215`.
- C1 generation decoded result includes `stop_reason`: `cluster1/generation/constrained_gen.py`.
- XGrammar final-state support is feature-detected, not assumed: `cluster1/generation/constrained_decoding.py`.
- Test: `cluster1/tests/test_generation_provenance.py:107`.

### `masked_token_rate`

Confirmed behavior: `masked_token_rate` remains a masking diagnostic, not acceptance evidence. Analyzer output keeps it separate from grammar acceptance.

Evidence:

- Computed by `cluster1/generation/constrained_decoding.py`.
- C1 analyzer has separate grammar acceptance and masked-token diagnostics: `cluster1/experiments/analyze_cluster1.py`.

## 5. Modal-Side Evidence Audit

### Grammar SHA Computed Inside Modal

PASS by static code-path inspection.

- C1: `shared/modal_harness/generation.py:82` resolves the runtime grammar path with `_resolve_grammar_path`, then calls `grammar_provenance(...)` before loading the grammar.
- C2: `cluster2/modal/generation.py:291` resolves the generation routing path, then calls `grammar_provenance(...)` before loading the grammar.
- The helper hashes raw bytes: `cluster1/generation/provenance.py:44`.

Actual Modal artifact verification is **UNKNOWN** because Modal execution was forbidden.

### Validation Computed Inside Modal

PASS by static code-path inspection.

- C1: `RemoteGenerator.generate_one(...)` calls `validate_source_layers(...)` and returns validation fields in `RemoteGenerationResult`.
- C2: `run_c2_generation_with_loaded_model(...)` calls `validate_source_layers(...)` and returns validation fields in `RemoteC2GenerationResult` and `generation_identity`.
- Local C1/C2 runners compare local validation only after local SHA match.

Actual Modal artifact verification is **UNKNOWN** until n=1 smoke.

### Runtime Versions From Modal

PASS by static code-path inspection.

- C1 and C2 call `runtime_versions()` inside generation runtime functions.
- Paper gates reject `"unknown"` package versions.

### Image Provenance

PASS.

- Stable `modal_image_sha` is accepted if Modal exposes one.
- Otherwise `modal_image_provenance_sha256` and reconstructable `modal_image_provenance_components` are recorded.
- Fallback components include image source manifest, Modal env markers, Python runtime details, runtime package versions, and generation GPU context.

### Model/Tokenizer Revision

PASS by static code-path inspection.

- C1 records observed/best-effort model and tokenizer revisions.
- C2 requires immutable request revisions and compares loaded revisions against request parameters before generation.
- C2 payload records model/tokenizer identity.

## 6. Validator-Layer Audit

PASS.

Observed split behavior in `cluster1/grammar/triton_kernel_validator.py:404`:

- Grammar file read/parser setup failure: `runtime_error`.
- GBNF parse failure: `gbnf_parse_valid=False`, `semantic_valid=False`, `grammar_valid=False`, `rejection_layer="gbnf_parse"`.
- Python AST failure after GBNF parse success: `gbnf_parse_valid=True`, `semantic_valid=False`, `grammar_valid=False`, `rejection_layer="python_ast"`.
- Semantic validator failure after AST success: `gbnf_parse_valid=True`, `semantic_valid=False`, `grammar_valid=False`, `rejection_layer="semantic_validator"`.
- Semantic helper runtime failure: `rejection_layer="runtime_error"`.
- Full acceptance: all booleans true and `rejection_layer=None`.

`accepts_source(...)` remains backward compatible at `cluster1/grammar/triton_kernel_validator.py:397` by returning `validate_source_layers(...).grammar_valid`.

The implementation avoids duplicated validator logic in generation paths; C1 and C2 Modal paths call the shared layered helper.

## 7. Analyzer/Reporting Audit

PASS for methodology-critical semantics.

Confirmed:

- C1 grammar acceptance summaries use `grammar_valid`, `gbnf_parse_valid`, and `semantic_valid`: `cluster1/experiments/analyze_cluster1.py:516`.
- C1 rejection-layer and stop-reason breakdowns are available in `cluster1/experiments/analyze_cluster1.py`.
- Compile summaries remain based on `compile_success`; they are not filtered by grammar acceptance.
- Shared factorial diagnostics normalize grammar validation fields and expose grammar acceptance, rejection-layer, and stop-reason summaries.
- Shared factorial primary response remains `functional_success`; compile analysis remains secondary.

Residual reporting caveat:

- `cluster1/experiments/make_cluster1_figures.py` remains a frozen legacy compile-only figure path. It labels by `grammar_active` and plots `masked_token_rate`, but its module docstring and warning mark this as legacy and not current G acceptance reporting.

## 8. Metadata Gate Audit

### Legacy Loading

PASS.

- C1 old rows load through `generation_result_record_for_deserialization(...)`: `cluster1/results/dataclass.py:364`.
- C2 old generated metadata loads through defaulted dataclass fields: `cluster2/results/dataclass.py:245`.
- Replay rows remain frozen/legacy and do not receive synthetic current runtime grammar evidence.

### Paper-Scale Blocking

PASS.

- C1 paper rows are checked by `validate_paper_scale_metadata(...)`: `cluster1/results/dataclass.py:162`.
- C1 Modal runner applies the paper gate before writing when `scale_tier="paper"`.
- C1 validator CLI applies the same gate with `--require-generation-metadata` or `--require-full-n20`.
- C2 generated paper rows are checked by `validate_generated_paper_scale_metadata(...)`: `cluster2/results/dataclass.py:989`.
- C2 paper primary G+C is also blocked until a task-agnostic G n=20 replay artifact exists: `cluster2/tests/test_run_cluster2_modal.py:597`.

### Missing Field Behavior

PASS for paper-scale gates. PARTIAL for non-paper strictness.

- Paper gates reject missing grammar SHA/path/variant, split validation fields, stop reason, package versions, revisions, and Modal image SHA/fallback.
- Current Modal code populates these fields for smoke/development rows.
- However, write-time strictness is automatic only for paper scale and current-schema grammar-active rows. A test-double or older non-paper baseline/C payload can still default runtime/model fields to `"unknown"`/null and be written unless the stricter gate is requested.

### Unknown Field Behavior

PASS for paper-scale gates.

- Paper gates reject `"unknown"` for package versions and model/tokenizer revisions.
- Paper gates allow `modal_image_sha="unknown"` only when fallback digest and components are present and consistent.

## 9. Test Coverage Audit

| test file | behavior covered | missing cases |
|---|---|---|
| `cluster1/tests/test_generation_provenance.py` | raw-byte SHA, runtime versions fallback, image SHA/fallback, stop reason, layered validator classifications | No actual Modal runtime artifact check, by audit rule |
| `cluster1/tests/test_results.py` | C1 schema fields, joint grammar invariant, legacy defaults, paper gate, fallback components, malformed SHA, JSONL round-trip | Could add non-paper current-row strictness for baseline rows |
| `shared/tests/test_modal_harness_schemas.py` | C1 Modal schema metadata invariants and legacy variant default | No actual Modal call |
| `cluster1/tests/test_run_cluster1_modal.py` | C1 Modal conversion propagation, uninstrumented G rejection, SHA/path mismatch, paper write gate | Add uninstrumented baseline non-paper rejection if strict current-row gate is desired |
| `cluster1/tests/test_validate_cluster1_results.py` | C1 validator metadata gate, legacy loading, full-n20 flag | None for paper gate |
| `cluster1/tests/test_analysis.py` | Analyzer uses `grammar_valid` for acceptance metric; legacy figure path warning | None critical |
| `cluster2/tests/test_modal_generation_c2.py` | C2 G+C schema requires validation metadata, C rejects grammar metadata, payload identity/runtime/image checks, hash gates | No actual Modal call |
| `cluster2/tests/test_run_cluster2_modal.py` | C2 payload extraction, Modal/local validation mismatch, SHA mismatch, paper gates, task-agnostic n20 blocker | Add non-paper C/G+C current-row strictness if desired |
| `cluster2/tests/test_results_logger.py` | C2 JSONL serialization, generated metadata preservation, paper gate, C1 compatibility | None critical |
| `shared/tests/test_generation_metadata_constants.py` | C1/C2 metadata constants alignment | None |
| `shared/tests/test_factorial_analysis.py` | Grammar acceptance diagnostics alongside functional/compile analysis | None critical |
| `shared/tests/test_aggregation.py` | C2 aggregation/replay/generation hash and metadata consistency | Does not enforce `grammar_valid=True` for inclusion, which is correct because acceptance is reported separately |

## 10. Local Validation Results

Commands run with the local venv interpreter:

```text
.venv/bin/python -m pytest cluster1/tests/test_results.py cluster1/tests/test_constrained_gen.py cluster1/tests/test_run_cluster1_modal.py shared/tests/test_modal_harness_schemas.py -q
```

Outcome: **189 passed in 0.70s**.

```text
.venv/bin/python -m pytest cluster1/tests/test_grammar.py cluster1/tests/test_grammar_acceptance.py cluster1/tests/test_validate_cluster1_results.py cluster1/tests/test_analysis.py -q
```

Outcome: **772 passed in 122.19s**.

```text
.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_results_logger.py shared/tests/test_aggregation.py shared/tests/test_factorial_analysis.py -q
```

Outcome: **156 passed in 2.09s**.

Broader validation after focused tests passed:

```text
.venv/bin/python -m pytest shared/tests cluster1/tests cluster2/tests -v
```

Outcome: **1906 passed, 8 skipped in 340.31s**.

No Modal, GPU, generation, n=5, or n=20 command was run.

## 11. Blockers and Risks

### Critical Blockers

None found locally.

### Remaining Risks

- Actual Modal runtime evidence remains UNKNOWN until an n=1 smoke artifact is produced and inspected.
- Non-paper current-row metadata strictness is weaker than paper strictness for baseline/C payloads, although current runtime code does populate the fields.
- C1 sidecar summaries are incomplete against the approved plan; rows remain the source of truth.

## 12. Ordered Fix Plan

### Critical Blockers

None.

### High-Priority Correctness Fixes Before n=20/Paper

1. Enforce current metadata on all new Modal rows, not only paper rows.
   - Files/functions: `cluster1/experiments/run_cluster1_modal.py::_validate_remote_generation_metadata_against_local`, `cluster2/experiments/run_cluster2_modal.py::_generation_grammar_metadata_from_payload`.
   - Required change: for current Modal payloads, require `generation_metadata_schema_version >= 1`, non-unknown base runtime/model fields, and valid image SHA or fallback for baseline/C rows as well as G/G+C. Keep legacy file loading unchanged.
   - Tests: add C1 test rejecting an uninstrumented baseline Modal payload; add C2 test rejecting a C payload missing runtime identity in current-generation mode.
   - Expected validation command: `.venv/bin/python -m pytest cluster1/tests/test_run_cluster1_modal.py cluster2/tests/test_run_cluster2_modal.py -q`.

2. Validate the first actual Modal n=1 smoke artifact with the metadata gate before any n=5 rerun.
   - Files/functions: `cluster1/experiments/validate_cluster1_results.py::validate_results`, `cluster2/experiments/run_cluster2_modal.py::_validate_paper_scale_generation_metadata` if C2 smoke follows.
   - Required change: no implementation required if using existing flags; operationally run the existing metadata gate on the produced n=1 artifact.
   - Tests: existing metadata gate tests are sufficient.
   - Expected validation command: `.venv/bin/python -m pytest cluster1/tests/test_validate_cluster1_results.py cluster2/tests/test_run_cluster2_modal.py -q`.

### Medium-Priority Reporting/Artifact Fixes

3. Add C1 run sidecar summaries requested by the plan.
   - Files/functions: `cluster1/experiments/run_cluster1_modal.py::_build_initial_metadata`, `_finish_run_metadata`, and per-row update path near `_run`.
   - Required change: summarize observed grammar SHA values, package versions, Modal image SHA/fallback digests, grammar validation counts, rejection-layer counts, and stop-reason counts in the `.meta.json` sidecar without making sidecars necessary to interpret rows.
   - Tests: update `cluster1/tests/test_run_cluster1_modal.py::test_metadata_records_running_then_completed`.
   - Expected validation command: `.venv/bin/python -m pytest cluster1/tests/test_run_cluster1_modal.py -q`.

### Optional Polish

4. Make replay-row legacy status more explicit in docs/comments.
   - Files/functions: `cluster2/results/dataclass.py::Cluster2ReplayRowMetadata`, `cluster2/README.md`.
   - Required change: state that replay rows inherit frozen artifact provenance and are excluded from current paper-scale generation metadata eligibility.
   - Tests: existing `cluster2/tests/test_replay_manifest.py` and `cluster2/tests/test_results_logger.py` should remain sufficient.
   - Expected validation command: `.venv/bin/python -m pytest cluster2/tests/test_replay_manifest.py cluster2/tests/test_results_logger.py -q`.

## 13. Go/No-Go Recommendation

- Ready for Modal n=1 smoke: **YES**, n=1 only, after using the current instrumented code paths and validating the output artifact with the metadata gate. This audit confirms code-path alignment, not actual Modal artifact contents.
- Ready for n=5 rerun: **NO**. Require successful n=1 artifact validation first, then the planned smoke/development progression.
- Ready for n=20 planning: **NO**. n=20 remains blocked until Modal smoke/development artifacts prove row-level runtime metadata, split validation, analyzer semantics, and paper-scale gates in produced artifacts.
