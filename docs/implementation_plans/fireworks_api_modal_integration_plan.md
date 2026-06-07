# Fireworks API + Modal Integration: Full-Factorial n=20 Implementation Plan

Version: 0.1.1
Date: 2026-06-07
Source branch: `codex/fireworks-api-modal-implementation-plan`
Original planning baseline: `origin/codex-track-handoff-context` at `4b85c24 Audit L2 n20 runtime gate promotion`
Promoted baseline: `codex-track-handoff-context` at `04d2eef Record failed L2 n20 validation`
Status: `PLAN_DRAFT — NOT_APPROVED — NO_CODE_WORK_AUTHORIZED`

Execution authorization flags:

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
ARTIFACT_MUTATION_AUTHORIZED: NO
MLRUNS_MUTATION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
FIREWORKS_API_CALL_AUTHORIZED: NO
CODE_WORK_AUTHORIZED: NO
DEPENDENCY_CHANGE_AUTHORIZED: NO
LOCKFILE_CHANGE_AUTHORIZED: NO
ANALYZER_REFRESH_AUTHORIZED: NO
REPORT_REFRESH_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
```

> **BLOCKING PREREQUISITE**: All code work in this plan is **blocked**. The L2
> n=20 run (`full_pipeline_grammar_mode_cp_factorial_v1 / l2_n20`) is now
> preserved and audited at `04d2eef` as `L2_N20_RUN_FAILED_VALIDATION` with
> 228 of 240 rows. That failed-validation state does **not** clear Fireworks
> implementation. No file outside `docs/` may be modified until a separate
> signed Fireworks authorization packet either waits for an L2 recovery packet
> or explicitly accepts the failed-validation baseline and its claim boundaries.

---

## 0. Purpose and Scope

This document is a **planning and specification artifact only**. It contains no
executable code and authorizes no Modal run, Fireworks API call, GPU job,
generation, billing query, output mutation, MLflow write, dependency change, or
lockfile change.

The goal is to define a new, self-contained generation cluster—provisionally
called **Cluster FW** (Fireworks Cluster)—that replicates the exact 12-cell
`grammar_mode × C_loop × P_loop` factorial design already executed in L1a and
L1b, and attempted in L2, under the existing
`full_pipeline_grammar_mode_cp_factorial_v1` experiment family, but substitutes
the locally-loaded Qwen model with two frontier-scale models served via the
Fireworks AI API:

| Slot | Model | Fireworks API ID |
|---|---|---|
| FW-A | DeepSeek-R1 (Fast) | `accounts/fireworks/models/deepseek-r1` |
| FW-B | Llama 3.1 405B Instruct | `accounts/fireworks/models/llama-v3p1-405b-instruct` |

All existing Modal-based compile, correctness, and profiling infrastructure
(`shared/modal_harness/`) is **reused unchanged** as the remote execution
sandbox. This plan does not modify any existing contract, experiment runner,
analyzer, or shared factor definition. It creates **new parallel contracts and
runners** under a new cluster namespace, following the same structural
conventions as Cluster 2 and Cluster 3.

---

## 1. Research Context and Motivation

The existing factorial experiment (`full_pipeline_grammar_mode_cp_factorial_v1`)
uses a locally-served Qwen model inside Modal containers to generate Triton
kernels across 12 cells of a 2³ design (Factor G: grammar constraint, Factor C:
correctness repair loop, Factor P: profiling loop). The L2 n=20 attempt targets
20 seeds per cell and 240 rows total, but the currently preserved L2 artifact is
partial at 228 of 240 rows and remains non-paper evidence until recovery and
analyzer/report review are separately authorized and completed.

This Fireworks integration extends that experiment to frontier-scale models
(300B–671B parameter range) using a serverless/on-demand API, making GPU
generation cost elastic and removing the need to load model weights inside Modal
containers. The comparison across model scales is the central empirical
contribution of the thesis.

**Research questions this cluster addresses:**

1. Does grammar-constrained decoding (Factor G) provide the same
   compilation-rate lift at frontier scale as it does with smaller models?
2. Do the C and P feedback loops provide superadditive benefit at frontier
   scale, where the model's base capability is much higher?
3. Does DeepSeek-R1's extended thinking phase interact with GBNF grammar
   constraints in ways that differ from instruction-tuned non-reasoning models
   (Llama 405B)?
4. What is the grammar resistance rate (max_tokens exhausted without valid
   closing token) for each frontier model under each grammar variant?

---

## 2. Prerequisites and Blocking Gates

The following must be true before **any code work** on this plan begins:

### Gate 1 — L2 n=20 Status Decision

- The authorized L2 n=20 run is preserved and audited as failed validation in
  `audits/l2_n20_execution_completion_report.md`.
- The preserved L2 namespace contains 12 cell files but only 228 of 240 expected
  rows; `task_agnostic__c_on__p_on` is partial at 8 of 20 rows.
- The post-run analyzer/report command was not run, so no paper-scale L2 graph,
  report, or result claim is unlocked.
- A future Fireworks authorization packet must explicitly choose one of two
  paths before any code work:
  - wait for a separately signed L2 recovery/retry packet and successful L2
    validation; or
  - accept the failed-validation L2 baseline as a planning caveat and keep all
    Fireworks output/reporting claims separated from unresolved L2 evidence.

### Gate 2 — Fireworks Account Readiness (Pre-Implementation Verification)

Before any implementation commit, an agent or human operator must verify and
document all of the following by reading the **live Fireworks documentation and
account dashboard** on the verification date:

| Item | Verification Required |
|---|---|
| Serverless vs. on-demand availability | DeepSeek-R1 model pages currently indicate "Serverless: Not supported" — verify whether this has changed; confirm on-demand pricing and provisioning steps if serverless remains unavailable |
| Exact model API IDs | Confirm the canonical IDs against `https://fireworks.ai/models` at verification time |
| GBNF grammar support for both models | The structured-output grammar docs state "all fireworks models support this feature" but must be verified specifically for DeepSeek-R1 and Llama 405B at verification time |
| `reasoning_effort` interaction with grammar | Verify whether enabling grammar constraints disables or modifies thinking token output for DeepSeek-R1 (the `json_schema` response format disables reasoning; verify grammar mode behavior) |
| Context window and max output tokens | DeepSeek-R1: 163,840 context / 32,768 max output (Fast) or 64,000 max output (0528 variant); verify at verification time |
| Rate limits | Confirm requests-per-minute and tokens-per-minute limits for on-demand vs. serverless endpoints |
| Pricing | Confirm $/M input and output tokens for each model on the verification date; record in the implementation authorization packet |
| FIREWORKS_API_KEY provisioning | Key must be stored in the Modal secret `tritongen-fireworks-secret` (new secret, not the existing `tritongen-secret`) |

