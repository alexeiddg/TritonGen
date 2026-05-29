# Artifact And Result Registry

## 1. Purpose

This registry is the citation-grade source for current artifact identities in the preliminary Cluster 1 + Cluster 2 technical handoff. Raw outputs remain in `outputs/`; this file references those artifacts, summarizes verified counts and schema facts, and records caveats. It does not copy raw rows and does not rewrite any output.

The registry exists to prevent filename, row-count, schema, provenance, and caveat drift. Later report-facing docs should cite this registry before making claims from current result artifacts.

## 2. Scope

The current preliminary scope is the 2^2 subset over grammar guidance and correctness feedback:

| Report condition | Code condition | Meaning |
| --- | --- | --- |
| None | `none` | Baseline/replay condition without grammar guidance or correctness-feedback repair. |
| G | `G` | Task-agnostic grammar-guided Cluster 1 condition. |
| C | `C` | Cluster 2 correctness-feedback condition without grammar. |
| G+C | `G+C` | Cluster 2 combined grammar plus correctness-feedback condition. |

Cluster 3 and the `P` factor are implemented locally through Phase 10. Phase
11 has one validated n=1 Modal P smoke row registered below, and Phase 12 has
one validated n=5 development-scale `G+P` template-grammar diagnostic artifact
registered below. Phase 12b attempted a bounded targeted F1 diagnostic, but
both authorized fixture attempts classified as `F0_BAD_SIGNATURE` remotely and
produced zero rows. Phase 12d reran the aligned launcher-compatible fixture and
registered one valid targeted branch diagnostic row proving remote
`F1_COMPILE` seed classification and P-loop dispatch. Phase 12e registered one
valid targeted branch diagnostic row proving initial `F2_NUMERIC_LARGE`
classification and C-loop dispatch under `G+C+P`. These artifacts validate
bounded plumbing/schema/provenance/branch coverage only. Phase 13 froze and
audited the diagnostic evidence matrix without adding result rows or output
artifacts. Phase 14a registered one validated P-only n=5 development matrix
cell for elementwise/fp32; all five rows terminated at `F0_PARSE`, with zero
`F1_COMPILE` seeds and zero P attempts. Phase 14b registered one validated
C+P n=5 development matrix cell for elementwise/fp32; all five rows terminated
at `F0_PARSE`, with zero `F1_COMPILE` seeds, zero P attempts, zero initial F2
rows, and zero C attempts. Phase 14c registered one validated `G+C+P` n=5
development matrix cell for elementwise/fp32 using the `template_upper_bound`
grammar variant; all five rows were clean successes, with zero `F1_COMPILE`
seeds, zero initial F2 rows, zero P attempts, and zero C attempts. Phase 14d
approved the existing Phase 12 `G+P` n=5 template-grammar development artifact
for reuse as the Phase 14 `G+P` matrix cell after comparability, schema,
content-hash, grammar-metadata, and boundary validation. Phase 14e froze the
four-cell n=5 development matrix as condition coverage only, using the Phase
14a P cell, Phase 14b C+P cell, Phase 14c G+C+P cell, and reused Phase 12 G+P
cell. The frozen matrix has 20 rows total, zero P attempts, and zero C fires.
Full 2^3 factorial results are not current results.
Template G
artifacts are diagnostic/reference
material only and are not the primary G condition for this handoff.

Only Section 3 artifacts are current authoritative inputs for the primary 2^2 analysis. Diagnostic template artifacts, including the current-pipeline template upper-bound G artifact, the current-pipeline template G+C artifact, and the old template-G 180/180 artifact, are listed separately in Section 9 and must not be substituted into the current primary table.

## 2A. Cluster 3 Planned Artifacts And Schema

Cluster 3 v1 row schema:

- Schema version: `CLUSTER3_RESULTS_SCHEMA_VERSION = 1`
- Implementation path: `cluster3/results/dataclass.py`
- Logger path: `cluster3/results/logger.py`
- No-P pair manifest: `cluster3/contracts/no_p_pair_manifest.json`

Cluster 3 Phase 11 validated smoke artifact:

| Artifact path | Condition | Scale | Row count | Schema | Status | Hash / sidecar | Caveats |
|---|---|---|---:|---|---|---|---|
| `outputs/cluster3/p_smoke_l4_n1.jsonl` | `P` | n=1 smoke | 1 | `CLUSTER3_RESULTS_SCHEMA_VERSION = 1` enforced by `Cluster3EvalRow` and `outputs/cluster3/p_smoke_l4_n1.jsonl.hashes.json` | generated / validated / smoke only / not paper-scale | JSONL SHA256 `361a2dd708b028aa96b785d4f0aaa802134ec4df7092b3371b51c7ab7698e32c`; sidecar SHA256 `b7ee6a807cc3258d470ab37ac51b7f99ac9b4e27c8240144234fe775fb619483` | Not development-scale; not paper-scale; no P-lift claim; no pass@k/functional lift claim; no full 2^3 factorial result; no performance/speedup/profiler claim; used only to validate Modal plumbing, row schema, logger sidecar, provenance, and P firing boundary. |

Cluster 3 Phase 12 validated development-scale template artifact, reused by
Phase 14d as the G+P n=5 matrix cell:

| Artifact path | Condition | Grammar/template mode | Scale | Kernel / dtype | Row count | Schema | Status | Hash / sidecar | P signal | Caveats |
|---|---|---|---|---|---:|---|---|---|---|---|
| `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` | `G+P` | CLI `--grammar-variant template_upper_bound`; `grammar_path=cluster1/grammar/triton_kernel.gbnf`; nested `generated_metadata.grammar_claim_scope=diagnostic_non_primary` | n=5 development-scale; reused as Phase 14 G+P matrix cell by Phase 14d decision | elementwise / fp32 | 5 | `CLUSTER3_RESULTS_SCHEMA_VERSION = 1` enforced by `Cluster3EvalRow` and `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl.hashes.json` | generated / validated / reused prior Phase 12 evidence for Phase 14 matrix / development-scale only / not paper-scale | JSONL SHA256 `9447d987655cba5aadb79d42d115f6baa989b1ea36ba7bf6023975d656e54423`; sidecar SHA256 `54f3d06c5749bf27b856f0ef79545f6dda1dbb3199a7665726952d59125efb68` | F1_COMPILE seeds `0`; `p_repair_attempted` rows `0`; P stop reasons: `p_not_applicable=5`; terminal failure codes: `None=5` | Development-scale only; reused prior Phase 12 artifact, not a fresh Phase 14d Modal run; diagnostic template route only; not paper-scale; not pass@k evidence; no P-lift claim; no correctness-improvement claim; no full 2^3 factorial result; no statistical claim; no performance/speedup/profiler claim; insufficient F1 signal, so not an F1-loop validation. |

