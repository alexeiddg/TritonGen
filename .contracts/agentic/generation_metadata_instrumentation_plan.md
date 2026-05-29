# Generation Metadata Instrumentation Plan

## 1. Executive summary

The bug class is assertion-only generation evidence. Current artifacts can say
that grammar was intended or active, but they do not prove which grammar bytes
were loaded inside the runtime that generated a row, which runtime and image
produced it, why generation stopped, or whether the final source satisfied the
two-layer G acceptance contract.

This instrumentation must precede any further n=20 interpretation. The fresh
n=5 task-agnostic result shows that rows produced under supposed constrained
decoding can fail the local validator. Until every row carries grammar
provenance and post-generation validation metadata, `grammar_active=True` is
only evidence that the constrained path was attempted, not evidence that the
source is G-accepted.

This is evidence and provenance instrumentation, not a methodology redesign.
Do not change the meaning of `compile_success` or `functional_success`; add
fields that let reviewers audit the grammar path, grammar bytes, runtime,
stop reason, and G validation outcome.

The request sometimes describes the fix as twelve metadata fields, but the
named field set contains fourteen row fields: `grammar_sha`, `grammar_path`,
`grammar_variant`, `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`,
`rejection_layer`, `stop_reason`, `xgrammar_version`, `transformers_version`,
`tokenizers_version`, `model_revision`, `tokenizer_revision`, and
`modal_image_sha`. This plan treats the named field set as authoritative.

Key risks to account for before changing code:

- Modal may not expose a stable image SHA.
- XGrammar 0.1.33 may not expose a final-state API through the current wrapper.
- The existing validator exposes only `accepts_source(...) -> bool`; splitting
  GBNF parse and semantic failure needs a careful public helper.
- Running validation inside Modal may add import and runtime overhead.
- Existing readers are strict about dataclass fields and can break if defaults
  and deserialization shims are not added first.

Direct answers to the required questions:

1. `grammar_active` is currently used to label G condition rows in Cluster 1
   and shared analysis. It is not a valid substitute for `grammar_valid`.
2. `masked_token_rate` is computed in
   `cluster1/generation/constrained_decoding.py` as the mean fraction of masked
   logits per processor call. It proves masking occurred on observed steps, but
   it does not prove strict final G acceptance.
3. Current artifacts do not record the actual grammar hash computed inside
   Modal.
4. Current artifacts do not record the XGrammar version from inside Modal.
5. Current artifacts do not record a Modal image digest or SHA.
6. The validator can be refactored to split pure GBNF parse failure from
   semantic failure because `accepts_source` already performs those operations
   sequentially, but no public split API exists yet.
7. Stop reason cannot be determined accurately with the current
   `generate_source` wrapper. It only receives `output_ids` from
   `model.generate`.
8. Paper-scale G/G+C rows must require all fields listed in Section 18 with
   non-null/non-unknown values, except where Modal image SHA is unavailable and
   an approved fallback digest is recorded.
9. Legacy rows may leave new fields as `null` or `"unknown"` and must remain
   loadable.
10. n=20 must remain blocked until Modal rows include runtime grammar SHA,
    grammar path/variant, runtime versions, stop reason, split validation
    fields, joint `grammar_valid`, and rejection attribution.

## 2. Current codebase map

Actual Cluster 1 generation entrypoints:

- Local runner: `cluster1/experiments/run_cluster1.py`.
  - `main()` parses CLI args, loads model/tokenizer, loads one compiled grammar
    if needed, iterates cells, calls `run_one_generation(...)`, and appends via
    `cluster1.results.logger.append_result_jsonl`.
  - `run_one_generation(...)` builds the prompt, calls
    `cluster1.generation.constrained_gen.generate_source(...)`, then runs
    local compile checks and builds `GenerationResult`.
- Modal runner: `cluster1/experiments/run_cluster1_modal.py`.
  - `main(...)` is the Modal local entrypoint.
  - `_run(...)` iterates cells, writes `.meta.json`, calls `_run_one_cell(...)`,
    validates invariants, and appends JSONL.
  - `_run_one_cell(...)` calls `generate_source_modal(...)` and
    `check_compiles_modal(...)`, then converts through
    `remote_results_to_generation_result(...)`.
- Core generation wrapper: `cluster1/generation/constrained_gen.py`.
  - `generate_source(...)` tokenizes the prompt, optionally adds
    `TritonGrammarLogitsProcessor`, calls `model.generate(**generate_kwargs)`,
    decodes only new tokens, and returns `DecodedKernel`.
  - `DecodedKernel` currently carries only `source`, `masked_token_rate`,
    `generation_seed`, and `temperature`.

Actual Modal generation functions:

- Cluster 1 remote generation lives in `shared/modal_harness/generation.py`.
  - `RemoteGenerator` is an `@app.cls` using `llm_generation_image`.
  - `load_model()` loads `AutoTokenizer` and `AutoModelForCausalLM` inside the
    Modal container.
  - `generate_one(...)` validates `RemoteGenerationRequest`, resolves the
    grammar path, loads `CompiledGrammar`, runs `generate_source(...)`, and
    returns `RemoteGenerationResult.model_dump()`.
- Cluster 2 generated C/G+C path lives in `cluster2/modal/generation.py`.
  - `RemoteC2Generator` is an `@app.cls` using `c2_generation_image`.
  - `run_c2_generation_with_loaded_model(...)` routes `C` versus `G+C`;
    `G+C` uses the same Cluster 1 grammar loader and `generate_source(...)`.
  - `build_success_payload(...)` emits a wrapper payload with
    `generation_identity`, `model_identity`, `generation_hashes`, and
    `modal_context`.

Actual grammar-loading path:

