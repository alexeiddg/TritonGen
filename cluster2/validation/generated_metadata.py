"""Schema-aware validation helpers for Cluster 2 generated result rows."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cluster2.results.dataclass import Cluster2EvalRow
from shared.eval.failure_taxonomy import FAILURE_CODES
from shared.generation_metadata import (
    CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION,
    GRAMMAR_PATHS_BY_VARIANT,
    UNKNOWN,
    is_immutable_hub_revision,
    is_stable_modal_image_identifier,
)


GENERATED_METADATA_FIELDS: frozenset[str] = frozenset(
    {
        "grammar_variant",
        "grammar_path",
        "grammar_sha",
        "grammar_claim_scope",
        "gbnf_parse_valid",
        "semantic_valid",
        "grammar_valid",
        "rejection_layer",
        "stop_reason",
        "xgrammar_version",
        "transformers_version",
        "tokenizers_version",
        "model_id",
        "model_revision",
        "tokenizer_revision",
        "modal_image_sha",
        "modal_image_provenance_sha256",
        "modal_image_provenance_components",
        "generation_metadata_schema_version",
        "generation_seed",
        "replay_pair_id",
        "replay_control_condition",
        "replay_base_seed",
        "replay_generation_seed",
        "prompt_sha256",
        "temperature",
        "max_new_tokens",
        "c2_generation_hashes",
    }
)

TOP_LEVEL_RESULT_FIELDS: frozenset[str] = frozenset(
    {
        "condition",
        "source_class",
        "generation_mode",
        "attempt_index",
        "kernel_class",
        "kernel_name",
        "dtype",
        "base_seed",
        "source_hash",
        "grammar_active",
        "compile_success",
        "functional_success",
        "repair_set_success",
        "eval_set_success",
        "failure_code",
        "trace_summary",
        "replay_metadata",
        "generated_metadata",
        "repair_trace",
    }
)

_MISSING = object()
_UNKNOWN_VALUES = {None, "", UNKNOWN}


@dataclass(frozen=True)
class GPlusCSmokeValidation:
    """Validated G+C smoke rows plus warning-only context."""

    rows: tuple[Cluster2EvalRow, ...]
    warnings: tuple[str, ...] = ()


def get_generated_metadata(row: Mapping[str, Any] | Cluster2EvalRow) -> dict[str, Any]:
    """Return current-schema ``generated_metadata`` as a dict when present."""

    payload = _row_payload(row)
    metadata = payload.get("generated_metadata")
    if isinstance(metadata, Mapping):
        return dict(metadata)
    return {}


def get_field(
    row: Mapping[str, Any] | Cluster2EvalRow,
    field_name: str,
    *,
    allow_legacy_top_level_metadata: bool = False,
) -> Any:
    """Read a field from its current schema location with optional legacy fallback."""

    payload = _row_payload(row)
    metadata = get_generated_metadata(payload)
    if field_name in TOP_LEVEL_RESULT_FIELDS:
        if field_name in payload:
            return payload[field_name]
        return _MISSING
    if field_name in GENERATED_METADATA_FIELDS:
        if field_name in metadata:
            return metadata[field_name]
        if allow_legacy_top_level_metadata and field_name in payload:
            return payload[field_name]
        return _MISSING
    if field_name in payload:
        return payload[field_name]
    if field_name in metadata:
        return metadata[field_name]
    return _MISSING


def validate_g_plus_c_smoke_jsonl(
    path: str | Path,
    *,
    expected_rows: int | None = None,
    allow_legacy_top_level_metadata: bool = False,
) -> GPlusCSmokeValidation:
    """Validate an existing G+C smoke artifact against the current C2 schema."""

    raw_rows = _load_raw_jsonl(path)
    if expected_rows is not None and len(raw_rows) != expected_rows:
        raise ValueError(f"expected {expected_rows} rows, found {len(raw_rows)}")
    return validate_g_plus_c_smoke_rows(
        raw_rows,
        allow_legacy_top_level_metadata=allow_legacy_top_level_metadata,
    )


def validate_g_plus_c_smoke_rows(
    rows: Iterable[Mapping[str, Any] | Cluster2EvalRow],
    *,
    allow_legacy_top_level_metadata: bool = False,
) -> GPlusCSmokeValidation:
    """Validate raw or dataclass G+C smoke rows without flattening metadata."""

    expected_grammar_sha = _current_task_agnostic_grammar_sha()
    failures: list[str] = []
    validated: list[Cluster2EvalRow] = []
    for row_number, row in enumerate(rows, start=1):
        payload = _row_payload(row)
        failures.extend(
            _validate_g_plus_c_smoke_payload(
                payload,
                row_number=row_number,
                expected_grammar_sha=expected_grammar_sha,
                allow_legacy_top_level_metadata=allow_legacy_top_level_metadata,
            )
        )
        if not failures:
            validated.append(
                Cluster2EvalRow.from_dict(
                    _current_schema_payload(
                        payload,
                        allow_legacy_top_level_metadata=(
                            allow_legacy_top_level_metadata
                        ),
                    )
                )
            )
    if failures:
        raise ValueError("G+C smoke validation failed: " + "; ".join(failures))
    return GPlusCSmokeValidation(rows=tuple(validated))


def _validate_g_plus_c_smoke_payload(
    payload: Mapping[str, Any],
    *,
    row_number: int,
    expected_grammar_sha: str,
    allow_legacy_top_level_metadata: bool,
) -> list[str]:
    failures: list[str] = []
    metadata = get_generated_metadata(payload)
    if not metadata and not allow_legacy_top_level_metadata:
        failures.append(_row_message(row_number, "missing generated_metadata"))

    def read(field_name: str) -> Any:
        return get_field(
            payload,
            field_name,
            allow_legacy_top_level_metadata=allow_legacy_top_level_metadata,
        )

    _expect_equal(failures, row_number, "condition", read("condition"), "G+C")
    _expect_equal(
        failures,
        row_number,
        "generation_mode",
        read("generation_mode"),
        "new_c2_generation_with_G_adapter",
    )
    _expect_equal(failures, row_number, "grammar_active", read("grammar_active"), True)

    _expect_equal(
        failures,
        row_number,
        "generated_metadata.grammar_variant",
        read("grammar_variant"),
        "task_agnostic",
    )
    grammar_path = read("grammar_path")
    expected_path = GRAMMAR_PATHS_BY_VARIANT["task_agnostic"]
    if not isinstance(grammar_path, str) or expected_path not in grammar_path:
        failures.append(
            _row_message(
                row_number,
                "generated_metadata.grammar_path must contain "
                f"{expected_path!r}; got {grammar_path!r}",
            )
        )
    _expect_equal(
        failures,
        row_number,
        "generated_metadata.grammar_sha",
        read("grammar_sha"),
        expected_grammar_sha,
    )

    for field_name in ("model_revision", "tokenizer_revision"):
        value = read(field_name)
        _require_known_string(
            failures,
            row_number,
            f"generated_metadata.{field_name}",
            value,
        )
        if isinstance(value, str) and value not in _UNKNOWN_VALUES:
            if not is_immutable_hub_revision(value):
                failures.append(
                    _row_message(
                        row_number,
                        f"generated_metadata.{field_name} must be an immutable "
                        f"Hub revision; got {value!r}",
                    )
                )

    modal_image_sha = read("modal_image_sha")
    _require_known_string(
        failures,
        row_number,
        "generated_metadata.modal_image_sha",
        modal_image_sha,
    )
    if isinstance(modal_image_sha, str) and modal_image_sha not in _UNKNOWN_VALUES:
        if not is_stable_modal_image_identifier(modal_image_sha):
            failures.append(
                _row_message(
                    row_number,
                    "generated_metadata.modal_image_sha must be a stable Modal "
                    f"image identifier; got {modal_image_sha!r}",
                )
            )

    schema_version = read("generation_metadata_schema_version")
    if schema_version is _MISSING:
        failures.append(
            _row_message(
                row_number,
                "missing generated_metadata.generation_metadata_schema_version",
            )
        )
    elif (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version < CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
    ):
        failures.append(
            _row_message(
                row_number,
                "generated_metadata.generation_metadata_schema_version must be "
                f">= {CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION}; got {schema_version!r}",
            )
        )

    for field_name in (
        "gbnf_parse_valid",
        "semantic_valid",
        "grammar_valid",
        "functional_success",
        "repair_set_success",
        "eval_set_success",
    ):
        value = read(field_name)
        if value is not True and value is not False:
            failures.append(
                _row_message(
                    row_number,
                    f"{_display_name(field_name)} must be a boolean; got {value!r}",
                )
            )

    compile_success = read("compile_success")
    if compile_success is _MISSING:
        failures.append(_row_message(row_number, "missing top-level compile_success"))
    elif compile_success is not True and compile_success is not False:
        failures.append(
            _row_message(
                row_number,
                f"top-level compile_success must be a boolean; got {compile_success!r}",
            )
        )

    failure_code = read("failure_code")
    functional_success = read("functional_success")
    if functional_success is True and failure_code is not None:
        failures.append(
            _row_message(
                row_number,
                "failure_code must be null when functional_success is true",
            )
        )
    if failure_code is not None and failure_code not in FAILURE_CODES:
        failures.append(
            _row_message(row_number, f"failure_code is not canonical: {failure_code!r}")
        )

    trace_summary = read("trace_summary")
    if not isinstance(trace_summary, Mapping):
        failures.append(_row_message(row_number, "missing trace_summary evidence"))
    elif trace_summary.get("failure_code") != failure_code:
        failures.append(
            _row_message(row_number, "trace_summary.failure_code must match row")
        )

    repair_trace = read("repair_trace")
    if not isinstance(repair_trace, list | tuple) or not repair_trace:
        failures.append(_row_message(row_number, "missing repair_trace evidence"))
    return failures


def _row_payload(row: Mapping[str, Any] | Cluster2EvalRow) -> dict[str, Any]:
    if isinstance(row, Cluster2EvalRow):
        return row.to_dict()
    if not isinstance(row, Mapping):
        raise TypeError("Cluster 2 validation rows must be mappings or Cluster2EvalRow")
    return dict(row)


def _current_schema_payload(
    payload: Mapping[str, Any],
    *,
    allow_legacy_top_level_metadata: bool,
) -> dict[str, Any]:
    current = dict(payload)
    if current.get("generated_metadata") is None and allow_legacy_top_level_metadata:
        metadata = {
            field_name: current[field_name]
            for field_name in GENERATED_METADATA_FIELDS
            if field_name in current
        }
        current["generated_metadata"] = metadata
        for field_name in GENERATED_METADATA_FIELDS:
            current.pop(field_name, None)
    return current


def _load_raw_jsonl(path: str | Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        if not line:
            raise ValueError(f"blank JSONL line at {line_number}")
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"JSONL line {line_number} is not an object")
        rows.append(payload)
    return tuple(rows)


def _current_task_agnostic_grammar_sha() -> str:
    path = _repo_root() / GRAMMAR_PATHS_BY_VARIANT["task_agnostic"]
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _require_known_string(
    failures: list[str],
    row_number: int,
    field_name: str,
    value: Any,
) -> None:
    if value is None or value == "" or value == UNKNOWN:
        failures.append(
            _row_message(row_number, f"{field_name} must not be null, empty, or unknown")
        )
    elif not isinstance(value, str):
        failures.append(
            _row_message(row_number, f"{field_name} must be a string; got {value!r}")
        )


def _expect_equal(
    failures: list[str],
    row_number: int,
    field_name: str,
    value: Any,
    expected: Any,
) -> None:
    if value != expected:
        failures.append(
            _row_message(row_number, f"{field_name} expected {expected!r}; got {value!r}")
        )


def _display_name(field_name: str) -> str:
    if field_name in GENERATED_METADATA_FIELDS:
        return f"generated_metadata.{field_name}"
    return f"top-level {field_name}"


def _row_message(row_number: int, message: str) -> str:
    return f"row {row_number}: {message}"