Cluster 3 Phase 12b blocked targeted F1 diagnostic attempts:

| Artifact path | Fixture source | Condition | Scale | Row count | Remote seed classification | Status | Hash / sidecar | Caveats |
|---|---|---|---|---:|---|---|---|---|
| `outputs/cluster3/g_plus_p_f1_targeted_smoke_n1.jsonl` | `cluster3/tests/fixtures/f1_compile_kernels/bad_constexpr.py` | `G+P` | n=1 targeted smoke diagnostic | 0 | `F0_BAD_SIGNATURE` | blocked / zero-row / not valid F1 or P-loop evidence | JSONL SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; sidecar `outputs/cluster3/g_plus_p_f1_targeted_smoke_n1.jsonl.hashes.json`, SHA256 `33b0b976da99f2b14cff65f6734ef8f31986f294e45c82435b0d8f847ba0c3ef` | Not valid branch-coverage evidence; seed did not reach `F1_COMPILE`; P did not fire; not development-scale statistical evidence; not paper-scale; no P-lift/pass@k/performance claim. |
| `outputs/cluster3/g_plus_p_f1_targeted_smoke_n1_alt.jsonl` | `cluster3/tests/fixtures/f1_compile_kernels/type_error_in_pointer_arith.py` | `G+P` | n=1 targeted smoke diagnostic | 0 | `F0_BAD_SIGNATURE` | blocked / zero-row / not valid F1 or P-loop evidence | JSONL SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; sidecar `outputs/cluster3/g_plus_p_f1_targeted_smoke_n1_alt.jsonl.hashes.json`, SHA256 `33b0b976da99f2b14cff65f6734ef8f31986f294e45c82435b0d8f847ba0c3ef` | Not valid branch-coverage evidence; seed did not reach `F1_COMPILE`; P did not fire; not development-scale statistical evidence; not paper-scale; no P-lift/pass@k/performance claim. |

Cluster 3 Phase 12d validated targeted F1/P-loop branch diagnostic:

| Artifact path | Fixture source | Condition | Scale | Row count | Schema | Observed seed failure | P result | Terminal failure | Status | Hash / sidecar | Caveats |
|---|---|---|---|---:|---|---|---|---|---|---|---|
| `outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl` | `cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py` | `G+P` | n=1 targeted branch diagnostic | 1 | `CLUSTER3_RESULTS_SCHEMA_VERSION = 1` enforced by `Cluster3EvalRow` and `outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl.hashes.json` | `F1_COMPILE` | P fired; `p_repair_attempted=true`; stop reason `p_compile_repaired_then_success` | `None`; compile and functional success true after P attempt | generated / validated / branch diagnostic only / not paper-scale | JSONL SHA256 `dedfe81f40eb094b3983c4a16cd32ee1b88a832950922fd6b22b73a1928c929e`; sidecar SHA256 `33b0b976da99f2b14cff65f6734ef8f31986f294e45c82435b0d8f847ba0c3ef` | Branch-coverage diagnostic only; not n=5 statistical evidence; not n=20 paper-scale evidence; not pass@k evidence; no P-lift claim; no correctness-improvement claim; no performance/speedup/profiler claim. |

Cluster 3 Phase 12e validated targeted initial-F2/C-loop branch diagnostic:

| Artifact path | Fixture source | Condition | Scale | Row count | Schema | Observed initial failure | P result | C result | Terminal failure | Status | Hash / sidecar | Caveats |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| `outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl` | `cluster2/tests/fixtures/f2_corrupted_relu.py` | `G+C+P` | n=1 targeted branch diagnostic | 1 | `CLUSTER3_RESULTS_SCHEMA_VERSION = 1` enforced by `Cluster3EvalRow` and `outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl.hashes.json` | `F2_NUMERIC_LARGE` | P did not fire; `p_repair_attempted=false`; stop reason `p_not_applicable` | C fired; `c_loop_source=initial_f2`; `c_terminal_failure_code=None`; `c_terminal_level_reached=2` | `None`; compile and functional success true after C attempt | generated / validated / branch diagnostic only / not paper-scale | JSONL SHA256 `2d36f185652134f31e9999a00200ad78c19cff2557067840f6f735e519383e69`; sidecar SHA256 `e07225fb62f064a68643272c5cccb977ea8919bac30b9cc83d5c9d7c8f4e7fde` | Branch-coverage diagnostic only; not n=5 statistical evidence; not n=20 paper-scale evidence; not pass@k evidence; no P/C-lift claim; no correctness-improvement claim; no performance/speedup/profiler claim. |

Cluster 3 Phase 13 diagnostic evidence freeze:

| Report path | Evidence set audited | Row/schema/hash status | Boundary status | Go/no-go | Caveats |
|---|---|---|---|---|---|
| `audits/cluster3_phase13_diagnostic_evidence_freeze_report.md` | Phase 11 P smoke, Phase 12 G+P n=5 template development run, Phase 12d aligned F1/P-loop diagnostic, Phase 12e initial-F2/C-loop diagnostic | expected row counts `1/5/1/1`; all rows validate with `Cluster3EvalRow`; all four `.hashes.json` sidecars exist and validate with logger helpers | no private-eval or performance/profiler/timing matches in valid Cluster 3 JSONL artifacts | `HOLD_FOR_COMMIT_AND_PROVENANCE_FREEZE` before broader expansion | Evidence freeze only; no new rows; not paper-scale; not pass@k; no P/C-lift; no correctness-improvement claim; no performance/speedup/profiler claim. |

Cluster 3 Phase 14a validated P-only n=5 matrix cell:

| Artifact path | Condition | Scale | Kernel / dtype | Row count | Schema | Status | Hash / sidecar | Failure / P signal | Caveats |
|---|---|---|---|---:|---|---|---|---|---|
| `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl` | `P` | n=5 development matrix cell | elementwise / fp32 | 5 | `CLUSTER3_RESULTS_SCHEMA_VERSION = 1` enforced by `Cluster3EvalRow` and `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl.hashes.json` | generated / validated / one matrix cell only / not paper-scale | JSONL SHA256 `d9d92f6a809bf3786eefacc8a8ae20358fc92a1aa684cf3ffd5ea12763a693ea`; sidecar SHA256 `3928d54583e5d74aac38bd73fb1d43c8a577dc5c84471d719da065f6ca64aad7` | failure codes: `F0_PARSE=5`; `F1_COMPILE` seeds `0`; `p_repair_attempted` rows `0`; P stop reasons: `p_not_applicable=5`; C fired count `0` | One matrix cell only; development-scale only; insufficient F1/P-loop signal; not paper-scale; not pass@k evidence; no P-lift claim; no C-lift claim; no statistical evidence; no correctness-improvement claim; no performance/speedup/profiler/timing claim. |

