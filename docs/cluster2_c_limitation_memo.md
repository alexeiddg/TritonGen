# Cluster 2 C Limitation Memo

- Status: thesis-facing limitation characterization
- Scope: Cluster 2 correctness-feedback repair (`C`) as exercised by the diagnostic template G+C run
- Diagnostic artifact: `outputs/cluster2/template_g_plus_c_paper_n20_l4.jsonl`
- Run report: `audits/template_g_plus_c_paper_n20_l4_run_report.md`
- Not a C redesign proposal
- Not a primary 2^2 analyzer input

## Executive Summary

The current Cluster 2 correctness-feedback repair loop should be characterized as a mixed limitation, not as an implementation failure.

In the diagnostic template G+C run, all 180 rows compiled. Functional success was 96/180. The remaining 84 rows reached Level 2 numerical/correctness failure and exhausted the C repair budget without any row being repaired to functional success. This result is scientifically meaningful because it isolates the correctness-feedback loop after compile success, rather than confounding C with parse, signature, or compile failures.

The repair-trace audit supports the classification `MIXED_LIMITATION`: some failures are information-limited because the public feedback intentionally withholds diagnostic details; others are capability-limited because the public feedback contains plausible repair clues but the model cycles among repeated failing variants.

## Empirical Observation

The diagnostic template G+C artifact contains 180 valid rows:

| Metric | Count |
|---|---:|
| Compile success | 180/180 |
| Functional success | 96/180 |
| F2 reached | 84/180 |
| F2 repaired to functional success | 0/84 |
| Repair budget exhausted | 84/84 |

Failure concentration was not uniform:

| Cell family | Functional outcome |
|---|---:|
| elementwise, all dtypes | 60/60 functional |
| matmul/fp16 | 20/20 functional |
| matmul/bf16 | 16/20 functional |
| matmul/fp32 | 0/20 functional |
| reduction, all dtypes | 0/60 functional |

The repair traces also show source cycling. Across the 84 F2 rows, every row repeated at least one source hash during the repair trace, and 68/84 terminal source hashes had appeared earlier in the same trace. This means the loop was not simply crashing or failing to iterate; it was repeatedly generating a small family of still-failing candidates.

## Mechanism Analysis

Two mechanisms appear at the same time.

First, some rows are information-limited. Eval-only failures may report only generic Level 2 failure text because private eval-shape details are deliberately hidden. In those cases, the model is told that a candidate passed initial correctness shapes but failed Level 2, without enough public information to identify the hidden generalization error. This is an intentional methodology boundary, not an accidental omission.

Second, some rows are capability-limited. Reduction failures report NaN/Inf on a public repair shape. Matmul/fp32 failures report numeric mismatch, tolerances, and shape. Those feedback payloads are not complete line-level diagnoses, but they contain enough information for a plausible repair attempt. The model nevertheless cycles among repeated variants and does not synthesize a functional repair within the budget.

This combination supports `MIXED_LIMITATION`: C is limited both by the informational content of the feedback and by the model's ability to use that feedback at this scale.

## Implication For C Design

The current C design is intentionally narrow. It supplies Level 2 numerical/correctness feedback only after a candidate has passed earlier gates. It does not provide compile-error details, signature hints, private eval-shape details, profiling information, timing information, or patch suggestions.

The diagnostic template G+C result shows that this feedback format is insufficient for the failure modes that survive task-encoded grammar in the tested model configuration. The loop can reach and report numerical failures, but the available public feedback often does not localize the defect enough for the model to produce a successful repair.

That limitation is part of the research result. It suggests that "feedback improves correctness" is too broad as a thesis statement. A better formulation is: the diagnostic value of feedback determines whether a repair loop can improve correctness.

## What This Does Not Imply

This does not imply that C is broken.

The dispatcher, F2-only routing policy, prompt construction, trace recording, budget exhaustion behavior, and row writing all appear operational. The loop fires on allowed F2 failures, records six-attempt traces when the budget is exhausted, preserves source hashes, and terminates with canonical failure codes.

This also does not imply that C should be broadened immediately. Allowing C to consume compile errors, private eval-shape details, line-level hints, or direct patch suggestions would change the meaning of the C factor. Such changes belong in future work or ablation studies, not in a silent redesign of the current Cluster 2 result.

Finally, this memo does not promote template G+C into the primary 2^2 analyzer. The template path is diagnostic upper-bound evidence used to understand the C loop under compile-success conditions. Primary 2^2 claims remain owned by the registered none, G, C, and task-agnostic G+C artifacts.

## Implications For Future Work

Richer feedback may improve repair success. Examples include more diagnostic public details, line-level annotations, structured error localization, or partial patch suggestions. Each would need a separate contract because it changes the information available to the model.

Larger or more capable models may also use the same numerical feedback more effectively. The current result should therefore be framed as a limitation at this model scale and feedback format, not as a universal impossibility result for correctness-feedback repair.

Cluster 3/P is complementary rather than redundant. P observes compile-error feedback, which is usually more localized than numerical mismatch feedback. If P repairs a meaningful fraction of F1 compile failures, that supports the claim that feedback information content drives repair success. If P also fails despite more localized compile-error feedback, that supports a stronger model-capability limitation.

## Reporting Guidance

Use this memo to prevent the incorrect interpretation "C is broken." A more precise thesis-facing sentence is:

> The Cluster 2 C loop is operational, but the current numerical-feedback format exposes a mixed limitation: some failures do not provide enough public diagnostic information, and some failures remain unrepaired even when the feedback is plausibly diagnostic.

Do not report this as a performance result, a full 2^3 result, or evidence that template artifacts are primary.
