# Cluster 2 Synthetic F2 Repair Smoke Plan

**Status:** implementation plan only
**Date:** 2026-05-15
**Scope:** Fix Brief B, synthetic F2 smoke for C repair-loop activation
**Write policy for this plan:** no source changes, no contract edits, no artifact writes
**Execution policy for future implementation:** smoke-scale only; no paper-scale runs until the smoke gate passes

## Purpose

Cluster 2 claims that correctness feedback (`C`, and secondarily `G+C`) can
repair candidate kernels after public Level 2 numerical failures. Boundary tests
already cover the termination guard that prevents F0 and F1 failures from
entering the repair path, but the repository does not yet contain an observed
end-to-end example where:

1. iteration 0 is a valid Triton candidate that passes Level 0 and Level 1,
2. Level 2 fails with an F2 code,
3. the public numerical failure summary is converted into feedback,
4. the repair loop sends that feedback to the model,
5. a repaired candidate is evaluated, and
6. the full iteration trace is serialized.

This plan adds the smallest deterministic smoke surface needed to prove that
path. The goal is not to broaden Cluster 2, add new failure semantics, or improve
the model. The goal is to align the implementation with the existing research
claim before GPU-expensive runs.

## Research Alignment

The smoke demonstrates this single contract:

```text
Given a candidate that reaches Level 2 and fails numerically, the C repair loop
constructs numerical-only feedback, asks for a repair, evaluates the repaired
candidate, and records the full trace under the fixed repair budget.
```

The smoke is a preflight artifact, not a new benchmark, result cell, or paper
metric. Its outputs may be used as evidence that the repair mechanism functions,
but they must not be aggregated into Cluster 2 paper-scale convergence rates.

## Non-Negotiable Boundaries

- Do not change the failure taxonomy. Use only the existing F2 codes:
  `F2_NUMERIC_LARGE`, `F2_NUMERIC_NAN`, and `F2_SHAPE_MISMATCH`.
- Do not weaken the Fix 2 termination guard. F0 and F1 failures must still stop
  before feedback construction.
- Do not introduce repair feedback for compile errors, parse errors, decorator
  errors, signature errors, Triton API errors, or runtime launch errors.
- Do not add Cluster 3 behavior: no profiling, timing, speedup, sanitizer,
  compiler repair, performance feedback, or P-factor fields.
- Do not modify frozen Cluster 1 artifacts or replay-control generation logic.
- Do not change grammar behavior or the frozen G adapter to make this smoke pass.
- Do not alter Level 2 tolerance semantics to accommodate a fixture. If a
  fixture does not produce the intended F2 failure, adjust only the fixture.
- Do not expose private eval-shape values, hidden test details, or non-public
  failure data in feedback prompts.
- Do not add a second repair loop implementation. The smoke must call the same
  C repair loop used by production Cluster 2 runs.
- Do not let this work drift into broad KernelBench coverage. Keep exactly three
  archetypes: ReLU/pointwise, softmax/reduction, and matmul/GEMM.

## Source-Of-Truth Contracts

The implementation must remain consistent with:

- `.contracts/agentic/cluster2_contract.md`
- `.contracts/agentic/cluster2_integrated_agent_plan.md`
- `.contracts/research/eval_metrics.md`
- `cluster2/feedback/prompts.py`
- `cluster2/feedback/repair_loop.py`
- `cluster2/feedback/trace.py`
- `cluster2/modal/correctness.py`
- `cluster2/modal/correctness_runner.py`
- `cluster2/results/logger.py`

The future patch may update `.contracts/agentic/cluster2_contract.md`, but only
to add the F2 smoke as a paper-scale precondition. It must not rewrite the
Cluster 2 research question.

## Required Future Files

Create these deterministic fixture files:

- `cluster2/tests/fixtures/f2_corrupted_relu.py`
- `cluster2/tests/fixtures/f2_corrupted_softmax.py`
- `cluster2/tests/fixtures/f2_corrupted_matmul.py`

Create this smoke runner:

- `cluster2/experiments/run_f2_repair_smoke.py`

Create this integration test:

- `cluster2/tests/test_f2_repair_smoke_integration.py`

Create these permanent expected-trace fixtures after the real smoke runs:

- `cluster2/tests/fixtures/expected_smoke_traces/relu.jsonl`
- `cluster2/tests/fixtures/expected_smoke_traces/softmax.jsonl`
- `cluster2/tests/fixtures/expected_smoke_traces/matmul.jsonl`

Write live smoke outputs here:

- `outputs/cluster2/smoke_f2_repair_relu.jsonl`
- `outputs/cluster2/smoke_f2_repair_softmax.jsonl`
- `outputs/cluster2/smoke_f2_repair_matmul.jsonl`

