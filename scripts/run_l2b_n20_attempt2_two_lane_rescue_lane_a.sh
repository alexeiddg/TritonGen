#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="/tmp/tritongen_l2b_n20_attempt2_two_lane_rescue_logs"
LANE_A_STAGE="l2b_n20_attempt2_wave2_missing360_recovery_full_coverage"
LANE_A_OUTPUT_ROOT="outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery"
LANE_A_OBSERVABILITY_ROOT="artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery"
SOURCE_OUTPUT_ROOT="outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2"
SOURCE_OBSERVABILITY_ROOT="artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2"
MISSING_CELLS="template_upper_bound__c_off__p_on,template_upper_bound__c_on__p_on,task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on"

LANE_A_COMMAND="TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_wave2_missing360_recovery_full_coverage --l2b-shard-selector wave:3:3 --l2b-recovery-cells ${MISSING_CELLS} --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_PACKET_V1"

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

require_clean_worktree() {
  if [[ -n "$(git status --porcelain)" ]]; then
    git status --short
    exit 1
  fi
}

require_origin_aligned() {
  git fetch --quiet origin codex-track-handoff-context
  local_head="$(git rev-parse HEAD)"
  origin_head="$(git rev-parse origin/codex-track-handoff-context)"
  if [[ "${local_head}" != "${origin_head}" ]]; then
    echo "local HEAD is not aligned with origin/codex-track-handoff-context" >&2
    exit 1
  fi
}

require_source_attempt2_present() {
  test -d "${SOURCE_OUTPUT_ROOT}"
  test -d "${SOURCE_OBSERVABILITY_ROOT}"
}

require_target_absent() {
  if [[ -e "${LANE_A_OUTPUT_ROOT}" || -e "${LANE_A_OBSERVABILITY_ROOT}" ]]; then
    echo "Lane A target path already exists" >&2
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
require_clean_worktree
require_origin_aligned
require_source_attempt2_present
require_target_absent

run_logged "lane_a_launch" "${LANE_A_COMMAND}"
run_logged "lane_a_validation" ".venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage ${LANE_A_STAGE} --wave-id wave_2 --l2b-recovery-cells ${MISSING_CELLS} --expected-rows 360 --require-content-hash-sidecars --require-observability-sidecars"
run_logged "lane_a_union_validation" ".venv/bin/python -m cluster3.analysis.validate_l2b_two_lane_rescue_union --mode lane-a --expected-total-rows 1440"