Cluster 3 Phase 14b validated C+P n=5 matrix cell:

| Artifact path | Condition | Scale | Kernel / dtype | Row count | Schema | Status | Hash / sidecar | Failure / P / C signal | Caveats |
|---|---|---|---|---:|---|---|---|---|---|
| `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl` | `C+P` | n=5 development matrix cell | elementwise / fp32 | 5 | `CLUSTER3_RESULTS_SCHEMA_VERSION = 1` enforced by `Cluster3EvalRow` and `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl.hashes.json` | generated / validated / one matrix cell only / not paper-scale | JSONL SHA256 `7ce0606820a3de8735b163ea7cf8e34d1681ddac68fbab35f3ce4364d1c03930`; sidecar SHA256 `2199348868fe3ab292cb0bad9ad486d592c733f7c45e4567d3ae07237b86302c` | failure codes: `F0_PARSE=5`; initial failure codes: `F0_PARSE=5`; `F1_COMPILE` seeds `0`; initial F2 rows `0`; `p_repair_attempted` rows `0`; P stop reasons: `p_not_applicable=5`; C fired count `0`; C loop sources: `none=5`; C terminal failure-code counts: none | One matrix cell only; development-scale only; insufficient repair signal because no F1/P or F2/C path occurred; not paper-scale; not pass@k evidence; no P-lift claim; no C-lift claim; no statistical evidence; no correctness-improvement claim; no performance/speedup/profiler/timing claim. |

Cluster 3 Phase 14c validated G+C+P n=5 matrix cell:

| Artifact path | Condition | Scale | Kernel / dtype | Row count | Schema | Grammar metadata | Status | Hash / sidecar | Failure / P / C signal | Caveats |
|---|---|---|---|---:|---|---|---|---|---|---|
| `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl` | `G+C+P` | n=5 development matrix cell | elementwise / fp32 | 5 | `CLUSTER3_RESULTS_SCHEMA_VERSION = 1` enforced by `Cluster3EvalRow` and `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl.hashes.json` | `grammar_active=true` for all rows; nested `generated_metadata.grammar_variant=template_upper_bound`; nested `generated_metadata.grammar_claim_scope=diagnostic_non_primary` | generated / validated / one matrix cell only / not paper-scale | JSONL SHA256 `90985813219ea1dd461bdc7b06a4c8af0ad25aa730ed1f4564a5bf12784154c0`; sidecar SHA256 `e07225fb62f064a68643272c5cccb977ea8919bac30b9cc83d5c9d7c8f4e7fde` | failure codes: `None=5`; initial failure codes: `None=5`; `F1_COMPILE` seeds `0`; initial F2 rows `0`; `p_repair_attempted` rows `0`; P stop reasons: `p_not_applicable=5`; C fired count `0`; C loop sources: `none=5`; C terminal failure-code counts: none | One matrix cell only; development-scale only; template upper-bound grammar route is diagnostic/non-primary; insufficient repair signal because no F1/P or F2/C path occurred; not paper-scale; not pass@k evidence; no P-lift claim; no C-lift claim; no statistical evidence; no correctness-improvement claim; no performance/speedup/profiler/timing claim. |

Cluster 3 Phase 14d G+P reuse-vs-rerun decision:

| Reused artifact path | Matrix cell | Decision | Comparability status | Validation status | Caveats |
|---|---|---|---|---|---|
| `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` | `G+P` n=5 development matrix cell, elementwise / fp32 | Reuse approved; no fresh Phase 14d Modal run required | rows `5`; condition `G+P=5`; kernel_class `elementwise=5`; dtype `fp32=5`; `grammar_active=true=5`; nested `generated_metadata.grammar_variant=template_upper_bound=5`; nested `generated_metadata.grammar_claim_scope=diagnostic_non_primary=5`; failure codes `None=5` | `Cluster3EvalRow.from_dict` passed for all rows; content-hash sidecar validation passed; boundary scans had no private-eval or performance/profiler/timing matches; report `audits/cluster3_phase14d_g_plus_p_reuse_vs_rerun_decision.md` | Reused prior Phase 12 evidence, not a fresh Phase 14d run; development-scale only; diagnostic template route only; insufficient repair signal because `F1_COMPILE` seeds `0` and P attempts `0`; not paper-scale; not pass@k evidence; no P-lift claim; no C-lift claim; no statistical evidence; no correctness-improvement claim; no performance/speedup/profiler/timing claim. |

Cluster 3 Phase 14e four-cell n=5 development matrix freeze:

| Matrix cell | Artifact path | Rows | Failure / initial failure counts | Grammar metadata | Repair signal | Hash / sidecar | Freeze status | Caveats |
|---|---|---:|---|---|---|---|---|---|
| `P` | `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl` | 5 | failure `F0_PARSE=5`; initial `F0_PARSE=5` | `grammar_active=false=5` | `F1_COMPILE` seeds `0`; P attempts `0`; C fires `0`; P stop reasons `p_not_applicable=5` | JSONL SHA256 `d9d92f6a809bf3786eefacc8a8ae20358fc92a1aa684cf3ffd5ea12763a693ea`; sidecar SHA256 `3928d54583e5d74aac38bd73fb1d43c8a577dc5c84471d719da065f6ca64aad7` | Frozen by `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md` | Development-scale condition coverage only; insufficient F1/P signal; not paper-scale; not pass@k; no P/C-lift; no statistical, correctness-improvement, or performance claim. |
| `C+P` | `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl` | 5 | failure `F0_PARSE=5`; initial `F0_PARSE=5` | `grammar_active=false=5` | `F1_COMPILE` seeds `0`; initial F2 rows `0`; P attempts `0`; C fires `0`; P stop reasons `p_not_applicable=5`; C loop sources `none=5` | JSONL SHA256 `7ce0606820a3de8735b163ea7cf8e34d1681ddac68fbab35f3ce4364d1c03930`; sidecar SHA256 `2199348868fe3ab292cb0bad9ad486d592c733f7c45e4567d3ae07237b86302c` | Frozen by `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md` | Development-scale condition coverage only; insufficient repair signal; not paper-scale; not pass@k; no P/C-lift; no statistical, correctness-improvement, or performance claim. |
| `G+C+P` | `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl` | 5 | failure `None=5`; initial `None=5` | `grammar_active=true=5`; nested `template_upper_bound=5`; nested `diagnostic_non_primary=5` | `F1_COMPILE` seeds `0`; initial F2 rows `0`; P attempts `0`; C fires `0`; P stop reasons `p_not_applicable=5`; C loop sources `none=5` | JSONL SHA256 `90985813219ea1dd461bdc7b06a4c8af0ad25aa730ed1f4564a5bf12784154c0`; sidecar SHA256 `e07225fb62f064a68643272c5cccb977ea8919bac30b9cc83d5c9d7c8f4e7fde` | Frozen by `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md` | Development-scale condition coverage only; template upper-bound route is diagnostic/non-primary; insufficient repair signal; not paper-scale; not pass@k; no P/C-lift; no statistical, correctness-improvement, or performance claim. |
| `G+P` | `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` | 5 | failure `None=5`; initial `None=5` | `grammar_active=true=5`; nested `template_upper_bound=5`; nested `diagnostic_non_primary=5` | `F1_COMPILE` seeds `0`; P attempts `0`; C fires `0`; P stop reasons `p_not_applicable=5` | JSONL SHA256 `9447d987655cba5aadb79d42d115f6baa989b1ea36ba7bf6023975d656e54423`; sidecar SHA256 `54f3d06c5749bf27b856f0ef79545f6dda1dbb3199a7665726952d59125efb68` | Frozen by `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md`; reused prior Phase 12 evidence approved by Phase 14d | Development-scale condition coverage only; reused prior Phase 12 artifact, not a fresh Phase 14 run; template upper-bound route is diagnostic/non-primary; insufficient F1/P signal; not paper-scale; not pass@k; no P/C-lift; no statistical, correctness-improvement, or performance claim. |

