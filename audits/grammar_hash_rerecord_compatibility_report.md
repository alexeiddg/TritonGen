# Grammar Hash Rerecord Compatibility Report

## Executive summary

Classification: `DIVERGENCE_FIX_REQUIRED`.

The current `cluster1/grammar/triton_kernel_agnostic.gbnf` hash was computed with the repository canonical hash helper as `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`. The active Phase -1 G hash gate still records `756f46a76e8fc6e208a263a69678873ecbbe7327d1c3c7ee9fe6a902fb96600f` in `cluster2/modal/generation.py`.

The grammar file is the intended task-agnostic grammar according to the file header, `.contracts/research/cluster1_generated_surface.md`, and `cluster1/grammar/corpus/api_coverage_report.md`. Smoke fixture and broader grammar/corpus checks pass against the current grammar. However, compatibility check B failed: the existing frozen n=5 task-agnostic G rerun artifact has 31 source rows rejected by the current task-agnostic grammar validator. Per the task rules, the hash was not rerecorded.

## Hash-gate failure reproduced

Failing command:

```bash
.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py::test_remote_generator_generate_one_hash_matches_phase_minus_1 -v
```

Result: failed.

Responsible active gate state:

- `cluster2/modal/generation.py`, `PHASE_MINUS1_G_GENERATION_SOURCE_HASHES`
- Path entry: `cluster1/grammar/triton_kernel_agnostic.gbnf`

Failure:

- Expected: `756f46a76e8fc6e208a263a69678873ecbbe7327d1c3c7ee9fe6a902fb96600f`
- Actual: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`

## Old hash vs new hash

Canonical hash command:

```bash
.venv/bin/python -c "from shared.eval.content_hashes import file_sha256; print(file_sha256('cluster1/grammar/triton_kernel_agnostic.gbnf'))"
```

Old recorded hash:

```text
756f46a76e8fc6e208a263a69678873ecbbe7327d1c3c7ee9fe6a902fb96600f
```

Current grammar hash:

```text
7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32
```

## Manifest/gate file updated

No Phase -1 gate state was updated.

Reason: compatibility check B failed before rerecording. Updating the hash would violate the task rule not to update hashes when the current grammar fails compatibility checks.

The old hash remains active in `cluster2/modal/generation.py`.

## Hash-gate verification result

No post-update passing hash-gate verification was run because no hash update was permitted.

The reproduced hash gate remains blocked until the n=5 compatibility divergence is resolved or explicitly reclassified by approval.

## Smoke fixture compatibility result

Command:

```bash
.venv/bin/python -m pytest cluster1/tests/test_grammar_acceptance.py -v
```

Result: passed.

Fixture count: 215 parametrized acceptance cases.

Rejected expected-good fixtures: none.

Additional grammar/corpus command:

```bash
.venv/bin/python -m pytest cluster1/tests -k "grammar or corpus or fixture" -v
```

Result: passed.

Selected tests: 843 passed, 236 deselected.

This broader selector included the API coverage snapshot checks, task-agnostic grammar acceptance checks, and existing generated n=5 disagreement policy tests.

## n=5 output compatibility result

Artifact:

```text
outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl
```

Diagnostic command:

```bash
.venv/bin/python - <<'PY'
import json
from collections import Counter
from pathlib import Path

from cluster1.grammar.triton_kernel_validator import (
    TASK_AGNOSTIC_GBNF_PATH,
    _compile_lark_parser,
    accepts_source,
)

artifact = Path('outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl')
parser = _compile_lark_parser(TASK_AGNOSTIC_GBNF_PATH.read_text(encoding='utf-8'))
rows = []
with artifact.open(encoding='utf-8') as handle:
    for line_no, line in enumerate(handle, start=1):
        if line.strip():
            row = json.loads(line)
            row['_line_no'] = line_no
            rows.append(row)

source_rows = [row for row in rows if isinstance(row.get('source'), str) and row['source'].strip()]
rejections = []
for row in source_rows:
    source = row['source']
    parser_ok = True
    reason = ''
    try:
        parser.parse(source)
    except Exception as exc:
        parser_ok = False
        reason = f'PARSER_REJECT: {type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else exc!r}'
    semantic_ok = accepts_source(source, TASK_AGNOSTIC_GBNF_PATH) if parser_ok else False
    if not semantic_ok:
        if parser_ok:
            reason = 'SEMANTIC_VALIDATOR_REJECT: parser accepted but task-agnostic semantic validator rejected generated surface'
        rejections.append((row, reason))