### Gate 3 — Signed Implementation Authorization Packet

A separate signed authorization packet (following the format of
`docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md`)
must be created for the Fireworks integration, covering:

- Exact commit baseline at code-start time
- Named Modal secret for `FIREWORKS_API_KEY`
- Spend cap for Fireworks API (total $ ceiling, per-model sub-caps)
- Stop conditions (max tokens per cell, abort-on-cost-threshold logic)
- Expected artifact locations for the FW cluster outputs
- Explicit Fireworks-only execution authorization signature defined by that
  future packet; this non-authorizing plan deliberately omits any active YES
  authorization token

---

## 3. Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│           Cluster FW — Fireworks Generation Harness       │
│  (New cluster namespace; no existing code modified)       │
└──────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐        ┌───────────────────────────┐
│  Fireworks AI    │        │  Modal Sandbox Bridge      │
│  API Endpoint    │        │  (unchanged existing       │
│  (inference/v1)  │        │   shared/modal_harness/)   │
│                  │        │                            │
│  • DeepSeek-R1   │        │  • compile_and_verify()   │
│  • Llama 405B    │        │  • profile_kernel()       │
│  • GBNF grammar  │        │  • GPU: L4/A10G           │
└──────────────────┘        └───────────────────────────┘
         │                              │
         └──────────────┬───────────────┘
                        ▼
          ┌─────────────────────────────┐
          │  12-Cell Factorial Matrix   │
          │  Controller                 │
          │  (new: cluster_fw/)         │
          │                             │
          │  grammar_variant × C × P    │
          │  n=20 seeds, 240 rows       │
          │  2 models × 240 = 480 rows  │
          └─────────────────────────────┘
                        │
                        ▼
          ┌─────────────────────────────┐
          │  Existing Infrastructure    │
          │  • shared/factors/          │
          │  • shared/observability/    │
          │  • shared/analysis/         │
          │  • MLflow tracking          │
          │  • Artifact registry        │
          └─────────────────────────────┘
```

### Design Principles

1. **Strict cluster isolation**: The new `cluster_fw/` directory is a parallel
   namespace. It imports `shared/` modules but does **not** import from
   `cluster1/`, `cluster2/`, or `cluster3/`.

2. **No existing contract modification**: The existing
   `CANONICAL_FACTOR_CELLS`, `GRAMMAR_PATHS_BY_VARIANT`, and
   `_CLUSTER_ALLOWED_CELLS` in `shared/factors/` are **not modified**. Cluster
   FW registers its own allowed cells in a local registry following the same
   pattern.

3. **Modal harness reuse without modification**: `shared/modal_harness/app.py`
   defines `modal.App("tritongen-gpu-harness")`. Cluster FW uses
   `modal.Function.lookup("tritongen-gpu-harness", "<fn_name>")` as a remote
   bridge. No new Modal App is created; no `@app.function` decorators are added
   to the FW runner.

4. **Observability parity**: Cluster FW generates the same sidecar files as
   existing clusters: content-hash sidecar, observability JSON (O0–O4 fields),
   and MLflow run metadata. It additionally records `fw_model_id`,
   `fw_thinking_tokens`, `fw_grammar_resistance_count`, and `fw_spend_usd` per
   row.

5. **Artifact namespace separation**: FW outputs go to a new experiment family
   path. The exact path must be defined in the authorization packet; a proposed
   template is:
   `outputs/fw_pipeline_grammar_mode_cp_factorial_v1/fw_n20/<cell>/<seed>/`.

---

## 4. New Cluster Namespace Layout

The following new directory tree is proposed. **No file outside this tree and
`docs/` is created or modified during FW cluster implementation.**

```
cluster_fw/
├── __init__.py
├── constants.py              # FW_MODELS dict, FW_MAX_TOKENS_BY_MODEL, spend cap sentinel
├── contracts/
│   └── fw_cluster_contract.md   # Frozen contract (mirrors cluster2/contracts/ convention)
├── data/
│   └── prompts/              # Task specification prompts for FW run (symlink or copy from cluster3/data/prompts/)
├── experiments/
│   └── run_fw_modal.py       # Main argparse runner (doc-only template in Phase 2)
├── generation/
│   ├── __init__.py
│   ├── fw_client.py          # FireworksGenerationHarness class
│   └── fw_grammar_loader.py  # Loads GBNF from cluster1/grammar/ paths (read-only import)
├── modal/
│   ├── __init__.py
│   └── fw_sandbox_bridge.py  # ModalSandboxBridge class (modal.Function.lookup only)
├── results/
│   ├── __init__.py
│   ├── dataclass.py          # FWRowResult dataclass (mirrors cluster2/results/dataclass.py convention)
│   └── logger.py             # JSONL row writer
└── tests/
    ├── __init__.py
    ├── fixtures/
    └── test_fw_client.py     # Unit tests (mocked; no real API calls in test suite)