Archived blocked Phase 11 attempt:

| Artifact path | Status | Row count | Hash / sidecar | Caveats |
|---|---|---:|---|---|
| `outputs/cluster3/blocked/p_smoke_l4_n1.blocked_attempt_001.jsonl` | archived zero-byte placeholder from the initial Modal hydration failure | 0 | SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; archived sidecar `outputs/cluster3/blocked/p_smoke_l4_n1.blocked_attempt_001.hashes.json`, SHA256 `4d54798cc47072e4c04278d63ff33b0a01b8a3e1dc1abcf3527834b43b607aca` | Not valid smoke evidence; not schema-validated row evidence; preserved only as blocked-run provenance for `MISSING_MODAL_RUN_CONTEXT`. |

Legacy Cluster 3 planned development output identifiers retained for docs-lock
compatibility:

| Planned path | Intended gate | Status |
|---|---|---|
| `outputs/cluster3/p_dev_l4_n5.jsonl` | Legacy P n=5 development identifier from pre-matrix planning | planned / not generated yet |
| `outputs/cluster3/g_plus_p_dev_l4_n5.jsonl` | Legacy G+P n=5 development identifier from pre-matrix planning | planned / not generated yet |
| `outputs/cluster3/c_plus_p_dev_l4_n5.jsonl` | Legacy C+P n=5 development identifier from pre-matrix planning | planned / not generated yet |
| `outputs/cluster3/g_plus_c_plus_p_dev_l4_n5.jsonl` | Legacy G+C+P n=5 development identifier from pre-matrix planning | planned / not generated yet |

Remaining planned future Cluster 3 matrix output paths:

| Planned path | Intended gate | Status |
|---|---|---|
| `outputs/cluster3/matrix_n5_g_plus_p_elementwise_fp32.jsonl` | Optional fresh G+P n=5 matrix rerun only if Phase 14d reuse approval is later overturned | not generated; not currently recommended because Phase 14d approved reuse of `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` |

Caveats:

- One Phase 11 n=1 P smoke row is registered. It is smoke-only evidence for
  plumbing/schema/provenance and P boundary behavior, not result-scale evidence.
- One Phase 12 n=5 `G+P` template-grammar development artifact is registered.
  It is development-scale diagnostic evidence for bounded Modal plumbing,
  schema, provenance, and template selection only. It observed zero
  `F1_COMPILE` seeds and zero P repair attempts, so it is insufficient F1-loop
  signal and must not be cited as evidence that P helped.
- Phase 12b targeted F1 diagnostic attempts are registered only as blocked
  zero-row evidence. Both existing F1 fixture sources classified remotely as
  `F0_BAD_SIGNATURE`, so no valid row, F1 seed, or P-loop evidence was produced.
- Phase 12d registered one targeted branch diagnostic row from the aligned
  fixture. It proves the remote `F1_COMPILE` -> P-loop branch fired for that
  fixture, but it is not statistical, paper-scale, pass@k, P-lift, or
  performance evidence.
- Phase 12e registered one targeted branch diagnostic row from the existing
  Cluster 2 wrong-output ReLU fixture. It proves the remote initial `F2` ->
  C-loop branch fired under `G+C+P` while P remained inactive, but it is not
  statistical, paper-scale, pass@k, P/C-lift, or performance evidence.
- Phase 13 froze and audited the registered diagnostic evidence matrix. It
  added no output rows and recommends holding broader expansion until the
  current prior-phase dirty tree is committed or otherwise provenance-frozen.
- Phase 14a registered one P-only n=5 development matrix cell for
  elementwise/fp32. All five rows were `F0_PARSE`, with zero `F1_COMPILE`
  seeds and zero P attempts. This validates bounded P-only matrix-cell
  plumbing and P boundary behavior, but it is insufficient F1/P-loop signal and
  not evidence that P helped.
- Phase 14b registered one C+P n=5 development matrix cell for
  elementwise/fp32. All five rows were `F0_PARSE`, with zero `F1_COMPILE`
  seeds, zero P attempts, zero initial F2 rows, and zero C attempts. This
  validates bounded C+P matrix-cell plumbing and repair boundary behavior, but
  it is insufficient repair signal and not evidence that P or C helped.
- Phase 14c registered one G+C+P n=5 development matrix cell for
  elementwise/fp32 using `template_upper_bound` grammar metadata with
  `diagnostic_non_primary` claim scope. All five rows were clean successes,
  with zero `F1_COMPILE` seeds, zero initial F2 rows, zero P attempts, and zero
  C attempts. This validates bounded G+C+P matrix-cell plumbing and grammar
  metadata propagation, but it is insufficient repair signal and not evidence
  that G, P, or C helped.
- Phase 14d approved reuse of the existing Phase 12 `G+P` n=5 template-grammar
  development artifact as the Phase 14 G+P matrix cell. That reuse decision is
  based on matching row count, condition, kernel class, dtype, schema,
  grammar-active status, nested grammar metadata, content-hash validation, and
  boundary scans. It is reused prior Phase 12 evidence, not a fresh Phase 14d
  Modal run, and remains insufficient repair signal because it has zero
  `F1_COMPILE` seeds and zero P attempts.
