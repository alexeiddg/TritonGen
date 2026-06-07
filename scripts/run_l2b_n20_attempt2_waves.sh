#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="/tmp/tritongen_l2b_n20_attempt2_logs"
BRANCH="codex-track-handoff-context"
STAGE="l2b_n20_attempt2_full_coverage"
NAMESPACE="l2b_n20_attempt2"

require_repo_root() {
  local root
  root="$(git rev-parse --show-toplevel)"
  if [[ "$root" != "$(pwd)" ]]; then
    echo "Run from repo root: $root" >&2
    exit 1
  fi
}

require_mlflow_disabled() {
  if [[ "${TRITONGEN_MLFLOW:-}" != "0" ]]; then
    echo "TRITONGEN_MLFLOW must be 0" >&2
    exit 1
  fi
}

require_clean_worktree() {
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Worktree must be clean before launching ${STAGE}" >&2
    git status --short --branch >&2
    exit 1
  fi
}

require_origin_aligned() {
  local local_head origin_head
  git fetch --quiet origin "${BRANCH}"
  local_head="$(git rev-parse HEAD)"
  origin_head="$(git rev-parse "origin/${BRANCH}")"
  if [[ "$local_head" != "$origin_head" ]]; then
    echo "Local HEAD and origin/${BRANCH} must match" >&2
    echo "local:  ${local_head}" >&2
    echo "origin: ${origin_head}" >&2
    exit 1
  fi
}

require_attempt2_targets_absent() {
  local paths=(
    "outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/${NAMESPACE}"
    "artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/${NAMESPACE}"
    "artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/${NAMESPACE}"
    "artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/${NAMESPACE}"
    "artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/${NAMESPACE}"
  )
  local path
  for path in "${paths[@]}"; do
    if [[ -e "$path" ]]; then
      echo "Attempt2 target path already exists: $path" >&2
      exit 1
    fi
  done
}

run_logged() {
  local label="$1"
  local command="$2"
  local log_path="${LOG_DIR}/${label}.log"
  mkdir -p "$LOG_DIR"
  echo "UTC ${label} start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "$command" > "$log_path"
  bash -lc "$command" 2>&1 | tee -a "$log_path"
  echo "UTC ${label} end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

preflight() {
  require_repo_root
  require_mlflow_disabled
  require_clean_worktree
  require_origin_aligned
  require_attempt2_targets_absent
}

preflight

run_logged "wave_1_launch" "TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --l2b-shard-selector wave:0:3 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1"
run_logged "wave_1_validation" ".venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_full_coverage --wave-id wave_1 --expected-rows 720 --require-content-hash-sidecars --require-observability-sidecars"

run_logged "wave_2_launch" "TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --l2b-shard-selector wave:3:3 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1"
run_logged "wave_2_validation" ".venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_full_coverage --wave-id wave_2 --expected-rows 720 --require-content-hash-sidecars --require-observability-sidecars"

run_logged "wave_3_launch" "TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --l2b-shard-selector wave:7:2 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1"
run_logged "wave_3_validation" ".venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_full_coverage --wave-id wave_3 --expected-rows 480 --require-content-hash-sidecars --require-observability-sidecars"

run_logged "wave_4_launch" "TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --l2b-shard-selector matmul__fp32 --kernel-class matmul --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1"
run_logged "wave_4_validation" ".venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_full_coverage --wave-id wave_4 --expected-rows 240 --require-content-hash-sidecars --require-observability-sidecars"