```

---

## 5. The 12-Cell Factorial Design for Cluster FW

Cluster FW replicates the **exact same 12-cell layout** as `grammar_mode x C x P`
used in L1a, L1b, and L2. The mapping from the existing three-factor cell
notation to the Fireworks harness parameters is:

| Cell ID | Existing FactorCell | grammar_variant | C_loop_active | P_loop_active |
|---|---|---|---|---|
| 1 | `none` | `none` | False | False |
| 2 | `C` | `none` | True | False |
| 3 | `P` | `none` | False | True |
| 4 | `C+P` | `none` | True | True |
| 5 | `G` (template) | `template_upper_bound` | False | False |
| 6 | `G+C` (template) | `template_upper_bound` | True | False |
| 7 | `G+P` (template) | `template_upper_bound` | False | True |
| 8 | `G+C+P` (template) | `template_upper_bound` | True | True |
| 9 | `G` (task_agnostic) | `task_agnostic` | False | False |
| 10 | `G+C` (task_agnostic) | `task_agnostic` | True | False |
| 11 | `G+P` (task_agnostic) | `task_agnostic` | False | True |
| 12 | `G+C+P` (task_agnostic) | `task_agnostic` | True | True |

**Note on existing cell mapping**: The existing system uses a 2³ design where
Factor G has two grammar variants (`template_upper_bound` and `task_agnostic`).
The 12-cell design is implemented as a `grammar_mode` × C × P design rather
than a strict 2³. Cluster FW preserves this 12-cell convention exactly. No new
cell types or factor values are introduced.

**Per-model row count**:
- 12 cells × 20 seeds = 240 rows per model
- 2 models (FW-A DeepSeek-R1, FW-B Llama 405B) × 240 = **480 total rows**

---

## 6. Fireworks Generation Harness Specification

### 6.1 `cluster_fw/generation/fw_client.py`

**Class: `FireworksGenerationHarness`**

Wraps the OpenAI-compatible Fireworks endpoint. All parameters below must be
verified against live Fireworks documentation at implementation time.

| Parameter | Value | Notes |
|---|---|---|
| Base URL | `https://api.fireworks.ai/inference/v1` | Do not hardcode; read from a constant |
| Auth | Bearer `FIREWORKS_API_KEY` env var | Must be set via Modal secret `tritongen-fireworks-secret` |
| `max_tokens` (DeepSeek-R1) | 8192 minimum; 16384 recommended | R1 spends 1,500–3,000 tokens on `<think>` before generating code; insufficient budget causes truncated output that triggers false F1 failures |
| `max_tokens` (Llama 405B) | 4096 | Adjust if multi-turn context grows large |
| `temperature` | 0.8 | Match existing cluster3 default; verify at implementation time |
| `seed` | Passed per-row from the experiment matrix | Required for reproducibility; must match the seeding policy in the existing experiment harness |
| Grammar field | `response_format={"type": "grammar", "grammar": <gbnf_str>}` | Set to `None` for `grammar_variant == "none"` cells; must be verified for DeepSeek-R1 compatibility |

**DeepSeek-R1 thinking token extraction** (two methods; implement with fallback):

```
# Method 1 — structured field (preferred if available)
message = response.choices[0].message
reasoning = message.model_extra.get("fireworks", {}).get("thinking", {}).get("text", "")

# Method 2 — regex fallback on raw content
import re
match = re.search(r"<think>(.*?)</think>", raw_content, re.DOTALL)
reasoning = match.group(1).strip() if match else ""
code_output = raw_content.split("</think>")[-1].strip()
```

**Return contract** of `generate_kernel()`:

```python
@dataclass
class FWGenerationResult:
    model_id: str
    grammar_variant: str          # "none" | "template_upper_bound" | "task_agnostic"
    prompt_tokens: int
    completion_tokens: int
    thinking_tokens: int          # 0 for Llama 405B
    reasoning_text: str           # "" for Llama 405B
    code_output: str
    raw_response: str             # full raw text before split
    grammar_resistance: bool      # True if completion_tokens == max_tokens and no valid closing token
    spend_usd_estimate: float     # prompt_tokens * input_rate + completion_tokens * output_rate
    latency_seconds: float
```

The `spend_usd_estimate` is a per-row estimate using pricing constants defined
at runner startup. **Actual billing is read from the Fireworks dashboard after
the run**, not from estimates. Estimates are logged for stop-cap enforcement
only.