- Cluster 1 canonical variant mapping is
  `cluster1/generation/grammar_variants.py`.
  - `template_upper_bound -> cluster1/grammar/triton_kernel.gbnf`.
  - `task_agnostic -> cluster1/grammar/triton_kernel_agnostic.gbnf`.
- Cluster 1 Modal request validation in `shared/modal_harness/schemas.py`
  checks that `grammar_path` matches `grammar_variant`.
- Cluster 1 Modal runtime resolves the path in
  `shared/modal_harness/generation.py::_resolve_grammar_path(...)`.
- Local Cluster 1 runner still has its own `DEFAULT_GRAMMAR_PATH` and a
  task-agnostic path guard in `cluster1/experiments/run_cluster1.py`; this
  needs alignment during implementation.
- Cluster 2 duplicates grammar routing in `cluster2/modal/generation.py`
  through `C2_GRAMMAR_PATHS_BY_VARIANT` and in
  `cluster2/results/dataclass.py::_validate_generated_grammar_metadata`.

Actual XGrammar initialization path:

- `cluster1/generation/grammar_loader.py::load_compiled_grammar(...)` computes
  a tokenizer vocabulary fingerprint, reads `Path(grammar_path).read_text(...)`,
  compiles the GBNF text through XGrammar, and returns `CompiledGrammar`.
- `cluster1/generation/constrained_decoding.py::TritonGrammarLogitsProcessor`
  creates an XGrammar `GrammarMatcher` in `_init_xgrammar_matcher(...)` unless
  the backend exposes a fake/direct mask API used by tests.
- The processor calls `accept_token(...)`, `fill_next_token_bitmask(...)`, and
  applies disallowed tokens to logits.

Actual artifact serialization path:

- Cluster 1 rows use `cluster1/results/dataclass.py::GenerationResult`.
- Cluster 1 JSONL writes use `cluster1/results/logger.py::append_result_jsonl`.
- Cluster 1 Modal run sidecars are written in
  `cluster1/experiments/run_cluster1_modal.py::_write_run_metadata`.
- Cluster 1 readers/analyzers use:
  - `cluster1/experiments/validate_cluster1_results.py`;
  - `cluster1/experiments/analyze_cluster1.py`;
  - `cluster1/experiments/make_cluster1_figures.py`.
- Cluster 2 rows use `cluster2/results/dataclass.py::Cluster2EvalRow` with
  `Cluster2GeneratedRowMetadata` or `Cluster2ReplayRowMetadata`.
- Cluster 2 JSONL and hash sidecars use `cluster2/results/logger.py`.

Actual schema/dataclass path:

- Cluster 1 durable row schema: `cluster1/results/dataclass.py`.
- Cluster 1 Modal wire schema: `shared/modal_harness/schemas.py`.
- Cluster 2 durable row schema: `cluster2/results/dataclass.py`.
- Cluster 2 Modal wire schema: `cluster2/modal/schemas.py`.
- Cluster 2 Modal wrapper payload validation:
  `cluster2/modal/generation.py::validate_remote_c2_generation_payload`.

Actual validator APIs:

- `cluster1/grammar/triton_kernel_validator.py::accepts_source(source,
  grammar_path=...) -> bool` is the public current API.
- Internally it reads GBNF text, compiles a Lark parser, calls
  `parser.parse(source)`, calls `ast.parse(source)`, and dispatches to
  `_semantic_accepts(...)` or `_semantic_accepts_task_agnostic(...)`.
- `validate_grammar_file(...)` validates grammar files, not generated rows.

Actual analyzer/aggregation paths using grammar condition metadata:

- `cluster1/experiments/analyze_cluster1.py` derives condition from
  `row.grammar_active`, groups by `row.grammar_variant`, reports masked token
  rate, and computes compile-only pass metrics.
- `cluster1/experiments/validate_cluster1_results.py` validates
  `grammar_active`, `grammar_variant`, and `masked_token_rate`, but not
  grammar acceptance.
- `cluster1/experiments/make_cluster1_figures.py` maps `grammar_active` to
  condition and asserts masked-token-rate presence.
- `shared/analysis/factorial.py` normalizes rows by explicit `condition` if
  present, otherwise derives `G` from `grammar_active`.
- `shared/eval/aggregation.py` validates C2 generated/replay hash classes and
  detects primary task-agnostic G+C rows by `generated_metadata.grammar_variant`
  and `grammar_claim_scope`.

## 3. Existing metadata inventory

Required field status:

| Field | Current status | Existing location | Decision |
| --- | --- | --- | --- |
| `grammar_sha` | Missing | C2 has source-file hashes and frozen manifest hashes, but not runtime grammar bytes per row | Add per-row; compute inside generation runtime for Modal |
| `grammar_path` | Partial | C1 request and sidecar run_config; C1 durable rows missing. C2 generated metadata has it | Add to C1 rows and C1 remote result; preserve/extend C2 generated metadata |
| `grammar_variant` | Present | C1 rows; C2 generated metadata; sidecars | Reuse; keep canonical values |
| `gbnf_parse_valid` | Missing | Validator has internal parse step only | Add per-row |
| `semantic_valid` | Missing | Validator has internal semantic step only | Add per-row |
| `grammar_valid` | Mentioned in docs only | `.contracts/research/eval_metrics.md` | Add per-row; do not alias to `grammar_active` |
| `rejection_layer` | Missing | Docs discuss old uppercase labels | Add per-row with required lowercase values |
| `stop_reason` | Missing | No current generation wrapper result | Add to `DecodedKernel` and remote results |
| `xgrammar_version` | Missing from Modal rows | Image pins source file to 0.1.33; C2 sidecar external pins may be local | Add per-row from Modal runtime |
| `transformers_version` | Missing from Modal rows | Image pins source file; C2 sidecar external pins may be local | Add per-row from Modal runtime |
| `tokenizers_version` | Missing from Modal rows | Image pins source file | Add per-row from Modal runtime |
| `model_revision` | Missing in C1 rows; present in C2 generated requests/rows | C2 row metadata and request | Add C1 per-row best effort; preserve C2 |
| `tokenizer_revision` | Missing in C1 rows; present in C2 generated requests/rows | C2 row metadata and request | Add C1 per-row best effort; preserve C2 |
| `modal_image_sha` | Missing | No row or sidecar field | Add if Modal exposes it; otherwise record approved fallback digest |

