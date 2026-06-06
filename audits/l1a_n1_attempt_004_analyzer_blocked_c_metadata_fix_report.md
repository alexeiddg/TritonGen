# L1a n=1 Attempt 004 Analyzer Blocked C Metadata Fix Report

## Scope

- branch: `codex-track-handoff-context`
- pre-fix execution commit: `c723286b395476998e519f53463a3ef3f46b825c`
- signed packet: `FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`
- execution command: `TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite`
- start timestamp: `2026-06-06T09:04:57Z`
- final row completion timestamp: `2026-06-06T09:21:48.086155Z`
- end timestamp recorded before validation: `2026-06-06T09:22:05Z`

## Attempt Result

Attempt 004 completed the signed 12-cell L1a n=1 runner command and emitted
exactly 12 JSONL rows, one per planned `grammar_mode x C x P` cell. The signed
schema, row-count, content-hash, observability, grammar-mode, and local matrix
eligibility validations passed.

The signed analyzer/report command did not pass. It failed before writing
analysis/report artifacts with:

```text
ValueError: quarantined repair-history artifact has incomplete agentic_transcript_v1 metadata for artifact='outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl': {0: ['repair_prompt_template_version', 'repair_prompt_renderer_version', 'repair_anchor_attempt_index', 'repair_latest_attempt_index', 'repair_history_attempt_count', 'repair_prompt_sha256', 'repair_prompt_char_count', 'repair_max_prompt_chars', 'repair_include_latest_source', 'repair_anchor_source_hash', 'repair_latest_source_hash', 'repair_history_summary_sha256']}
```

## Diagnosis

The failure is a local row-emission metadata completeness bug. The Cluster 3 C
loop returns `terminal_prompt_metadata` through its embedded Cluster 2 repair
loop result, but `_build_row` copied only P-loop terminal prompt metadata into
`generated_metadata`. C-loop rows with `terminal_prompt_hash_source =
"c_repair_prompt"` therefore carried C repair traces and terminal prompt hash
evidence without the analyzer's existing `c_repair_*` alias fields.

This did not change generation, sampling, grammar, repair policy, evaluation,
or pass/fail semantics. It did leave missing provenance information in output
JSONL rows, so attempt 004 is not a clean L1a result.

## Patch

- Added C repair-history metadata fields to `Cluster3GeneratedRowMetadata`.
- Added C repair-history metadata validation parallel to the existing P metadata
  validation.
- Copied C-loop `terminal_prompt_metadata` into `generated_metadata` via the
  analyzer's existing `c_repair_*` aliases.
- Added a focused CLI test proving agentic C-loop rows now persist rendered C
  prompt metadata.

## Validation

Passed:

```text
.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py cluster3/tests/test_condition_adapters.py cluster3/tests/test_dispatcher.py cluster3/tests/test_cluster3_schema.py cluster3/tests/test_grammar_mode_matrix.py cluster3/tests/test_run_cluster3_modal_cli.py -q
928 passed

.venv/bin/python -m compileall -q cluster3 shared/factors

git diff --check
```

Known unrelated test caveat:

```text
.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_run_cluster3_modal_cli.py shared/tests/test_analyzer_cluster3.py -q
```

failed one pre-existing shared analyzer golden comparison
(`test_analyzer_2x2_reproducible_without_cluster3_rows`) due metric-registry
JSON drift outside this patch path. Cluster 3 schema and CLI tests passed.

## Archive

Attempt 004 artifacts were archived without deletion under the authorized L1a
namespaces:

- `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/blocked_attempts/attempt_004_20260606T090457Z/`
- `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/blocked_attempts/attempt_004_20260606T090457Z/`

After archive, all 60 exact planned retry target files were absent from the
active L1a output and observability directories.

## Authorization Boundary

- Runtime MLflow remained disabled with `TRITONGEN_MLFLOW=0`.
- No L1b, L2, n=5, n=20, paper-scale, profiler, benchmark, or performance
  optimization command was run.
- No runtime code changed generation prompts, sampling/model settings, grammar
  semantics, repair policy, or pass/fail definitions.
- `mlruns/` was not mutated.

## Classification

`L1A_ATTEMPT_004_ANALYZER_BLOCKED_C_METADATA_FIX_LOCAL_COMPLETE`

## Next Step

Commit this narrow fix and run one fresh signed L1a n=1 12-cell attempt from
the patched local branch. After completion, rerun the signed validation bundle
and the signed analyzer/report command.