### 6.2 Grammar Loading

Grammar GBNF files are **read-only imported** from their existing canonical
paths:

| Grammar variant | Source path |
|---|---|
| `template_upper_bound` | `cluster1/grammar/triton_kernel.gbnf` |
| `task_agnostic` | `cluster1/grammar/triton_kernel_agnostic.gbnf` |

`cluster_fw/generation/fw_grammar_loader.py` reads these paths at runner
startup and caches them in memory. It does not modify the files.

### 6.3 Spend Safety Switch

A cumulative spend accumulator is maintained across the entire matrix run:

```
if cumulative_spend_usd >= SPEND_CAP_USD:
    abort_run("spend cap reached")
```

Additionally, per-request, if `prompt_tokens + completion_tokens` exceeds a
configurable context guard (proposed: 32,000 tokens), the cell is marked
`ABORTED_CONTEXT_OVERFLOW` rather than retried.

---

## 7. Modal Sandbox Bridge Specification

### 7.1 `cluster_fw/modal/fw_sandbox_bridge.py`

**Class: `ModalSandboxBridge`**

Uses `modal.Function.lookup()` to invoke existing Modal functions. It does
**not** define new `@app.function` decorators or new Modal apps.

The existing Modal app name is `"tritongen-gpu-harness"` (from
`shared/modal_harness/app.py`). The bridge binds to it at runtime.

**Pre-run warm-up protocol**: Before executing `run_full_matrix()`, the runner
calls a lightweight no-op payload against both the compilation function and the
profiling function. This ensures the GPU container has scaled from 0 and
eliminates cold-start latency (45–90 s on A10G) from the first timed cell. The
warm-up call uses a trivially valid kernel and is logged but excluded from
result rows.

**Functions to bind** (exact names must be verified against the live deployed
Modal app at implementation time):

| Bridge method | Expected Modal function name | GPU tier |
|---|---|---|
| `remote_compile_and_test(kernel_code)` | Verify against `shared/modal_harness/compile.py` and `cluster2/modal/correctness.py` | L4 or A10G |
| `remote_profile(kernel_code)` | Verify against `cluster3/modal/correctness_runner.py` profiling surface | A10G or A100 |

**Return contracts** are unchanged from the existing cluster3 bridge pattern:

```python
# Compile result
{"status": "F1_FAIL" | "F2_FAIL" | "F3_PASS", "error_msg": str}

# Profile result
{"speedup": float, "roofline_distance": float, "bottleneck": str,
 "achieved_gflops": float}
```

---

## 8. Factorial Matrix Controller Specification

### 8.1 `cluster_fw/experiments/run_fw_modal.py`

**Class: `FWFactorialController`**

Orchestrates the complete 12-cell × 20-seed × 2-model matrix.

**CLI interface** (proposed):

```
python cluster_fw/experiments/run_fw_modal.py \
    --model-key deepseek_r1 \
    --n-seeds 20 \
    --grammar-mode grammar_mode_cp_12cell \
    --output-root outputs/fw_pipeline_grammar_mode_cp_factorial_v1/fw_n20 \
    --spend-cap 150.00 \
    --signed-fw-authorization <TOKEN>
```

The `--signed-fw-authorization` flag mirrors the existing `--signed-l2-authorization`
pattern in the L2 runner. The runtime gate rejects execution unless a valid
signed token is present and matches the expected experiment profile.

**Loop structure**:

```
for model_key in [model selected by --model-key]:
    warm_up_modal_containers()
    for grammar_variant in ["none", "template_upper_bound", "task_agnostic"]:
        for (c_active, p_active) in [(F,F), (T,F), (F,T), (T,T)]:
            cell_config = build_cell_config(grammar_variant, c_active, p_active)
            for seed in range(n_seeds):
                for task in task_suite:
                    result = run_trial(cell_config, task, seed)
                    write_row(result)
                    update_spend_accumulator(result)
                    if spend_cap_exceeded():
                        abort_run()
```

**C-loop (correctness repair)**:

When `c_active=True`, the runner performs up to `C_MAX_ATTEMPTS=4` generation
retries on compile failure, appending compiler error tracebacks to the prompt.
The prompt reconstruction format matches the existing cluster3 pattern:

```
{original_task_prompt}

<previous_attempt>
{generated_code}
</previous_attempt>
<compiler_feedback>
{error_msg}
</compiler_feedback>
Instruction: Analyze the compiler error and fix the code.
```

**P-loop (performance repair)**:

When `p_active=True` and the kernel has passed F3 (correctness), the runner
performs up to `P_MAX_ATTEMPTS=3` profiling-driven refinement iterations,
appending Nsight Compute metrics to the prompt. Format matches cluster3 pattern.
Each tuned kernel is re-verified via `remote_compile_and_test()` before
accepting. If re-verification fails, the loop stops and the last passing kernel
is preserved.

### 8.2 Result Row Schema (`cluster_fw/results/dataclass.py`)

Each output row extends the existing cluster result schema with FW-specific
fields. The dataclass must be compatible with the existing shared analysis
pipeline at `shared/analysis/factorial.py`.

**New fields** (in addition to all existing cluster3 row fields):