Fields present locally but not in Modal artifacts:

- `masked_token_rate` is produced inside Modal and returned to C1 rows, but it
  is a constraint-strength diagnostic, not acceptance evidence.
- The C2 content-hash sidecar records source hashes and external pins, but
  those are sidecar/run-class metadata, not the exact per-row Modal runtime.

Fields present in sidecars but not rows:

- C1 `.meta.json` sidecars include `model_id`, `grammar_variant`, run config,
  Modal GPU, git commit, and row counts.
- C2 `.hashes.json` sidecars include eval/generation hash classes and external
  pins.
- Frozen replay manifests include `model_revision` and `tokenizer_revision` as
  `"unavailable_in_frozen_cluster1_artifact"` for old Cluster 1 artifacts.

## 4. Design decision: row fields vs sidecar fields

Per-row fields are required for anything needed after JSONL merge, filtering,
or replay:

- `grammar_sha`
- `grammar_path`
- `grammar_variant`
- `gbnf_parse_valid`
- `semantic_valid`
- `grammar_valid`
- `rejection_layer`
- `stop_reason`
- `xgrammar_version`
- `transformers_version`
- `tokenizers_version`
- `model_revision`
- `tokenizer_revision`
- `modal_image_sha` or an approved per-row fallback provenance digest

Sidecars may duplicate run-level constants:

- package versions observed once per container class;
- Modal image definition hash or fallback digest;
- local grammar SHA used for cross-checking;
- aggregate rejection-layer counts;
- artifact-level paper metadata gates.

Rows remain the source of truth. Sidecars can speed audit and summarize a run,
but a row must still be reproducible and interpretable when copied into a
merged artifact.

## 5. Proposed schema changes

Cluster 1 durable rows:

- Update `cluster1/results/dataclass.py::GenerationResult` with optional
  defaulted fields appended after existing fields:
  - `grammar_sha: str | None = None`
  - `grammar_path: str | None = None`
  - `gbnf_parse_valid: bool | None = None`
  - `semantic_valid: bool | None = None`
  - `grammar_valid: bool | None = None`
  - `rejection_layer: str | None = None`
  - `stop_reason: str = "unknown"`
  - `xgrammar_version: str = "unknown"`
  - `transformers_version: str = "unknown"`
  - `tokenizers_version: str = "unknown"`
  - `model_revision: str = "unknown"`
  - `tokenizer_revision: str = "unknown"`
  - `modal_image_sha: str = "unknown"`
  - Optional fallback field if Modal SHA is unavailable:
    `modal_image_provenance_sha256: str | None = None`
- Extend `generation_result_record_for_deserialization(...)` to fill all new
  fields for legacy rows. This is required because current readers compute
  `field_names = fields(GenerationResult)` and fail on missing fields.
- Extend `validate_result_invariants(...)` with grammar-metadata rules, while
  allowing legacy defaults unless a paper-scale strict gate is requested.

Cluster 1 Modal wire schema:

- Update `shared/modal_harness/schemas.py::RemoteGenerationResult` with the
  same generation metadata fields needed before conversion.
- Consider adding a nested pydantic model only if it stays backward compatible.
  A flat shape is easier because `RemoteGenerationResult` is already flat.

Core generation wrapper:

- Update `cluster1/generation/constrained_gen.py::DecodedKernel` with:
  - `stop_reason`
  - optional `generated_token_count`
  - optional internal `grammar_final_state_observed`
- Do not add compile or correctness fields here.

Cluster 2 durable rows:

- Update `cluster2/results/dataclass.py::Cluster2GeneratedRowMetadata` with the
  required generation metadata fields, all defaulted for backward
  compatibility.
- For replay rows, either add the same optional fields to
  `Cluster2ReplayRowMetadata` or document that replay rows inherit legacy
  metadata from frozen Cluster 1 artifacts and cannot satisfy new paper-scale
  metadata gates.

Cluster 2 Modal wire and wrapper schema:

- Update `cluster2/modal/generation.py::build_success_payload(...)` to include
  grammar provenance, runtime provenance, stop reason, and validation fields in
  `generation_identity`, `model_identity`, and a new `runtime_identity` or flat
  keys.
- Update `validate_remote_c2_generation_payload(...)` accordingly.
- Update `cluster2/experiments/run_cluster2_modal.py::_generation_grammar_metadata_from_payload`
  or add a sibling extraction helper so generated rows receive the new fields.

Backward-compatibility strategy:

- Legacy rows load with `None` for grammar validation/provenance fields and
  `"unknown"` for string runtime fields.
- New smoke/development rows must include fields, but can use `"unknown"` for
  `modal_image_sha` only if the fallback digest is present.
- Paper-scale rows must pass a strict metadata gate; legacy rows cannot.

Aliases/migrations:

- Do not alias `grammar_active` to `grammar_valid`.
- Reuse existing `grammar_variant`.
- C2 `grammar_claim_scope` remains separate and should not be treated as
  `grammar_valid`.

## 6. Grammar provenance implementation plan

Where to compute `grammar_sha`:

- Compute SHA-256 over raw grammar file bytes at the exact path resolved by the
  runtime that calls `load_compiled_grammar(...)`.
