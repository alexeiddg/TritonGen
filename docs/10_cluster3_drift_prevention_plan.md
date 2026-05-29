# Cluster 3 Drift-Prevention Plan

## Opening Note

Cluster 3 and the `P` factor are deferred. This document does not claim Cluster 3 results, does not claim `P` results, and does not authorize Modal runs.

This document defines preconditions and drift-prevention rules before implementation. It is guardrails-first, not an implementation specification. Any future Cluster 3 implementation must update this document or create a formal implementation plan before code is written.

The reviewed v1 successor plan now exists at
`docs/cluster3_implementation_specification.md`. That specification authorizes
starting Phase 0 implementation only for bounded compile-error repair over
`F1_COMPILE`; it does not claim P results, profiler/speedup behavior, or
paper-scale readiness.

## 1. Purpose

Cluster 3 will eventually extend the factor design with `P`, a performance-oriented control factor. Current docs and contracts describe `P` as deferred; they do not define reportable `P` semantics or results.

The goal of this document is to prevent the methodology drift seen while Cluster 1 and Cluster 2 were being reconstructed. Cluster 3 must inherit the current discipline around definitions, artifacts, schemas, failure boundaries, Modal provenance, analyzer reportability, and documentation alignment.

Primary sources:

- `docs/00_project_map.md`
- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`
- `docs/09_preliminary_report_outline.md`
- `.contracts/research/research_scope.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/scale_policy.md`

## 2. Lessons From Cluster 1 And Cluster 2

Cluster 3 must inherit these lessons:

- Definitions must be locked before code.
- Artifact identities must be registered before paper-scale or report-facing runs.
- Result schema must be aligned with analyzer behavior before Modal runs.
- Result schema and registry entries must carry `scale_tier` before paper-scale runs.
- Failure taxonomy must define what each control is allowed to observe.
- Modal provenance must be mandatory for generated/evaluated rows.
- Durable row writing is required for long remote runs.
- Smoke, development, and audit gates must precede paper-scale execution.
- Docs and contracts must be updated in the same workflow as code that changes report-facing behavior.
- Analyzer reportability must be explicit; inspectable JSON is not automatically an official result.

The current 2^2 handoff exists because earlier code, docs, contracts, artifacts, and analyzer semantics drifted apart. Cluster 3 must not repeat that pattern.

## 3. Source-Of-Truth Requirements For Cluster 3

Before Cluster 3 becomes report-facing, it needs an explicit source stack:

1. Formal Cluster 3 contract or `.contracts/research/research_scope.md` update.
2. This Cluster 3 drift-prevention plan or a successor Cluster 3 implementation plan.
3. `docs/05_artifacts_and_results_registry.md` entries for any new artifacts.
4. Current Cluster 3 code and tests.
5. Audit reports that verify implementation, artifact, and analyzer behavior.
6. `.contracts/agentic/` notes only as working context.

`.contracts/agentic/` is not citation-grade. Raw audit prompts and agent plans are not methodology. Their useful conclusions must be verified against code, tests, artifacts, and current docs before promotion.

## 4. P Factor Definition Gate

Before any Cluster 3 code, a written definition of `P` is required.

The definition must answer:

- What exactly does `P` control?
- Is `P` performance feedback, profiler feedback, timing feedback, schedule feedback, compiler feedback, ranking, candidate selection, or something else?
- Which failure or result classes can `P` observe?
- Which fields can `P` change?
- Does `P` repair code, choose configs, rank candidates, guide generation, or schedule evaluation?
- Is `P` allowed to see numerical correctness information?
- Is `P` allowed to see timing or profiling data?
- What is explicitly out of scope?

Acceptance rule:

- No Cluster 3 implementation begins until this definition is written and reviewed.
- For v1 compile-error repair, this gate is satisfied by
  `docs/cluster3_implementation_specification.md`. Any later profiler,
  performance, timing, F1 runtime, or paper-facing P expansion must reopen this
  gate.
- If the answer changes later, the formal contract, this plan or successor implementation plan, schemas, analyzer docs, artifact registry, and decision log must be updated before new runs.

## 5. Failure-Boundary Gate

`P` must have explicit allowed inputs and actions before any feedback path exists. It must not accidentally repair F0, F1, or F2 failures unless that behavior is part of the reviewed `P` definition.

If `P` observes timing or performance, the metric and measurement protocol must be specified before code. If `P` observes profiler output, the allowed profiler fields must be listed. All `P` feedback content must be auditable and serialized in a way that can be inspected later without hidden chat context.

| Failure/result class | Can P observe? | Can P act? | Required justification |
|---|---:|---:|---|
| F0 parse/signature/surface failure | TBD; default no until defined | TBD; default no until defined | Required if `P` includes compiler/surface repair. Must explain why this is not hidden `C` or broad repair drift. |
| F1 compile/runtime launch failure | TBD; default no until defined | TBD; default no until defined | Required if `P` includes compiler/runtime repair. Must define allowed error content. |
| F2 numerical/correctness failure | TBD; default no until defined | TBD; default no until defined | Required if `P` can see correctness. Must preserve independence from `C`. |
| F3 evaluation/infrastructure failure | No by default | No by default | F3 is infrastructure evidence, not a successful generated-kernel outcome. Any exception needs a separate infrastructure policy. |
| Level 4 timing/performance measurement | TBD; blocked until metric contract | TBD; blocked until metric contract | Requires timing protocol, repeats, warmup, hardware, baselines, noise handling, and reportability policy. |
| Profiler-derived fields | TBD; blocked until profiler contract | TBD; blocked until profiler contract | Requires allowed fields, redaction rules, and feedback-content auditability. |

## 6. Metric Contract Gate

Before implementation, Cluster 3 must define:

- primary Cluster 3 metric;
- secondary metrics;
- relationship to existing `functional_success` and `compile_success`;
- whether timing, profiling, or speedup becomes reportable;
- exact timing or profiling protocol if used;
- repeat count, warmup count, measurement window, and summary statistic;
- fixed hardware/GPU assumptions;
- baseline comparison target;
- what counts as measurement failure versus non-measurement;
- how noisy or missing measurements are represented in JSONL and analyzer output.

No speedup or performance claims are allowed without a locked measurement contract. A code path that records timing fields before this contract exists is drift.

## 7. Schema And Analyzer Gate

Every new result field must be defined before code.

Required propagation steps:

- result schema updated;
- JSONL logger updated;
- metadata validator updated;
- analyzer loader and normalization updated;
- tests updated;
- methodology docs updated;
- artifact registry updated.
- `scale_tier` serialized in row schema and registry for any future
  paper/preliminary P artifact.

Rule:

- No new result field may be added without analyzer handling.
- No analyzer-derived result may be cited unless the analyzer output is reportable or explicitly labeled non-final.
- Schema changes must include nullability, units, allowed values, source, and failure behavior.
- Analyzer reportability for P must reject conflicts between raw row
  `scale_tier`, registry/manifest scale tier, and invocation annotation. CLI
  annotation is a legacy/current-artifact compatibility path, not the normal
  path for future P paper-scale rows.

## 8. Artifact Registry Gate

Before Cluster 3 runs, the registry plan must list:

- planned artifact paths;
- condition names;
- row counts and intended row counts;
- scale tier;
- schema version;
- expected provenance fields;
- caveat fields;
- pairing identity fields;
- intended analyzer output path and reportability criteria.

No artifact can be cited before it is registered in `docs/05_artifacts_and_results_registry.md`. New artifacts must be new lineages; existing output artifacts must not be manually rewritten.
P registry entries must include `scale_tier`, analyzer manifest/config identity,
and the reportability conflict policy before any P result is cited.

## 9. Modal And Provenance Gate

Any Cluster 3 Modal or remote-execution path must record:

- `model_id`;
- `model_revision`;
- `tokenizer_revision`;
- Modal image provenance;
- package versions;
- hardware/GPU type;
- generation budget such as `max_new_tokens`;
- seeds and replay identity;
- hash gates if source boundaries are frozen;
- timing/profiling runtime configuration if `P` uses measurement.

Unknown provenance fields are caveats or blockers depending on scale tier:

| Scale tier | Unknown required provenance policy |
|---|---|
| smoke | Allowed only if explicitly labeled as a smoke caveat and not promoted. |
| development | Allowed only with an audit note and no paper claim. |
| paper/preliminary | Blocker unless the missing field is formally waived and visibly caveated. |

Modal execution alone does not prove reproducibility. Provenance, hashes, artifact identity, and analyzer reportability are what make a run auditable.

## 10. Scale-Gate Protocol

Cluster 3 must move through scale gates in order:

```text
n=1 smoke -> n=5 development -> audit -> n=20 paper/preliminary-scale
```

No paper-scale run may start until smoke, development, and audit gates pass.

| Scale | Purpose | Required checks | Output status |
|---|---|---|---|
| n=1 smoke | Prove the path runs end to end without crashing | schema validation, provenance presence, no forbidden feedback leakage, durable writing path | infrastructure evidence only |
| n=5 development | Exercise factor semantics and failure boundaries | paired identity, analyzer dry run, metric sanity, row-count validation, caveat review | development evidence only unless promoted |
| audit | Verify readiness before paper/preliminary scale | docs/contracts alignment, hash gates, analyzer plan, artifact registry plan, cost/risk review | go/no-go record |
| n=20 paper/preliminary | Produce report-candidate rows | frozen definitions, frozen schema, frozen prompts/feedback, provenance gate, registry entry, reportability criteria | report-facing only when registered and not blocked |

## 11. Replay And Pairing Gate

Cluster 3 must define paired identity before any generated run:

- paired unit definition;
- seed schedule;
- replay control mapping;
- condition-to-control mapping;
- missing-row policy;
- analyzer pairing tests;
- explicit handling of unpaired rows.

No paired statistical claim is allowed without verified pair identity. If raw controls do not carry `replay_pair_id`, tuple matching rules must be documented and tested before report-facing analysis.

## 12. Documentation-Update Gate

The same PR, commit, or review workflow that introduces Cluster 3 behavior must update:

- formal contract;
- methodology doc or implementation plan;
- artifact registry;
- decision log;
- analyzer docs;
- README if public scope changes;
- handoff phase state.

Docs are not a cleanup step after a run. For report-facing behavior, docs are part of the change.

## 13. Cluster 3 Acceptance Checklist Before Implementation

- [ ] P definition written.
- [ ] P failure boundaries written.
- [ ] Metric contract written.
- [ ] Schema contract written.
- [ ] Analyzer plan written.
- [ ] Modal/provenance plan written.
- [ ] Artifact registry plan written.
- [ ] Smoke command planned but not yet run.
- [ ] Tests planned.
- [ ] Documentation paths planned.
- [ ] Explicit out-of-scope list written.
- [ ] Review complete before code starts.

## 14. Cluster 3 Acceptance Checklist Before Paper-Scale Run

- [ ] n=1 smoke passed.
- [ ] n=5 development run passed.
- [ ] Metadata/provenance gate passed.
- [ ] Analyzer dry run passed.
- [ ] Artifact registry updated.
- [ ] Failure taxonomy updated.
- [ ] Analysis/statistics docs updated.
- [ ] Formal contract updated.
- [ ] Decision log updated.
- [ ] Audit passed.
- [ ] No reportability blockers remain.
- [ ] No required provenance fields are unknown without waiver.

## 15. Anti-Drift Checklist

- [ ] No code without definition.
- [ ] No Modal run without schema.
- [ ] No artifact without registry.
- [ ] No metric without research question.
- [ ] No feedback without failure boundary.
- [ ] No result field without analyzer.
- [ ] No report claim without artifact.
- [ ] No performance claim without measurement contract.
- [ ] No paper-scale run without smoke, development, and audit gates.
- [ ] No hidden reuse of agentic notes as citation-grade methodology.

## 16. Relationship To Current Preliminary Report

The current preliminary report remains 2^2:

- `none`
- `G`
- `C`
- `G+C`

Cluster 3 is future work. This plan is a lessons-learned and next-step guardrail document, not result evidence. It should be referenced only to explain what future `P` work must define before implementation.

## 17. Open Questions For Cluster 3

- What is the exact definition of `P`?
- Does `P` use profiler data, timing data, performance data, compiler/runtime errors, ranking, or generation guidance?
- Does `P` act as repair, reranker, generator guidance, scheduler, or evaluator?
- Is `P` allowed to see numerical correctness information?
- Does `P` require new Modal infrastructure?
- Does `P` need new correctness, safety, or performance levels beyond the current Level 0/1/2 and infrastructure/F3 ladder?
- How will `P` stay independent from `C`?
- How will missing rows and unpaired rows be handled?
- What makes a `P` analyzer output reportable?

## 18. Traceability Table

| Guardrail | Origin lesson | Current supporting doc | Future required artifact/test | Risk if skipped |
|---|---|---|---|---|
| Define P before code | Cluster 1/2 factor-name drift | `docs/08_decision_log.md` D18; `.contracts/research/research_scope.md` | Formal Cluster 3 implementation plan | Hidden factor semantics and uninterpretable conditions |
| Define allowed feedback classes | C had to lock F2-only repair | `docs/03_methodology_cluster2.md`; `docs/06_failure_taxonomy_and_eval_ladder.md` | Feedback-boundary tests for P | P becomes broad untracked repair |
| Define metric contract | Current docs forbid unsupported performance claims | `.contracts/research/eval_metrics.md`; `docs/09_preliminary_report_outline.md` | Timing/profiling metric tests and analyzer fixtures | Speed claims become unauditable |
| Define schema before Modal | Cluster 2 needed schema/provenance fixes | `docs/04_modal_infrastructure.md`; `docs/07_analysis_and_statistics.md` | P row schema tests, metadata validators | Raw rows cannot be analyzed or trusted |
| Register artifacts before citation | G/G+C coverage caveats must travel with artifacts | `docs/05_artifacts_and_results_registry.md` | P registry entries and row-count validation | Filename, row-count, and caveat drift |
| Preserve provenance | Unknown fields became caveats | `docs/04_modal_infrastructure.md`; `docs/08_decision_log.md` D10 | Provenance validation tests and run audit | Non-reproducible or non-auditable rows |
| Durable row writing | Cluster 2 partial-run history | `docs/04_modal_infrastructure.md`; `docs/03_methodology_cluster2.md` | P logger durability tests | Long runs can lose all evidence |
| Verify pairing | Current comparisons rely on matched identity | `docs/07_analysis_and_statistics.md`; `docs/08_decision_log.md` D07 | Analyzer pairing tests for P cells | Invalid paired statistical claims |
| Preserve reportability status | Current analyzer is reportable only under explicit scale-tier annotation and visible caveats | `docs/07_analysis_and_statistics.md`; `docs/09_preliminary_report_outline.md` | P analyzer output with row and registry scale-tier metadata | Exploratory output becomes final claim |
| Keep docs/contracts aligned | Phase 8 corrected stale formal surfaces | `README.md`; `.contracts/research/*`; `docs/08_decision_log.md` | Same-workflow doc/contract updates | Future agents inherit stale methodology |

## 19. What This Document Does Not Claim

- No Cluster 3 implementation exists or is validated by this document.
- No `P` results are claimed.
- No performance or speedup result is claimed.
- No full 2^3 completion is claimed.
- No Modal run or paper-scale run is authorized by this document.
- This is not itself the Cluster 3 implementation plan; the reviewed v1
  successor plan is `docs/cluster3_implementation_specification.md`.
- This document does not make analyzer output reportable.

## 20. Current Required Document Before Cluster 3 Code

The required v1 implementation plan is
`docs/cluster3_implementation_specification.md`. Phase 0 code should start from
that document, not from older agentic notes or audit prompts.

Cluster 3 results, performance/profiler behavior, paper-scale runs, and any
scope beyond compile-error repair remain deferred until the relevant contracts,
artifact registry entries, analyzer behavior, and run audits are updated.