| Field | Type | Description |
|---|---|---|
| `fw_model_id` | `str` | Full Fireworks model API ID |
| `fw_model_key` | `str` | Short key: `"deepseek_r1"` or `"llama_405b"` |
| `fw_thinking_tokens` | `int` | Reasoning phase tokens (0 for Llama 405B) |
| `fw_grammar_resistance` | `bool` | True if generation hit max_tokens without closing |
| `fw_spend_usd_estimate` | `float` | Per-row spend estimate (for cap enforcement only) |
| `fw_latency_seconds` | `float` | Fireworks API wall time |
| `fw_prompt_tokens` | `int` | Input token count from API response |
| `fw_completion_tokens` | `int` | Output token count from API response |
| `fw_reasoning_effort` | `str \| None` | Value of `reasoning_effort` param if set |

---

## 9. Infrastructure Hazards and Mitigations

### 9.1 DeepSeek-R1 Thinking Token Budget Saturation

**Hazard**: DeepSeek-R1 generates 1,500–3,000 thinking tokens before producing
any code. With `max_tokens=4096`, the model routinely gets cut off mid-output.
Truncated output triggers false F1 (parse/compile) failures and inflates the
C-loop retry count.

**Mitigation**: Set `max_tokens=8192` as the minimum for all DeepSeek-R1 cells.
Use `max_tokens=16384` for C-loop and P-loop cells where accumulated context
history pushes prompt size up. Track `fw_grammar_resistance` per row to detect
budget saturation vs. genuine syntax errors.

### 9.2 Grammar Interference with RL-Trained Reasoning Models

**Hazard**: DeepSeek-R1 was trained via RL to optimize its output format. When
server-side GBNF token masking forces explicit syntactic constraints (e.g.,
fixed decorator patterns, power-of-two tile sizes), the model's preferred token
path may be blocked. This can manifest as:

- Repetitive loop locking (repeated whitespace or period characters)
- Premature generation termination before a valid closing token
- Context window exhaustion without syntactically valid output

**Mitigation and Measurement**:
- Log `fw_grammar_resistance=True` whenever `completion_tokens >= 0.95 * max_tokens`
  and the output does not contain a valid GBNF-closing token sequence.
- This is a **key experimental metric**, not a bug — grammar resistance rate
  is one of the primary research findings comparing reasoning vs.
  instruction-tuned frontier models under structural constraints.
- Do not suppress or auto-retry grammar resistance events; log them and
  terminate the cell trial with `status="FW_GRAMMAR_RESISTANCE"`.

**Important caveat**: Verify at implementation time whether Fireworks'
`response_format: grammar` silently disables DeepSeek-R1's thinking phase
(as `json_schema` disables it). If grammar mode disables thinking, cells 9–12
(G+task_agnostic) cannot capture reasoning traces and must be documented as
such in the methodology.

### 9.3 Modal Container Cold Starts

**Hazard**: Fireworks API calls return within seconds, but the first
`modal.Function.lookup().remote()` call after container scale-down incurs a
45–90 s GPU cold start. If the warm-up call is omitted, the first cell's timing
metrics include cold-start latency.

**Mitigation**: Implement `warm_up_modal_containers()` as the first call in
`run_full_matrix()`. Send a trivially correct kernel (single elementwise `relu`)
through both `remote_compile_and_test()` and `remote_profile()`. Verify
successful return before advancing to real matrix cells. Log warm-up latency
separately; exclude it from all result rows.

### 9.4 Factorial Cost Compounding

**Hazard**: Multi-turn C-loop and P-loop prompts compound token counts rapidly.
A single cell with 4 C-loop retries and 3 P-loop iterations can generate 40,000+
tokens of context for the final P-loop generation call. Across 20 seeds and 12
cells, unmonitored compounding can produce unexpectedly large bills.

**Mitigation**:
- Implement per-request token count guard: if `prompt_tokens + completion_tokens`
  exceeds `CONTEXT_GUARD_TOKENS=32000`, mark the trial
  `ABORTED_CONTEXT_OVERFLOW` and continue to next seed without retry.
- Implement cumulative spend cap (`SPEND_CAP_USD` flag); abort the entire run
  if exceeded.
- Store full prompt/response histories in artifact JSON for each row so
  context growth can be post-hoc audited.

### 9.5 Serverless vs. On-Demand Deployment (Critical Prerequisite)

**Current status**: As of 2026-06-06, Fireworks model pages for all DeepSeek-R1
variants and Llama 3.1 405B Instruct Long explicitly show "Serverless: Not
supported." Both require on-demand (dedicated GPU) deployment.

**Implementation implication**: On-demand deployments require provisioning a
dedicated endpoint via the Fireworks dashboard or API before the run. The
endpoint address replaces the generic serverless base URL. This provisioning
step must be completed and its address recorded in the implementation
authorization packet before the run begins.

**Verification required at implementation time**:
- Check whether serverless availability has changed for either model.
- If on-demand is still required: document the endpoint provisioning steps in
  the implementation authorization packet.
- If serverless is now available: verify pricing and rate limits, and update
  the plan accordingly.

---

## 10. Observability and Artifact Conventions

### 10.1 Output Artifact Layout

Following the existing convention:

```
outputs/
└── fw_pipeline_grammar_mode_cp_factorial_v1/
    ├── fw_n20_deepseek_r1/
    │   ├── <cell>/<seed>/<kernel_class>/
    │   │   ├── result.jsonl           # row result
    │   │   ├── result.hash            # content-hash sidecar (O0)
    │   │   └── observability.json     # O1-O4 sidecar
    │   └── ...
    └── fw_n20_llama_405b/
        └── (same structure)
```