## Phase 0: Read-Only Audit

Before editing source, audit the current C repair path.

Confirm:

- the exact public Level 2 eval result structure available to feedback prompts;
- where F0/F1 termination is enforced;
- how `repair_iteration` is represented in trace rows;
- how `feedback_content` is currently attached to a repair attempt;
- how generated candidates are requested from the model;
- whether the runner already has a seam for candidate injection;
- whether result logging can write an expanded smoke sidecar without changing
  paper-scale result row schemas.

Acceptance criteria:

- Document the current call graph from candidate source to Level 2 result to
  feedback prompt to repaired candidate.
- Identify the smallest API extension needed for a seed candidate, if any.
- Confirm that no production row schema expansion is needed for the smoke.

## Phase 1: Deterministic F2 Fixtures

Each fixture must be a complete hand-written Triton Python module for the same
`KernelSpec` shape contract used by the corresponding Cluster 2 archetype.
Fixtures must be valid candidates, not mocks.

### ReLU fixture

Target path:

```text
cluster2/tests/fixtures/f2_corrupted_relu.py
```

Corruption:

```text
tl.where(x > 0, x, 0.0) -> tl.where(x > 0, x, 1.0)
```

Expected behavior:

- Level 0 passes.
- Level 1 passes.
- Level 2 fails as `F2_NUMERIC_LARGE`.
- The failure is caused only by numerical mismatch against `torch.relu`.

### Softmax fixture

Target path:

```text
cluster2/tests/fixtures/f2_corrupted_softmax.py
```

Corruption:

```text
change the reduction axis or output indexing so the module still compiles and
launches but returns the wrong softmax shape or wrong-direction reduction
```

Expected behavior:

- Level 0 passes.
- Level 1 passes.
- Level 2 fails as `F2_SHAPE_MISMATCH` when the current evaluator can observe
  the bad-axis output shape.
- If the current Triton shape contract makes a true shape mismatch impossible
  without causing F1, keep the candidate Level 1-clean and explicitly lock the
  fixture to `F2_NUMERIC_LARGE` instead. Do not change evaluator semantics just
  to force `F2_SHAPE_MISMATCH`.

### Matmul fixture

Target path:

```text
cluster2/tests/fixtures/f2_corrupted_matmul.py
```

Corruption:

```text
tl.dot(a, b) -> tl.dot(b, a)
```

Use a supported non-square shape where the kernel still compiles and launches,
or otherwise use a documented operand/indexing corruption that preserves Level 1
and produces a wrong numerical result.

Expected behavior:

- Level 0 passes.
- Level 1 passes.
- Level 2 fails as `F2_NUMERIC_LARGE`.
- The fixture remains a matmul/GEMM archetype; do not replace it with a generic
  pointwise wrong-output kernel.

### Fixture documentation

Each fixture must contain a short top-level comment naming:

- the intended archetype;
- the exact corruption;
- the expected F2 code;
- the reason it should pass Level 0 and Level 1.

No fixture should import test helpers or smoke-only code.

## Phase 2: Seed-Candidate Entry Point

The smoke needs to bypass initial model generation and start iteration 0 from a
known broken candidate source. This should be implemented as a small API
extension to `cluster2/feedback/repair_loop.py` only if no suitable entry point
already exists.

Required behavior:

- accepts an explicit iteration-0 source string and metadata;
- evaluates the seed candidate through the exact same Level 0/1/2 path as a
  generated candidate;
- records iteration 0 as candidate origin `seed_fixture`;
- constructs feedback only when the seed candidate fails with F2;
- calls the same model-generation repair function used by normal `C` and `G+C`;
- records repair attempts as iterations 1 through 5;
- stops on first Level 2 success;
- records budget exhaustion when no repair converges by iteration 5.

Forbidden behavior:

- no fake eval result injection;
- no fixture-specific branches inside the production repair loop;
- no alternate feedback builder;
- no alternate trace serializer;
- no retry-on-F0/F1 behavior;
- no generated-vs-replay comparison changes.

## Phase 3: Smoke Runner

Create:

```text
cluster2/experiments/run_f2_repair_smoke.py
```

Runner responsibilities:

- accept one fixture path or an `--all` mode for the three canonical fixtures;
- infer or require the archetype name: `relu`, `softmax`, or `matmul`;
- load the fixture source as iteration 0;
- run the C repair loop with `repair_budget=5`;
- use the normal model path for repair candidates;
- write one JSONL artifact per archetype under `outputs/cluster2/`;
- return nonzero if iteration 0 is not an F2 failure;
- return nonzero if no feedback prompt is constructed for the first repair;
- return nonzero if trace serialization is missing required fields.