- Phase 14e froze the four-cell non-paper-scale n=5 development matrix:
  P, C+P, G+C+P, and reused G+P. All four cells have five rows each and
  validate against `Cluster3EvalRow`; all hash sidecars validate; boundary
  scans found no private-eval or performance/profiler/timing matches. The
  matrix has zero P attempts and zero C fires, so it is condition-coverage
  evidence only and remains insufficient repair-signal evidence.
- The initial Phase 11 attempt created a zero-byte placeholder and sidecar
  before Modal runner hydration failed. Those files were archived under
  `outputs/cluster3/blocked/` and must not be cited as generated smoke evidence.
- No Phase 12 Cluster 3 rows are registered as paper-scale, pass@k/lift, or
  performance evidence.
- The Phase 12d targeted branch row is likewise not registered as paper-scale,
  pass@k/lift, or performance evidence.
- The Phase 12e targeted branch row is likewise not registered as paper-scale,
  pass@k/lift, or performance evidence.
- The Phase 13 freeze report is not a result artifact and does not add
  paper-scale, pass@k/lift, or performance evidence.
- The Phase 14a P-only n=5 artifact is one development matrix cell only and
  does not add paper-scale, pass@k/lift, statistical, or performance evidence.
- The Phase 14b C+P n=5 artifact is one development matrix cell only and
  does not add paper-scale, pass@k/lift, statistical, or performance evidence.
- The Phase 14c G+C+P n=5 artifact is one development matrix cell only and
  does not add paper-scale, pass@k/lift, statistical, or performance evidence.
- The Phase 14d G+P reuse decision completes the optional non-paper-scale n=5
  matrix cell mapping by reusing the validated Phase 12 G+P artifact. It does
  not add new output rows and does not add paper-scale, pass@k/lift,
  statistical, correctness-improvement, or performance evidence.
- The Phase 14e freeze report does not add output rows. It freezes the
  four-cell n=5 development matrix as development-scale condition coverage
  only and does not add paper-scale, pass@k/lift, statistical,
  correctness-improvement, or performance evidence.
- No paper-scale P artifacts exist in this registry.
- No performance/speedup/profiler artifacts exist for Cluster 3.
- Planned future paths are identifiers for future authorized gates, not evidence of generated output.

## 3. Current Authoritative Artifacts

| Report condition | Code condition | Cluster/source | Artifact path | Rows | Intended rows | Role | Current status | Caveats |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| None | `none` | Cluster 1 replay | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | 180 | Baseline replay/control | Authoritative current raw artifact | Compile-only; flat legacy schema; no `condition`; no `generated_metadata`; no model/tokenizer/modal/package revision provenance fields. |
| G | `G` | Cluster 1 | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | 180 | Task-agnostic grammar condition | Authoritative with coverage caveat | Missing three matmul rows; compile-only; no `condition`; no `generated_metadata`; `modal_image_sha` is `unknown`. |
| C | `C` | Cluster 2 | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | 180 | Correctness-feedback condition | Authoritative current raw artifact | No grammar; all rows are `F0_PARSE`; `compile_success` is absent and must be normalized from `failure_code` by the analyzer. |
| G+C | `G+C` | Cluster 2 | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | 180 | Combined grammar plus correctness-feedback condition | Authoritative with coverage caveat | Missing the same three matmul rows as G; includes five `F3_EVAL_PIPELINE` rows governed by analyzer policy. |
| 2^2 analyzer | N/A | `shared.analysis` | `outputs/analysis/factorial_2x2_preliminary.json` | 714 loaded rows | N/A | Preliminary analyzer output | Reportable under explicit scale-tier annotation, with caveats | Valid JSON with `metadata.reportable=true`, `metadata.scale_tiers=["paper"]`, `metadata.raw_scale_tiers_before_annotation=["unspecified"]`, `metadata.scale_tier_source="analysis_cli_annotation"`, and `metadata.requested_scale_tier="paper"`; P cells are not populated. |

## 4. Verified Artifact Summaries

The following summaries were recomputed from the actual files with `.venv/bin/python` during Phase 2.

### None: `outputs/cluster1/baseline_repaired_l4_n20.jsonl`

| Field | Verified value |
| --- | --- |
| Exists | yes |
| Valid JSONL | yes |
| Valid rows | 180 |
| Bad JSON lines | 0 |
| Condition values | absent/null on 180 rows; condition is inferred as `none` from role and path |
| `generated_metadata` rows | 0 |
| `kernel_class` distribution | elementwise 60; reduction 60; matmul 60 |
| `dtype` distribution | fp32 60; fp16 60; bf16 60 |
| `failure_code` distribution | null 180 |
| `compile_success` distribution | false 180 |
| `functional_success` distribution | null 180 |
| Grammar metadata | `grammar_active=false` on 180 rows; grammar variant/validity fields absent or null |
| Provenance presence | `model_revision`, `tokenizer_revision`, `modal_image_sha`, `transformers_version`, `tokenizers_version`, `xgrammar_version`, and `grammar_sha` missing/null on 180 rows |
| Report readiness | Authoritative baseline replay artifact with legacy schema/provenance caveats |

### G: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`

| Field | Verified value |
| --- | --- |
| Exists | yes |
| Valid JSONL | yes |
| Valid rows | 177 |
| Bad JSON lines | 0 |
| Condition values | absent/null on 177 rows; condition is inferred as `G` from role and path |
| `generated_metadata` rows | 0 |
| `kernel_class` distribution | elementwise 60; reduction 60; matmul 57 |
| `dtype` distribution | fp32 59; fp16 60; bf16 58 |
| `failure_code` distribution | null 3; `F1_RUNTIME` 152; `F1_COMPILE` 9; `F0_PARSE` 13 |
| `compile_success` distribution | true 3; false 174 |
| `functional_success` distribution | null 177 |
| Grammar metadata | `grammar_active=true` 177; `grammar_variant=task_agnostic` 177; `grammar_valid=true` 49 and false 128; `gbnf_parse_valid=true` 105 and false 72; `semantic_valid=true` 49 and false 128 |
| Rejection metadata | null 49; `semantic_validator` 56; `gbnf_parse` 72 |
| Stop reason | `eos_token` 105; `max_new_tokens` 72 |
| Provenance presence | model/tokenizer revisions present 177; package versions present 177; `grammar_sha` present 177; `modal_image_sha=unknown` 177 |
| Report readiness | Authoritative G artifact with explicit 177/180 coverage and compile-only caveats |

### C: `outputs/cluster2/c_paper_n20_l4.jsonl`

