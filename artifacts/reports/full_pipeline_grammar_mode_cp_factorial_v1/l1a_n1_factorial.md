# Full 2³ factorial analysis

The full 2³ factorial over G, C, and P remains the defined project goal.

## Table 1 Cell Summaries
| metric_name | response_variable | analysis_role | summary_level | scale_tier | cell_status | condition | condition_label | kernel_class | dtype | n_cells | successes | success_rate | interpretation_flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| level2_functional_success_rate | functional_success | primary | condition | smoke | populated | C | C |  |  | 1 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition | smoke | populated | C+P | C+P |  |  | 1 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition | smoke | populated | G | template G reference mixed |  |  | 2 | 1 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition | smoke | populated | G+C | template G reference + C mixed |  |  | 2 | 1 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition | smoke | populated | G+C+P | template G reference + C + P mixed |  |  | 2 | 1 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition | smoke | populated | G+P | template G reference + P mixed |  |  | 2 | 1 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition | smoke | populated | P | P |  |  | 1 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition | smoke | populated | none | none |  |  | 1 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | smoke | populated | C | C | elementwise | fp32 | 1 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | smoke | populated | C+P | C+P | elementwise | fp32 | 1 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | smoke | populated | G | template G reference mixed | elementwise | fp32 | 2 | 1 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | smoke | populated | G+C | template G reference + C mixed | elementwise | fp32 | 2 | 1 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | smoke | populated | G+C+P | template G reference + C + P mixed | elementwise | fp32 | 2 | 1 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | smoke | populated | G+P | template G reference + P mixed | elementwise | fp32 | 2 | 1 | 0.5 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | smoke | populated | P | P | elementwise | fp32 | 1 | 0 | 0 |  |
| level2_functional_success_rate | functional_success | primary | condition_kernel_dtype | smoke | populated | none | none | elementwise | fp32 | 1 | 0 | 0 |  |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | smoke | populated | C | C |  |  | 1 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | smoke | populated | C+P | C+P |  |  | 1 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | smoke | populated | G | template G reference mixed |  |  | 2 | 2 | 1 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | smoke | populated | G+C | template G reference + C mixed |  |  | 2 | 2 | 1 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | smoke | populated | G+C+P | template G reference + C + P mixed |  |  | 2 | 2 | 1 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | smoke | populated | G+P | template G reference + P mixed |  |  | 2 | 2 | 1 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | smoke | populated | P | P |  |  | 1 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition | smoke | populated | none | none |  |  | 1 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | smoke | populated | C | C | elementwise | fp32 | 1 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | smoke | populated | C+P | C+P | elementwise | fp32 | 1 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | smoke | populated | G | template G reference mixed | elementwise | fp32 | 2 | 2 | 1 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | smoke | populated | G+C | template G reference + C mixed | elementwise | fp32 | 2 | 2 | 1 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | smoke | populated | G+C+P | template G reference + C + P mixed | elementwise | fp32 | 2 | 2 | 1 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | smoke | populated | G+P | template G reference + P mixed | elementwise | fp32 | 2 | 2 | 1 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | smoke | populated | P | P | elementwise | fp32 | 1 | 0 | 0 | diagnostic_only, strict_surface_metric |
| level1_compile_success_rate | compile_success | secondary_diagnostic | condition_kernel_dtype | smoke | populated | none | none | elementwise | fp32 | 1 | 0 | 0 | diagnostic_only, strict_surface_metric |

## Table 2 Paired Comparisons
| metric_name | response_variable | comparison | comparison_label | n_pairs | success_rate_a | success_rate_b | absolute_lift | ci_low | ci_high | p_value | p_value_holm | paired_analysis | interpretation_flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| level1_compile_success_rate | compile_success | G+C vs C | template G reference + C mixed vs C | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | True | diagnostic_only, strict_surface_metric |

## Table 3 Factorial Terms
| response_variable | model_type | model_family | model_fit_status | term | coefficient | direction | model_warnings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | G |  | unavailable | model_separation_detected |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | C |  | unavailable | model_separation_detected |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | P |  | unavailable | model_separation_detected |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | G:C |  | unavailable | model_separation_detected |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | G:P |  | unavailable | model_separation_detected |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | C:P |  | unavailable | model_separation_detected |
| functional_success | full_eight_cell | binary_logistic_irls | not_fit | G:C:P |  | unavailable | model_separation_detected |
