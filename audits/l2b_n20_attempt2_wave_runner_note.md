# L2b n20 Attempt2 Wave Runner Note

This note records the local shell runner for the signed L2b n20 attempt2 wave
sequence. The runner path is:

```text
scripts/run_l2b_n20_attempt2_waves.sh
```

Run it only after explicit execution authorization for the signed attempt2
phase:

```bash
TRITONGEN_MLFLOW=0 bash scripts/run_l2b_n20_attempt2_waves.sh
```

The runner embeds only the signed Wave 1 through Wave 4 commands and their
post-wave validation commands from
`docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n20_attempt2_authorization_packet.md`.
It writes logs to `/tmp/tritongen_l2b_n20_attempt2_logs/`, stops on the first
nonzero command, requires a clean worktree, requires local HEAD and
`origin/codex-track-handoff-context` to match, and requires the attempt2 target
paths to be absent before Wave 1.

The runner does not call analyzer, report, billing, cleanup, deletion, or any
original `l2b_n20` namespace command.
