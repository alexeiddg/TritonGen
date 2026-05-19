import sys
from types import SimpleNamespace

from cluster1.generation import modal_generate
from shared.modal_harness import generation as remote_generation

MODEL_REVISION = "a" * 40
TOKENIZER_REVISION = "b" * 40


def test_generate_source_modal_passes_configured_gpu_to_remote_generator(monkeypatch):
    calls: dict[str, object] = {}

    class FakeGenerator:
        def __init__(self, **kwargs):
            calls["init"] = kwargs
            self.generate_one = SimpleNamespace(remote=self._remote)

        def _remote(self, req_dict):
            calls["request"] = req_dict
            return {
                "source": "import triton\n",
                "model_id": req_dict["model_id"],
                "grammar_active": False,
                "grammar_variant": None,
                "masked_token_rate": None,
                "generation_seed": req_dict["generation_seed"],
                "temperature": req_dict["temperature"],
                "run_id": req_dict["run_id"],
            }

    def fake_remote_generator_for_gpu(gpu):
        calls["selected_gpu"] = gpu
        return FakeGenerator

    monkeypatch.setattr(
        modal_generate,
        "remote_generator_for_gpu",
        fake_remote_generator_for_gpu,
    )

    result = modal_generate.generate_source_modal(
        prompt="task",
        model_id="repo/model",
        model_revision=MODEL_REVISION,
        tokenizer_revision=TOKENIZER_REVISION,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        grammar_active=False,
        generation_seed=0,
        temperature=0.2,
        max_new_tokens=64,
        run_id="run",
        modal_generation_gpu="L4",
    )

    assert result.model_id == "repo/model"
    assert calls["selected_gpu"] == "L4"
    assert calls["init"] == {
        "model_id": "repo/model",
        "model_revision": MODEL_REVISION,
        "tokenizer_revision": TOKENIZER_REVISION,
        "generation_gpu": "L4",
    }
    assert calls["request"]["model_revision"] == MODEL_REVISION
    assert calls["request"]["tokenizer_revision"] == TOKENIZER_REVISION


def test_tokenizer_grammar_id_uses_loaded_snapshot_for_known_revision(monkeypatch):
    calls: dict[str, object] = {}

    def fake_snapshot_download(**kwargs):
        calls.update(kwargs)
        return "/cache/huggingface/snapshots/tokenizer"

    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        SimpleNamespace(snapshot_download=fake_snapshot_download),
    )

    tokenizer_id = remote_generation._resolve_tokenizer_grammar_id(
        "repo/model",
        TOKENIZER_REVISION,
    )

    assert tokenizer_id == "/cache/huggingface/snapshots/tokenizer"
    assert calls["repo_id"] == "repo/model"
    assert calls["revision"] == TOKENIZER_REVISION
    assert "tokenizer.json" in calls["allow_patterns"]


def test_tokenizer_grammar_id_keeps_legacy_model_id_without_known_revision():
    assert remote_generation._resolve_tokenizer_grammar_id("repo/model", None) == (
        "repo/model"
    )
    assert remote_generation._resolve_tokenizer_grammar_id("repo/model", "unknown") == (
        "repo/model"
    )


def test_compiled_grammar_tokenizer_id_prefers_loaded_snapshot():
    generator = SimpleNamespace(tokenizer_grammar_id="/cache/snapshots/tokenizer")

    assert remote_generation._compiled_grammar_tokenizer_id(generator, "repo/model") == (
        "/cache/snapshots/tokenizer"
    )
    assert remote_generation._compiled_grammar_tokenizer_id(object(), "repo/model") == (
        "repo/model"
    )


def test_observed_revisions_preserve_explicit_tokenizer_revision_fallback():
    class FakeConfig:
        _commit_hash = "observed-model-revision"

    class FakeModel:
        config = FakeConfig()

    class FakeTokenizer:
        pass

    generator = SimpleNamespace(
        model=FakeModel(),
        tokenizer=FakeTokenizer(),
        requested_model_revision=MODEL_REVISION,
        requested_tokenizer_revision=TOKENIZER_REVISION,
    )

    assert remote_generation._observed_model_tokenizer_revisions(generator) == (
        "observed-model-revision",
        TOKENIZER_REVISION,
    )
