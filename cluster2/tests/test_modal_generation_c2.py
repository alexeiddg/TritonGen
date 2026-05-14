"""Phase 7 tests for isolated Cluster 2 Modal generation."""

from __future__ import annotations

import builtins
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from cluster2.generation.modal_generate_c2 import (
    build_c2_generation_request,
    configured_modal_generation_gpu,
    generate_source_c2_modal,
)
from cluster2.modal import generation as c2_generation
from cluster2.modal.generation import (
    C2_GENERATION_HASH_CLASS,
    C2_G_PLUS_C_GRAMMAR_PATH,
    C2_G_PLUS_C_GRAMMAR_VARIANT,
    PHASE_MINUS1_G_GENERATION_SOURCE_HASHES,
    REMOTE_C2_GENERATION_GPU,
    current_remote_generator_generate_one_hash,
    expected_phase_minus1_remote_generator_generate_one_hash,
    generation_routing_for_condition,
    remote_c2_generator_for_gpu,
    run_c2_generation_with_loaded_model,
    validate_remote_c2_generation_payload,
    verify_phase_minus1_g_generation_hashes,
    verify_phase_minus1_remote_generator_hash,
)
from cluster2.modal.schemas import (
    FORBIDDEN_REQUEST_RESULT_FIELD_NAMES,
    EvalIdentity,
    RemoteC2GenerationRequest,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_MODAL_GENERATION_PATH = REPO_ROOT / "shared" / "modal_harness" / "generation.py"
SHARED_MODAL_SCHEMAS_PATH = REPO_ROOT / "shared" / "modal_harness" / "schemas.py"
SHARED_MODAL_SMOKE_PATH = REPO_ROOT / "shared" / "modal_harness" / "smoke.py"


@dataclass(frozen=True)
class FakeDecoded:
    source: str
    generation_seed: int | None


def test_c2_generation_request_rejects_none_and_g() -> None:
    for condition in ("none", "G"):
        with pytest.raises(ValueError, match="must not invoke C2 generation"):
            RemoteC2GenerationRequest(**_request_payload(condition))


def test_c2_generation_request_accepts_c_and_g_plus_c() -> None:
    c_request = build_c2_generation_request(**_adapter_kwargs("C"))
    gc_request = build_c2_generation_request(**_adapter_kwargs("G+C"))

    assert c_request.identity.condition == "C"
    assert gc_request.identity.condition == "G+C"


def test_no_generation_path_exists_for_none_or_g() -> None:
    called = False

    def fake_remote_call(_: dict[str, Any]) -> dict[str, Any]:
        nonlocal called
        called = True
        raise AssertionError("replay controls must not call remote generation")

    for condition in ("none", "G"):
        with pytest.raises(ValueError, match="must not invoke C2 generation"):
            generate_source_c2_modal(
                **_adapter_kwargs(condition),
                remote_call=fake_remote_call,
            )
    assert called is False


def test_c_generation_passes_grammar_inactive() -> None:
    calls: list[dict[str, Any]] = []

    def fake_generate_source(**kwargs: Any) -> FakeDecoded:
        calls.append(kwargs)
        return FakeDecoded(source=_relu_source(), generation_seed=kwargs["seed"])

    payload = run_c2_generation_with_loaded_model(
        _request_payload("C"),
        model=object(),
        tokenizer=object(),
        tokenizer_grammar_id="snapshot://tokenizer-rev",
        loaded_model_id="model",
        loaded_model_revision="model-rev",
        loaded_tokenizer_revision="tokenizer-rev",
        generate_source_fn=fake_generate_source,
        load_compiled_grammar_fn=_raise_if_called,
        hardware_checker_cls=_raise_if_called,
        verify_g_hashes_fn=_raise_if_called,
    )

    assert calls[0]["grammar_active"] is False
    assert calls[0]["compiled_grammar"] is None
    assert calls[0]["hardware_checker"] is None
    assert payload["generation_identity"]["grammar_active"] is False
    assert payload["generation_identity"]["grammar_variant"] is None
    assert payload["source"] == _relu_source()


def test_g_plus_c_uses_template_upper_bound() -> None:
    calls: dict[str, Any] = {}

    def fake_verify() -> dict[str, str]:
        calls["verified"] = True
        return {"RemoteGenerator.generate_one": "a" * 64}

    def fake_load_grammar(grammar_path: str, tokenizer_id: str) -> object:
        calls["grammar_path"] = grammar_path
        calls["tokenizer_id"] = tokenizer_id
        return "compiled-grammar"

    class FakeHardwareChecker:
        def __init__(self, *, dtype_bytes: int) -> None:
            calls["dtype_bytes"] = dtype_bytes

    def fake_generate_source(**kwargs: Any) -> FakeDecoded:
        calls["generate_kwargs"] = kwargs
        return FakeDecoded(source=_relu_source(), generation_seed=kwargs["seed"])

    payload = run_c2_generation_with_loaded_model(
        _request_payload("G+C", generation_seed=17),
        model=object(),
        tokenizer=object(),
        tokenizer_grammar_id="snapshot://tokenizer-rev",
        loaded_model_id="model",
        loaded_model_revision="model-rev",
        loaded_tokenizer_revision="tokenizer-rev",
        generate_source_fn=fake_generate_source,
        load_compiled_grammar_fn=fake_load_grammar,
        hardware_checker_cls=FakeHardwareChecker,
        verify_g_hashes_fn=fake_verify,
    )

    assert calls["verified"] is True
    assert calls["grammar_path"].endswith(C2_G_PLUS_C_GRAMMAR_PATH)
    assert calls["tokenizer_id"] == "snapshot://tokenizer-rev"
    assert calls["dtype_bytes"] == 4
    assert calls["generate_kwargs"]["grammar_active"] is True
    assert calls["generate_kwargs"]["compiled_grammar"] == "compiled-grammar"
    assert payload["generation_identity"]["grammar_active"] is True
    assert (
        payload["generation_identity"]["grammar_variant"]
        == C2_G_PLUS_C_GRAMMAR_VARIANT
    )
    assert payload["generation_identity"]["grammar_variant"] == "template_upper_bound"


def test_c2_generation_passes_model_and_tokenizer_revisions() -> None:
    seen_request: dict[str, Any] = {}

    def fake_remote_call(req_dict: dict[str, Any]) -> dict[str, Any]:
        seen_request.update(req_dict)
        return run_c2_generation_with_loaded_model(
            req_dict,
            model=object(),
            tokenizer=object(),
            tokenizer_grammar_id="snapshot://tok-123",
            loaded_model_id="model",
            loaded_model_revision="model-123",
            loaded_tokenizer_revision="tok-123",
            generate_source_fn=lambda **kwargs: FakeDecoded(
                source=_relu_source(),
                generation_seed=kwargs["seed"],
            ),
            verify_g_hashes_fn=_raise_if_called,
        )

    payload = generate_source_c2_modal(
        **_adapter_kwargs(
            "C",
            model_revision="model-123",
            tokenizer_revision="tok-123",
        ),
        remote_call=fake_remote_call,
    )

    assert seen_request["model_revision"] == "model-123"
    assert seen_request["tokenizer_revision"] == "tok-123"
    assert payload["model_identity"]["model_revision"] == "model-123"
    assert payload["model_identity"]["tokenizer_revision"] == "tok-123"
    assert payload["model_identity"]["tokenizer_grammar_id"] == "snapshot://tok-123"


def test_c2_generation_passes_l4_explicitly() -> None:
    payload = run_c2_generation_with_loaded_model(
        _request_payload("C"),
        model=object(),
        tokenizer=object(),
        tokenizer_grammar_id="snapshot://tokenizer-rev",
        generate_source_fn=lambda **kwargs: FakeDecoded(
            source=_relu_source(),
            generation_seed=kwargs["seed"],
        ),
        verify_g_hashes_fn=_raise_if_called,
    )

    assert REMOTE_C2_GENERATION_GPU == "L4"
    assert configured_modal_generation_gpu() == "L4"
    assert payload["modal_generation_gpu"] == "L4"
    assert payload["modal_context"]["modal_generation_gpu"] == "L4"
    assert remote_c2_generator_for_gpu("L4") is remote_c2_generator_for_gpu()
    with pytest.raises(ValueError, match="unsupported C2 generation GPU"):
        remote_c2_generator_for_gpu("L40S")


def test_generation_payload_identity_hashes_and_hash_class() -> None:
    payload = run_c2_generation_with_loaded_model(
        _request_payload("C"),
        model=object(),
        tokenizer=object(),
        tokenizer_grammar_id="snapshot://tokenizer-rev",
        generate_source_fn=lambda **kwargs: FakeDecoded(
            source=_relu_source(),
            generation_seed=kwargs["seed"],
        ),
        verify_g_hashes_fn=_raise_if_called,
    )

    source_sha256 = hashlib.sha256(_relu_source().encode("utf-8")).hexdigest()
    assert payload["identity"]["condition"] == "C"
    assert payload["identity"]["generation_mode"] == "new_c2_generation"
    assert payload["source_identity"]["source_sha256"] == source_sha256
    assert payload["generation_hash_class"] == C2_GENERATION_HASH_CLASS
    assert "cluster2/modal/generation.py" in payload["generation_hashes"]
    assert "cluster2/generation/modal_generate_c2.py" in payload["generation_hashes"]
    assert validate_remote_c2_generation_payload(payload) == payload


def test_remote_generator_generate_one_hash_matches_phase_minus_1() -> None:
    expected = expected_phase_minus1_remote_generator_generate_one_hash()
    g_hashes = verify_phase_minus1_g_generation_hashes()

    assert current_remote_generator_generate_one_hash() == expected
    assert (
        verify_phase_minus1_remote_generator_hash()["RemoteGenerator.generate_one"]
        == expected
    )
    assert g_hashes["RemoteGenerator.generate_one"] == expected
    assert g_hashes["frozen_cluster1_artifacts_manifest"]
    for rel_path, expected_hash in PHASE_MINUS1_G_GENERATION_SOURCE_HASHES.items():
        assert g_hashes[f"frozen_g_asset:{rel_path}"] == expected_hash


def test_g_plus_c_hash_gate_rejects_frozen_g_source_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    drifted_hashes = dict(PHASE_MINUS1_G_GENERATION_SOURCE_HASHES)
    drifted_hashes["cluster1/generation/constrained_gen.py"] = "0" * 64
    monkeypatch.setattr(
        c2_generation,
        "PHASE_MINUS1_G_GENERATION_SOURCE_HASHES",
        drifted_hashes,
    )

    calls: dict[str, bool] = {}

    def fake_load_grammar(_grammar_path: str, _tokenizer_id: str) -> object:
        calls["load_grammar"] = True
        return object()

    class FakeHardwareChecker:
        def __init__(self, *, dtype_bytes: int) -> None:
            calls["hardware_checker"] = True

    def fake_generate_source(**_kwargs: Any) -> FakeDecoded:
        calls["generate_source"] = True
        return FakeDecoded(source=_relu_source(), generation_seed=11)

    real_import = builtins.__import__

    def fail_on_pregate_grammar_variant_import(
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if name == "cluster1.generation.grammar_variants":
            raise AssertionError("grammar_variants imported before G hash gate")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_on_pregate_grammar_variant_import)

    with pytest.raises(ValueError, match="frozen G asset hash mismatch"):
        run_c2_generation_with_loaded_model(
            _request_payload("G+C"),
            model=object(),
            tokenizer=object(),
            tokenizer_grammar_id="snapshot://tokenizer-rev",
            generate_source_fn=fake_generate_source,
            load_compiled_grammar_fn=fake_load_grammar,
            hardware_checker_cls=FakeHardwareChecker,
            verify_g_hashes_fn=None,
        )

    assert calls == {}


def test_shared_modal_generation_file_untouched() -> None:
    assert current_remote_generator_generate_one_hash() == (
        expected_phase_minus1_remote_generator_generate_one_hash()
    )
    _assert_git_file_unchanged(SHARED_MODAL_GENERATION_PATH)


def test_shared_modal_schemas_file_untouched() -> None:
    _assert_git_file_unchanged(SHARED_MODAL_SCHEMAS_PATH)


def test_shared_modal_smoke_file_untouched() -> None:
    _assert_git_file_unchanged(SHARED_MODAL_SMOKE_PATH)


def test_generation_payload_has_no_timing_or_token_accounting_fields() -> None:
    payload = run_c2_generation_with_loaded_model(
        _request_payload("G+C"),
        model=object(),
        tokenizer=object(),
        tokenizer_grammar_id="snapshot://tokenizer-rev",
        generate_source_fn=lambda **kwargs: FakeDecoded(
            source=_relu_source(),
            generation_seed=kwargs["seed"],
        ),
        load_compiled_grammar_fn=lambda _path, _tokenizer_id: object(),
        hardware_checker_cls=lambda **_kwargs: object(),
        verify_g_hashes_fn=lambda: {"RemoteGenerator.generate_one": "a" * 64},
    )
    keys = _all_keys(payload)

    assert FORBIDDEN_REQUEST_RESULT_FIELD_NAMES.isdisjoint(keys)
    assert "performance" not in keys
    assert "masked_token_rate" not in keys
    assert "input_token_count" not in keys
    assert "output_token_count" not in keys
    assert "tokens_generated" not in keys


def test_generation_routing_rejects_replay_controls() -> None:
    assert generation_routing_for_condition("C").grammar_active is False
    assert generation_routing_for_condition("G+C").grammar_active is True
    assert (
        generation_routing_for_condition("G+C").grammar_path
        == C2_G_PLUS_C_GRAMMAR_PATH
    )

    with pytest.raises(ValueError, match="must not invoke C2 generation"):
        generation_routing_for_condition("none")
    with pytest.raises(ValueError, match="must not invoke C2 generation"):
        generation_routing_for_condition("G")


def _request_payload(
    condition: str,
    *,
    generation_seed: int | None = 11,
) -> dict[str, Any]:
    return {
        "identity": _identity(condition),
        "prompt": "write a complete Triton relu kernel",
        "model_id": "model",
        "model_revision": "model-rev",
        "tokenizer_revision": "tokenizer-rev",
        "generation_seed": generation_seed,
    }


def _adapter_kwargs(
    condition: str,
    *,
    model_revision: str = "model-rev",
    tokenizer_revision: str = "tokenizer-rev",
) -> dict[str, Any]:
    return {
        "identity": _identity(condition),
        "prompt": "write a complete Triton relu kernel",
        "model_id": "model",
        "model_revision": model_revision,
        "tokenizer_revision": tokenizer_revision,
        "generation_seed": 11,
        "temperature": 0.2,
        "max_new_tokens": 128,
    }


def _identity(condition: str) -> EvalIdentity:
    source_class = (
        "replay_control_row" if condition in {"none", "G"} else "generated_row"
    )
    generation_mode = {
        "none": "replay_control",
        "G": "replay_control",
        "C": "new_c2_generation",
        "G+C": "new_c2_generation_with_G_adapter",
    }[condition]
    return EvalIdentity(
        run_id="phase7-test-run",
        condition=condition,
        source_class=source_class,
        generation_mode=generation_mode,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        sample_index=0,
        base_seed=123,
        attempt_index=0,
    )


def _relu_source() -> str:
    return (
        "import torch\n\n"
        "def relu(x: torch.Tensor) -> torch.Tensor:\n"
        "    return torch.relu(x)\n"
    )


def _raise_if_called(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("unexpected call")


def _all_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                keys.add(key)
            keys.update(_all_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_all_keys(item))
    return keys


def _assert_git_file_unchanged(path: Path) -> None:
    proc = subprocess.run(
        ["git", "diff", "--quiet", "--", str(path.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )
    assert proc.returncode == 0, f"unstaged changes detected in {path}"

    staged_proc = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", str(path.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )
    assert staged_proc.returncode == 0, f"staged changes detected in {path}"