### 10.2 Billing and Spend Tracking

In addition to the existing Modal billing artifacts:

- A `fw_spend_log.jsonl` is written per run with one entry per API call:
  `{timestamp, model_id, cell, seed, prompt_tokens, completion_tokens, spend_estimate_usd}`.
- A `fw_spend_summary.json` is written at run completion with per-model and
  per-cell total estimates.
- Actual billing must be verified against the Fireworks dashboard after run
  completion. Dashboard exports should be archived in
  `artifacts/billing/fw_pipeline_grammar_mode_cp_factorial_v1/`.

### 10.3 Analyzer Compatibility

The existing `shared/analysis/factorial.py` operates on result rows via
shared field names. Cluster FW rows must include all existing required fields
plus the FW-specific additions. The analyzer must not be modified to accommodate
FW rows; instead, FW rows must be shaped to be compatible with the existing
schema. If any new analyzer work is needed to surface FW-specific metrics
(e.g., grammar resistance rate by model), that work is a **separate** doc and
planning item, not part of this plan.

---

## 11. Task Suite Specification

The Fireworks cluster uses the **same task suite** as the existing L2 run
to ensure comparability. Task specifications (kernel class + prompt template)
must be imported read-only from `cluster3/data/prompts/` or the equivalent
shared location. No new task definitions are created.

At implementation time, verify the exact canonical task list used in the L2 run
from the completed L2 observability artifacts before writing any code.

---

## 12. New Contracts to Create

Following the repo convention, the following new contracts must be created as
part of the implementation phases. They are listed here for planning only;
their content will be drafted in Phase 1 (Contracts Drafting phase):

| File | Purpose | Class |
|---|---|---|
| `cluster_fw/contracts/fw_cluster_contract.md` | Frozen methodology contract for Cluster FW | `FORMAL_CONTRACT` |
| `docs/implementation_plans/fireworks_api_modal_integration_plan.md` | This file | `AGENT_INTERNAL` |
| `docs/experiment_packets/fw_n20_authorization_packet.md` | Execution authorization packet | `AGENT_POLICY` |
| `audits/fw_implementation_audit_<phase>.md` | Per-phase audit records | `EVIDENCE_SNAPSHOT` |

---

## 13. Phased Implementation Plan

Each phase is a **separate commit or commit series on a separate feature
branch**, fast-forward promoted into the integration branch after a phase-level
audit. No phase executes code or modifies existing files.

---

### Phase 0 — Plan Ratification (This Document)

**Branch**: `codex/fireworks-api-modal-implementation-plan`
**Deliverables**:
- `docs/implementation_plans/fireworks_api_modal_integration_plan.md` v0.1.0 (this file)
- Registry entry in `docs/handoff/document_version_registry.md`
- Hub entry in `docs/handoff/agentic_document_hub.md`

**Gate**: Plan reviewed and baseline committed. No code, no execution.

**Commit message template**:
```
Add Fireworks API + Modal integration plan v0.1.0

docs/implementation_plans/fireworks_api_modal_integration_plan.md:
  Plan document only. No code, no execution authorized.
```

---

### Phase 1 — Contracts and Frozen Methodology

**Branch**: `codex/fw-cluster-contracts`
**Deliverables**:
- `cluster_fw/contracts/fw_cluster_contract.md`: Frozen methodology contract
  specifying grammar variant mapping, cell ordering, seed policy, loop budgets
  (C_MAX_ATTEMPTS=4, P_MAX_ATTEMPTS=3), token budget policy, spend cap policy,
  task suite policy, and comparability guarantee to L2 n=20
- Pre-implementation verification checklist for Gate 2 (Section 2 above)
- Registry and hub updates

**Gate**: Contract reviewed; no implementation code exists.

---

### Phase 2 — Skeleton and Constants

**Branch**: `codex/fw-cluster-skeleton`
**Deliverables**:
- `cluster_fw/__init__.py` (empty)
- `cluster_fw/constants.py`: `FW_MODELS` dict, `FW_MAX_TOKENS_BY_MODEL`,
  `FW_DEFAULT_TEMPERATURE`, `C_MAX_ATTEMPTS`, `P_MAX_ATTEMPTS`,
  `CONTEXT_GUARD_TOKENS`, `SPEND_CAP_USD` sentinel (unset; must be passed at
  runtime), `FW_APP_NAME = "tritongen-gpu-harness"`
- `cluster_fw/results/__init__.py`
- `cluster_fw/results/dataclass.py`: `FWRowResult` dataclass (no logic)
- Registry and hub updates, phase audit

**Gate**: Skeleton lints cleanly. No generation logic. No Modal calls.

---

### Phase 3 — Grammar Loader

**Branch**: `codex/fw-grammar-loader`
**Deliverables**:
- `cluster_fw/generation/__init__.py`
- `cluster_fw/generation/fw_grammar_loader.py`:
  - `load_grammar(variant: str) -> str | None`
  - Reads from canonical cluster1 grammar paths (read-only)
  - Returns `None` for `variant == "none"`
  - Raises `ValueError` for unknown variants
- `cluster_fw/tests/test_fw_grammar_loader.py`: Unit tests (file existence,
  correct path resolution, None for none variant, error for unknown)
