# L1b development-scale 2³ factorial diagnostic analysis

This analysis is development-scale evidence only and is not paper-scale or reportable paper evidence.
The full 2³ factorial over G, C, and P remains the defined project goal.
Three-way interaction fields are diagnostic only and not reportable paper-scale claims.

## Table 1 Cell Summaries
| metric_name | response_variable | analysis_role | summary_level | scale_tier | cell_status | condition | condition_label | kernel_class | dtype | n_cells | successes | success_rate | interpretation_flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| level2_functional_success_rate | functional_success | primary | condition | development | populated | C | C |  |  | 5 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition | development | populated | C+P | C+P |  |  | 5 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition | development | populated | G | template G reference mixed |  |  | 10 | 5 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition | development | populated | G+C | template G reference + C mixed |  |  | 10 | 5 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition | development | populated | G+C+P | template G reference + C + P mixed |  |  | 10 | 5 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition | development | populated | G+P | template G reference + P mixed |  |  | 10 | 5 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition | development | populated | P | P |  |  | 5 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition | development | populated | none | none |  |  | 5 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | development | populated | C | C | elementwise | fp32 | 5 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | development | populated | C+P | C+P | elementwise | fp32 | 5 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | development | populated | G | template G reference mixed | elementwise | fp32 | 10 | 5 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | development | populated | G+C | template G reference + C mixed | elementwise | fp32 | 10 | 5 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | development | populated | G+C+P | template G reference + C + P mixed | elementwise | fp32 | 10 | 5 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | development | populated | G+P | template G reference + P mixed | elementwise | fp32 | 10 | 5 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | development | populated | P | P | elementwise | fp32 | 5 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | development | populated | none | none | elementwise | fp32 | 5 | 0 | 0 |  |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | development | populated | C | C |  |  | 5 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | development | populated | C+P | C+P |  |  | 5 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | development | populated | G | template G reference mixed |  |  | 10 | 6 | 0.6 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | development | populated | G+C | template G reference + C mixed |  |  | 10 | 6 | 0.6 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | development | populated | G+C+P | template G reference + C + P mixed |  |  | 10 | 6 | 0.6 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | development | populated | G+P | template G reference + P mixed |  |  | 10 | 6 | 0.6 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | development | populated | P | P |  |  | 5 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | development | populated | none | none |  |  | 5 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | development | populated | C | C | elementwise | fp32 | 5 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | development | populated | C+P | C+P | elementwise | fp32 | 5 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | development | populated | G | template G reference mixed | elementwise | fp32 | 10 | 6 | 0.6 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | development | populated | G+C | template G reference + C mixed | elementwise | fp32 | 10 | 6 | 0.6 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | development | populated | G+C+P | template G reference + C + P mixed | elementwise | fp32 | 10 | 6 | 0.6 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | development | populated | G+P | template G reference + P mixed | elementwise | fp32 | 10 | 6 | 0.6 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | development | populated | P | P | elementwise | fp32 | 5 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | development | populated | none | none | elementwise | fp32 | 5 | 0 | 0 | diagnostic_only, strict_surface_metric |

## Table 2 Paired Comparisons
_No rows emitted._

## Table 3 Factorial Terms
| response_variable | model_type | model_family | model_fit_status | term | coefficient | direction | model_warnings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | G |  | unavailable | model_separation_detected, three_way_interaction_requires_reportable_primary_paper_scale_output |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | C |  | unavailable | model_separation_detected, three_way_interaction_requires_reportable_primary_paper_scale_output |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | P |  | unavailable | model_separation_detected, three_way_interaction_requires_reportable_primary_paper_scale_output |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | G:C |  | unavailable | model_separation_detected, three_way_interaction_requires_reportable_primary_paper_scale_output |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | G:P |  | unavailable | model_separation_detected, three_way_interaction_requires_reportable_primary_paper_scale_output |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | C:P |  | unavailable | model_separation_detected, three_way_interaction_requires_reportable_primary_paper_scale_output |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | G:C:P |  | unavailable | model_separation_detected, three_way_interaction_requires_reportable_primary_paper_scale_output |
