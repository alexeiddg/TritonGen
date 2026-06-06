# L1a Final Signature Packet Promotion Audit Report

version: 1.0.0
created_at: 2026-06-06
classification: L1A_FINAL_SIGNATURE_PACKET_PROMOTION_COMPLETE
AUTHORIZES_EXECUTION: NO
signature_status: UNSIGNED

## source branch

`codex/l1a-final-signature-packet`

## target branch

`codex-track-handoff-context`

## promoted commit

`316723a Prepare L1a final signature packet`

The target branch fast-forwarded from
`c05e111 Audit L1a executable selector support promotion` to `316723a`.

## packet status

The promoted packet is
`docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
v0.5.3. It is a final human-signature review surface only. It remains
unsigned, non-authorizing, and blocked for execution.

## target approval status

No human signature, spend approval, launch approval, billing-query approval, or
output/artifact/mlruns mutation approval is present in the promoted packet.

## execution command status

The packet records source-backed local command-construction surfaces for future
review:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --execution-plan
```

and a future selector-level command that requires
`SIGNED_L1A_PACKET_ID_REQUIRED`. These commands were inspected as text only and
were not executed during this promotion.

## matrix status

The packet preserves the 12-cell `grammar_mode x C x P` L1a n=1 design:

- `grammar_off` with C off/on and P off/on;
- `template_upper_bound` with C off/on and P off/on;
- `task_agnostic` with C off/on and P off/on.

No scientific rows, sampling policy, repair policy, grammar semantics, or
pass/fail definitions changed in the promotion audit.

## path/collision status

The promoted packet keeps deterministic per-cell JSONL, content-hash,
observability, analyzer, and report path surfaces under the planned L1a n=1
roots. The collision policy remains `fail_if_any_target_path_exists`, and
`--overwrite` remains part of the unsigned future command surface rather than
an authorization to mutate outputs.

## grammar hash status

The promoted packet preserves the grammar-mode mapping and hash locks:

- `grammar_off`: no grammar file;
- `template_upper_bound`: `cluster1/grammar/triton_kernel.gbnf`,
  `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82`;
- `task_agnostic`: `cluster1/grammar/triton_kernel_agnostic.gbnf`,
  `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`.

## model/seed status

The promoted packet preserves:

- model id: `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`;
- model revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`;
- tokenizer revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`;
- decoding config: `temperature=0.2`, `max_new_tokens=1536`;
- seed policy: L1a n=1 with `base_seed=0` per cell/invocation.

## preflight estimate status

The advisory estimate remains
`NOT_SIGNABLE_SYNTHETIC_PLACEHOLDER_ATTACHED`. It is not billing evidence and is
not sufficient for signature. A signable estimate with verified pricing and
approved timing inputs remains required before any execution authorization.

## stop/spend limit status

Stop and spend limits remain `PROPOSED_NOT_SIGNED`, including row, generation
attempt, correctness-call, wall-clock, estimated-cost, and reconciled-cost
limits. They require explicit human signature or replacement before launch.

## Modal image digest status

The Modal image digest remains
`REQUIRED_BEFORE_SIGNATURE_REMOTE_IMAGE_DIGEST_UNKNOWN`. No remote image
inspection, rebuild, or Modal invocation was authorized or performed.

## billing reconciliation status

Billing reconciliation remains plan-only. Billing API/query authorization,
time-window selection, and redacted output path selection remain required before
any post-run billing collection.

## post-run validation status

Post-run validation commands are listed as proposed/unsigned command surfaces.
They require real post-run artifacts and explicit authorization before any
schema, content-hash, observability, analyzer, report, or billing validation can
run.

## signature block status

The promoted packet keeps `signature_status: UNSIGNED`, blank or
`REQUIRED_BEFORE_SIGNATURE` signer fields, proposed stop/spend limits, a
not-signable preflight estimate, required image digest, required billing plan
acceptance, required post-run validation acceptance, and an absent execution
authorization statement.

## authorization status

Authorization remains blocked:

- `AUTHORIZES_EXECUTION: NO`;
- Modal execution not authorized;
- GPU execution not authorized;
- generation not authorized;
- experiment execution not authorized;
- output/artifact/mlruns mutation not authorized;
- paper-scale execution not authorized;
- performance execution and profiling not authorized;
- MLflow runtime writes not authorized;
- billing query not authorized.

## unresolved blockers

The following blockers remain before any future signature or execution packet:

- exact signed target commit for `codex-track-handoff-context`;
- explicit human signature and authorization statement;
- approved numeric stop limits;
- approved numeric spend limits;
- signable preflight estimate with verified pricing and timing inputs;
- remote Modal image digest;
- accepted billing reconciliation plan and billing query authorization;
- accepted post-run validation bundle and output/artifact/mlruns mutation
  authorization.

## validation/scans run

The promotion used local git and text scans only:

- `git status --short --branch`: source branch clean at `316723a`; target clean
  before fast-forward; target ahead of origin by one commit after promotion;
- `git log --oneline -8`: confirmed `316723a` in source history and target
  history after fast-forward;
- `git diff --check`: clean;
- `git diff --name-only codex-track-handoff-context..HEAD -- cluster1 cluster2 cluster3 shared`: empty before promotion;
- `git diff --name-only codex-track-handoff-context..HEAD -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock`: empty before promotion;
- positive authorization scan for execution/spend enablement markers: empty;
- required-status scan: found `AUTHORIZES_EXECUTION: NO`, `UNSIGNED`,
  `PROPOSED_NOT_SIGNED`, `NOT_SIGNABLE`, `REQUIRED_BEFORE_SIGNATURE`,
  `REMOTE_IMAGE_DIGEST_UNKNOWN`, `billing reconciliation`, `preflight`,
  `spend cap`, `stop limits`, `execution-plan`, `grammar_mode_cp_12cell`,
  `c05e111`, and `e9f180a`;
- evidence-boundary scan for runtime, cost, benchmark, optimization, billing, or
  execution-completion claims: empty;
- false-signature scan: only explicitly negated or placeholder labels such as
  `UNSIGNED`, `PROPOSED_NOT_SIGNED`, and `SIGNED_L1A_PACKET_ID_REQUIRED`.

## no-execution proof

No Modal command, GPU job, generation command, experiment runner, benchmark,
profiler, billing query, analyzer/report refresh, or post-run validation command
was run. The only commands used were git inspection, text search, branch
checkout, fast-forward merge, and audit-file authoring.

## no-output/mlruns mutation proof

The protected-path diff against the pre-promotion target was empty for
`outputs`, `artifacts`, `mlruns`, `docs/preliminary_report`, dependency files,
and lockfiles. The audit commit adds only this promotion audit report.

## classification

L1A_FINAL_SIGNATURE_PACKET_PROMOTION_COMPLETE

## next-step recommendation

Push `codex-track-handoff-context` after the promotion audit commit. The next
substantive step is human signature-readiness review only. Do not prepare or
run an execution packet until the human signer supplies an exact target commit,
approved command bundle, numeric stop/spend limits, signable preflight estimate,
remote image digest, billing reconciliation authorization, post-run validation
authorization, output/artifact/mlruns mutation authorization, and an explicit
execution authorization statement.