- For Cluster 1 Modal, this is inside
  `shared/modal_harness/generation.py::RemoteGenerator.generate_one(...)`,
  after `_resolve_grammar_path(req.grammar_path)` and before
  `load_compiled_grammar(...)`.
- For Cluster 2 G+C Modal, this is inside
  `cluster2/modal/generation.py::run_c2_generation_with_loaded_model(...)`,
  after `_resolve_grammar_path(routing.grammar_path)` and before
  `load_compiled_grammar_fn(...)`.
- For local Cluster 1, compute in `cluster1/experiments/run_cluster1.py` from
  the actual `args.grammar_path` handed to `load_compiled_grammar(...)`.

How to ensure Modal computes it inside the container:

- Add a light helper, for example `cluster1/generation/provenance.py`:
  - `sha256_file(path: str | Path) -> str`
  - `grammar_provenance(runtime_path, grammar_variant, canonical_path) -> dict`
- Import the helper inside Modal method bodies, not at module top if it risks
  heavy imports.
- Return the computed hash in `RemoteGenerationResult` and C2 generation
  payloads. Do not infer it locally from repo files.

How to compare with local hash:

- In the local C1 runner, after receiving `RemoteGenerationResult`, compute the
  local SHA for `grammar_path_for_variant(generation.grammar_variant)` and
  compare to `generation.grammar_sha`.
- If hashes differ, mark the row as `grammar_valid=False`,
  `rejection_layer="runtime_error"` or fail the run before writing, depending
  on strictness.
- For paper-scale, fail before writing unless a deliberate runtime/local
  mismatch override exists.

How to validate variant/path/hash consistency:

- Canonical variant-to-path mapping remains
  `cluster1/generation/grammar_variants.py::GRAMMAR_PATHS_BY_VARIANT`.
- Cluster 2 should stop duplicating the mapping or should import/derive from
  the Cluster 1 mapping and keep only `grammar_claim_scope`.
- Check that:
  - `grammar_variant` is one of `template_upper_bound`, `task_agnostic`;
  - the canonical path for that variant resolves to a file;
  - the runtime-loaded path basename and hash match the canonical local file.

Failure behavior if grammar path does not match variant:

- Request-time mismatch remains a `ValueError`.
- Runtime mismatch inside Modal should return/raise a structured generation
  error with `stop_reason="error"` and `rejection_layer="runtime_error"`.
- Paper-scale runs should treat mismatch as a hard blocker, not as a rejected
  sample.

## 7. Runtime/image/model provenance implementation plan

Where to collect package versions:

- Add a helper such as `cluster1/generation/provenance.py::runtime_versions()`
  using `importlib.metadata.version(...)`.
- Call it inside:
  - `shared/modal_harness/generation.py::RemoteGenerator.generate_one(...)`;
  - `cluster2/modal/generation.py::run_c2_generation_with_loaded_model(...)`;
  - local `cluster1/experiments/run_cluster1.py` if local generation remains
    supported.

How to collect versions:

- `xgrammar_version = md.version("xgrammar")`
- `transformers_version = md.version("transformers")`
- `tokenizers_version = md.version("tokenizers")`
- Use `"unknown"` only when the package metadata lookup fails.
- Paper-scale Modal rows should reject `"unknown"` for these three fields.

How to collect `model_revision` and `tokenizer_revision`:

- Cluster 2 already requires request fields and validates loaded revisions.
  Preserve them and optionally compare to observed object metadata.
- Cluster 1 currently only passes `model_id`. Add best-effort revision
  extraction in `RemoteGenerator.load_model()`:
  - tokenizer: `tokenizer.init_kwargs.get("_commit_hash")` or
    `tokenizer._commit_hash` if available;
  - model: `model.config._commit_hash` if available;
  - fallback `"unknown"`.
- For future paper-scale C1, require explicit model/tokenizer revisions in the
  runner config or fail the metadata gate if extraction returns `"unknown"`.

How to collect `modal_image_sha` or fallback:

- First try Modal-exposed runtime metadata or environment variables. The
  current repo only has `shared/modal_harness/runtime.py::current_modal_ids()`;
  extend it cautiously with `current_modal_image_sha()` if Modal exposes a
  stable image or container digest.
- If Modal does not expose a stable image SHA, define and record:
  - `modal_image_sha = "unknown"`;
  - `modal_image_provenance_sha256 = sha256(JSON(sorted package pins,
    `shared/modal_harness/images.py` source hash, Python version, Modal image
    source path hash, generation GPU))`.
- For paper-scale, require either a real `modal_image_sha` or the fallback
  digest plus the image source hash and package versions.

How to handle unknown values:

- Legacy rows: allow `"unknown"`.
- Smoke/development rows: allow `"unknown"` only for `modal_image_sha` if the
  fallback digest exists.
- Paper-scale rows: block on `"unknown"` for xgrammar/transformers/tokenizers,
  model revision, tokenizer revision, grammar SHA/path/variant, and validation
  fields.

## 8. Stop reason implementation plan

Where generation outputs expose termination state:

- Current `cluster1/generation/constrained_gen.py::generate_source(...)` only
  receives raw `output_ids` from `model.generate(...)`.
- It does not request `return_dict_in_generate=True`, does not use a custom
  `StoppingCriteria`, and does not ask `TritonGrammarLogitsProcessor` whether
  the matcher is in a final/accepting state.

Whether XGrammar exposes final state:

- The current repo code and tests do not use any final-state API. Searches
  found only `GrammarMatcher.accept_token(...)` and
  `fill_next_token_bitmask(...)`.
- Treat final-state observability as unknown until the implementation agent
  introspects the XGrammar 0.1.33 API inside the Modal generation image.

How to distinguish stop reasons:

- Update `generate_source(...)` to compute generated token IDs and token count.
- If generation raises, propagate a structured `stop_reason="error"` in the
  remote result if a result row is still emitted.