| Field | Verified value |
| --- | --- |
| Exists | yes |
| Valid JSONL | yes |
| Valid rows | 180 |
| Bad JSON lines | 0 |
| Condition values | `C` 180 |
| `generated_metadata` rows | 180 |
| `kernel_class` distribution | elementwise 60; reduction 60; matmul 60 |
| `dtype` distribution | fp32 60; fp16 60; bf16 60 |
| `failure_code` distribution | `F0_PARSE` 180 |
| `compile_success` distribution | absent/null 180 |
| `functional_success` distribution | false 180 |
| Grammar metadata | no active grammar; grammar variant/path/SHA and grammar validity fields are null/absent for all rows |
| Stop reason | `eos_token` 175; `max_new_tokens` 5 |
| Provenance presence | model/tokenizer revisions present 180; `modal_image_sha=im-tU3VQyAbFvrusOxtlwspCN` 180; package versions present 180; `grammar_sha` missing/null 180 |
| Replay metadata | nested `replay_pair_id`, replay seeds, prompt hash, temperature, and token budget present under `generated_metadata` |
| Report readiness | Authoritative C artifact; analyzer must derive compile success from `failure_code` because the raw field is absent |

### G+C: `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`

| Field | Verified value |
| --- | --- |
| Exists | yes |
| Valid JSONL | yes |
| Valid rows | 177 |
| Bad JSON lines | 0 |
| Condition values | `G+C` 177 |
| `generated_metadata` rows | 177 |
| `kernel_class` distribution | elementwise 60; reduction 60; matmul 57 |
| `dtype` distribution | fp32 59; fp16 60; bf16 58 |
| `failure_code` distribution | `F2_NUMERIC_NAN` 4; `F1_RUNTIME` 146; `F1_COMPILE` 10; `F0_PARSE` 12; `F3_EVAL_PIPELINE` 5 |
| `compile_success` distribution | true 4; false 173 |
| `functional_success` distribution | false 177 |
| Grammar metadata | `grammar_active=true` 177; `grammar_variant=task_agnostic` 177; `grammar_valid=true` 52 and false 125; `gbnf_parse_valid=true` 100 and false 77; `semantic_valid=true` 52 and false 125 |
| Rejection metadata | null 52; `semantic_validator` 48; `gbnf_parse` 77 |
| Stop reason | `eos_token` 100; `max_new_tokens` 77 |
| Provenance presence | model/tokenizer revisions present 177; `modal_image_sha=im-tU3VQyAbFvrusOxtlwspCN` 177; package versions present 177; `grammar_sha` present 177 |
| Replay metadata | nested `replay_pair_id`, replay seeds, prompt hash, temperature, and token budget present under `generated_metadata` |
| Report readiness | Authoritative G+C artifact with explicit 177/180 coverage caveat and F3 policy caveat |

## 5. Artifact Schema Summary

| Condition | Schema shape | `compile_success` source | `functional_success` source | `failure_code` source | Grammar metadata | Provenance metadata |
| --- | --- | --- | --- | --- | --- | --- |
| None | Flat Cluster 1 legacy rows; no `generated_metadata` | Top-level field, all false | Absent/null; analyzer normalizes Cluster 1 functional success as false/unproven | Absent/null | Top-level `grammar_active=false`; no grammar variant/SHA | Legacy only; revision/package/image fields missing |
| G | Flat Cluster 1 task-agnostic rows; no `generated_metadata` | Top-level field | Absent/null; analyzer normalizes Cluster 1 functional success as false/unproven | Top-level `failure_code` where present | Top-level task-agnostic grammar fields, grammar SHA, parser/semantic validity, rejection layer | Top-level model/tokenizer/package/grammar fields present; `modal_image_sha=unknown` |
| C | Cluster 2 generated rows with nested `generated_metadata` | Absent in raw rows; analyzer derives false from `F0_PARSE` | Top-level field, all false | Top-level `failure_code` and trace summary | No active grammar; null grammar metadata | Nested model/tokenizer/modal/package/replay provenance present |
| G+C | Cluster 2 generated rows with nested `generated_metadata` | Top-level field; F3 policy applies | Top-level field, all false | Top-level `failure_code` and trace summary | Top-level and nested task-agnostic grammar metadata present | Nested model/tokenizer/modal/package/grammar/replay provenance present |

## 6. Coverage By Kernel And Dtype

| Cell | None rows | G rows | C rows | G+C rows |
| --- | ---: | ---: | ---: | ---: |
| elementwise/fp32 | 20 | 20 | 20 | 20 |
| elementwise/fp16 | 20 | 20 | 20 | 20 |
| elementwise/bf16 | 20 | 20 | 20 | 20 |
| reduction/fp32 | 20 | 20 | 20 | 20 |
| reduction/fp16 | 20 | 20 | 20 | 20 |
| reduction/bf16 | 20 | 20 | 20 | 20 |
| matmul/fp32 | 20 | 19 | 20 | 19 |
| matmul/fp16 | 20 | 20 | 20 | 20 |
| matmul/bf16 | 20 | 18 | 20 | 18 |

## 7. Known Missing Rows And Coverage Caveats

G and G+C are 177/180 artifacts, not complete 180/180 artifacts.

Known missing rows:

| Kernel class | Dtype | Missing seed |
| --- | --- | ---: |
| matmul | fp32 | 5 |
| matmul | bf16 | 0 |
| matmul | bf16 | 18 |

These rows must be handled explicitly in paired analysis. Current analyzer metadata records the policy as `COVERAGE_WARNING_SKIP_MISSING`. Do not silently claim 180/180 G or G+C coverage, do not impute missing rows, and do not use old template-G artifacts to fill the task-agnostic G gap.

## 8. Analyzer Output Status

| Field | Verified value |
| --- | --- |
| Path | `outputs/analysis/factorial_2x2_preliminary.json` |
| Exists | yes |
| Valid JSON | yes |
| Top-level keys | `cell_summaries`, `condition_rates`, `diagnostics`, `factorial_model`, `metadata`, `paired_comparisons`, `paper_tables` |
| Reportable value | top-level field absent; `metadata.reportable=true` |
| Loaded rows | `diagnostics.rows_loaded=714`; `factorial_model.n_observations=714` |
| Scope | `metadata.scope_kind=temporary_2^2_subset`; populated cells are `none`, `G`, `C`, and `G+C`; P-containing cells are missing/deferred |
| Scale-tier metadata | `metadata.scale_tiers=["paper"]`; `metadata.raw_scale_tiers_before_annotation=["unspecified"]`; `metadata.scale_tier_source="analysis_cli_annotation"`; `metadata.requested_scale_tier="paper"` |
| Raw scale-tier state | Current raw none/G/C/G+C artifacts do not serialize row-level `scale_tier`; the analyzer output was annotated at analysis time and raw artifacts were not rewritten |
| F3 policy | `F3_EVAL_PIPELINE` rows are excluded from compile-success rate calculations and treated as compile false in matched-pair analysis when independent compile-pass evidence is absent |
| Current citation status | Reportable current 2^2 analyzer artifact under the recorded `analysis_cli_annotation`; not a full 2^3/P result and still subject to the row-count, F3, single-class model, and provenance caveats below |