Recommended CLI shape:

```text
.venv/bin/python cluster2/experiments/run_f2_repair_smoke.py \
  --fixture cluster2/tests/fixtures/f2_corrupted_relu.py \
  --archetype relu \
  --condition C \
  --repair-budget 5 \
  --output outputs/cluster2/smoke_f2_repair_relu.jsonl
```

The runner may support `G+C` later, but the required Fix Brief B gate is `C`.
Avoid expanding this into a general Cluster 2 experiment runner.

## Phase 4: Trace Contract

The smoke trace JSONL must be inspectable by humans and stable enough for tests.
Use the existing repair trace representation wherever possible. Add smoke-only
sidecar fields only when they avoid changing the production result schema.

Each iteration row must include at least:

- `run_id`
- `condition`
- `archetype`
- `fixture_path`
- `fixture_sha256`
- `repair_budget`
- `repair_iteration`
- `candidate_origin`
- `source_sha256`
- `level_reached`
- `failure_code`
- `functional_success`
- `feedback_content`
- `eval_summary`
- `repair_converged`
- `successful_attempt_index`
- `budget_exhausted`

Field meaning:

- `repair_iteration=0` is the injected fixture candidate.
- `repair_iteration=1..5` are model repair attempts.
- `feedback_content` on repair iteration `i > 0` is the exact public feedback
  content used to request candidate `i`.
- `feedback_content` on iteration 0 is empty or `null`.
- `eval_summary` may contain public numerical fields such as output shape,
  reference shape, max abs diff, max relative diff, NaN/Inf indicators, dtype,
  and tolerance.

Do not place full private eval inputs, hidden shape sets, timing values,
compiler traces, stack traces, tokenizer dumps, or raw model credentials in the
trace.

## Phase 5: Feedback Content Gate

The integration test must verify that first repair feedback is numerical-only.

Allowed content classes:

- F2 failure code;
- output shape and reference shape;
- max absolute difference;
- max relative difference;
- absolute and relative tolerances;
- NaN/Inf indicators;
- concise instruction to produce a corrected complete kernel.

Forbidden content classes:

- `F0`
- `F1`
- parse or syntax failures;
- decorator or signature complaints;
- Triton API names used as error explanations;
- compiler, LLVM, PTX, C++, CUDA backtrace, or runtime launch diagnostics;
- profiler, benchmark, speedup, Nsight, NCU, NVML, sanitizer, or P-factor terms;
- hidden/private/eval-shape disclosure;
- any instruction that changes the task rather than asks for correction.

The regex gate should be conservative. If it flags a legitimate prompt, refine
the prompt text, not the gate, unless the gate is demonstrably overbroad.

## Phase 6: Integration Test

Create:

```text
cluster2/tests/test_f2_repair_smoke_integration.py
```

Test requirements:

1. For each fixture, iteration 0 reaches Level 2 and fails with the expected F2
   code.
2. Iteration 1 receives non-empty `feedback_content`.
3. The feedback text passes the numerical-only gate.
4. Trace rows record `repair_iteration` as `0, 1, ..., n` with no gaps.
5. If the repair model produces a correct candidate, `repair_converged=True`
   and `successful_attempt_index` equals the successful repair iteration.
6. If the repair model does not produce a correct candidate,
   `repair_converged=False`, `budget_exhausted=True`, and the final iteration
   is 5.
7. F0 and F1 fixture variants, if added as negative controls, still do not enter
   repair feedback.

CI design:

- The permanent test may use a deterministic model adapter to exercise both the
  convergence branch and the budget-exhaustion branch without relying on live
  LLM quality.
- The real smoke runner must still use the production model path for the manual
  preflight artifact and Fix 4 prompt audit.
- Do not let the deterministic adapter become a production code path. Keep it in
  tests or behind dependency injection already used by the repair loop.

## Phase 7: Expected Smoke Traces

After the real smoke runner has been executed, save one complete trace per
archetype under:

```text
cluster2/tests/fixtures/expected_smoke_traces/
```

These traces are canonical evidence that the F2 path fired end-to-end. They
should be reviewed before being committed.

For regression tests, prefer stable assertions over byte-for-byte comparison of
live model outputs. Stable assertions include:

- fixture hash matches;
- iteration 0 F2 code matches;
- first repair prompt passes the numerical-only gate;
- trace iteration indexes are correct;
- convergence or budget exhaustion fields are internally consistent;
- no forbidden feedback terms appear.

If a trace includes nondeterministic model text, preserve it as an audit artifact
but avoid making CI depend on exact repaired source bytes unless the model path
is deterministic in the test.

## Phase 8: Cluster 2 Contract Update

After the smoke is implemented and validated, update:

