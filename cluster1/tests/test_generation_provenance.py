"""Tests for generation provenance and layered grammar validation."""

from __future__ import annotations

import hashlib
from pathlib import Path

from cluster1.generation import provenance
from cluster1.grammar import triton_kernel_validator as validator

MODEL_REVISION = "a" * 40
TOKENIZER_REVISION = "b" * 40


def test_sha256_file_reads_raw_bytes(tmp_path: Path) -> None:
    path = tmp_path / "grammar.gbnf"
    content = b"root ::= 'x'\n"
    path.write_bytes(content)

    assert provenance.sha256_file(path) == hashlib.sha256(content).hexdigest()


def test_runtime_versions_do_not_raise(monkeypatch) -> None:
    versions = {
        "xgrammar": "0.1.33",
        "transformers": "4.47.1",
        "tokenizers": "0.21.4",
    }
    monkeypatch.setattr(
        provenance.importlib_metadata,
        "version",
        lambda package: versions[package],
    )

    assert provenance.runtime_versions() == {
        "xgrammar_version": "0.1.33",
        "transformers_version": "4.47.1",
        "tokenizers_version": "0.21.4",
    }


def test_modal_image_provenance_accepts_stable_digest(monkeypatch) -> None:
    for name in provenance.MODAL_IMAGE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MODAL_IMAGE_SHA", "c" * 64)
    monkeypatch.setenv("MODAL_IMAGE_TAG", "mutable-tag")

    result = provenance.modal_image_provenance()

    assert result["modal_image_sha"] == "c" * 64
    assert isinstance(result["modal_image_provenance_sha256"], str)
    assert len(result["modal_image_provenance_sha256"]) == 64
    assert isinstance(result["modal_image_provenance_components"], dict)
    assert result["modal_image_provenance_components"]["modal_image_env"] == {
        "MODAL_IMAGE_SHA": "c" * 64,
        "MODAL_IMAGE_TAG": "mutable-tag",
    }


def test_modal_image_provenance_prefers_modal_image_id(monkeypatch) -> None:
    for name in provenance.MODAL_IMAGE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MODAL_IMAGE_TAG", "mutable-tag")
    monkeypatch.setenv("MODAL_IMAGE_ID", "im-123")
    monkeypatch.setenv("MODAL_IMAGE_SHA", "c" * 64)
    monkeypatch.setenv("MODAL_IMAGE_DIGEST", "sha256:" + "d" * 64)

    result = provenance.modal_image_provenance()

    assert result["modal_image_sha"] == "im-123"
    assert isinstance(result["modal_image_provenance_sha256"], str)
    assert len(result["modal_image_provenance_sha256"]) == 64
    assert isinstance(result["modal_image_provenance_components"], dict)
    assert result["modal_image_provenance_components"]["modal_image_env"] == {
        "MODAL_IMAGE_DIGEST": "sha256:" + "d" * 64,
        "MODAL_IMAGE_ID": "im-123",
        "MODAL_IMAGE_SHA": "c" * 64,
        "MODAL_IMAGE_TAG": "mutable-tag",
    }
    assert (
        provenance.modal_image_provenance_digest(
            result["modal_image_provenance_components"]
        )
        == result["modal_image_provenance_sha256"]
    )


def test_modal_image_provenance_uses_fallback_sha_without_runtime_id(
    monkeypatch,
) -> None:
    for name in provenance.MODAL_IMAGE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MODAL_IMAGE_TAG", "mutable-tag")

    result = provenance.modal_image_provenance()

    assert result["modal_image_sha"] == result["modal_image_provenance_sha256"]
    assert result["modal_image_sha"] != "unknown"
    assert result["modal_image_provenance_components"]["modal_image_env"] == {
        "MODAL_IMAGE_TAG": "mutable-tag",
    }