- Phase audit

**Gate**: Tests pass with `pytest cluster_fw/tests/test_fw_grammar_loader.py`.
No API calls.

---

### Phase 4 — Fireworks Client (Mocked)

**Branch**: `codex/fw-generation-client`
**Deliverables**:
- `cluster_fw/generation/fw_client.py`:
  - `FireworksGenerationHarness` class
  - `generate_kernel(model_id, prompt, grammar_text, seed) -> FWGenerationResult`
  - DeepSeek-R1 thinking token extraction (both methods, with fallback)
  - `fw_grammar_resistance` detection logic
  - Spend estimate calculation
  - Raises `ValueError` if `FIREWORKS_API_KEY` env var is unset
- `cluster_fw/tests/test_fw_client.py`:
  - All tests use `unittest.mock.patch` on `openai.OpenAI`; zero real API calls
  - Tests: missing API key, grammar mode set correctly, None grammar skips field,
    thinking token extraction (structured and regex paths), grammar resistance
    detection, spend estimate calculation
- Phase audit

**Gate**: Tests pass with mocked client. No real API calls in CI.

---

### Phase 5 — Modal Sandbox Bridge

**Branch**: `codex/fw-modal-bridge`
**Deliverables**:
- `cluster_fw/modal/__init__.py`
- `cluster_fw/modal/fw_sandbox_bridge.py`:
  - `ModalSandboxBridge` class
  - `remote_compile_and_test(kernel_code: str) -> dict`
  - `remote_profile(kernel_code: str) -> dict`
  - `warm_up() -> None`
  - Uses `modal.Function.lookup(FW_APP_NAME, fn_name)` only
  - Does not import any `@app.function` decorated module directly
- `cluster_fw/tests/test_fw_sandbox_bridge.py`:
  - All tests mock `modal.Function.lookup`
  - Tests: correct function names bound, error handling, warm-up called before
    first real invocation
- Phase audit

**Gate**: Tests pass. No real Modal calls. `modal.Function.lookup` is mocked.

---

### Phase 6 — Result Logger

**Branch**: `codex/fw-result-logger`
**Deliverables**:
- `cluster_fw/results/logger.py`:
  - `FWResultLogger` class
  - `write_row(result: FWRowResult) -> None`
  - JSONL output to target path; atomic writes
  - Content-hash sidecar writer (mirrors existing cluster convention)
  - Observability JSON sidecar writer (O0–O4 fields + FW-specific fields)
  - Spend log writer (`fw_spend_log.jsonl`)
- `cluster_fw/tests/test_fw_result_logger.py`: Unit tests (output file creation,
  row format, sidecar written, spend log entry format)
- Phase audit

**Gate**: Tests pass. No real output mutations to `outputs/` or `artifacts/`.

---

### Phase 7 — Factorial Controller (Dry-Run Mode Only)

**Branch**: `codex/fw-factorial-controller`
**Deliverables**:
- `cluster_fw/experiments/run_fw_modal.py`:
  - `FWFactorialController` class with `run_trial()` and `run_full_matrix()`
  - `--dry-run` flag: builds full cell × seed × task matrix, logs planned
    runs, makes zero API calls and zero Modal calls
  - `--signed-fw-authorization` runtime gate (fail-closed; blocks execution
    unless a valid token is provided)
  - Spend accumulator and context guard
  - Warm-up protocol
  - C-loop prompt reconstruction
  - P-loop prompt reconstruction
- `cluster_fw/tests/test_fw_factorial_controller.py`:
  - All tests use mocked `FireworksGenerationHarness` and `ModalSandboxBridge`
  - Tests: dry-run produces correct cell count (12 cells × n_seeds), spend cap
    abort logic, context guard abort logic, C-loop prompt format, P-loop prompt
    format, grammar resistance does not trigger retry
- Phase audit, dry-run output verified

**Gate**: `python cluster_fw/experiments/run_fw_modal.py --dry-run --n-seeds 2`
produces correct 12-cell × 2-seed plan log with zero API or Modal calls.

---

### Phase 8 — Authorization Packet Draft

**Branch**: `codex/fw-authorization-packet`
**Deliverables**:
- `docs/experiment_packets/fw_n20_authorization_packet.md` (v0.1.0, unsigned):
  - Target baseline commit at packet time
  - Exact `--model-key`, `--n-seeds 20`, `--grammar-mode`, `--output-root`,
    `--spend-cap` argument values
  - Pre-run Fireworks account verification checklist (Gate 2)
  - On-demand endpoint provisioning steps (if serverless still unavailable)
  - Expected artifact paths (all 480 rows)
  - Stop conditions
  - Post-run validation commands
  - Unsigned signature block (`AUTHORIZES_EXECUTION: NO`)
- `audits/fw_authorization_packet_draft_report.md`
- Registry and hub updates

**Gate**: Packet reviewed. Still `AUTHORIZES_EXECUTION: NO`. No execution.

---

### Phase 9 — Pre-Run Preflight and Signed Authorization

**Branch**: `codex/fw-signed-authorization`
**Deliverables**:
- Gate 2 verification report (Fireworks account, model availability, pricing,
  on-demand endpoint, grammar support) filed as `audits/fw_preflight_report.md`
- `docs/experiment_packets/fw_n20_authorization_packet.md` bumped to v1.0.0
  with the explicit Fireworks-only execution authorization token defined by
  that future signed packet; this non-authorizing plan deliberately omits that
  token