- If the generated sequence includes/finalizes on `tokenizer.eos_token_id`,
  classify `stop_reason="eos_token"` unless XGrammar final-state observation
  proves `grammar_final_state`.
- If generated token count reaches `max_new_tokens` without EOS, classify
  `stop_reason="max_new_tokens"`.
- If grammar-active and a reliable matcher final/accepting-state API says the
  final generated prefix is complete, classify `stop_reason="grammar_final_state"`.
- Otherwise classify `stop_reason="unknown"`.

What if `grammar_final_state` cannot be observed directly:

- Do not infer it from `gbnf_parse_valid=True` alone.
- Record `eos_token`, `max_new_tokens`, or `unknown`.
- Mark this as an open question for paper-scale gating. The implementation can
  still proceed with populated `stop_reason`, but n=20 should not interpret
  `unknown` as final grammar completion.

## 9. Post-generation validation implementation plan

Existing validator APIs to call:

- Refactor `cluster1/grammar/triton_kernel_validator.py` to add a public helper,
  for example:
  - `validate_source_layers(source: str, grammar_path: Path) -> GrammarSourceValidation`
- Keep `accepts_source(...)` as a compatibility wrapper returning
  `validate_source_layers(...).grammar_valid`.

How to separate GBNF parse from semantic validator:

- In the new helper:
  1. Read GBNF text.
  2. Compile Lark parser using existing `_compile_lark_parser(...)`.
  3. Run `parser.parse(source)`.
  4. If it fails: `gbnf_parse_valid=False`, `semantic_valid=False`,
     `grammar_valid=False`, `rejection_layer="gbnf_parse"`.
  5. If parse passes, run `ast.parse(source)`.
  6. If AST fails: `gbnf_parse_valid=True`, `semantic_valid=False`,
     `grammar_valid=False`, `rejection_layer="python_ast"`.
  7. Run existing semantic checker:
     `_semantic_accepts_task_agnostic(...)` or `_semantic_accepts(...)`.
  8. Set `semantic_valid` and joint `grammar_valid`.

How to avoid duplicating validator logic:

- Do not reimplement grammar or AST rules in generation code.
- Move the existing `accepts_source` sequence into the new helper and call it
  from both `accepts_source` and instrumentation.
- Keep private semantic functions private unless tests need to probe them.

How to classify `rejection_layer`:

- `None` when `grammar_valid is True`.
- `gbnf_parse` when Lark parse fails.
- `python_ast` when GBNF parse passes but Python AST parse fails.
- `semantic_validator` when AST parse passes but semantic validator rejects.
- `runtime_error` when grammar file reading, validator setup, hash mismatch, or
  runtime validation crashes.
- `unknown` only for legacy rows or unexpected classifier gaps.

Where validation runs:

- Primary row evidence for Modal-generated rows should be computed inside the
  same Modal container that performed generation and returned in the remote
  payload. This aligns validation evidence with the actual runtime that loaded
  the grammar and prevents JSONL rows from relying only on local reconstruction.
- For C1 Modal rows, `RemoteGenerator.generate_one(...)` should run the
  layered validator after decoding and return `gbnf_parse_valid`,
  `semantic_valid`, `grammar_valid`, and `rejection_layer` in
  `RemoteGenerationResult`.
- For C2 generated G+C rows,
  `cluster2/modal/generation.py::run_c2_generation_with_loaded_model(...)`
  should run the same layered validator after decoding and include the fields
  in the C2 success payload before `generated_row(...)` is constructed.
- Local post-generation validation should still run before paper-scale JSONL
  rows are accepted, using the local grammar file only after its SHA matches the
  Modal-computed `grammar_sha`. Treat local validation as an audit gate and
  drift detector: if it disagrees with Modal-returned validation, block strict
  runs or record a structured runtime validation mismatch, rather than silently
  replacing the Modal result.
- For non-Modal local generation, the same helper runs locally because the
  local process is the generation runtime.

## 10. Artifact serialization plan

Cluster 1 JSONL rows:

- Add the new flat fields to every `GenerationResult` JSON object.
- Baseline rows should include fields with `None` for grammar-specific
  validation/provenance and runtime/model/image fields populated.
- G rows should include non-null grammar provenance and validation fields.

Cluster 1 meta sidecars:

- Add a `generation_metadata_schema_version`.
- Add run-level summaries:
  - unique observed grammar SHA values;
  - package versions observed;
  - modal image SHA/fallback digest;
  - grammar validation counts;
  - rejection-layer counts.
- Sidecars must not be required to interpret individual rows.

Cluster 2 JSONL rows:

- Add new fields under `generated_metadata` for `C` and `G+C`.
- `C` rows should have grammar fields null but runtime/model/image fields
  populated.
- `G+C` rows should have all grammar provenance and validation fields
  populated.

Cluster 2 hash sidecars:

- Keep existing content-hash semantics.
- Add runtime/image provenance summaries only if they do not change the
  content-hash contract unexpectedly. If they do, increment the sidecar schema
  version and update tests.

Preserving old artifact loading:

- All new dataclass fields must have defaults.
- Deserialization helpers must fill missing fields.
- Strict C2 `from_dict` paths must accept legacy rows through defaults, not by
  silently dropping unknown fields.

Marking legacy rows:

- Add `metadata_schema_version` or `generation_metadata_schema_version`.
- Legacy rows without the new fields should be treated as
  `generation_metadata_schema_version=0`.
- New rows should use version 1 and should be eligible for strict gating.

## 11. Analyzer/aggregation update plan

Where `grammar_active` is currently used incorrectly as acceptance evidence:

- `cluster1/experiments/analyze_cluster1.py::_condition_for_row(...)` labels
  rows as `G` solely from `row.grammar_active`.