def test_modal_image_provenance_fallback_changes_with_components(
    monkeypatch,
) -> None:
    for name in provenance.MODAL_IMAGE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        provenance.importlib_metadata,
        "version",
        lambda _package: "test-version",
    )

    first = provenance.modal_image_provenance(
        extra={"modal_generation_gpu": "L4"},
    )
    second = provenance.modal_image_provenance(
        extra={"modal_generation_gpu": "L40S"},
    )

    assert first["modal_image_sha"] == first["modal_image_provenance_sha256"]
    assert second["modal_image_sha"] == second["modal_image_provenance_sha256"]
    assert first["modal_image_provenance_components"] != second[
        "modal_image_provenance_components"
    ]
    assert first["modal_image_provenance_sha256"] != second[
        "modal_image_provenance_sha256"
    ]


def test_stop_reason_classification() -> None:
    assert (
        provenance.classify_stop_reason(
            generated_token_ids=[1, 2],
            max_new_tokens=4,
            eos_token_id=2,
        )
        == "eos_token"
    )
    assert (
        provenance.classify_stop_reason(
            generated_token_ids=[1, 2, 3],
            max_new_tokens=3,
            eos_token_id=99,
        )
        == "max_new_tokens"
    )
    assert (
        provenance.classify_stop_reason(
            generated_token_ids=[1],
            max_new_tokens=3,
            grammar_final_state_observed=True,
        )
        == "unknown"
    )
    assert (
        provenance.classify_stop_reason(
            generated_token_ids=[1],
            max_new_tokens=3,
            grammar_final_state_observed=True,
            stopped_on_grammar_final_state=True,
        )
        == "grammar_final_state"
    )
    assert (
        provenance.classify_stop_reason(
            generated_token_ids=[],
            max_new_tokens=3,
        )
        == "unknown"
    )


def test_model_tokenizer_revisions_prefer_observed_commit_hashes() -> None:
    class FakeConfig:
        _commit_hash = "observed-model"

    class FakeModel:
        config = FakeConfig()

    class FakeTokenizer:
        init_kwargs = {"_commit_hash": "observed-tokenizer"}

    assert provenance.model_tokenizer_revisions(
        FakeModel(),
        FakeTokenizer(),
        model_revision="requested-model",
        tokenizer_revision="requested-tokenizer",
    ) == {
        "model_revision": "observed-model",
        "tokenizer_revision": "observed-tokenizer",
    }


def test_extract_tokenizer_revision_uses_init_kwargs_commit_hash() -> None:
    class FakeTokenizer:
        init_kwargs = {"_commit_hash": "tok-sha"}

    assert provenance.extract_tokenizer_revision(FakeTokenizer()) == "tok-sha"


def test_extract_tokenizer_revision_uses_tokenizer_commit_hash_attribute() -> None:
    class FakeTokenizer:
        _commit_hash = "tok-sha"

    assert provenance.extract_tokenizer_revision(FakeTokenizer()) == "tok-sha"


def test_extract_tokenizer_revision_uses_explicit_revision_fallback() -> None:
    class FakeTokenizer:
        pass

    assert (
        provenance.extract_tokenizer_revision(
            FakeTokenizer(),
            explicit_revision="explicit-sha",
        )
        == "explicit-sha"
    )


def test_extract_tokenizer_revision_returns_unknown_without_usable_source() -> None:
    class FakeTokenizer:
        init_kwargs = {"_commit_hash": "unknown"}
        _commit_hash = ""

    assert provenance.extract_tokenizer_revision(FakeTokenizer()) == "unknown"


def test_resolve_tokenizer_revision_uses_explicit_tokenizer_revision() -> None:
    assert (
        provenance.resolve_tokenizer_revision(
            model_id="repo/model",
            model_revision=MODEL_REVISION,
            tokenizer_revision=TOKENIZER_REVISION,
        )
        == TOKENIZER_REVISION
    )
    assert (
        provenance.tokenizer_revision_policy(
            model_id="repo/model",
            model_revision=MODEL_REVISION,
            tokenizer_revision=TOKENIZER_REVISION,
        )
        == "explicit_tokenizer_revision"
    )