- Exact `FIREWORKS_API_KEY` secret name confirmed in Modal
- Spend cap value confirmed and signed
- Registry and hub updates

**Gate**: All Gate 1, Gate 2, Gate 3 conditions satisfied. Signed packet
reviewed by human operator. FW run may begin.

---

### Phase 10 — Execution and Post-Run Audit

**Branch**: Execution on `codex-track-handoff-context` (or successor) after
signed authorization.

**Deliverables** (execution phase, not doc-only):
- FW run outputs in `outputs/fw_pipeline_grammar_mode_cp_factorial_v1/`
- Spend log and summary in `artifacts/billing/fw_pipeline_grammar_mode_cp_factorial_v1/`
- Post-run audit `audits/fw_n20_execution_completion_report.md`
- Analyzer run over FW results (pending Gate from L2 analyzer extension plan)
- Registry and hub updates

---

## 14. Registry and Hub Update Requirements

When this plan document is committed (Phase 0), the following updates are
required **in the same commit**:

### `docs/handoff/document_version_registry.md`

Add a new row (bump registry version by 1 minor):

```
| AGENT_INTERNAL | docs/implementation_plans/fireworks_api_modal_integration_plan.md | v0.1.0 | <date> | Plan document only; baseline for Fireworks API + Modal integration |
```

Bump registry version from `1.116.0` → `1.117.0`.

### `docs/handoff/agentic_document_hub.md`

Add a new row to the Core Control Documents table:

```
| Fireworks API + Modal integration plan | docs/implementation_plans/fireworks_api_modal_integration_plan.md |
```

Bump hub version from `1.37.27` → `1.37.28`.

---

## 15. What This Plan Does Not Cover

The following topics are explicitly out of scope for this plan and must be
addressed in separate planning documents if needed:

- **Analyzer extension**: Adding `fw_model_id` and `fw_grammar_resistance` as
  new analysis dimensions to `shared/analysis/factorial.py` or producing a
  cross-cluster comparison report. This requires a separate doc after Phase 8.
- **vLLM or self-hosted frontier inference**: The
  `docs/frontier_model_vllm_viability_report.md` covers this separately.
- **Cluster 3 P-factor for FW cluster**: Whether the P-loop should invoke a
  Fireworks planning call (analogous to the Cluster 3 planning loop) rather
  than a Fireworks code generation call is a research design question. This plan
  assumes the P-loop uses the **same** Fireworks generation harness with
  performance-augmented prompts. If the research design changes, this plan
  must be versioned and updated before Phase 7 begins.
- **MLflow runtime integration**: This plan assumes MLflow runtime writes remain
  disabled for the FW cluster (matching the L2 policy). If MLflow runtime
  tracking is desired for FW runs, that requires a separate signed decision.
- **Cost reconciliation tooling**: Automated Fireworks billing export and
  reconciliation tooling is not in scope. Manual dashboard export is assumed.

---

## 16. Open Questions for Human Review

Before any phase begins, the following open questions must be resolved:

1. **Model selection final decision**: The two model slots (FW-A: DeepSeek-R1,
   FW-B: Llama 405B) are proposed based on the user's architectural blueprint.
   Confirm these are the final selections, or specify alternatives if the
   model pages show changed availability.

2. **Serverless vs. on-demand**: If on-demand deployment is still required for
   both models at implementation time, what is the provisioned endpoint lifetime
   and cost? Should the run be staged across two separate sessions (one per
   model) to minimize on-demand idle time?

3. **Run sequence**: Should both models run in the same matrix controller
   invocation (sequential), or in two separate authorized runs (one per model)?
   Separate runs simplify cost attribution and stop-cap enforcement.

4. **Grammar mode for DeepSeek-R1**: If Fireworks confirms that
   `response_format: grammar` disables DeepSeek-R1 thinking tokens, the G-factor
   cells for DeepSeek-R1 will have `fw_thinking_tokens=0` and no reasoning
   trace. This is scientifically significant and must be documented in the
   frozen contract before implementation.

5. **Task suite finalization**: Which exact kernel classes and prompts are
   included in the FW n=20 run? Must be identical to L2 for comparability.
   Confirm the canonical task list from the completed L2 observability artifacts
   after Gate 1 clears.

6. **Seed policy**: Does the FW run use the same seed values as L2 for
   per-seed comparability, or independent seeds? Document the policy in the
   frozen contract.

---

## 17. Summary

This document defines a 10-phase, doc-first, commit-gated implementation plan
for integrating the Fireworks AI API with the existing TritonGen Modal harness.
The plan:

- Creates a new `cluster_fw/` namespace without modifying any existing code
- Reuses all existing Modal compilation, correctness, and profiling infrastructure
- Replicates the exact 12-cell `grammar_mode × C × P` factorial design at
  frontier scale (DeepSeek-R1 671B and Llama 3.1 405B)
- Documents all known infrastructure hazards (thinking token budget, grammar
  interference, cold starts, cost compounding, serverless availability)
- Requires human sign-off at Gates 1, 2, and 3 before any execution
- Is **fully blocked** until a new signed packet decides how to handle the
  preserved failed-validation L2 baseline

No code work, Modal call, Fireworks API call, GPU job, output mutation,
dependency change, or billing action is authorized by this document.