- `cluster1/experiments/validate_cluster1_results.py` validates active grammar
  rows by masked-token-rate presence, not by `grammar_valid`.
- `cluster1/experiments/make_cluster1_figures.py` asserts G rows have
  `masked_token_rate` and labels by `grammar_active`.
- `shared/analysis/factorial.py::_normalize_condition(...)` derives `G` from
  `grammar_active` if explicit condition is missing.

How `grammar_valid` should be used:

- Keep `grammar_active` as "attempted constrained decoding".
- Use `grammar_valid` as the primary G-acceptance evidence field in Cluster 1
  grammar reports and paper gates.
- Add stop-reason-conditioned acceptance summaries:
  - counts by `stop_reason`;
  - `grammar_valid_rate` within `stop_reason == "grammar_final_state"` when
    final-state observation is reliable;
  - explicit "not available" labeling when `grammar_final_state` cannot be
    observed and rows use `eos_token`, `max_new_tokens`, or `unknown`.
- Add analyzer columns/tables:
  - `grammar_valid_count`;
  - `grammar_valid_rate`;
  - `gbnf_parse_valid_rate`;
  - `semantic_valid_rate`;
  - `rejection_layer` breakdown.
- In paper-facing reports, label `grammar_active` as attempted constrained
  decoding and `grammar_valid` as joint G acceptance.

How to preserve compile/functional semantics:

- Do not change `compile_success`.
- Do not change `functional_success`.
- Do not filter compile or functional summaries by `grammar_valid` unless a
  separate explicit grammar-accepted-only diagnostic report is requested.
- For primary G/G+C claims, report both outcome metrics and grammar acceptance
  rates so failed grammar acceptance cannot be hidden.

## 12. Tests to add/update

Minimum tests:

- Provenance helper unit tests:
  - SHA helper reads bytes and returns expected 64-char digest.
  - Runtime version helper returns strings or `"unknown"` without raising.
- Grammar hash test against known file bytes:
  - temporary GBNF file with known bytes;
  - assert SHA-256 equals expected digest.
- Runtime provenance test with non-empty versions:
  - monkeypatch/importlib metadata to return versions for `xgrammar`,
    `transformers`, `tokenizers`;
  - assert fields are propagated into remote result payloads.
- Schema backward-compatibility test:
  - old Cluster 1 row without new fields loads through
    `generation_result_record_for_deserialization(...)`;
  - old Cluster 2 generated metadata without new fields loads through
    `Cluster2GeneratedRowMetadata.from_dict(...)`.
- Row serialization test:
  - `append_result_jsonl(...)` emits every new C1 field;
  - `serialize_cluster2_row(...)` emits every new C2 generated metadata field.
- Rejection-layer classification test:
  - malformed GBNF parse source -> `gbnf_parse`;
  - GBNF-pass/Python-AST-fail fixture if available -> `python_ast`;
  - AST-pass/semantic-fail fixture -> `semantic_validator`;
  - forced validator exception -> `runtime_error`.
- Stop-reason classification test:
  - fake model emits EOS before max -> `eos_token`;
  - fake model reaches token budget -> `max_new_tokens`;
  - fake processor exposes final-state method -> `grammar_final_state`;
  - unsupported state -> `unknown`.
- Analyzer uses `grammar_valid` instead of `grammar_active` test:
  - create G rows with `grammar_active=True` and mixed `grammar_valid`;
  - assert grammar acceptance table uses `grammar_valid`;
  - assert condition label still uses `grammar_active`.
- Modal-smoke artifact field-presence test:
  - after smoke run, load JSONL and assert all required keys are present.
- Modal-side validation propagation test:
  - fake or monkeypatched remote generation returns split validation fields;
  - assert C1 `remote_results_to_generation_result(...)` and C2
    `_generation_grammar_metadata_from_payload(...)` preserve them.
- Local/Modal validation consistency gate test:
  - construct a row where Modal-returned `grammar_sha` matches the local file
    but validation fields disagree with local revalidation;
  - assert strict/paper mode blocks or records the configured mismatch error.
- Paper-scale gate test:
  - rows with missing/unknown required metadata fail the paper-scale gate.

Likely files to update tests in:

- `cluster1/tests/test_results.py`
- `cluster1/tests/test_constrained_gen.py`
- `cluster1/tests/test_run_cluster1_modal.py`
- `cluster1/tests/test_validate_cluster1_results.py`
- `cluster1/tests/test_analysis.py`
- `cluster1/tests/test_grammar.py`
- `shared/tests/test_modal_harness_schemas.py`
- `cluster2/tests/test_modal_generation_c2.py`
- `cluster2/tests/test_run_cluster2_modal.py`
- `cluster2/tests/test_results_logger.py`
- `shared/tests/test_aggregation.py`
- `shared/tests/test_factorial_analysis.py`

## 13. Minimal smoke validation plan

After implementation, run in tiers:

1. n=1 Cluster 1 Modal G task-agnostic smoke.
2. If n=1 passes, n=2 Cluster 1 Modal G task-agnostic smoke.
3. Only if n=1/n=2 pass, run n=5 task-agnostic G.

Required artifact checks for each smoke:

- all required fields are present;
- `grammar_sha` matches the local file hash for the canonical variant path;
- `grammar_path` points to the loaded task-agnostic grammar path;
- `grammar_variant == "task_agnostic"`;
- `xgrammar_version` is recorded and not `"unknown"`;
- `transformers_version` and `tokenizers_version` are recorded;
- model/tokenizer revisions are recorded or the smoke is explicitly labeled
  non-paper;
- `modal_image_sha` or fallback image provenance digest is recorded;
- `stop_reason` is populated;
- `gbnf_parse_valid` is populated;
- `semantic_valid` is populated;
- `grammar_valid` is populated and equals
  `gbnf_parse_valid and semantic_valid`;