print(f'total_rows={len(rows)}')
print(f'rows_with_source={len(source_rows)}')
print(f'accepted_rows={len(source_rows) - len(rejections)}')
print(f'rejected_rows={len(rejections)}')
print(Counter(reason.split(':', 1)[0] for _, reason in rejections))
PY
```

Result: failed compatibility.

Counts:

- Total rows: 45
- Rows with source: 45
- Accepted rows: 14
- Rejected rows: 31
- Parser rejections: 29
- Semantic validator rejections: 2

Rejected row identities:

| line | kernel | dtype | seed | compile_success | rejection class |
| ---: | --- | --- | ---: | --- | --- |
| 3 | elementwise/relu | fp32 | 2 | false | semantic validator reject |
| 16 | reduction/softmax | fp32 | 0 | false | parser reject |
| 17 | reduction/softmax | fp32 | 1 | false | semantic validator reject |
| 18 | reduction/softmax | fp32 | 2 | false | parser reject |
| 19 | reduction/softmax | fp32 | 3 | false | parser reject |
| 20 | reduction/softmax | fp32 | 4 | false | parser reject |
| 21 | reduction/softmax | fp16 | 0 | false | parser reject |
| 22 | reduction/softmax | fp16 | 1 | false | parser reject |
| 23 | reduction/softmax | fp16 | 2 | false | parser reject |
| 24 | reduction/softmax | fp16 | 3 | false | parser reject |
| 25 | reduction/softmax | fp16 | 4 | false | parser reject |
| 26 | reduction/softmax | bf16 | 0 | false | parser reject |
| 27 | reduction/softmax | bf16 | 1 | false | parser reject |
| 28 | reduction/softmax | bf16 | 2 | false | parser reject |
| 29 | reduction/softmax | bf16 | 3 | false | parser reject |
| 30 | reduction/softmax | bf16 | 4 | false | parser reject |
| 31 | matmul/gemm | fp32 | 0 | true | parser reject |
| 32 | matmul/gemm | fp32 | 1 | true | parser reject |
| 33 | matmul/gemm | fp32 | 2 | true | parser reject |
| 34 | matmul/gemm | fp32 | 3 | true | parser reject |
| 35 | matmul/gemm | fp32 | 4 | true | parser reject |
| 36 | matmul/gemm | fp16 | 0 | false | parser reject |
| 37 | matmul/gemm | fp16 | 1 | false | parser reject |
| 38 | matmul/gemm | fp16 | 2 | false | parser reject |
| 39 | matmul/gemm | fp16 | 3 | false | parser reject |
| 40 | matmul/gemm | fp16 | 4 | false | parser reject |
| 41 | matmul/gemm | bf16 | 0 | false | parser reject |
| 42 | matmul/gemm | bf16 | 1 | false | parser reject |
| 43 | matmul/gemm | bf16 | 2 | false | parser reject |
| 44 | matmul/gemm | bf16 | 3 | false | parser reject |
| 45 | matmul/gemm | bf16 | 4 | false | parser reject |

Preliminary classification: `OLD_OUTPUT_INCOMPATIBLE`.

This is still blocking for the requested hash rerecord because the existing n=5 task-agnostic G rerun artifact is an explicitly requested compatibility input. Some rejected rows are malformed or incomplete generated source, but five `matmul/gemm` fp32 rows are marked `compile_success=true` in the frozen artifact while rejected by the current grammar parser. That makes this incompatible with a clean compatibility pass and requires explicit divergence resolution before any hash update.

## Files modified

- `audits/grammar_hash_rerecord_compatibility_report.md`

No grammar files, frozen outputs, Cluster 2 runtime behavior, repair-loop behavior, metrics, or Phase -1 hash gate state were modified.

## Remaining risks

- The active hash gate remains blocked on the old recorded hash.
- The current grammar may be the intended task-agnostic API-coverage grammar, but it is not compatibility-clean against `outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl`.
- The n=5 artifact contains generated rows that are not accepted by the current grammar validator; the correct resolution may be to document approved non-blocking exceptions, adjust the compatibility definition, or separately approve a grammar/output reconciliation path.

## Go/no-go recommendation

No-go for Phase -1 hash rerecording in this turn.

Recommended next step: resolve the n=5 output compatibility divergence first. Do not update `PHASE_MINUS1_G_GENERATION_SOURCE_HASHES` until the 31 rejected rows are either accepted by an approved compatibility policy or explicitly classified as non-blocking exceptions.