```text
.contracts/agentic/cluster2_contract.md
```

Required contract addition:

- Cluster 2 paper-scale `C` and `G+C` runs require a passing synthetic F2 repair
  smoke preflight.
- The preflight must verify all three archetypes.
- The preflight must record trace artifacts at the canonical smoke output paths.
- The paper-scale runner must refuse to start if the required smoke artifacts
  are missing, stale, malformed, or failing validation.
- The smoke trace `feedback_content` fields are the canonical source for the
  Fix 4 manual audit of 10-20 actual feedback prompts.

Do not add new paper claims. The contract update should say this smoke is a
precondition and audit artifact, not an experimental factor.

## Phase 9: Runner Preflight Gate

Add a preflight check to the Cluster 2 paper-scale runner after the smoke exists.

The preflight should verify:

- `outputs/cluster2/smoke_f2_repair_relu.jsonl` exists and validates;
- `outputs/cluster2/smoke_f2_repair_softmax.jsonl` exists and validates;
- `outputs/cluster2/smoke_f2_repair_matmul.jsonl` exists and validates;
- each trace was produced by the current fixture hash;
- each trace has iteration 0 F2 failure;
- each trace has at least one repair iteration with numerical-only feedback;
- each trace records convergence or budget exhaustion consistently.

The preflight should not run the smoke automatically during paper-scale runs.
It should fail fast with an actionable message instructing the operator to run
the smoke first.

## Validation Commands

Fixture and repair-loop tests:

```text
.venv/bin/python -m pytest cluster2/tests/test_f2_repair_smoke_integration.py -v
```

Full Cluster 2 test subset after implementation:

```text
.venv/bin/python -m pytest cluster2/tests -v
```

Real smoke runs:

```text
.venv/bin/python cluster2/experiments/run_f2_repair_smoke.py \
  --fixture cluster2/tests/fixtures/f2_corrupted_relu.py \
  --archetype relu \
  --condition C \
  --repair-budget 5 \
  --output outputs/cluster2/smoke_f2_repair_relu.jsonl

.venv/bin/python cluster2/experiments/run_f2_repair_smoke.py \
  --fixture cluster2/tests/fixtures/f2_corrupted_softmax.py \
  --archetype softmax \
  --condition C \
  --repair-budget 5 \
  --output outputs/cluster2/smoke_f2_repair_softmax.jsonl

.venv/bin/python cluster2/experiments/run_f2_repair_smoke.py \
  --fixture cluster2/tests/fixtures/f2_corrupted_matmul.py \
  --archetype matmul \
  --condition C \
  --repair-budget 5 \
  --output outputs/cluster2/smoke_f2_repair_matmul.jsonl
```

Manual audit:

```text
Read the feedback_content fields from the three smoke JSONL artifacts and verify
that 10-20 prompts contain only public numerical correctness feedback.
```

## Done Criteria

The fix is complete when:

- all three fixture files exist and are documented;
- each fixture passes Level 0 and Level 1;
- each fixture triggers a deterministic F2 failure at Level 2;
- the smoke runner injects each fixture as iteration 0;
- iteration 1 is produced from an actual feedback prompt;
- all trace rows serialize with correct repair iteration indexes;
- the first repair feedback for each archetype passes the numerical-only gate;
- convergence and budget exhaustion are both covered by automated tests;
- real smoke artifacts exist under `outputs/cluster2/`;
- expected trace fixtures are saved under
  `cluster2/tests/fixtures/expected_smoke_traces/`;
- `.contracts/agentic/cluster2_contract.md` records the smoke as a paper-scale
  precondition;
- the paper-scale runner refuses to start when the smoke gate has not passed.

## Stop Conditions

Stop and escalate before paper-scale execution if:

- a fixture cannot be made to pass Level 0 and Level 1 without changing evaluator
  semantics;
- the repair loop cannot accept a seed candidate without duplicating production
  logic;
- F0 or F1 failures can still trigger repair feedback;
- feedback prompts contain structural, compiler, profiler, private-eval, or
  task-changing content;
- trace serialization omits `feedback_content` or loses iteration order;
- the smoke requires edits to Cluster 1 frozen behavior.

## Review Checklist

- Is this still only proving C repair-loop activation on F2 inputs?
- Did any patch add new failure codes or new experimental factors?
- Did any patch alter Level 2 numerical correctness semantics?
- Did any patch weaken F0/F1 termination behavior?
- Did any prompt disclose private eval information?
- Did any trace include timing, profiling, speedup, or P-factor content?
- Are fixture changes limited to the three archetypes requested?
- Can a reader inspect a smoke artifact and understand:
  `bad numerical output -> feedback prompt -> repaired candidate -> result`?