The analyzer emits four paired comparisons in the current JSON: two primary functional comparisons (`C vs none`, `G+C vs G`) and two secondary compile diagnostics (`G vs none`, `G+C vs C`). The functional model is not fit because the functional outcome has a single class; its additive interaction field is 0.0, but this must remain caveated alongside the 177/180 G/G+C coverage, five G+C `F3_EVAL_PIPELINE` rows, absent P cells, and provenance limitations.

## 9. Legacy And Non-Authoritative Artifacts

This registry does not exhaustively inventory every historical output. Known non-authoritative categories:

| Category | Current policy |
| --- | --- |
| n=5 artifacts | Development/legacy evidence only. Do not use for current preliminary paper-scale claims. |
| Template-G artifacts | Diagnostic/reference material only. Do not treat as the primary G condition. Current and legacy template artifacts are non-primary unless explicitly registered with caveats below. |
| Old smoke outputs | Smoke evidence only, not report-scale artifacts. |
| Failed or partial older runs | Historical evidence unless explicitly promoted into this registry with current caveats. |
| Old analyzer-missing reports | Superseded by the presence of `outputs/analysis/factorial_2x2_preliminary.json`, but useful as historical evidence. |

### Current Template Upper-Bound G Diagnostic Artifact

`outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` is registered as a current-pipeline Cluster 1 diagnostic artifact only. It is a task-encoded `template_upper_bound` grammar reference, labeled `G_template` / template upper-bound G for diagnostics. It is not primary G and is not part of the current primary 2^2 analyzer.

| Field | Current registry classification |
| --- | --- |
| Artifact path | `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` |
| Cluster 2 frozen replay artifact ID | `g_template_upper_bound_current_pipeline_n20_l4` |
| Sidecar | `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl.meta.json` |
| Role | Diagnostic template upper-bound G / task-encoded grammar ceiling |
| Condition label | `G_template` / template upper-bound G; raw validator condition `G` with `grammar_variant=template_upper_bound` |
| Cluster | 1 |
| Evaluation surface | Compile-only / Level 1 launch acceptance; no Level 2 correctness |
| Primary analysis | No |
| Diagnostic analysis | Yes |
| Cluster 2 replay registration | Registered in `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` with `coverage_policy=EXACT_COVERAGE`, `scale_tier=paper`, `diagnostic_only=true`, and `primary_analysis=false`; selected only for the explicit `template_upper_bound` diagnostic replay route |
| Rows | 180 |
| Intended rows | 180 |
| By kernel/dtype | 20 rows in each elementwise, reduction, and matmul by fp32, fp16, and bf16 cell |
| Compile result | 180/180 `compile_success=true` (100.0%) |
| Grammar funnel | `gbnf_parse_valid=true` 180/180; `semantic_valid=true` 60/180; `grammar_valid=true` 60/180 |
| Rejection/stop metadata | `rejection_layer=null` 60; `semantic_validator` 120; `stop_reason=eos_token` 180 |
| Failure/error metadata | `failure_code=null` 180; `compile_error_type=null` 180 |
| Metadata gate status | PASS for basic Cluster 1 validator, `--require-generation-metadata`, and `--grammar-variant template_upper_bound --require-generation-metadata` |
| Provenance | `model_id=Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`; model/tokenizer revision `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`; `grammar_path=cluster1/grammar/triton_kernel.gbnf`; grammar SHA `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82`; `modal_image_sha=im-tU3VQyAbFvrusOxtlwspCN`; `modal_image_provenance_sha256=82fb2024879bf2db36d75995b0704ade1a9c32dc2d3d3aff6207332995dc7535`; transformers 4.47.1, tokenizers 0.21.1, xgrammar 0.1.33 |
| Scale/token caveat | Sidecar records `scale_tier=paper`, `max_new_tokens=2048`, `condition=G`, and `overwrite=false`; rows remain flat Cluster 1 rows and do not serialize row-level `condition`, `scale_tier`, `base_seed`, `sample_index`, or `max_new_tokens` |
| Missing-row policy | Must not be used to fill the three missing task-agnostic G rows |
| Pairing status | Must not be paired with current task-agnostic G+C |
| Diagnostic-comparison status | Matching current-pipeline template G+C diagnostic artifact exists at `outputs/cluster2/template_g_plus_c_paper_n20_l4.jsonl`; comparison is diagnostic-only and outside the primary analyzer |
| Report placement | Optional diagnostic section or appendix only; never a primary results table cell |

Valid claim: the current-pipeline template upper-bound G diagnostic produced 180/180 compile-success rows under Cluster 1 compile-only validation and passed the current Cluster 1 generation-metadata gate. Invalid claims: primary G evidence, task-agnostic G evidence, Level 2 correctness, replacement for missing task-agnostic rows, current primary analyzer input, or treating this G artifact alone as template G+C evidence.

### Current Template G+C Diagnostic Artifact

`outputs/cluster2/template_g_plus_c_paper_n20_l4.jsonl` is registered as a current-pipeline Cluster 2 diagnostic artifact only. It is the correctness-feedback analogue of the current template upper-bound G replay source. It is not a primary G+C condition and is not part of the current primary 2^2 analyzer.

