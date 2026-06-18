#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="/tmp/tritongen_l2b_n20_attempt2_wave4_parallel_logs"
BRANCH="codex-track-handoff-context"
WAVE4_STAGE="l2b_n20_attempt2_wave4_parallel_full_coverage"
WAVE4_OUTPUT_ROOT="outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel"
WAVE4_OBSERVABILITY_ROOT="artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel"
WAVE4_ANALYSIS_ROOT="artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel"
WAVE4_REPORTS_ROOT="artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel"
WAVE4_BILLING_ROOT="artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel"

LANE_A_OUTPUT_ROOT="outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery"
LANE_A_OBSERVABILITY_ROOT="artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery"
LANE_A_ANALYSIS_ROOT="artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery"
LANE_A_REPORTS_ROOT="artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery"
LANE_A_BILLING_ROOT="artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery"
LANE_B_OUTPUT_ROOT="outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel"
LANE_B_OBSERVABILITY_ROOT="artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel"
LANE_B_ANALYSIS_ROOT="artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel"
LANE_B_REPORTS_ROOT="artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel"
LANE_B_BILLING_ROOT="artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel"

WAVE4_COMMAND="TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_wave4_parallel_full_coverage --l2b-shard-selector matmul__fp32 --kernel-class matmul --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_WAVE4_AUTHORIZATION_PACKET_V1"
WAVE4_VALIDATION_COMMAND=".venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage ${WAVE4_STAGE} --wave-id wave_4 --expected-rows 240 --require-content-hash-sidecars --require-observability-sidecars"

require_repo_root() {
  test -d .git
  test -x .venv/bin/python
}

require_mlflow_disabled() {
  if [[ "${TRITONGEN_MLFLOW:-}" != "0" ]]; then
    echo "TRITONGEN_MLFLOW=0 is required" >&2
    exit 1
  fi
}

is_allowed_dirty_path() {
  case "$1" in
    "${LANE_A_OUTPUT_ROOT}"*|\
    "${LANE_A_OBSERVABILITY_ROOT}"*|\
    "${LANE_A_ANALYSIS_ROOT}"*|\
    "${LANE_A_REPORTS_ROOT}"*|\
    "${LANE_A_BILLING_ROOT}"*|\
    "${LANE_B_OUTPUT_ROOT}"*|\
    "${LANE_B_OBSERVABILITY_ROOT}"*|\
    "${LANE_B_ANALYSIS_ROOT}"*|\
    "${LANE_B_REPORTS_ROOT}"*|\
    "${LANE_B_BILLING_ROOT}"*|\
    docs/paper_draft/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

require_clean_except_allowed_live_paths() {
  status_output="$(git status --porcelain)"
  if [[ -z "${status_output}" ]]; then
    return 0
  fi
  while IFS= read -r status_line; do
    path="${status_line:3}"
    if [[ "${status_line:0:2}" == "R " || "${status_line:0:2}" == " C" ]]; then
      path="${path##* -> }"
    fi
    if ! is_allowed_dirty_path "${path}"; then
      echo "Dirty path is not authorized for Wave 4 launch: ${status_line}" >&2
      git status --short
      exit 1
    fi
  done <<< "${status_output}"
}

require_origin_aligned() {
  git fetch --quiet origin "${BRANCH}"
  local_head="$(git rev-parse HEAD)"
  origin_head="$(git rev-parse "origin/${BRANCH}")"
  if [[ "${local_head}" != "${origin_head}" ]]; then
    echo "local HEAD is not aligned with origin/${BRANCH}" >&2
    exit 1
  fi
}

require_wave4_target_absent() {
  if [[ -e "${WAVE4_OUTPUT_ROOT}" || -e "${WAVE4_OBSERVABILITY_ROOT}" ]]; then
    echo "Wave 4 target path already exists" >&2
    exit 1
  fi
  if compgen -G "${WAVE4_ANALYSIS_ROOT}*" > /dev/null; then
    echo "Wave 4 analysis target already exists" >&2
    exit 1
  fi
  if compgen -G "${WAVE4_REPORTS_ROOT}*" > /dev/null; then
    echo "Wave 4 reports target already exists" >&2
    exit 1
  fi
  if compgen -G "${WAVE4_BILLING_ROOT}*" > /dev/null; then
    echo "Wave 4 billing target already exists" >&2
    exit 1
  fi
}

run_logged() {
  label="$1"
  command="$2"
  mkdir -p "${LOG_DIR}"
  start_utc="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "${label} start_utc=${start_utc}"
  echo "${command}" > "${LOG_DIR}/${label}.command.txt"
  bash -lc "${command}" > "${LOG_DIR}/${label}.stdout.log" 2> "${LOG_DIR}/${label}.stderr.log"
  end_utc="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "${label} end_utc=${end_utc}"
}

require_repo_root
require_mlflow_disabled
require_clean_except_allowed_live_paths
require_origin_aligned
require_wave4_target_absent

run_logged "wave4_launch" "${WAVE4_COMMAND}"
run_logged "wave4_validation" "${WAVE4_VALIDATION_COMMAND}"