- `rejection_layer` is populated when rejected and null when accepted.
- Modal-returned validation fields match local revalidation after the
  `grammar_sha` check, or the smoke is classified as a validation drift failure.
- stop-reason-conditioned acceptance can be computed when
  `grammar_final_state` is observable; otherwise the report clearly shows the
  limitation instead of inferring final grammar completion.

The n=5 task-agnostic G run remains development evidence only unless the
paper-scale gate passes and sample-size/kernel-set policy is met.

## 14. Contract/documentation update plan

Committed research docs that need updates after implementation:

- `.contracts/research/eval_metrics.md`
  - Align rejection-layer values to lowercase:
    `python_ast`, `gbnf_parse`, `semantic_validator`, `runtime_error`,
    `unknown`.
  - State that `grammar_valid` is the joint G acceptance field.
- `.contracts/research/scale_policy.md`
  - Add the new paper-scale metadata gate.
  - State that future current-grammar artifacts must include runtime grammar
    provenance.
- `cluster1/README.md`
  - Replace any wording that implies `grammar_active` proves acceptance.
  - Document `grammar_active` versus `grammar_valid`.
- Cluster 2 docs/contracts that discuss G+C or frozen G replay:
  - `cluster2/contracts/phase_minus1_manifest.json` and
    `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` should not be
    edited in this planning pass, but future regenerated manifests must record
    the new metadata status.

Planning-only files:

- `.contracts/agentic/generation_metadata_instrumentation_plan.md` is a plan,
  not an implementation contract until reviewed.
- Existing `.contracts/agentic/cluster1_contract.md` and
  `.contracts/agentic/cluster2_contract.md` can be updated after implementation
  if they are still used as active agent instructions.

Documentation semantics:

- "G acceptance" means `gbnf_parse_valid is True` and `semantic_valid is True`.
- `grammar_active` means attempted constrained decoding.
- `masked_token_rate` means masking happened on observed logits steps; it is
  not strict enforcement or acceptance evidence.

## 15. Migration/legacy artifact policy

- Existing artifacts without the new metadata remain readable.
- Existing artifacts cannot satisfy the new paper-scale metadata gate.
- Old n=5 task-agnostic artifacts remain historical/development artifacts.
- Old frozen template G n=20 artifacts remain diagnostic/reference controls
  but do not prove the new task-agnostic G acceptance contract.
- Future current-grammar artifacts must include the new metadata to be used for
  serious G/G+C interpretation.
- Do not rewrite old artifacts in place. If backfilling is required, write a
  clearly named derived artifact with provenance explaining it is post-hoc
  local validation, not original runtime provenance.

## 16. Risk register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Modal image SHA not exposed | Cannot prove exact image digest | Record package versions plus image source hash and a deterministic fallback `modal_image_provenance_sha256`; keep `modal_image_sha="unknown"` |
| XGrammar final-state not exposed | Cannot prove `grammar_final_state` stop reason | Use feature detection; record `unknown` rather than inferring; make paper-gate policy explicit |
| Validator APIs are private/internal | Refactor can break tests or hidden assumptions | Add public `validate_source_layers` and keep `accepts_source` as compatibility wrapper |
| Running validator inside Modal adds overhead | Generation latency and image import cost increase | Keep the layered validator lightweight, run it in Modal for row evidence, measure overhead in smoke, and use local revalidation as an audit gate rather than the primary source |
| GBNF parser and XGrammar parser may differ | Local GBNF parse could reject XGrammar-accepted outputs or vice versa | Record both runtime grammar SHA and local validation result; treat disagreement as evidence, not silently accepted |
| Model/tokenizer revision unavailable | Paper rows lack reproducibility | Require explicit revision inputs for paper-scale runs or block paper gate |
| Schema change breaks old readers | Existing frozen artifacts become unreadable | Add defaults and deserialization shims before analyzers are updated |
| Analyzer changes alter prior tables | Historical reports may change labels/counts | Add new grammar acceptance tables without changing compile/functional semantics; mark legacy rows |
| C2 duplicates grammar mapping | C1 and C2 path mappings can drift | Import canonical C1 mapping or add cross-tests |
| Generation exceptions currently do not emit rows | Runtime errors may only appear as infrastructure failures | Do not force error rows in this instrumentation unless separately approved; record failure counts in sidecars |

## 17. Implementation phases

Phase A: code map and schema additions

- Add defaulted fields to C1 and C2 dataclasses.
- Add fields to Modal wire schemas.
- Add deserialization compatibility helpers.
- Add initial schema serialization tests.

Phase B: provenance helpers

- Add lightweight helpers for file SHA, runtime package versions, model/tokenizer
  revision extraction, and Modal image SHA/fallback digest.
- Add unit tests with monkeypatched metadata.

Phase C: post-generation validation

- Refactor `triton_kernel_validator.accepts_source` around a public layered
  validation helper.
- Add rejection-layer classification tests.
- Add a strict-mode local/Modal validation consistency check that blocks rows
  when Modal-returned validation and local revalidation disagree.

Phase D: Modal row instrumentation

- Instrument `RemoteGenerator.generate_one`.
- Instrument `run_c2_generation_with_loaded_model`.
- Propagate fields through `RemoteGenerationResult`, C2 payloads, C1
  `remote_results_to_generation_result`, and C2 `generated_row`.
- Ensure Modal-side instrumentation, not only local conversion code, produces
  grammar provenance, runtime provenance, stop reason, and split validation
  fields for Modal-generated rows.

Phase E: analyzer/reporting updates

- Add grammar acceptance and rejection-layer summaries.
- Update paper-facing language checks so `grammar_active` is not treated as
  acceptance.
- Preserve compile/functional summaries.

Phase F: tests and smoke