| Field | Current registry classification |
| --- | --- |
| Artifact ID | `g_plus_c_template_upper_bound_current_pipeline_n20_l4` |
| Artifact path | `outputs/cluster2/template_g_plus_c_paper_n20_l4.jsonl` |
| Role | Diagnostic template G+C functional ceiling / task-encoded grammar plus correctness-feedback diagnostic |
| Condition label | `G+C` with `grammar_variant=template_upper_bound` |
| Source cluster | 2 |
| Replay source | `g_template_upper_bound_current_pipeline_n20_l4` |
| Replay caveat | Paired against the diagnostic-only template G replay artifact registered with `diagnostic_only=true` and `primary_analysis=false` |
| Primary analysis | No |
| Diagnostic analysis | Yes |
| Rows | 180 |
| Intended rows | 180 |
| By kernel/dtype | 20 rows in each elementwise, reduction, and matmul by fp32, fp16, and bf16 cell |
| Compile result | 180/180 `compile_success=true` (100.00%) |
| Functional result | 96/180 `functional_success=true` (53.33%) |
| Failure-code distribution | `failure_code=null` 96; `F2_NUMERIC_NAN` 60; `F2_NUMERIC_LARGE` 24 |
| Repair-loop behavior | 84 rows reached F2, all exhausted terminal attempt 5; 0 F2 rows repaired to functional success; 0 `F3_EVAL_PIPELINE` rows |
| Grammar metadata | `grammar_active=true` 180/180; `grammar_variant=template_upper_bound` 180/180; grammar SHA `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82` 180/180 |
| Provenance | `model_id=Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`; model/tokenizer revision `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`; `modal_image_sha=im-tU3VQyAbFvrusOxtlwspCN`; `modal_image_provenance_sha256=82fb2024879bf2db36d75995b0704ade1a9c32dc2d3d3aff6207332995dc7535`; transformers 4.47.1, tokenizers 0.21.1, xgrammar 0.1.33 |
| Scale/token caveat | Launched with `--scale-tier paper` and `--max-new-tokens 2048`; raw rows do not serialize row-level `scale_tier` |
| Validation status | JSONL integrity and strict Cluster 2 validator/schema pytest target passed |
| Primary analyzer status | Must not be added to `outputs/analysis/factorial_2x2_preliminary.json` or any primary analyzer comparison |
| Report placement | Optional diagnostic section or appendix only; never a primary results table cell |

Valid claim: the current-pipeline template G+C diagnostic produced 180 Cluster 2 Level 0/1/2 rows paired against the current template G replay source, with 180/180 compile success and 96/180 functional success under the diagnostic template route. Invalid claims: primary G+C evidence, task-agnostic G+C evidence, replacement for current primary artifacts, or primary analyzer input.

### Legacy Template-G Diagnostic Artifact

`outputs/cluster1/final_g_l4_n20.jsonl` is preserved as legacy diagnostic evidence only. It is not a current authoritative input and is not part of the primary 2^2 analyzer.

| Field | Current registry classification |
| --- | --- |
| Artifact path | `outputs/cluster1/final_g_l4_n20.jsonl` |
| Sidecar | `outputs/cluster1/final_g_l4_n20.jsonl.meta.json` |
| Role | Legacy diagnostic / `template_upper_bound` / compile-only reference |
| Rows | 180 |
| Legacy compile result | 180/180 rows have `compile_success=true` under legacy Cluster 1 validation |
| Current metadata status | Fails the current paper-scale generation metadata gate; rows lack current split grammar validation fields, grammar provenance, model/tokenizer revisions, Modal image/provenance, package versions, stop reason, and row-level `scale_tier` |
| Current primary status | Not primary G; not task-agnostic G; not Level 2 correctness evidence; not a current 2^2 analyzer input |
| Pairing status | Must not be paired with current task-agnostic G+C |
| Missing-row policy | Must not be used to fill the three missing task-agnostic G rows |

Valid claim: the legacy template grammar run produced 180/180 compile-success rows over the old Cluster 1 n=20 grid. Invalid claims: current primary G evidence, task-agnostic G evidence, current G+C pairing evidence, Level 2 functional correctness, current paper-scale metadata compliance, or current primary analyzer evidence.

## 10. Rules For Adding Future Artifacts

- Every new artifact must be registered here with path, condition, source cluster, row count, intended row count, schema shape, provenance fields, caveats, and role.
- Every paper-scale artifact must have smoke/dev/audit provenance before it is cited.
- No artifact can be cited in report-facing docs before it is registered here.
- No output artifact should be manually rewritten to match documentation.
- The registry must be updated in the same commit or review unit as report-facing docs that cite a new artifact.
- Missing rows must be recorded as missing rows, not silently imputed or backfilled from legacy artifacts.
- Analyzer outputs must preserve their own `reportable` status and metadata caveats.
- Future paper-scale artifacts must serialize `scale_tier` in rows and in this registry. Analyzer manifests or invocation annotations may fill missing legacy row tiers only when this registry or an analysis policy authorizes it.
- Analyzer reportability must reject conflicts between explicit raw row `scale_tier`, registry/manifest scale tier, and invocation annotation.

## 11. Traceability Pointers

| Claim or artifact | Primary path | Supporting paths |
| --- | --- | --- |
| Current artifact identities and caveats | `docs/05_artifacts_and_results_registry.md` | `audits/repository_documentation_methodology_readiness_audit.md` |
| None raw artifact | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | `outputs/cluster1/baseline_repaired_l4_n20_summary.md` |
| G raw artifact | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | `audits/task_agnostic_g_aligned_pipeline_n20_l4_report.md`; `audits/task_agnostic_g_n20_missing_rows_and_token_exhaustion_rca.md` |
| Current template upper-bound G diagnostic artifact | `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` | `audits/template_upper_bound_g_current_pipeline_n20_l4_run_report.md`; `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl.meta.json` |
| Current template G+C diagnostic artifact | `outputs/cluster2/template_g_plus_c_paper_n20_l4.jsonl` | `audits/template_g_plus_c_paper_n20_l4_run_report.md`; `audits/template_g_plus_c_manifest_alignment_report.md`; `audits/template_g_plus_c_smoke_n1_report.md` |
| Legacy template-G diagnostic artifact | `outputs/cluster1/final_g_l4_n20.jsonl` | `audits/template_g_180_legacy_compatibility_audit.md`; `outputs/cluster1/final_g_l4_n20.jsonl.meta.json` |
| C raw artifact | `outputs/cluster2/c_paper_n20_l4.jsonl` | `audits/cluster2_c_paper_n20_l4_report.md` |
| G+C raw artifact | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | `audits/cluster2_g_plus_c_paper_n20_l4_run_report.md`; `audits/cluster2_g_plus_c_paper_n20_l4_report.md` |
| Analyzer output | `outputs/analysis/factorial_2x2_preliminary.json` | `shared/analysis/factorial.py`; `shared/tests/test_factorial_analysis.py`; `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md`; `audits/analyzer_pre_output_verification_audit.md` |
| Cluster 1 methodology semantics | Future `docs/02_methodology_cluster1.md` | `cluster1/grammar/triton_kernel_agnostic.gbnf`; `cluster1/grammar/triton_kernel_validator.py`; `cluster1/tests/` |
| Cluster 2 methodology semantics | Future `docs/03_methodology_cluster2.md` | `cluster2/experiments/run_cluster2_modal.py`; `cluster2/feedback/`; `cluster2/replay/`; `cluster2/tests/` |
| Evaluation and analyzer semantics | Future `docs/06_failure_taxonomy_and_eval_ladder.md`; future `docs/07_analysis_and_statistics.md` | `shared/eval/`; `shared/analysis/factorial.py`; `shared/tests/` |
