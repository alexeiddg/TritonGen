# L2 n20 Runtime Gate Enable Report

Date: 2026-06-06
Branch: `codex/l2-n20-runtime-gate-enable`
Baseline: `2102259 Audit L2 n20 final authorization promotion`
Classification: `L2_N20_RUNTIME_GATE_ENABLE_READY_FOR_REVIEW`

## Executive Summary

This branch implements the narrow runtime-gate unlock required after the final
L2 n=20 authorization packet was promoted. It allows only the exact signed
L2 n=20 selector command for the 12-cell `grammar_mode x C x P` matrix to pass
local pre-launch validation.

No L2 execution was performed. No Modal, GPU, generation, billing query,
analyzer/report refresh, preliminary-report refresh, dependency update, lockfile
change, or output/artifact/mlruns mutation was performed.

## Promoted Final Authorization Reference

- Packet: `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md`
- Packet status: `SIGNED_FOR_L2_N20_ONLY`
- Packet execution authorization: `AUTHORIZES_EXECUTION: YES_L2_N20_ONLY`
- Promoted authorization commit: `bd84940 Authorize L2 n20 execution`
- Promotion audit commit: `2102259 Audit L2 n20 final authorization promotion`
- Signed selector token:
  `FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_V1`

## Runtime-Gate Root Blocker

The promoted final packet intentionally recorded that the target runtime profile
still failed closed in code. That was correct for the packet branch because it
was a signed authorization surface, not a runtime enablement branch.

This branch closes only that root blocker by removing the L2 profile-level
runtime block and keeping the existing selector pre-launch guard in place.

## Patch Summary

- `cluster3/experiments/run_cluster3_modal.py`
  - keeps L1a/L1b/L2 selector profiles separate;
  - enables the L2 profile to reach the shared signed-selector validator;
  - adds a required `--repair-history-policy agentic_transcript_v1` guard;
  - preserves fail-closed validation for wrong token, wrong rung, wrong scale,
    wrong `n`, wrong kernel class, wrong dtype, MLflow enabled, resume,
    selector-level observability overrides, path collisions, row/cell mismatch,
    and namespace mismatch.
- `cluster3/planning/grammar_mode_matrix.py`
  - updates the L2 support status to
    `L2_SIGNED_RUNTIME_GATE_ENABLED_NO_EXECUTION`.
- `cluster3/tests/test_run_cluster3_modal_cli.py`
  - adds positive pre-launch validation for the signed L2 n=20 selector;
  - adds focused negative tests for invalid L2 variants and cross-rung token
    misuse.

## Exact Signed L2 Pass Conditions

The runtime pre-launch guard passes only when all of these conditions hold:

- `TRITONGEN_MLFLOW=0`
- `--condition grammar_mode_cp_12cell`
- `--kernel-class elementwise`
- `--scale-tier paper`
- `--n 20`
- `--dtypes fp32`
- `--repair-history-policy agentic_transcript_v1`
- `--signed-l2-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_V1`
- `--overwrite`
- no explicit selector-level `--output` override
- no explicit selector-level observability overrides
- exactly 12 planned cells
- exactly 240 planned rows
- all planned output/content-hash sidecar paths remain under the signed L2
  output namespace
- all planned observability sidecar paths remain under the signed L2
  observability namespace
- every target path is absent before launch

## Fail-Closed Conditions

The gate remains fail-closed for:

- missing, wrong, L1a, or L1b signed tokens;
- L1a/L1b selector surfaces receiving the L2 token;
- `n=1`, `n=5`, `n=19`, or any non-20 L2 request;
- non-paper L2 scale tiers;
- non-elementwise kernels;
- non-fp32 dtypes;
- non-`agentic_transcript_v1` repair-history policy;
- `TRITONGEN_MLFLOW=1` or omitted/incorrect MLflow disablement;
- resume instead of overwrite;
- dry-plan or execution-plan modes attempting to use runtime authorization;
- selector-level output or observability overrides;
- any existing target output, content-hash, observability event, summary, or
  hash path;