- Run local unit tests.
- Run n=1/n=2 Modal smoke only after local tests pass.
- Run n=5 task-agnostic G only after smoke artifacts pass metadata checks.

Phase G: docs/contracts

- Update research docs and active contracts with final field semantics,
  migration policy, and paper-scale metadata gate.

## 18. Acceptance criteria

Go criteria for future implementation:

- Every new C1 row has all metadata keys.
- Every new C2 generated row has all metadata keys under generated metadata or
  documented row-level equivalents.
- Modal G/G+C rows compute `grammar_sha` inside the Modal container.
- Local runner verifies Modal `grammar_sha` against the expected local grammar
  before treating validation as comparable.
- `grammar_path` and `grammar_variant` consistency is enforced.
- `gbnf_parse_valid`, `semantic_valid`, and `grammar_valid` are populated for
  grammar-active rows.
- For Modal-generated rows, split validation fields are computed in the Modal
  generation runtime and local strict-mode revalidation either matches or
  blocks the artifact.
- `grammar_valid == (gbnf_parse_valid and semantic_valid)` for all
  grammar-active rows.
- `rejection_layer` is null only for grammar-valid rows and otherwise one of
  `python_ast`, `gbnf_parse`, `semantic_validator`, `runtime_error`, `unknown`.
- `stop_reason` is populated and not silently inferred as
  `grammar_final_state`.
- Runtime package versions are recorded from the generation runtime.
- Model/tokenizer revisions are recorded or strict paper mode blocks the run.
- Modal image SHA or fallback digest is recorded.
- Legacy artifacts load without rewriting.
- Paper-scale metadata gate rejects legacy or incomplete rows.
- Analyzers report grammar acceptance separately from attempted constrained
  decoding.

No-go conditions that must block n=20:

- Missing runtime `grammar_sha` for Modal G/G+C rows.
- `grammar_active` is still used as the only G evidence in paper-facing output.
- Missing split validation fields for grammar-active rows.
- Missing or `"unknown"` xgrammar/transformers/tokenizers versions in
  paper-scale rows.
- Unknown model/tokenizer revisions in paper-scale rows without explicit human
  approval.
- Unresolved grammar path/variant mismatch.
- Stop reason unavailable and not explicitly documented as an open paper-scale
  limitation.

## 19. Exact commands

Do not run these during this planning pass. Use `.venv/bin/python` for local
inspection and validation.

Local tests after implementation:

```bash
.venv/bin/python -m pytest cluster1/tests/test_results.py cluster1/tests/test_constrained_gen.py cluster1/tests/test_run_cluster1_modal.py shared/tests/test_modal_harness_schemas.py -q
.venv/bin/python -m pytest cluster1/tests/test_grammar.py cluster1/tests/test_grammar_acceptance.py cluster1/tests/test_validate_cluster1_results.py cluster1/tests/test_analysis.py -q
.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_results_logger.py shared/tests/test_aggregation.py shared/tests/test_factorial_analysis.py -q
```

Static analysis/import smoke after implementation:

```bash
.venv/bin/python -m pytest shared/tests/test_eval_imports.py shared/tests/test_modal_harness_local_imports.py cluster2/tests/test_modal_scaffolding.py -q
```

Modal smoke commands after implementation review only:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster1.experiments.run_cluster1_modal --condition G --grammar-variant task_agnostic --kernel-class elementwise --n 1 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --output outputs/cluster1/metadata_smoke_task_agnostic_g_elementwise_n1.jsonl --max-new-tokens 512 --modal-generation-gpu L4 --overwrite
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster1.experiments.run_cluster1_modal --condition G --grammar-variant task_agnostic --kernel-class elementwise --n 2 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --output outputs/cluster1/metadata_smoke_task_agnostic_g_elementwise_n2.jsonl --max-new-tokens 512 --modal-generation-gpu L4 --overwrite
```

Development n=5 only after n=1/n=2 metadata checks pass:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster1.experiments.run_cluster1_modal --condition G --grammar-variant task_agnostic --kernel-class all --n 5 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --output outputs/cluster1/metadata_development_task_agnostic_g_all_n5.jsonl --max-new-tokens 512 --modal-generation-gpu L4 --overwrite
```

Artifact validation after each smoke:

```bash
.venv/bin/python -m cluster1.experiments.validate_cluster1_results --input outputs/cluster1/metadata_smoke_task_agnostic_g_elementwise_n1.jsonl --condition G --kernel-class elementwise --n 1 --grammar-variant task_agnostic
.venv/bin/python -m cluster1.experiments.analyze_cluster1 --input outputs/cluster1/metadata_smoke_task_agnostic_g_elementwise_n1.jsonl --output outputs/cluster1/metadata_smoke_task_agnostic_g_elementwise_n1_summary.md --condition G --kernel-class elementwise --n 1 --grammar-variant task_agnostic --allow-small-matrix --validate
```

The implementation should also add a dedicated metadata gate command or test
so reviewers do not rely on ad hoc JSON inspection.

## 20. Open questions

- Does Modal expose a stable image digest/SHA for the running container in the
  current API? If not, approve the fallback digest design.
- Does XGrammar 0.1.33 expose a reliable final/accepting state on
  `GrammarMatcher`? If not, decide whether paper-scale rows may use
  `stop_reason="unknown"` or whether a custom stopping criterion is required.
- Should C1 generation errors produce structured error rows, or remain
  infrastructure failures in sidecars only?
- Should local revalidation mismatches be stored as separate audit fields, or
  should strict mode fail before writing any row with Modal/local validation
  disagreement?
- For paper-scale C1, should model/tokenizer revisions be explicit required CLI
  args rather than best-effort metadata extracted from Hugging Face objects?
- Should C2 replay rows inherit unknown legacy grammar metadata, or should
  replay artifacts be regenerated before any paper-scale G replay comparison?