def test_resolve_tokenizer_revision_uses_same_repo_model_revision() -> None:
    assert (
        provenance.resolve_tokenizer_revision(
            model_id="repo/model",
            model_revision=MODEL_REVISION,
            tokenizer_revision=None,
        )
        == MODEL_REVISION
    )
    assert (
        provenance.tokenizer_revision_policy(
            model_id="repo/model",
            model_revision=MODEL_REVISION,
            tokenizer_revision=None,
        )
        == "same_repo_model_revision"
    )


def test_resolve_tokenizer_revision_does_not_cross_repos() -> None:
    assert (
        provenance.resolve_tokenizer_revision(
            model_id="repo/model",
            tokenizer_id="repo/tokenizer",
            model_revision=MODEL_REVISION,
            tokenizer_revision=None,
        )
        is None
    )
    assert (
        provenance.tokenizer_revision_policy(
            model_id="repo/model",
            tokenizer_id="repo/tokenizer",
            model_revision=MODEL_REVISION,
            tokenizer_revision=None,
        )
        == "best_effort_extraction"
    )


def test_normalize_explicit_revision_rejects_mutable_names() -> None:
    for revision in ("main", "master", "latest", "HEAD", "refs/heads/main", "dev"):
        try:
            provenance.normalize_explicit_revision(
                revision,
                field_name="model_revision",
            )
        except ValueError as exc:
            assert "immutable revision" in str(exc)
        else:  # pragma: no cover - defensive assertion message
            raise AssertionError(f"expected {revision!r} to be rejected")


def test_normalize_explicit_revision_accepts_commit_sha() -> None:
    assert (
        provenance.normalize_explicit_revision(
            " " + MODEL_REVISION.upper() + " ",
            field_name="model_revision",
        )
        == MODEL_REVISION.upper()
    )


def test_layered_validator_classifies_gbnf_parse_failure() -> None:
    result = validator.validate_source_layers(
        "not valid source",
        grammar_path=validator.TASK_AGNOSTIC_GBNF_PATH,
    )

    assert result.gbnf_parse_valid is False
    assert result.semantic_valid is False
    assert result.grammar_valid is False
    assert result.rejection_layer == "gbnf_parse"


def test_layered_validator_classifies_python_ast_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    grammar_path = tmp_path / "fake.gbnf"
    grammar_path.write_text("root ::= 'ignored'\n", encoding="utf-8")

    class Parser:
        def parse(self, _source: str) -> None:
            return None

    monkeypatch.setattr(validator, "_compile_lark_parser", lambda _text: Parser())

    result = validator.validate_source_layers(
        "def broken(: pass",
        grammar_path=grammar_path,
    )

    assert result.gbnf_parse_valid is True
    assert result.semantic_valid is False
    assert result.grammar_valid is False
    assert result.rejection_layer == "python_ast"


def test_layered_validator_classifies_semantic_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    grammar_path = tmp_path / "fake.gbnf"
    grammar_path.write_text("root ::= 'ignored'\n", encoding="utf-8")

    class Parser:
        def parse(self, _source: str) -> None:
            return None

    monkeypatch.setattr(validator, "_compile_lark_parser", lambda _text: Parser())
    monkeypatch.setattr(validator, "_semantic_accepts", lambda _tree: False)
    monkeypatch.setattr(
        validator,
        "_uses_task_agnostic_semantics",
        lambda _path, _text: False,
    )

    result = validator.validate_source_layers("x = 1", grammar_path=grammar_path)

    assert result.gbnf_parse_valid is True
    assert result.semantic_valid is False
    assert result.grammar_valid is False
    assert result.rejection_layer == "semantic_validator"


def test_layered_validator_classifies_runtime_error(tmp_path: Path) -> None:
    result = validator.validate_source_layers(
        "x = 1",
        grammar_path=tmp_path / "missing.gbnf",
    )

    assert result.grammar_valid is False
    assert result.rejection_layer == "runtime_error"
