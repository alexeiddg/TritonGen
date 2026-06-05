"""Cluster 3 row schema and metadata dataclasses.

These records are intentionally source-free. Raw source, private eval payloads,
and full compile logs stay outside the durable row schema.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from typing import Any, Literal

from cluster2.constants import (
    AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1,
    DTYPE_NAMES,
    GENERATED_SOURCE_CLASS,
    REPLAY_CONTROL_CONDITIONS,
    REPAIR_HISTORY_POLICIES_V1,
)
from cluster2.feedback.trace import TraceSummary
from cluster2.results.dataclass import Cluster2ReplayRowMetadata
from cluster3.constants import (
    CLUSTER3_CONDITIONS,
    DEFAULT_P_REPAIR_BUDGET,
    P_FEEDBACK_FORMAT_V1,
    P_HISTORY_POLICY_V1,
    P_REPAIR_STOP_REASONS,
    generation_mode_for_cluster3_condition,
    normalize_cluster3_condition,
    source_class_for_cluster3_condition,
)
from cluster3.feedback.trace import (
    CTraceSource,
    Cluster3TraceSummary,
    PRepairAttemptSummary,
    PromptHashSource,
)
from shared.eval.correctness_shapes import LOCKED_KERNEL_CLASSES, get_shape_metadata
from shared.eval.failure_taxonomy import FAILURE_CODES
from shared.generation_metadata import (
    CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION,
    GRAMMAR_CLAIM_SCOPE_BY_VARIANT,
    GRAMMAR_PATHS_BY_VARIANT,
    UNKNOWN,
    VALID_REJECTION_LAYERS,
    VALID_STOP_REASONS,
    is_stable_modal_image_identifier,
    modal_image_provenance_digest,
)
from shared.factors.grammar_modes import (
    grammar_mode_from_active_variant,
    validate_grammar_mode_binding,
)


CLUSTER3_RESULTS_SCHEMA_VERSION: int = 1

TerminalSourceStage = Literal["initial", "p_attempt", "c_attempt"]

_C_LOOP_CONDITIONS: frozenset[str] = frozenset({"C+P", "G+C+P"})
_C_LOOP_SOURCES: frozenset[str] = frozenset({"none", "initial_f2", "post_p_f2"})
_TERMINAL_SOURCE_STAGES: frozenset[str] = frozenset(
    {"initial", "p_attempt", "c_attempt"}
)
_TERMINAL_PROMPT_HASH_SOURCES: frozenset[str] = frozenset(
    {
        "initial_prompt",
        "p_repair_prompt",
        "c_repair_prompt",
        "seed_prompt_metadata",
        "seed_prompt_unavailable",
    }
)
_P_COMPILE_REPAIRED_STOP_REASONS: frozenset[str] = frozenset(
    {
        "p_compile_repaired_then_success",
        "p_compile_repaired_f2_observed",
        "p_post_compile_f3_observed",
    }
)


@dataclass(frozen=True)
class Cluster3ReplayRowMetadata(Cluster2ReplayRowMetadata):
    """Replay/control provenance for no-P artifact rows used in pair checks."""


@dataclass(frozen=True)
class Cluster3GeneratedRowMetadata:
    """Generated-only provenance for Cluster 3 terminal row sources."""

    c3_generation_hashes: dict[str, str]
    generation_seed: int
    initial_generation_seed: int | None = None
    terminal_source_stage: TerminalSourceStage | None = None
    terminal_attempt_index: int | None = None
    terminal_source_hash: str | None = None
    terminal_prompt_hash: str | None = None
    terminal_prompt_hash_source: PromptHashSource | None = None
    p_repair_attempted: bool | None = None
    p_compile_repair_succeeded: bool | None = None
    p_repair_attempt_count: int | None = None
    p_history_policy: str = P_HISTORY_POLICY_V1
    p_repair_prompt_template_version: str | None = None
    p_repair_prompt_renderer_version: str | None = None
    p_repair_anchor_attempt_index: int | None = None
    p_repair_latest_attempt_index: int | None = None
    p_repair_history_attempt_count: int | None = None
    p_repair_prompt_sha256: str | None = None
    p_repair_prompt_char_count: int | None = None
    p_repair_max_prompt_chars: int | None = None
    p_repair_include_latest_source: bool | None = None
    p_repair_anchor_source_hash: str | None = None
    p_repair_latest_source_hash: str | None = None
    p_repair_history_summary_sha256: str | None = None
    p_repair_history_error_code: str | None = None
    c_loop_fired: bool | None = None
    c_loop_source: CTraceSource | None = None
    grammar_mode: str | None = None
    grammar_variant: str | None = None
    grammar_path: str | None = None
    grammar_sha: str | None = None
    grammar_claim_scope: str | None = None
    gbnf_parse_valid: bool | None = None
    semantic_valid: bool | None = None
    grammar_valid: bool | None = None
    rejection_layer: str | None = None
    stop_reason: str = UNKNOWN
    xgrammar_version: str = UNKNOWN
    transformers_version: str = UNKNOWN
    tokenizers_version: str = UNKNOWN
    modal_image_sha: str = UNKNOWN
    modal_image_provenance_sha256: str | None = None
    modal_image_provenance_components: dict[str, Any] | None = None
    generation_metadata_schema_version: int = 0
    replay_pair_id: str | None = None
    replay_control_condition: str | None = None
    replay_base_seed: int | None = None
    replay_generation_seed: int | None = None
    cluster1_artifact_id: str | None = None
    replay_source: str | None = None
    prompt_sha256: str | None = None
    model_id: str | None = None
    model_revision: str | None = None
    tokenizer_revision: str | None = None
    temperature: float | None = None
    max_new_tokens: int | None = None

    def __post_init__(self) -> None:
        _validate_hash_mapping(
            self.c3_generation_hashes,
            "c3_generation_hashes",
            require_non_empty=True,
        )
        _require_non_negative_int(self.generation_seed, "generation_seed")
        _validate_optional_non_negative_int(
            self.initial_generation_seed,
            "initial_generation_seed",
        )
        if self.terminal_source_stage is not None:
            _validate_terminal_source_stage(self.terminal_source_stage)
        _validate_optional_non_negative_int(
            self.terminal_attempt_index,
            "terminal_attempt_index",
        )
        _validate_optional_sha256(self.terminal_source_hash, "terminal_source_hash")
        _validate_optional_sha256(self.terminal_prompt_hash, "terminal_prompt_hash")
        if self.terminal_prompt_hash_source is not None:
            _validate_prompt_hash_source(
                self.terminal_prompt_hash,
                self.terminal_prompt_hash_source,
            )
        _validate_optional_bool(self.p_repair_attempted, "p_repair_attempted")
        _validate_optional_bool(
            self.p_compile_repair_succeeded,
            "p_compile_repair_succeeded",
        )
        _validate_optional_non_negative_int(
            self.p_repair_attempt_count,
            "p_repair_attempt_count",
        )
        _validate_p_repair_history_metadata(
            p_history_policy=self.p_history_policy,
            p_repair_prompt_template_version=(
                self.p_repair_prompt_template_version
            ),
            p_repair_prompt_renderer_version=(
                self.p_repair_prompt_renderer_version
            ),
            p_repair_anchor_attempt_index=self.p_repair_anchor_attempt_index,
            p_repair_latest_attempt_index=self.p_repair_latest_attempt_index,
            p_repair_history_attempt_count=self.p_repair_history_attempt_count,
            p_repair_prompt_sha256=self.p_repair_prompt_sha256,
            p_repair_prompt_char_count=self.p_repair_prompt_char_count,
            p_repair_max_prompt_chars=self.p_repair_max_prompt_chars,
            p_repair_include_latest_source=self.p_repair_include_latest_source,
            p_repair_anchor_source_hash=self.p_repair_anchor_source_hash,
            p_repair_latest_source_hash=self.p_repair_latest_source_hash,
            p_repair_history_summary_sha256=(
                self.p_repair_history_summary_sha256
            ),
            p_repair_history_error_code=self.p_repair_history_error_code,
        )
        _validate_optional_bool(self.c_loop_fired, "c_loop_fired")
        if self.c_loop_source is not None and self.c_loop_source not in _C_LOOP_SOURCES:
            raise ValueError(f"unsupported c_loop_source {self.c_loop_source!r}")
        _validate_generated_grammar_metadata(
            grammar_variant=self.grammar_variant,
            grammar_path=self.grammar_path,
            grammar_claim_scope=self.grammar_claim_scope,
        )
        _validate_generated_runtime_metadata(
            generation_metadata_schema_version=(
                self.generation_metadata_schema_version
            ),
            grammar_variant=self.grammar_variant,
            grammar_sha=self.grammar_sha,
            gbnf_parse_valid=self.gbnf_parse_valid,
            semantic_valid=self.semantic_valid,
            grammar_valid=self.grammar_valid,
            rejection_layer=self.rejection_layer,
            stop_reason=self.stop_reason,
            modal_image_sha=self.modal_image_sha,
            modal_image_provenance_sha256=self.modal_image_provenance_sha256,
            modal_image_provenance_components=(
                self.modal_image_provenance_components
            ),
        )
        _validate_optional_sha256(self.prompt_sha256, "prompt_sha256")
        if self.replay_control_condition is not None:
            if self.replay_control_condition not in REPLAY_CONTROL_CONDITIONS:
                raise ValueError(
                    "replay_control_condition must be one of: "
                    f"{', '.join(REPLAY_CONTROL_CONDITIONS)}"
                )
        _require_optional_non_empty_str(
            self.cluster1_artifact_id,
            "cluster1_artifact_id",
        )
        _require_optional_non_empty_str(self.replay_source, "replay_source")
        _validate_pairing_metadata(
            replay_pair_id=self.replay_pair_id,
            replay_base_seed=self.replay_base_seed,
            replay_generation_seed=self.replay_generation_seed,
            model_id=self.model_id,
            model_revision=self.model_revision,
            tokenizer_revision=self.tokenizer_revision,
            temperature=self.temperature,
            max_new_tokens=self.max_new_tokens,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster3GeneratedRowMetadata":
        return _from_dict_strict(cls, payload)


@dataclass(frozen=True)
class Cluster3EvalRow:
    """Primary Cluster 3 JSONL row."""

    condition: str
    source_class: str
    generation_mode: str
    attempt_index: int
    kernel_class: str
    kernel_name: str
    dtype: str
    base_seed: int
    source_hash: str
    grammar_active: bool
    compile_success: bool
    functional_success: bool
    repair_set_success: bool
    eval_set_success: bool
    failure_code: str | None
    trace_summary: Cluster3TraceSummary | None
    replay_metadata: Cluster3ReplayRowMetadata | None
    generated_metadata: Cluster3GeneratedRowMetadata | None
    repair_trace: tuple[TraceSummary, ...] | None
    initial_failure_code: str | None
    p_repair_attempted: bool
    p_compile_repair_succeeded: bool
    p_repair_changed_terminal_class: bool
    p_repair_budget: int
    p_repair_attempt_count: int
    p_initial_failure_code: str | None
    p_terminal_failure_code: str | None
    c_loop_fired: bool
    c_loop_source: Literal["none", "initial_f2", "post_p_f2"]
    c_terminal_failure_code: str | None
    c_terminal_level_reached: int | None
    p_compile_error_class: str | None
    p_raw_error_excerpt_sha256: str | None
    p_repair_stop_reason: str
    p_feedback_format: str
    p_history_policy: str
    p_repair_trace: tuple[PRepairAttemptSummary, ...] | None
    terminal_source_stage: TerminalSourceStage
    terminal_generation_seed: int
    terminal_attempt_index: int | None
    terminal_source_hash: str
    terminal_prompt_hash: str | None
    terminal_prompt_hash_source: PromptHashSource
    terminal_source_matches_row_source: bool
    grammar_mode: str | None = None

    def __post_init__(self) -> None:
        condition = normalize_cluster3_condition(self.condition)
        object.__setattr__(self, "condition", condition)
        self._validate_core_fields(condition)
        self._validate_p_policy()
        self._validate_c_policy(condition)
        self._validate_row_failure_code_binding()
        self._validate_terminal_provenance()
        self._validate_generated_metadata(condition)
        self._validate_trace_summary()

    def _validate_core_fields(self, condition: str) -> None:
        expected_source_class = source_class_for_cluster3_condition(condition)
        if self.source_class != expected_source_class:
            raise ValueError(
                f"condition {condition!r} requires source_class "
                f"{expected_source_class!r}; got {self.source_class!r}"
            )
        expected_generation_mode = generation_mode_for_cluster3_condition(condition)
        if self.generation_mode != expected_generation_mode:
            raise ValueError(
                f"condition {condition!r} requires generation_mode "
                f"{expected_generation_mode!r}; got {self.generation_mode!r}"
            )
        _require_non_negative_int(self.attempt_index, "attempt_index")
        _validate_locked_kernel_identity(self.kernel_class, self.kernel_name)
        if self.dtype not in DTYPE_NAMES:
            raise ValueError(
                f"unsupported dtype {self.dtype!r}; allowed: {', '.join(DTYPE_NAMES)}"
            )
        _require_non_negative_int(self.base_seed, "base_seed")
        _validate_sha256(self.source_hash, "source_hash")
        _require_bool(self.grammar_active, "grammar_active")
        _require_bool(self.compile_success, "compile_success")
        _require_bool(self.functional_success, "functional_success")
        _require_bool(self.repair_set_success, "repair_set_success")
        _require_bool(self.eval_set_success, "eval_set_success")
        if self.functional_success != (
            self.repair_set_success and self.eval_set_success
        ):
            raise ValueError(
                "functional_success must equal repair_set_success and eval_set_success"
            )
        _validate_optional_failure_code(self.failure_code, "failure_code")
        _validate_optional_failure_code(
            self.initial_failure_code,
            "initial_failure_code",
        )
        _validate_compile_success_consistency(
            compile_success=self.compile_success,
            functional_success=self.functional_success,
            failure_code=self.failure_code,
        )
        if self.functional_success and self.failure_code is not None:
            raise ValueError("failure_code must be None when functional_success is True")
        expected_grammar_active = condition in {"G+P", "G+C+P"}
        if self.grammar_active is not expected_grammar_active:
            raise ValueError("grammar_active must match Cluster 3 condition")

    def _validate_p_policy(self) -> None:
        _require_bool(self.p_repair_attempted, "p_repair_attempted")
        _require_bool(
            self.p_compile_repair_succeeded,
            "p_compile_repair_succeeded",
        )
        _require_bool(
            self.p_repair_changed_terminal_class,
            "p_repair_changed_terminal_class",
        )
        _require_non_negative_int(self.p_repair_budget, "p_repair_budget")
        if self.p_repair_budget > DEFAULT_P_REPAIR_BUDGET:
            raise ValueError(
                f"p_repair_budget must be <= {DEFAULT_P_REPAIR_BUDGET}"
            )
        _require_non_negative_int(
            self.p_repair_attempt_count,
            "p_repair_attempt_count",
        )
        if self.p_repair_attempt_count > self.p_repair_budget:
            raise ValueError("p_repair_attempt_count must be <= p_repair_budget")
        _validate_optional_failure_code(
            self.p_initial_failure_code,
            "p_initial_failure_code",
        )
        _validate_optional_failure_code(
            self.p_terminal_failure_code,
            "p_terminal_failure_code",
        )
        _require_optional_non_empty_str(
            self.p_compile_error_class,
            "p_compile_error_class",
        )
        _validate_optional_sha256(
            self.p_raw_error_excerpt_sha256,
            "p_raw_error_excerpt_sha256",
        )
        if self.p_feedback_format != P_FEEDBACK_FORMAT_V1:
            raise ValueError("p_feedback_format must equal P_FEEDBACK_FORMAT_V1")
        if self.p_history_policy not in REPAIR_HISTORY_POLICIES_V1:
            raise ValueError(f"unsupported p_history_policy {self.p_history_policy!r}")

        if not self.p_repair_attempted:
            self._validate_inactive_p_policy()
            return

        if self.p_initial_failure_code != "F1_COMPILE":
            raise ValueError("active P rows require p_initial_failure_code F1_COMPILE")
        if self.initial_failure_code != self.p_initial_failure_code:
            raise ValueError(
                "active P rows require initial_failure_code to match "
                "p_initial_failure_code"
            )
        if self.p_repair_stop_reason not in P_REPAIR_STOP_REASONS:
            raise ValueError(
                f"unsupported p_repair_stop_reason {self.p_repair_stop_reason!r}"
            )
        if self.p_repair_stop_reason == "p_not_applicable":
            raise ValueError("active P rows must not use p_not_applicable")
        if self.p_repair_trace is None:
            raise ValueError("active P rows require p_repair_trace")
        if not isinstance(self.p_repair_trace, tuple):
            object.__setattr__(self, "p_repair_trace", tuple(self.p_repair_trace))
        assert self.p_repair_trace is not None
        if len(self.p_repair_trace) != self.p_repair_attempt_count + 1:
            raise ValueError(
                "len(p_repair_trace) must equal p_repair_attempt_count + 1"
            )
        for expected_index, attempt in enumerate(self.p_repair_trace):
            if not isinstance(attempt, PRepairAttemptSummary):
                raise TypeError("p_repair_trace entries must be PRepairAttemptSummary")
            if attempt.attempt_index != expected_index:
                raise ValueError(
                    "p_repair_trace attempt_index values must run from 0 "
                    "through p_repair_attempt_count"
                )
        p_seed_attempt = self.p_repair_trace[0]
        if p_seed_attempt.failure_code != self.p_initial_failure_code:
            raise ValueError(
                "p_initial_failure_code must match P seed trace attempt"
            )
        if p_seed_attempt.compile_success is not False:
            raise ValueError("P seed trace attempt must record compile_success False")
        if self.p_compile_error_class is None:
            raise ValueError("active P rows require p_compile_error_class")
        if p_seed_attempt.compile_error_class != self.p_compile_error_class:
            raise ValueError(
                "p_compile_error_class must match P seed trace attempt"
            )
        if self.p_raw_error_excerpt_sha256 is None:
            raise ValueError("active P rows require p_raw_error_excerpt_sha256")
        p_terminal_attempt = self.p_repair_trace[-1]
        if p_terminal_attempt.failure_code != self.p_terminal_failure_code:
            raise ValueError(
                "p_terminal_failure_code must match P terminal trace attempt"
            )
        _validate_p_stop_reason_terminal_outcome(
            stop_reason=self.p_repair_stop_reason,
            terminal_failure_code=self.p_terminal_failure_code,
            compile_repair_succeeded=self.p_compile_repair_succeeded,
        )
        has_compile_success_evidence = p_terminal_attempt.compile_success is True
        has_post_compile_f3_evidence = (
            self.p_repair_stop_reason == "p_post_compile_f3_observed"
            and isinstance(self.p_terminal_failure_code, str)
            and self.p_terminal_failure_code.startswith("F3_")
        )
        if self.p_compile_repair_succeeded and not (
            has_compile_success_evidence or has_post_compile_f3_evidence
        ):
            raise ValueError(
                "p_compile_repair_succeeded requires P terminal trace compile_success"
            )
        expected_changed = _p_changed_terminal_class(
            self.p_initial_failure_code,
            self.p_terminal_failure_code,
        )
        if self.p_repair_changed_terminal_class is not expected_changed:
            raise ValueError(
                "p_repair_changed_terminal_class must match P terminal classes"
            )
        if self.p_compile_repair_succeeded and _is_f0_or_f1(
            self.p_terminal_failure_code,
        ):
            raise ValueError(
                "p_compile_repair_succeeded cannot have an F0/F1 P terminal"
            )

    def _validate_inactive_p_policy(self) -> None:
        if self.p_repair_attempt_count != 0:
            raise ValueError("inactive P rows require p_repair_attempt_count == 0")
        if self.p_initial_failure_code is not None:
            raise ValueError("inactive P rows require p_initial_failure_code is None")
        if self.p_terminal_failure_code is not None:
            raise ValueError("inactive P rows require p_terminal_failure_code is None")
        if self.p_repair_trace is not None:
            raise ValueError("inactive P rows require p_repair_trace is None")
        if self.p_compile_error_class is not None:
            raise ValueError("inactive P rows require p_compile_error_class is None")
        if self.p_raw_error_excerpt_sha256 is not None:
            raise ValueError(
                "inactive P rows require p_raw_error_excerpt_sha256 is None"
            )
        if self.p_repair_stop_reason != "p_not_applicable":
            raise ValueError("inactive P rows require p_not_applicable stop reason")
        if self.p_compile_repair_succeeded is not False:
            raise ValueError("inactive P rows require p_compile_repair_succeeded False")
        if self.p_repair_changed_terminal_class is not False:
            raise ValueError(
                "inactive P rows require p_repair_changed_terminal_class False"
            )

    def _validate_c_policy(self, condition: str) -> None:
        _require_bool(self.c_loop_fired, "c_loop_fired")
        if self.c_loop_source not in _C_LOOP_SOURCES:
            raise ValueError(f"unsupported c_loop_source {self.c_loop_source!r}")
        _validate_optional_failure_code(
            self.c_terminal_failure_code,
            "c_terminal_failure_code",
        )
        _validate_optional_non_negative_int(
            self.c_terminal_level_reached,
            "c_terminal_level_reached",
        )
        if self.repair_trace is not None:
            if not isinstance(self.repair_trace, tuple):
                object.__setattr__(self, "repair_trace", tuple(self.repair_trace))
            for trace in self.repair_trace:
                if not isinstance(trace, TraceSummary):
                    raise TypeError("repair_trace entries must be TraceSummary")

        if not self.c_loop_fired:
            if self.c_loop_source != "none":
                raise ValueError("c_loop_source must be none when C loop did not fire")
            if self.repair_trace is not None:
                raise ValueError("repair_trace must be None when C loop did not fire")
            if self.c_terminal_failure_code is not None:
                raise ValueError("c_terminal_failure_code must be None without C loop")
            if self.c_terminal_level_reached is not None:
                raise ValueError("c_terminal_level_reached must be None without C loop")
            return

        if condition not in _C_LOOP_CONDITIONS:
            raise ValueError("c_loop_fired requires a C+P or G+C+P condition")
        if self.c_loop_source not in {"initial_f2", "post_p_f2"}:
            raise ValueError("c_loop_fired requires initial_f2 or post_p_f2 source")
        if self.repair_trace is None:
            raise ValueError("c_loop_fired requires repair_trace")
        if self.c_terminal_level_reached is None:
            raise ValueError("c_loop_fired requires c_terminal_level_reached")
        if self.c_terminal_failure_code != self.failure_code:
            raise ValueError("c_terminal_failure_code must equal row failure_code")
        if self.c_loop_source == "initial_f2":
            if self.p_repair_attempted:
                raise ValueError("initial_f2 C rows must not have active P fields")
            if not _is_f2(self.initial_failure_code):
                raise ValueError("initial_f2 C rows require initial F2 failure")
        if self.c_loop_source == "post_p_f2":
            if not self.p_repair_attempted:
                raise ValueError("post_p_f2 C rows require an active P loop")
            if not _is_f2(self.p_terminal_failure_code):
                raise ValueError("post_p_f2 C rows require P terminal F2")
        for expected_index, trace in enumerate(self.repair_trace, start=1):
            if trace.attempt_index != expected_index:
                raise ValueError(
                    "repair_trace attempt_index values must run from 1 through "
                    "trace_summary.c_attempt_count"
                )

    def _validate_row_failure_code_binding(self) -> None:
        if self.p_repair_attempted and self.c_loop_fired:
            expected = self.c_terminal_failure_code
        elif self.p_repair_attempted:
            expected = self.p_terminal_failure_code
        elif self.c_loop_fired:
            expected = self.c_terminal_failure_code
        else:
            expected = self.initial_failure_code
        if self.failure_code != expected:
            raise ValueError("row failure_code must match terminal loop binding")

    def _validate_terminal_provenance(self) -> None:
        _validate_terminal_source_stage(self.terminal_source_stage)
        _require_non_negative_int(
            self.terminal_generation_seed,
            "terminal_generation_seed",
        )
        _validate_optional_non_negative_int(
            self.terminal_attempt_index,
            "terminal_attempt_index",
        )
        _validate_sha256(self.terminal_source_hash, "terminal_source_hash")
        _validate_optional_sha256(self.terminal_prompt_hash, "terminal_prompt_hash")
        _validate_prompt_hash_source(
            self.terminal_prompt_hash,
            self.terminal_prompt_hash_source,
        )
        _require_bool(
            self.terminal_source_matches_row_source,
            "terminal_source_matches_row_source",
        )
        if self.terminal_source_matches_row_source is not True:
            raise ValueError("terminal_source_matches_row_source must be True")
        if self.source_hash != self.terminal_source_hash:
            raise ValueError("source_hash must equal terminal_source_hash")
        if self.terminal_source_stage == "initial":
            if self.terminal_attempt_index != 0:
                raise ValueError("initial terminal source requires attempt index 0")
            if self.p_repair_attempted:
                assert self.p_repair_trace is not None
                if self.p_repair_attempt_count != 0:
                    raise ValueError(
                        "initial terminal source requires no generated P attempts"
                    )
                p_seed_attempt = self.p_repair_trace[0]
                if p_seed_attempt.attempt_index != 0:
                    raise ValueError("initial terminal source requires P seed attempt 0")
                if self.terminal_generation_seed != p_seed_attempt.generation_seed:
                    raise ValueError(
                        "terminal_generation_seed must match P seed trace attempt"
                    )
                if p_seed_attempt.source_hash is None:
                    raise ValueError("P seed trace attempt requires source_hash")
                if self.terminal_source_hash != p_seed_attempt.source_hash:
                    raise ValueError(
                        "terminal_source_hash must match P seed trace attempt"
                    )
            if self.c_loop_fired:
                if self.c_loop_source != "initial_f2":
                    raise ValueError(
                        "initial C seed terminal requires c_loop_source initial_f2"
                    )
                if self.repair_trace:
                    raise ValueError(
                        "C seed terminal source requires no generated C repair_trace entries"
                    )
                if self.terminal_prompt_hash_source not in {
                    "initial_prompt",
                    "seed_prompt_metadata",
                    "seed_prompt_unavailable",
                }:
                    raise ValueError(
                        "initial C seed terminal requires initial or seed prompt hash source"
                    )
            elif self.terminal_prompt_hash_source != "initial_prompt":
                raise ValueError("initial terminal source requires initial_prompt hash")
        elif self.terminal_attempt_index is None:
            raise ValueError(
                "P and C terminal sources require terminal_attempt_index"
            )
        if self.terminal_source_stage == "p_attempt":
            if not self.p_repair_attempted:
                raise ValueError("p_attempt terminal source requires active P loop")
            if self.p_repair_attempt_count == 0:
                raise ValueError(
                    "p_attempt terminal source requires a generated P attempt"
                )
            assert self.p_repair_trace is not None
            p_terminal_attempt = self.p_repair_trace[-1]
            if p_terminal_attempt.attempt_index != self.p_repair_attempt_count:
                raise ValueError(
                    "P terminal attempt index must match p_repair_attempt_count"
                )
            if self.terminal_attempt_index != p_terminal_attempt.attempt_index:
                raise ValueError(
                    "terminal_attempt_index must match P terminal trace attempt"
                )
            if self.terminal_generation_seed != p_terminal_attempt.generation_seed:
                raise ValueError(
                    "terminal_generation_seed must match P terminal trace attempt"
                )
            if p_terminal_attempt.source_hash is None:
                raise ValueError("P terminal trace attempt requires source_hash")
            if self.terminal_source_hash != p_terminal_attempt.source_hash:
                raise ValueError(
                    "terminal_source_hash must match P terminal trace attempt"
                )
            if self.c_loop_fired:
                if self.c_loop_source != "post_p_f2":
                    raise ValueError(
                        "post-P C seed terminal requires c_loop_source post_p_f2"
                    )
                if self.repair_trace:
                    raise ValueError(
                        "C seed terminal source requires no generated C repair_trace entries"
                    )
                if self.terminal_prompt_hash_source not in {
                    "p_repair_prompt",
                    "seed_prompt_metadata",
                    "seed_prompt_unavailable",
                }:
                    raise ValueError(
                        "post-P C seed terminal requires P or seed prompt hash source"
                    )
            elif self.terminal_prompt_hash_source != "p_repair_prompt":
                raise ValueError("P terminal source requires p_repair_prompt hash")
            if (
                self.terminal_prompt_hash_source == "p_repair_prompt"
                and self.terminal_prompt_hash is None
            ):
                raise ValueError("P terminal source requires terminal_prompt_hash")
        if self.terminal_source_stage == "c_attempt":
            if not self.c_loop_fired:
                raise ValueError("c_attempt terminal source requires active C loop")
            if not self.repair_trace:
                raise ValueError("c_attempt terminal source requires repair_trace")
            c_terminal_attempt = self.repair_trace[-1]
            if self.terminal_attempt_index != c_terminal_attempt.attempt_index:
                raise ValueError(
                    "terminal_attempt_index must match C terminal repair trace attempt"
                )
            if c_terminal_attempt.source_hash is None:
                raise ValueError("C terminal repair trace requires source_hash")
            if self.terminal_source_hash != c_terminal_attempt.source_hash:
                raise ValueError(
                    "terminal_source_hash must match C terminal repair trace attempt"
                )
            if c_terminal_attempt.failure_code != self.c_terminal_failure_code:
                raise ValueError(
                    "c_terminal_failure_code must match C terminal repair trace attempt"
                )
            if c_terminal_attempt.functional_success is not self.functional_success:
                raise ValueError(
                    "functional_success must match C terminal repair trace attempt"
                )
            if (
                c_terminal_attempt.repair_set_success is not None
                and c_terminal_attempt.repair_set_success is not self.repair_set_success
            ):
                raise ValueError(
                    "repair_set_success must match C terminal repair trace attempt"
                )
            if (
                c_terminal_attempt.eval_set_success is not None
                and c_terminal_attempt.eval_set_success is not self.eval_set_success
            ):
                raise ValueError(
                    "eval_set_success must match C terminal repair trace attempt"
                )
            if self.terminal_prompt_hash_source != "c_repair_prompt":
                raise ValueError("generated C terminal source requires c_repair_prompt")
            if self.terminal_prompt_hash is None:
                raise ValueError("generated C terminal source requires prompt hash")

    def _validate_generated_metadata(self, condition: str) -> None:
        if not isinstance(self.generated_metadata, Cluster3GeneratedRowMetadata):
            raise TypeError("Cluster 3 generated rows require generated_metadata")
        if self.generated_metadata.generation_seed != self.terminal_generation_seed:
            raise ValueError(
                "generated_metadata.generation_seed must equal terminal_generation_seed"
            )
        if self.replay_metadata is not None and not isinstance(
            self.replay_metadata,
            Cluster3ReplayRowMetadata,
        ):
            raise TypeError("replay_metadata must be Cluster3ReplayRowMetadata or None")
        if condition in {"G+P", "G+C+P"}:
            if (
                self.generated_metadata.grammar_variant is None
                or self.generated_metadata.grammar_path is None
                or self.generated_metadata.grammar_claim_scope is None
            ):
                raise ValueError("G Cluster 3 rows require grammar metadata")
            _validate_generated_grammar_metadata(
                grammar_variant=self.generated_metadata.grammar_variant,
                grammar_path=self.generated_metadata.grammar_path,
                grammar_claim_scope=self.generated_metadata.grammar_claim_scope,
            )
        else:
            if (
                self.generated_metadata.grammar_variant is not None
                or self.generated_metadata.grammar_path is not None
                or self.generated_metadata.grammar_claim_scope is not None
            ):
                raise ValueError("non-G Cluster 3 rows must remain grammar-free")
        self._validate_grammar_mode_binding()
        self._validate_optional_metadata_binding()

    def _validate_grammar_mode_binding(self) -> None:
        metadata = self.generated_metadata
        assert metadata is not None
        derived_mode = grammar_mode_from_active_variant(
            grammar_active=self.grammar_active,
            grammar_variant=metadata.grammar_variant,
        )
        if self.grammar_mode is None:
            object.__setattr__(self, "grammar_mode", derived_mode)
        else:
            validate_grammar_mode_binding(
                grammar_mode=self.grammar_mode,
                grammar_active=self.grammar_active,
                grammar_variant=metadata.grammar_variant,
                grammar_path=metadata.grammar_path,
                grammar_claim_scope=metadata.grammar_claim_scope,
            )
        if metadata.grammar_mode is not None:
            validate_grammar_mode_binding(
                grammar_mode=metadata.grammar_mode,
                grammar_active=self.grammar_active,
                grammar_variant=metadata.grammar_variant,
                grammar_path=metadata.grammar_path,
                grammar_claim_scope=metadata.grammar_claim_scope,
            )
            if self.grammar_mode != metadata.grammar_mode:
                raise ValueError("generated_metadata.grammar_mode must match row")

    def _validate_optional_metadata_binding(self) -> None:
        metadata = self.generated_metadata
        assert metadata is not None
        optional_pairs = (
            ("terminal_source_stage", self.terminal_source_stage),
            ("terminal_attempt_index", self.terminal_attempt_index),
            ("terminal_source_hash", self.terminal_source_hash),
            ("terminal_prompt_hash", self.terminal_prompt_hash),
            ("terminal_prompt_hash_source", self.terminal_prompt_hash_source),
            ("p_repair_attempted", self.p_repair_attempted),
            ("p_compile_repair_succeeded", self.p_compile_repair_succeeded),
            ("p_repair_attempt_count", self.p_repair_attempt_count),
            ("p_history_policy", self.p_history_policy),
            ("c_loop_fired", self.c_loop_fired),
            ("c_loop_source", self.c_loop_source),
        )
        for field_name, row_value in optional_pairs:
            metadata_value = getattr(metadata, field_name)
            if metadata_value is not None and metadata_value != row_value:
                raise ValueError(f"generated_metadata.{field_name} must match row")
        _validate_agentic_p_repair_trace_metadata(
            metadata=metadata,
            p_repair_trace=self.p_repair_trace,
            p_repair_attempt_count=self.p_repair_attempt_count,
        )

    def _validate_trace_summary(self) -> None:
        if not isinstance(self.trace_summary, Cluster3TraceSummary):
            raise TypeError("generated Cluster 3 rows require trace_summary")
        trace = self.trace_summary
        if trace.condition != self.condition:
            raise ValueError("trace_summary condition must match row condition")
        if trace.initial_failure_code != self.initial_failure_code:
            raise ValueError("trace_summary initial_failure_code must match row")
        if trace.final_failure_code != self.failure_code:
            raise ValueError("trace_summary final_failure_code must match row")
        if trace.p_loop_fired is not self.p_repair_attempted:
            raise ValueError("trace_summary p_loop_fired must match row")
        if trace.p_attempt_count != self.p_repair_attempt_count:
            raise ValueError("trace_summary p_attempt_count must match row")
        if trace.p_terminal_failure_code != self.p_terminal_failure_code:
            raise ValueError("trace_summary p_terminal_failure_code must match row")
        if trace.p_compile_repair_succeeded is not self.p_compile_repair_succeeded:
            raise ValueError(
                "trace_summary p_compile_repair_succeeded must match row"
            )
        if trace.c_loop_fired is not self.c_loop_fired:
            raise ValueError("trace_summary c_loop_fired must match row")
        if trace.c_loop_source != self.c_loop_source:
            raise ValueError("trace_summary c_loop_source must match row")
        expected_c_attempt_count = len(self.repair_trace or ()) if self.c_loop_fired else 0
        if trace.c_attempt_count != expected_c_attempt_count:
            raise ValueError("trace_summary c_attempt_count must match repair_trace")
        if trace.c_terminal_failure_code != self.c_terminal_failure_code:
            raise ValueError("trace_summary c_terminal_failure_code must match row")
        if trace.terminal_source_stage != self.terminal_source_stage:
            raise ValueError("trace_summary terminal_source_stage must match row")
        if trace.terminal_attempt_index != self.terminal_attempt_index:
            raise ValueError("trace_summary terminal_attempt_index must match row")
        if trace.terminal_source_hash != self.terminal_source_hash:
            raise ValueError("trace_summary terminal_source_hash must match row")
        if trace.row_source_hash != self.source_hash:
            raise ValueError("trace_summary row_source_hash must match row")
        if trace.terminal_generation_seed != self.terminal_generation_seed:
            raise ValueError("trace_summary terminal_generation_seed must match row")
        if trace.terminal_prompt_hash != self.terminal_prompt_hash:
            raise ValueError("trace_summary terminal_prompt_hash must match row")
        if trace.terminal_prompt_hash_source != self.terminal_prompt_hash_source:
            raise ValueError("trace_summary terminal_prompt_hash_source must match row")
        if trace.compile_success is not self.compile_success:
            raise ValueError("trace_summary compile_success must match row")
        if trace.functional_success is not self.functional_success:
            raise ValueError("trace_summary functional_success must match row")
        if trace.repair_set_success is not self.repair_set_success:
            raise ValueError("trace_summary repair_set_success must match row")
        if trace.eval_set_success is not self.eval_set_success:
            raise ValueError("trace_summary eval_set_success must match row")
        if trace.private_eval_data_included is not False:
            raise ValueError("trace_summary private_eval_data_included must be False")

    def canonical_key(self) -> tuple[str, str, str, int, str, int]:
        return (
            self.kernel_class,
            self.kernel_name,
            self.dtype,
            self.base_seed,
            self.condition,
            self.attempt_index,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster3EvalRow":
        if not isinstance(payload, dict):
            raise TypeError("Cluster3EvalRow.from_dict requires a dict")
        _reject_unknown_fields(cls, payload)
        converted = dict(payload)
        trace_summary = converted.get("trace_summary")
        if trace_summary is not None and not isinstance(
            trace_summary,
            Cluster3TraceSummary,
        ):
            converted["trace_summary"] = Cluster3TraceSummary.from_dict(trace_summary)
        repair_trace = converted.get("repair_trace")
        if repair_trace is not None:
            if not isinstance(repair_trace, list | tuple):
                raise ValueError("repair_trace must be a list when present")
            converted["repair_trace"] = tuple(
                item if isinstance(item, TraceSummary) else TraceSummary.from_dict(item)
                for item in repair_trace
            )
        p_repair_trace = converted.get("p_repair_trace")
        if p_repair_trace is not None:
            if not isinstance(p_repair_trace, list | tuple):
                raise ValueError("p_repair_trace must be a list when present")
            converted["p_repair_trace"] = tuple(
                item
                if isinstance(item, PRepairAttemptSummary)
                else PRepairAttemptSummary.from_dict(item)
                for item in p_repair_trace
            )
        replay_metadata = converted.get("replay_metadata")
        if replay_metadata is not None and not isinstance(
            replay_metadata,
            Cluster3ReplayRowMetadata,
        ):
            converted["replay_metadata"] = Cluster3ReplayRowMetadata.from_dict(
                replay_metadata
            )
        generated_metadata = converted.get("generated_metadata")
        if generated_metadata is not None and not isinstance(
            generated_metadata,
            Cluster3GeneratedRowMetadata,
        ):
            converted["generated_metadata"] = Cluster3GeneratedRowMetadata.from_dict(
                generated_metadata
            )
        return cls(**converted)

    @classmethod
    def from_json(cls, payload: str) -> "Cluster3EvalRow":
        if not isinstance(payload, str):
            raise TypeError("Cluster3EvalRow.from_json requires a string")
        return cls.from_dict(json.loads(payload))


@dataclass(frozen=True)
class Cluster3OptionalDiagnostics:
    """Optional diagnostics sidecars. Their paths are never required."""

    full_trace_sidecar_path: str | None = None
    private_eval_sidecar_path: str | None = None

    def __post_init__(self) -> None:
        _require_optional_non_empty_str(
            self.full_trace_sidecar_path,
            "full_trace_sidecar_path",
        )
        _require_optional_non_empty_str(
            self.private_eval_sidecar_path,
            "private_eval_sidecar_path",
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster3OptionalDiagnostics":
        return _from_dict_strict(cls, payload)


@dataclass(frozen=True)
class Cluster3ContentHashSidecar:
    """Deterministic Cluster 3 hash sidecar."""

    schema_version: int
    eval_pipeline_hashes: dict[str, str]
    generated_condition_hashes: dict[str, dict[str, str]]
    replay_control_hashes: dict[str, dict[str, str]]
    external_pins: dict[str, str]
    optional_diagnostics: Cluster3OptionalDiagnostics | None = None

    def __post_init__(self) -> None:
        if self.schema_version != CLUSTER3_RESULTS_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {CLUSTER3_RESULTS_SCHEMA_VERSION}"
            )
        _validate_hash_mapping(
            self.eval_pipeline_hashes,
            "eval_pipeline_hashes",
            require_non_empty=True,
        )
        _validate_condition_hash_mapping(
            self.generated_condition_hashes,
            "generated_condition_hashes",
            allowed_conditions=CLUSTER3_CONDITIONS,
        )
        _validate_condition_hash_mapping(
            self.replay_control_hashes,
            "replay_control_hashes",
            allowed_conditions=REPLAY_CONTROL_CONDITIONS,
        )
        _validate_string_mapping(self.external_pins, "external_pins")
        if self.optional_diagnostics is not None and not isinstance(
            self.optional_diagnostics,
            Cluster3OptionalDiagnostics,
        ):
            raise TypeError(
                "optional_diagnostics must be Cluster3OptionalDiagnostics or None"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    def content_signature_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "eval_pipeline_hashes": self.eval_pipeline_hashes,
            "generated_condition_hashes": self.generated_condition_hashes,
            "replay_control_hashes": self.replay_control_hashes,
            "external_pins": self.external_pins,
        }

    def content_signature_sha256(self) -> str:
        payload = _json_dumps(self.content_signature_dict())
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def require_hash_compatible(self, other: "Cluster3ContentHashSidecar") -> None:
        if not isinstance(other, Cluster3ContentHashSidecar):
            raise TypeError("other must be a Cluster3ContentHashSidecar")
        if self.content_signature_dict() != other.content_signature_dict():
            raise ValueError("content-hash sidecar mismatch")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster3ContentHashSidecar":
        if not isinstance(payload, dict):
            raise TypeError("Cluster3ContentHashSidecar.from_dict requires a dict")
        _reject_unknown_fields(cls, payload)
        converted = dict(payload)
        optional_diagnostics = converted.get("optional_diagnostics")
        if optional_diagnostics is not None and not isinstance(
            optional_diagnostics,
            Cluster3OptionalDiagnostics,
        ):
            converted["optional_diagnostics"] = Cluster3OptionalDiagnostics.from_dict(
                optional_diagnostics
            )
        return cls(**converted)


def generated_row(
    *,
    condition: str,
    attempt_index: int,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    source_hash: str,
    functional_success: bool,
    repair_set_success: bool,
    eval_set_success: bool,
    failure_code: str | None,
    trace_summary: Cluster3TraceSummary,
    c3_generation_hashes: dict[str, str],
    grammar_active: bool | None = None,
    grammar_mode: str | None = None,
    compile_success: bool | None = None,
    repair_trace: Sequence[TraceSummary] | None = None,
    generation_seed: int | None = None,
    initial_failure_code: str | None = None,
    p_repair_attempted: bool = False,
    p_compile_repair_succeeded: bool = False,
    p_repair_changed_terminal_class: bool = False,
    p_repair_budget: int = DEFAULT_P_REPAIR_BUDGET,
    p_repair_attempt_count: int = 0,
    p_initial_failure_code: str | None = None,
    p_terminal_failure_code: str | None = None,
    c_loop_fired: bool = False,
    c_loop_source: CTraceSource = "none",
    c_terminal_failure_code: str | None = None,
    c_terminal_level_reached: int | None = None,
    p_compile_error_class: str | None = None,
    p_raw_error_excerpt_sha256: str | None = None,
    p_repair_stop_reason: str = "p_not_applicable",
    p_feedback_format: str = P_FEEDBACK_FORMAT_V1,
    p_history_policy: str = P_HISTORY_POLICY_V1,
    p_repair_prompt_template_version: str | None = None,
    p_repair_prompt_renderer_version: str | None = None,
    p_repair_anchor_attempt_index: int | None = None,
    p_repair_latest_attempt_index: int | None = None,
    p_repair_history_attempt_count: int | None = None,
    p_repair_prompt_sha256: str | None = None,
    p_repair_prompt_char_count: int | None = None,
    p_repair_max_prompt_chars: int | None = None,
    p_repair_include_latest_source: bool | None = None,
    p_repair_anchor_source_hash: str | None = None,
    p_repair_latest_source_hash: str | None = None,
    p_repair_history_summary_sha256: str | None = None,
    p_repair_history_error_code: str | None = None,
    p_repair_trace: Sequence[PRepairAttemptSummary] | None = None,
    terminal_prompt_hash: str | None,
    terminal_prompt_hash_source: PromptHashSource,
    terminal_source_stage: TerminalSourceStage = "initial",
    terminal_generation_seed: int | None = None,
    terminal_attempt_index: int | None = 0,
    terminal_source_hash: str | None = None,
    terminal_source_matches_row_source: bool = True,
    replay_metadata: Cluster3ReplayRowMetadata | None = None,
    **metadata_overrides: Any,
) -> Cluster3EvalRow:
    """Build a generated Cluster 3 row with terminal-source provenance."""

    normalized = normalize_cluster3_condition(condition)
    resolved_grammar_active = (
        normalized in {"G+P", "G+C+P"}
        if grammar_active is None
        else grammar_active
    )
    resolved_terminal_generation_seed = (
        generation_seed
        if terminal_generation_seed is None and generation_seed is not None
        else terminal_generation_seed
    )
    if resolved_terminal_generation_seed is None:
        raise ValueError("generation_seed or terminal_generation_seed is required")
    resolved_terminal_source_hash = terminal_source_hash or source_hash
    resolved_compile_success = _resolve_compile_success(
        compile_success,
        functional_success=functional_success,
        failure_code=failure_code,
    )
    metadata_payload = dict(metadata_overrides)
    metadata_payload.setdefault(
        "grammar_mode",
        grammar_mode_from_active_variant(
            grammar_active=resolved_grammar_active,
            grammar_variant=metadata_payload.get("grammar_variant"),
        ),
    )
    if grammar_mode is not None and metadata_payload["grammar_mode"] != grammar_mode:
        raise ValueError("grammar_mode must match metadata grammar_mode")
    return Cluster3EvalRow(
        condition=normalized,
        source_class=GENERATED_SOURCE_CLASS,
        generation_mode=generation_mode_for_cluster3_condition(normalized),
        attempt_index=attempt_index,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        source_hash=source_hash,
        grammar_active=resolved_grammar_active,
        compile_success=resolved_compile_success,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
        failure_code=failure_code,
        trace_summary=trace_summary,
        replay_metadata=replay_metadata,
        generated_metadata=Cluster3GeneratedRowMetadata(
            c3_generation_hashes=c3_generation_hashes,
            generation_seed=resolved_terminal_generation_seed,
            terminal_source_stage=terminal_source_stage,
            terminal_attempt_index=terminal_attempt_index,
            terminal_source_hash=resolved_terminal_source_hash,
            terminal_prompt_hash=terminal_prompt_hash,
            terminal_prompt_hash_source=terminal_prompt_hash_source,
            p_repair_attempted=p_repair_attempted,
            p_compile_repair_succeeded=p_compile_repair_succeeded,
            p_repair_attempt_count=p_repair_attempt_count,
            p_history_policy=p_history_policy,
            p_repair_prompt_template_version=p_repair_prompt_template_version,
            p_repair_prompt_renderer_version=p_repair_prompt_renderer_version,
            p_repair_anchor_attempt_index=p_repair_anchor_attempt_index,
            p_repair_latest_attempt_index=p_repair_latest_attempt_index,
            p_repair_history_attempt_count=p_repair_history_attempt_count,
            p_repair_prompt_sha256=p_repair_prompt_sha256,
            p_repair_prompt_char_count=p_repair_prompt_char_count,
            p_repair_max_prompt_chars=p_repair_max_prompt_chars,
            p_repair_include_latest_source=p_repair_include_latest_source,
            p_repair_anchor_source_hash=p_repair_anchor_source_hash,
            p_repair_latest_source_hash=p_repair_latest_source_hash,
            p_repair_history_summary_sha256=p_repair_history_summary_sha256,
            p_repair_history_error_code=p_repair_history_error_code,
            c_loop_fired=c_loop_fired,
            c_loop_source=c_loop_source,
            **metadata_payload,
        ),
        repair_trace=None if repair_trace is None else tuple(repair_trace),
        initial_failure_code=initial_failure_code,
        p_repair_attempted=p_repair_attempted,
        p_compile_repair_succeeded=p_compile_repair_succeeded,
        p_repair_changed_terminal_class=p_repair_changed_terminal_class,
        p_repair_budget=p_repair_budget,
        p_repair_attempt_count=p_repair_attempt_count,
        p_initial_failure_code=p_initial_failure_code,
        p_terminal_failure_code=p_terminal_failure_code,
        c_loop_fired=c_loop_fired,
        c_loop_source=c_loop_source,
        c_terminal_failure_code=c_terminal_failure_code,
        c_terminal_level_reached=c_terminal_level_reached,
        p_compile_error_class=p_compile_error_class,
        p_raw_error_excerpt_sha256=p_raw_error_excerpt_sha256,
        p_repair_stop_reason=p_repair_stop_reason,
        p_feedback_format=p_feedback_format,
        p_history_policy=p_history_policy,
        p_repair_trace=None if p_repair_trace is None else tuple(p_repair_trace),
        terminal_source_stage=terminal_source_stage,
        terminal_generation_seed=resolved_terminal_generation_seed,
        terminal_attempt_index=terminal_attempt_index,
        terminal_source_hash=resolved_terminal_source_hash,
        terminal_prompt_hash=terminal_prompt_hash,
        terminal_prompt_hash_source=terminal_prompt_hash_source,
        terminal_source_matches_row_source=terminal_source_matches_row_source,
        grammar_mode=grammar_mode,
    )


def replay_control_row(
    *,
    replay_metadata: Cluster3ReplayRowMetadata,
    **generated_row_kwargs: Any,
) -> Cluster3EvalRow:
    """Build a Cluster 3 row carrying no-P control metadata for pair checks."""

    if not isinstance(replay_metadata, Cluster3ReplayRowMetadata):
        raise TypeError("replay_metadata must be Cluster3ReplayRowMetadata")
    return generated_row(replay_metadata=replay_metadata, **generated_row_kwargs)


def _resolve_compile_success(
    compile_success: bool | None,
    *,
    functional_success: bool,
    failure_code: str | None,
) -> bool:
    if compile_success is not None:
        _require_bool(compile_success, "compile_success")
        return compile_success
    if functional_success:
        return True
    if isinstance(failure_code, str) and failure_code.startswith("F2_"):
        return True
    return False


def _validate_compile_success_consistency(
    *,
    compile_success: bool,
    functional_success: bool,
    failure_code: str | None,
) -> None:
    if functional_success and not compile_success:
        raise ValueError("functional_success=True requires compile_success=True")
    if failure_code is None:
        return
    if failure_code.startswith(("F0_", "F1_")) and compile_success:
        raise ValueError(f"{failure_code} requires compile_success=False")
    if failure_code.startswith("F2_") and not compile_success:
        raise ValueError(f"{failure_code} requires compile_success=True")


def _p_changed_terminal_class(
    p_initial_failure_code: str | None,
    p_terminal_failure_code: str | None,
) -> bool:
    return (
        p_initial_failure_code != p_terminal_failure_code
        or (p_initial_failure_code is not None and p_terminal_failure_code is None)
    )


def _is_f0_or_f1(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith(("F0_", "F1_"))


def _is_f2(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith("F2_")


def _is_f3(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith("F3_")


def _is_non_repairable_p_terminal(value: str | None) -> bool:
    return isinstance(value, str) and (
        value.startswith("F0_") or value == "F1_RUNTIME"
    )


def _validate_p_stop_reason_terminal_outcome(
    *,
    stop_reason: str,
    terminal_failure_code: str | None,
    compile_repair_succeeded: bool,
) -> None:
    if stop_reason == "p_compile_repaired_then_success":
        valid = terminal_failure_code is None and compile_repair_succeeded is True
    elif stop_reason == "p_compile_repaired_f2_observed":
        valid = _is_f2(terminal_failure_code) and compile_repair_succeeded is True
    elif stop_reason == "p_post_compile_f3_observed":
        valid = _is_f3(terminal_failure_code) and compile_repair_succeeded is True
    elif stop_reason == "p_f3_without_compile_evidence":
        valid = _is_f3(terminal_failure_code) and compile_repair_succeeded is False
    elif stop_reason == "p_budget_exhausted":
        valid = (
            terminal_failure_code == "F1_COMPILE"
            and compile_repair_succeeded is False
        )
    elif stop_reason == "p_terminal_non_repairable":
        valid = (
            _is_non_repairable_p_terminal(terminal_failure_code)
            and compile_repair_succeeded is False
        )
    else:
        return
    if not valid:
        raise ValueError(
            "p_repair_stop_reason/p_compile_repair_succeeded must match "
            "P terminal outcome"
        )


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _from_dict_strict(cls: type[Any], payload: dict[str, Any]) -> Any:
    if not isinstance(payload, dict):
        raise TypeError(f"{cls.__name__}.from_dict requires a dict")
    _reject_unknown_fields(cls, payload)
    try:
        return cls(**payload)
    except TypeError as exc:
        raise ValueError(f"invalid {cls.__name__} payload: {exc}") from exc


def _reject_unknown_fields(cls: type[Any], payload: dict[str, Any]) -> None:
    field_names = {field.name for field in fields(cls)}
    unknown = sorted(set(payload) - field_names)
    if unknown:
        raise ValueError(f"unknown {cls.__name__} fields: {', '.join(unknown)}")


def _validate_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_name} must be a 64-character SHA256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a SHA256 hex digest") from exc


def _validate_optional_sha256(value: str | None, field_name: str) -> None:
    if value is None:
        return
    _validate_sha256(value, field_name)


def _validate_failure_code(value: str, field_name: str) -> None:
    if value not in FAILURE_CODES:
        raise ValueError(f"{field_name} must be canonical; got {value!r}")


def _validate_optional_failure_code(value: str | None, field_name: str) -> None:
    if value is None:
        return
    _validate_failure_code(value, field_name)


def _validate_hash_mapping(
    value: dict[str, str],
    field_name: str,
    *,
    require_non_empty: bool = False,
) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dict")
    if require_non_empty and not value:
        raise ValueError(f"{field_name} must not be empty")
    for key, digest in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field_name} keys must be non-empty strings")
        _validate_sha256(digest, f"{field_name}[{key!r}]")


def _validate_generated_grammar_metadata(
    *,
    grammar_variant: str | None,
    grammar_path: str | None,
    grammar_claim_scope: str | None,
) -> None:
    if grammar_variant is None:
        if grammar_path is not None:
            raise ValueError("grammar_path must be None without grammar_variant")
        if grammar_claim_scope is not None:
            raise ValueError(
                "grammar_claim_scope must be None without grammar_variant"
            )
        return

    if grammar_variant not in GRAMMAR_PATHS_BY_VARIANT:
        allowed = ", ".join(sorted(GRAMMAR_PATHS_BY_VARIANT))
        raise ValueError(
            f"grammar_variant must be one of: {allowed}; got {grammar_variant!r}"
        )
    expected_path = GRAMMAR_PATHS_BY_VARIANT[grammar_variant]
    if grammar_path != expected_path and not str(grammar_path).endswith(expected_path):
        raise ValueError("grammar_path does not match grammar_variant")
    if grammar_claim_scope != GRAMMAR_CLAIM_SCOPE_BY_VARIANT[grammar_variant]:
        raise ValueError("grammar_claim_scope does not match grammar_variant")


def _validate_generated_runtime_metadata(
    *,
    generation_metadata_schema_version: int,
    grammar_variant: str | None,
    grammar_sha: str | None,
    gbnf_parse_valid: bool | None,
    semantic_valid: bool | None,
    grammar_valid: bool | None,
    rejection_layer: str | None,
    stop_reason: str,
    modal_image_sha: str | None,
    modal_image_provenance_sha256: str | None,
    modal_image_provenance_components: dict[str, Any] | None,
) -> None:
    _require_non_negative_int(
        generation_metadata_schema_version,
        "generation_metadata_schema_version",
    )
    if stop_reason not in VALID_STOP_REASONS:
        allowed = ", ".join(sorted(VALID_STOP_REASONS))
        raise ValueError(f"stop_reason must be one of {allowed}; got {stop_reason!r}")
    if rejection_layer is not None and rejection_layer not in VALID_REJECTION_LAYERS:
        allowed = ", ".join(sorted(VALID_REJECTION_LAYERS))
        raise ValueError(
            f"rejection_layer must be one of {allowed} or None; "
            f"got {rejection_layer!r}"
        )
    _validate_optional_sha256(grammar_sha, "grammar_sha")
    _validate_optional_bool(gbnf_parse_valid, "gbnf_parse_valid")
    _validate_optional_bool(semantic_valid, "semantic_valid")
    _validate_optional_bool(grammar_valid, "grammar_valid")
    _validate_optional_stable_image_sha(modal_image_sha, "modal_image_sha")
    _validate_optional_sha256(
        modal_image_provenance_sha256,
        "modal_image_provenance_sha256",
    )
    _validate_modal_image_provenance_components(
        modal_image_provenance_sha256=modal_image_provenance_sha256,
        modal_image_provenance_components=modal_image_provenance_components,
    )
    if (
        generation_metadata_schema_version
        >= CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
        and modal_image_sha in (None, UNKNOWN)
    ):
        if not modal_image_provenance_sha256:
            raise ValueError(
                "current-schema generated metadata with unknown modal_image_sha "
                "requires modal_image_provenance_sha256"
            )
        if modal_image_provenance_components is None:
            raise ValueError(
                "current-schema generated metadata with unknown modal_image_sha "
                "requires modal_image_provenance_components"
            )
    validation_values = (gbnf_parse_valid, semantic_valid, grammar_valid)
    if grammar_variant is None:
        if grammar_sha is not None:
            raise ValueError("grammar_sha must be None without grammar_variant")
        if any(value is not None for value in validation_values):
            raise ValueError(
                "grammar validation fields must be None without grammar_variant"
            )
        return
    if generation_metadata_schema_version >= CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION:
        missing_current_schema_fields = [
            field_name
            for field_name, value in (
                ("grammar_sha", grammar_sha),
                ("gbnf_parse_valid", gbnf_parse_valid),
                ("semantic_valid", semantic_valid),
                ("grammar_valid", grammar_valid),
            )
            if value is None
        ]
        if missing_current_schema_fields:
            missing = ", ".join(sorted(missing_current_schema_fields))
            raise ValueError(
                "current-schema generated grammar metadata requires: "
                f"{missing}"
            )
    if all(value is not None for value in validation_values):
        expected = bool(gbnf_parse_valid and semantic_valid)
        if grammar_valid is not expected:
            raise ValueError(
                "grammar_valid must equal gbnf_parse_valid and semantic_valid"
            )
        if grammar_valid and rejection_layer is not None:
            raise ValueError("rejection_layer must be None when grammar_valid=True")
        if not grammar_valid and rejection_layer is None:
            raise ValueError("rejection_layer is required when grammar_valid=False")


def _validate_optional_stable_image_sha(value: str | None, field_name: str) -> None:
    if value is None or value == UNKNOWN:
        return
    if not is_stable_modal_image_identifier(value):
        raise ValueError(f"{field_name} must be a stable Modal image identifier")


def _validate_modal_image_provenance_components(
    *,
    modal_image_provenance_sha256: str | None,
    modal_image_provenance_components: dict[str, Any] | None,
) -> None:
    if modal_image_provenance_components is None:
        return
    if modal_image_provenance_sha256 is None:
        raise ValueError(
            "modal_image_provenance_sha256 is required when "
            "modal_image_provenance_components is present"
        )
    expected = modal_image_provenance_digest(modal_image_provenance_components)
    if modal_image_provenance_sha256 != expected:
        raise ValueError(
            "modal_image_provenance_sha256 must equal the digest of "
            "modal_image_provenance_components"
        )


def _validate_p_repair_history_metadata(
    *,
    p_history_policy: str,
    p_repair_prompt_template_version: str | None,
    p_repair_prompt_renderer_version: str | None,
    p_repair_anchor_attempt_index: int | None,
    p_repair_latest_attempt_index: int | None,
    p_repair_history_attempt_count: int | None,
    p_repair_prompt_sha256: str | None,
    p_repair_prompt_char_count: int | None,
    p_repair_max_prompt_chars: int | None,
    p_repair_include_latest_source: bool | None,
    p_repair_anchor_source_hash: str | None,
    p_repair_latest_source_hash: str | None,
    p_repair_history_summary_sha256: str | None,
    p_repair_history_error_code: str | None,
) -> None:
    if not isinstance(p_history_policy, str):
        raise TypeError("p_history_policy must be a string")
    if p_history_policy not in REPAIR_HISTORY_POLICIES_V1:
        raise ValueError(f"unsupported p_history_policy {p_history_policy!r}")
    _require_optional_non_empty_str(
        p_repair_prompt_template_version,
        "p_repair_prompt_template_version",
    )
    _require_optional_non_empty_str(
        p_repair_prompt_renderer_version,
        "p_repair_prompt_renderer_version",
    )
    _require_optional_non_empty_str(
        p_repair_history_error_code,
        "p_repair_history_error_code",
    )
    for field_name, value in (
        ("p_repair_anchor_attempt_index", p_repair_anchor_attempt_index),
        ("p_repair_latest_attempt_index", p_repair_latest_attempt_index),
        ("p_repair_history_attempt_count", p_repair_history_attempt_count),
    ):
        if value is not None:
            _require_non_negative_int(value, field_name)
    for field_name, value in (
        ("p_repair_prompt_char_count", p_repair_prompt_char_count),
        ("p_repair_max_prompt_chars", p_repair_max_prompt_chars),
    ):
        if value is not None:
            _require_positive_int(value, field_name)
    if p_repair_include_latest_source is not None:
        _require_bool(p_repair_include_latest_source, "p_repair_include_latest_source")
    for field_name, value in (
        ("p_repair_prompt_sha256", p_repair_prompt_sha256),
        ("p_repair_anchor_source_hash", p_repair_anchor_source_hash),
        ("p_repair_latest_source_hash", p_repair_latest_source_hash),
        ("p_repair_history_summary_sha256", p_repair_history_summary_sha256),
    ):
        _validate_optional_sha256(value, field_name)
    _validate_agentic_p_rendered_metadata(
        p_history_policy=p_history_policy,
        p_repair_prompt_template_version=p_repair_prompt_template_version,
        p_repair_prompt_renderer_version=p_repair_prompt_renderer_version,
        p_repair_anchor_attempt_index=p_repair_anchor_attempt_index,
        p_repair_latest_attempt_index=p_repair_latest_attempt_index,
        p_repair_history_attempt_count=p_repair_history_attempt_count,
        p_repair_prompt_sha256=p_repair_prompt_sha256,
        p_repair_prompt_char_count=p_repair_prompt_char_count,
        p_repair_max_prompt_chars=p_repair_max_prompt_chars,
        p_repair_include_latest_source=p_repair_include_latest_source,
        p_repair_anchor_source_hash=p_repair_anchor_source_hash,
        p_repair_latest_source_hash=p_repair_latest_source_hash,
        p_repair_history_summary_sha256=p_repair_history_summary_sha256,
    )


def _validate_agentic_p_rendered_metadata(
    *,
    p_history_policy: str,
    p_repair_prompt_template_version: str | None,
    p_repair_prompt_renderer_version: str | None,
    p_repair_anchor_attempt_index: int | None,
    p_repair_latest_attempt_index: int | None,
    p_repair_history_attempt_count: int | None,
    p_repair_prompt_sha256: str | None,
    p_repair_prompt_char_count: int | None,
    p_repair_max_prompt_chars: int | None,
    p_repair_include_latest_source: bool | None,
    p_repair_anchor_source_hash: str | None,
    p_repair_latest_source_hash: str | None,
    p_repair_history_summary_sha256: str | None,
) -> None:
    if p_history_policy != AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1:
        return
    required_fields = {
        "p_repair_prompt_template_version": p_repair_prompt_template_version,
        "p_repair_prompt_renderer_version": p_repair_prompt_renderer_version,
        "p_repair_anchor_attempt_index": p_repair_anchor_attempt_index,
        "p_repair_latest_attempt_index": p_repair_latest_attempt_index,
        "p_repair_history_attempt_count": p_repair_history_attempt_count,
        "p_repair_prompt_sha256": p_repair_prompt_sha256,
        "p_repair_prompt_char_count": p_repair_prompt_char_count,
        "p_repair_max_prompt_chars": p_repair_max_prompt_chars,
        "p_repair_include_latest_source": p_repair_include_latest_source,
        "p_repair_anchor_source_hash": p_repair_anchor_source_hash,
        "p_repair_latest_source_hash": p_repair_latest_source_hash,
        "p_repair_history_summary_sha256": p_repair_history_summary_sha256,
    }
    if all(value is None for value in required_fields.values()):
        return
    missing = sorted(
        field_name
        for field_name, value in required_fields.items()
        if value is None
    )
    if missing:
        raise ValueError(
            "agentic_transcript_v1 P metadata requires rendered prompt fields: "
            + ", ".join(missing)
        )
    if (
        p_repair_history_attempt_count is not None
        and p_repair_history_attempt_count <= 0
    ):
        raise ValueError(
            "p_repair_history_attempt_count must be positive for "
            "agentic_transcript_v1 rendered P metadata"
        )
    if (
        p_repair_latest_attempt_index is not None
        and p_repair_history_attempt_count is not None
        and p_repair_latest_attempt_index != p_repair_history_attempt_count - 1
    ):
        raise ValueError(
            "p_repair_latest_attempt_index must equal "
            "p_repair_history_attempt_count - 1 for "
            "agentic_transcript_v1 rendered P metadata"
        )
    if (
        p_repair_anchor_attempt_index is not None
        and p_repair_history_attempt_count is not None
        and p_repair_anchor_attempt_index >= p_repair_history_attempt_count
    ):
        raise ValueError(
            "p_repair_anchor_attempt_index must be less than "
            "p_repair_history_attempt_count for "
            "agentic_transcript_v1 rendered P metadata"
        )


def _validate_agentic_p_repair_trace_metadata(
    *,
    metadata: Cluster3GeneratedRowMetadata,
    p_repair_trace: tuple[PRepairAttemptSummary, ...] | None,
    p_repair_attempt_count: int,
) -> None:
    if metadata.p_history_policy != AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1:
        return
    if metadata.p_repair_history_attempt_count is None:
        if p_repair_attempt_count > 0:
            raise ValueError(
                "agentic_transcript_v1 P repair rows require rendered prompt metadata"
            )
        if p_repair_trace is not None and len(p_repair_trace) > 1:
            raise ValueError(
                "agentic_transcript_v1 multi-attempt P repair_trace requires "
                "rendered prompt metadata"
            )
        return
    if p_repair_trace is None:
        return

    history_count = metadata.p_repair_history_attempt_count
    if p_repair_attempt_count != history_count:
        raise ValueError(
            "p_repair_attempt_count must equal p_repair_history_attempt_count "
            "for agentic_transcript_v1 rendered P metadata"
        )
    expected_trace_length = history_count + 1
    if len(p_repair_trace) != expected_trace_length:
        raise ValueError(
            "p_repair_trace length must equal p_repair_history_attempt_count + 1 "
            "for agentic_transcript_v1 rendered P metadata"
        )
    traces_by_attempt: dict[int, PRepairAttemptSummary] = {}
    for trace in p_repair_trace:
        if trace.attempt_index in traces_by_attempt:
            raise ValueError(
                "p_repair_trace attempt indexes must be unique for "
                "agentic_transcript_v1 rendered P metadata"
            )
        traces_by_attempt[trace.attempt_index] = trace
    expected_attempt_indexes = set(range(expected_trace_length))
    if set(traces_by_attempt) != expected_attempt_indexes:
        raise ValueError(
            "p_repair_trace attempt indexes must be contiguous and zero-based for "
            "agentic_transcript_v1 rendered P metadata"
        )
    assert metadata.p_repair_anchor_attempt_index is not None
    assert metadata.p_repair_latest_attempt_index is not None
    anchor_trace = traces_by_attempt[metadata.p_repair_anchor_attempt_index]
    latest_trace = traces_by_attempt[metadata.p_repair_latest_attempt_index]
    if anchor_trace.source_hash != metadata.p_repair_anchor_source_hash:
        raise ValueError(
            "p_repair_anchor_source_hash must match p_repair_trace anchor source_hash"
        )
    if latest_trace.source_hash != metadata.p_repair_latest_source_hash:
        raise ValueError(
            "p_repair_latest_source_hash must match p_repair_trace latest source_hash"
        )


def _validate_condition_hash_mapping(
    value: dict[str, dict[str, str]],
    field_name: str,
    *,
    allowed_conditions: tuple[str, ...],
) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dict")
    for condition, hashes in value.items():
        if condition not in allowed_conditions:
            allowed = ", ".join(allowed_conditions)
            raise ValueError(
                f"{field_name} condition {condition!r} must be one of: {allowed}"
            )
        _validate_hash_mapping(
            hashes,
            f"{field_name}[{condition!r}]",
            require_non_empty=True,
        )


def _validate_string_mapping(value: dict[str, str], field_name: str) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dict")
    for key, string_value in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field_name} keys must be non-empty strings")
        if not isinstance(string_value, str) or not string_value:
            raise ValueError(f"{field_name}[{key!r}] must be a non-empty string")


def _validate_locked_kernel_identity(kernel_class: str, kernel_name: str) -> None:
    if kernel_class not in LOCKED_KERNEL_CLASSES:
        allowed = ", ".join(LOCKED_KERNEL_CLASSES)
        raise ValueError(f"unsupported kernel_class {kernel_class!r}; allowed: {allowed}")
    _require_non_empty_str(kernel_name, "kernel_name")
    expected_kernel_name = get_shape_metadata(kernel_class).kernel_name
    if kernel_name != expected_kernel_name:
        raise ValueError(
            f"kernel_class {kernel_class!r} requires kernel_name "
            f"{expected_kernel_name!r}; got {kernel_name!r}"
        )


def _validate_terminal_source_stage(value: str) -> None:
    if value not in _TERMINAL_SOURCE_STAGES:
        raise ValueError(
            "terminal_source_stage must be one of: "
            f"{', '.join(sorted(_TERMINAL_SOURCE_STAGES))}"
        )


def _validate_prompt_hash_source(
    prompt_hash: str | None,
    prompt_hash_source: str,
) -> None:
    if prompt_hash_source not in _TERMINAL_PROMPT_HASH_SOURCES:
        raise ValueError(
            "terminal_prompt_hash_source must be one of: "
            f"{', '.join(sorted(_TERMINAL_PROMPT_HASH_SOURCES))}"
        )
    if prompt_hash is None and prompt_hash_source != "seed_prompt_unavailable":
        raise ValueError(
            "terminal_prompt_hash is None only with seed_prompt_unavailable"
        )


def _validate_pairing_metadata(
    *,
    replay_pair_id: str | None,
    replay_base_seed: int | None,
    replay_generation_seed: int | None,
    model_id: str | None,
    model_revision: str | None,
    tokenizer_revision: str | None,
    temperature: float | None,
    max_new_tokens: int | None,
) -> None:
    _require_optional_non_empty_str(replay_pair_id, "replay_pair_id")
    _validate_optional_non_negative_int(replay_base_seed, "replay_base_seed")
    _validate_optional_non_negative_int(
        replay_generation_seed,
        "replay_generation_seed",
    )
    _require_optional_non_empty_str(model_id, "model_id")
    _require_optional_non_empty_str(model_revision, "model_revision")
    _require_optional_non_empty_str(tokenizer_revision, "tokenizer_revision")
    if temperature is not None:
        if not isinstance(temperature, int | float) or isinstance(temperature, bool):
            raise TypeError("temperature must be numeric")
        if temperature < 0:
            raise ValueError("temperature must be non-negative")
    if max_new_tokens is not None:
        _require_positive_int(max_new_tokens, "max_new_tokens")


def _require_bool(value: bool, field_name: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool")


def _validate_optional_bool(value: bool | None, field_name: str) -> None:
    if value is None:
        return
    _require_bool(value, field_name)


def _require_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _validate_optional_non_negative_int(
    value: int | None,
    field_name: str,
) -> None:
    if value is None:
        return
    _require_non_negative_int(value, field_name)


def _require_positive_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _require_non_empty_str(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")


def _require_optional_non_empty_str(value: str | None, field_name: str) -> None:
    if value is None:
        return
    _require_non_empty_str(value, field_name)
