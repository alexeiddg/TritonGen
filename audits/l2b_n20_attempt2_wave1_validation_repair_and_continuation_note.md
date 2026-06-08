# L2b n20 Attempt2 Wave 1 Validation Repair And Continuation Note

Wave 1 of `l2b_n20_attempt2_full_coverage` completed with 720 rows, but the
first validation attempt stopped on a validator CLI `NameError`. The validator
CLI now derives valid stage choices from `L2B_SELECTOR_PROFILE_IDS`, which
includes `l2b_n20_attempt2_full_coverage`.

The continuation runner is:

```text
scripts/run_l2b_n20_attempt2_waves_2_to_4.sh
```

Run only after explicit execution authorization:

```bash
TRITONGEN_MLFLOW=0 bash scripts/run_l2b_n20_attempt2_waves_2_to_4.sh
```

The runner validates Wave 1 first, then runs only the signed Wave 2, Wave 3,
and Wave 4 commands from the attempt2 packet, with validation after each wave.
It stops on the first nonzero command and writes logs to
`/tmp/tritongen_l2b_n20_attempt2_logs/`.

The runner does not rerun Wave 1, does not call analyzer/report/billing, and
does not delete, overwrite, retry, resume, or mutate the original `l2b_n20`
partial namespace.
