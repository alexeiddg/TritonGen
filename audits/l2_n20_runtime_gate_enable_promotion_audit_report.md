# L2 n20 Runtime Gate Enable Promotion Audit Report

Date: 2026-06-06
Source branch: `codex/l2-n20-runtime-gate-enable`
Target branch: `codex-track-handoff-context`
Promoted commit: `426ede8da8e4b3c946a55fc3e28a87d38305b963`
Signed L2 authorization reference: `210225946ce547ba7b03753d1f7b24a8ca286401`
Classification: `L2_N20_RUNTIME_GATE_PROMOTION_COMPLETE_EXECUTION_PRECHECK_READY`

## Source Branch

The source branch was `codex/l2-n20-runtime-gate-enable`.

Review state before promotion:

- `git status --short --branch` reported the runtime-gate branch with no dirty
  tracked files.
- `git log --oneline -10` showed
  `426ede8 Enable signed L2 n20 runtime gate` at the branch head, followed by
  `2102259 Audit L2 n20 final authorization promotion` and
  `bd84940 Authorize L2 n20 execution`.

## Promoted Commit

Promoted commit:

```text
426ede8da8e4b3c946a55fc3e28a87d38305b963
```

The commit adds the narrow runtime pre-launch unlock for the signed L2 n=20
selector profile, updates the L2 selector support status, adds focused positive
and negative selector tests, and records the implementation evidence in
`audits/l2_n20_runtime_gate_enable_report.md`.

## Signed L2 Authorization Reference

The runtime gate promotion is downstream of the signed final L2 authorization
promotion:

```text
210225946ce547ba7b03753d1f7b24a8ca286401
```

The signed packet is:

```text
docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md
```

It is signed only for the L2 n=20 12-cell
`grammar_mode x C x P` command surface with `AUTHORIZES_EXECUTION:
YES_L2_N20_ONLY`.

## Runtime-Gate Behavior

The promoted runtime gate allows the signed selector path to pass local
pre-launch validation only when all signed L2 conditions are present:

- `TRITONGEN_MLFLOW=0`
- `--condition grammar_mode_cp_12cell`
- `--kernel-class elementwise`
- `--scale-tier paper`
- `--n 20`
- `--dtypes fp32`
- `--repair-history-policy agentic_transcript_v1`
- `--signed-l2-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_V1`
- `--overwrite`
- exactly 12 planned cells
- exactly 240 planned rows
- L2 n20 output/content-hash/observability namespaces
- absent target paths before launch

## Fail-Closed Behavior

Focused tests and branch review confirmed the selector remains fail-closed for:

- unsigned L2 n=20 command surfaces;
- wrong L2 tokens;
- L1a/L1b token reuse on L2;
- L2 token reuse on L1a/L1b;
- L2 `n=1` or `n=5`;
- non-elementwise kernels;
- non-fp32 dtypes;
- runtime MLflow enabled;
- non-`agentic_transcript_v1` repair memory;
- retry/resume paths;
- existing target paths;
- planned row count other than 240;
- planned cell count other than 12;
- L2 namespace mismatch.

L1a and L1b selector paths remain unaffected by the L2 unlock.

## Tests Run

Required local validation was re-run before promotion:

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
git diff --name-only codex-track-handoff-context..HEAD -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Observed results:

- pytest: `190 passed`
- compileall: passed
- `git diff --check`: clean
- protected-surface diff: empty

## Protected Mutation Proof

The protected-surface diff before promotion was empty for:

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

The promotion audit itself creates only this audit report and handoff routing
updates. It does not stage runtime outputs, MLflow state, dependency files,
lockfiles, or preliminary-report refreshes.

## No-Execution Proof

This promotion audit did not run the signed L2 command. It did not run Modal,
GPU generation, billing reconciliation, analyzer/report refresh, or any
output-mutating command.

At this point, the only executed commands were local review, compile, Git,
protected-surface scan, and documentation/audit creation commands.

## Classification

`L2_N20_RUNTIME_GATE_PROMOTION_COMPLETE_EXECUTION_PRECHECK_READY`

## Next-Step Recommendation

Proceed only to the pre-execution checks from the signed operational prompt:
verify the promoted trunk is clean, confirm the L2 target paths are absent,
compare the local dry/execution plan against the signed packet, and then run
exactly one signed L2 n=20 command if all stop conditions remain clear.