- planned cell count other than 12;
- planned row count other than 240;
- condition-id duplication;
- namespace mismatch;
- L3, profiler, benchmark, speedup, performance, retry, or resume expansion.

## Tests Added Or Updated

- Updated the L2 execution-plan status expectation to
  `L2_SIGNED_RUNTIME_GATE_ENABLED_NO_EXECUTION`.
- Replaced the old signed-token-fails-closed L2 test with a positive
  pre-launch guard test that validates 12 cells, 240 rows, signed output
  namespace, signed observability namespace, and the L2 token placeholder.
- Added negative tests for L1 token reuse on L2, L2 token reuse on L1,
  `n=1`, `n=5`, non-elementwise kernel, non-fp32 dtype, MLflow enabled,
  non-agentic repair memory, resume, 239 planned rows, 11 planned cells, and
  namespace mismatch.

## Validation Run

Local validation run before commit:

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
rg -n "L3|profiler|benchmark|speedup|performance|MLFLOW=1|TRITONGEN_MLFLOW=1|retry authorized|resume authorized" cluster3 docs audits
rg -n "SIGNED_FOR_L2_N20_ONLY|YES_L2_N20_ONLY|240|n=20|grammar_mode_cp_12cell|TRITONGEN_MLFLOW=0|no retry|no resume|fail_if_any_target_path_exists" docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md cluster3 audits
```

Expected validation status: pass after final branch checks.

Observed results:

- `.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q`
  passed with `190 passed`.
- `.venv/bin/python -m compileall -q cluster3 shared` passed.
- `git diff --check` passed.
- Protected mutation scan for `outputs`, `artifacts`, `mlruns`,
  `docs/preliminary_report`, dependency files, and lockfiles was empty.
- Broad authorization leak scan over `cluster3 docs audits` was reviewed. The
  repository contains pre-existing historical, future-scope, and generated-doc
  matches for L3/performance/profiler/benchmark/speedup/MLflow text; the branch
  diff-specific scan adds only prohibition, no-execution, no-authorization, or
  fail-closed wording for those terms.
- L2 signature scan confirmed `SIGNED_FOR_L2_N20_ONLY`,
  `YES_L2_N20_ONLY`, `240`, `n=20`, `grammar_mode_cp_12cell`,
  `TRITONGEN_MLFLOW=0`, `no retry`, `no resume`, and
  `fail_if_any_target_path_exists` remain visible on the packet/code/audit
  surfaces.

## No-Execution Proof

- No Modal command was run.
- No `modal run` command was run.
- No `--signed-l2-authorization` execution command was run.
- The only runtime call exercised locally was the pre-launch validator inside
  pytest.
- The branch did not query billing, run generation, or invoke GPU work.

## Protected Mutation Proof

The protected mutation scan is expected to remain empty for:

```text
outputs
artifacts
mlruns
docs/preliminary_report
pyproject.toml
requirements.txt
requirements-dev.txt
uv.lock
poetry.lock
Pipfile.lock
```

No output, artifact, MLflow, dependency, lockfile, or preliminary-report file is
part of this runtime-gate patch.

## Remaining Blockers Before Launch

- Review and commit this runtime-gate branch.
- Promote or otherwise explicitly select this runtime-gate commit as the launch
  baseline.
- Re-run the exact pre-launch protected-path absence checks immediately before
  launch.
- Run only the signed L2 n=20 command from the packet if a later operational
  step explicitly requests execution from the reviewed baseline.
- Preserve no retry and no resume unless a new signed packet changes that.
- After a successful run, validate 240 rows, 12 cells, sidecars, analyzer
  strictness, and billing reconciliation before making graph/report/paper
  claims.

## Classification

`L2_N20_RUNTIME_GATE_ENABLE_READY_FOR_REVIEW`

## Next-Step Recommendation

Review and commit this branch. Do not launch L2 from this task. The next
separate operational step, if explicitly requested, should run exactly the
signed L2 n=20 command from the packet after confirming target paths are absent
and `TRITONGEN_MLFLOW=0` is set.
