"""Cluster 2 isolated Modal generation surface.

This module owns new Cluster 2 generation for ``C`` and ``G+C`` only. Replay
controls remain artifact-driven and never route through this surface.
"""

import ast
import hashlib
import json
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Mapping

import modal

from cluster2.constants import DEFAULT_C2_MODAL_GENERATION_GPU
from cluster2.modal.schemas import (
    C2ModalSurfaceMetadata,
    EvalIdentity,
    FORBIDDEN_REQUEST_RESULT_FIELD_NAMES,
    RemoteC2GenerationRequest,
    RemoteC2GenerationResult,
    modal_surface_metadata,
    require_c2_generation_condition,
)
from shared.eval.content_hashes import (
    collect_c2_generation_hashes,
)
from shared.modal_harness.app import app
from shared.modal_harness.images import llm_generation_image
from shared.modal_harness.runtime import current_modal_ids
from shared.modal_harness.secrets import hf_secrets
from shared.modal_harness.volumes import hf_cache_volume


C2_GENERATION_PAYLOAD_SCHEMA_VERSION = 1
C2_GENERATION_SURFACE = "c2_remote_generation"
C2_GENERATION_HASH_CLASS = "c2_generation_pipeline"
C2_G_PLUS_C_GRAMMAR_VARIANT = "task_agnostic"
C2_G_PLUS_C_GRAMMAR_PATH = "cluster1/grammar/triton_kernel_agnostic.gbnf"
C2_G_PLUS_C_TEMPLATE_UPPER_BOUND_GRAMMAR_VARIANT = "template_upper_bound"
C2_G_PLUS_C_TEMPLATE_UPPER_BOUND_GRAMMAR_PATH = "cluster1/grammar/triton_kernel.gbnf"
C2_GRAMMAR_PATHS_BY_VARIANT = {
    C2_G_PLUS_C_GRAMMAR_VARIANT: C2_G_PLUS_C_GRAMMAR_PATH,
    C2_G_PLUS_C_TEMPLATE_UPPER_BOUND_GRAMMAR_VARIANT: (
        C2_G_PLUS_C_TEMPLATE_UPPER_BOUND_GRAMMAR_PATH
    ),
}
C2_GRAMMAR_CLAIM_SCOPE_BY_VARIANT = {
    C2_G_PLUS_C_GRAMMAR_VARIANT: "primary",
    C2_G_PLUS_C_TEMPLATE_UPPER_BOUND_GRAMMAR_VARIANT: "diagnostic_non_primary",
}
C2_FROZEN_G_ARTIFACT_BY_GRAMMAR_VARIANT = {
    C2_G_PLUS_C_GRAMMAR_VARIANT: "g_task_agnostic_n5_l4_rerun",
    C2_G_PLUS_C_TEMPLATE_UPPER_BOUND_GRAMMAR_VARIANT: "g_template_upper_bound_n20_l4",
}
REMOTE_C2_GENERATION_GPU = DEFAULT_C2_MODAL_GENERATION_GPU
SUPPORTED_C2_GENERATION_GPUS = frozenset({REMOTE_C2_GENERATION_GPU})
INFRASTRUCTURE_FAILURE_STATUS = "INFRA_FAILURE"

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_MINUS1_MANIFEST_PATH = (
    REPO_ROOT / "cluster2" / "contracts" / "phase_minus1_manifest.json"
)
_C2_REMOTE_GENERATION_FORBIDDEN_EXTRA_FIELDS = frozenset({"performance"})
_TOKENIZER_SNAPSHOT_ALLOW_PATTERNS = (
    "added_tokens.json",
    "config.json",
    "generation_config.json",
    "merges.txt",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer.model",
    "tokenizer_config.json",
    "vocab.json",
    "vocab.txt",
)
# Phase 7 pins the frozen Cluster 1 G assets without mutating Phase -1 manifests.
PHASE_MINUS1_G_GENERATION_SOURCE_HASHES: dict[str, str] = {
    "cluster1/generation/grammar_variants.py": (
        "3024071bc1626d3b0b08c5461cd6583e259aac3400c0e18e21a696869b2b6299"
    ),
    "cluster1/grammar/triton_kernel.gbnf": (
        "0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82"
    ),
    "cluster1/grammar/triton_kernel_agnostic.gbnf": (
        "756f46a76e8fc6e208a263a69678873ecbbe7327d1c3c7ee9fe6a902fb96600f"
    ),
    "cluster1/generation/grammar_loader.py": (
        "1a21c61801ae1180408c39be6116cf4fe7aec0920ed2d047ba94839cf7c010eb"
    ),
    "cluster1/generation/constrained_gen.py": (
        "63957e7a1a509890bf9c0e66a25f6a623a9044ab0eb0a7aa4399750f9e072f2b"
    ),
    "cluster1/generation/constrained_decoding.py": (
        "6bd6181eabe1d6dc8d3d3a2bb4001a1b9570d77d9b9d2b3162e8e018256061d4"
    ),
    "cluster1/constraints/hardware_checker.py": (
        "cc1fc4e02156c659466f5b7ab75f7ff037e99f936e223b042750e356cdad9bab"
    ),
}

c2_generation_image = llm_generation_image.add_local_python_source("cluster2")


@dataclass(frozen=True)
class C2GenerationRouting:
    """Resolved C2 generation mode for one request condition."""

    condition: str
    grammar_active: bool
    grammar_variant: str | None
    grammar_path: str | None
    grammar_claim_scope: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _DecodedC2Kernel:
    source: str
    generation_seed: int | None
    temperature: float


@app.cls(
    image=c2_generation_image,
    gpu=REMOTE_C2_GENERATION_GPU,
    memory=32768,
    cpu=8.0,
    timeout=900,
    max_containers=2,
    min_containers=0,
    scaledown_window=600,
    volumes={"/cache/huggingface": hf_cache_volume},
    secrets=hf_secrets,
)
class RemoteC2Generator:
    """Load one C2 model/tokenizer revision pair and serve C2 generation."""

    model_id: str = modal.parameter()
    model_revision: str = modal.parameter()
    tokenizer_revision: str = modal.parameter()

    @modal.enter()
    def load_model(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            revision=self.tokenizer_revision,
            trust_remote_code=True,
        )
        self.tokenizer_grammar_id = _resolve_tokenizer_grammar_id(
            self.model_id,
            self.tokenizer_revision,
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            revision=self.model_revision,
            device_map="auto",
            low_cpu_mem_usage=True,
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )
        if hasattr(self.model, "eval"):
            self.model.eval()

        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        pad_token_id = getattr(self.tokenizer, "pad_token_id", None)
        generation_config = getattr(self.model, "generation_config", None)
        if pad_token_id is not None and generation_config is not None:
            generation_config.pad_token_id = pad_token_id

    @modal.method()
    def generate_one(self, req_dict: dict) -> dict:
        call_id, input_id = current_modal_ids()
        return run_c2_generation_with_loaded_model(
            req_dict,
            model=self.model,
            tokenizer=self.tokenizer,
            torch_module=self.torch,
            tokenizer_grammar_id=self.tokenizer_grammar_id,
            loaded_model_id=self.model_id,
            loaded_model_revision=self.model_revision,
            loaded_tokenizer_revision=self.tokenizer_revision,
            modal_function_call_id=call_id,
            modal_input_id=input_id,
        )


def remote_c2_generator_for_gpu(gpu: str = REMOTE_C2_GENERATION_GPU):
    """Return the C2 generator class configured for the explicit C2 GPU."""

    if gpu not in SUPPORTED_C2_GENERATION_GPUS:
        allowed = ", ".join(sorted(SUPPORTED_C2_GENERATION_GPUS))
        raise ValueError(f"unsupported C2 generation GPU {gpu!r}; allowed: {allowed}")
    return RemoteC2Generator


def generation_surface_metadata() -> C2ModalSurfaceMetadata:
    """Return metadata for the isolated C2 generation surface."""

    return modal_surface_metadata()


def validate_future_generation_condition(condition: str) -> str:
    """Validate C2 generation routing without invoking generation."""

    return require_c2_generation_condition(condition)


def generation_routing_for_condition(
    condition: str,
    grammar_variant: str | None = None,
) -> C2GenerationRouting:
    """Return grammar routing for one C2 generated condition."""

    normalized = require_c2_generation_condition(condition)
    if normalized == "C":
        if grammar_variant is not None:
            raise ValueError("condition 'C' must not request a grammar_variant")
        return C2GenerationRouting(
            condition=normalized,
            grammar_active=False,
            grammar_variant=None,
            grammar_path=None,
            grammar_claim_scope=None,
        )

    resolved_variant = grammar_variant or C2_G_PLUS_C_GRAMMAR_VARIANT
    if resolved_variant not in C2_GRAMMAR_PATHS_BY_VARIANT:
        allowed = ", ".join(sorted(C2_GRAMMAR_PATHS_BY_VARIANT))
        raise ValueError(
            f"unsupported G+C grammar_variant {resolved_variant!r}; "
            f"expected one of: {allowed}"
        )
    return C2GenerationRouting(
        condition=normalized,
        grammar_active=True,
        grammar_variant=resolved_variant,
        grammar_path=C2_GRAMMAR_PATHS_BY_VARIANT[resolved_variant],
        grammar_claim_scope=C2_GRAMMAR_CLAIM_SCOPE_BY_VARIANT[resolved_variant],
    )


def run_c2_generation_with_loaded_model(
    request_payload: dict[str, Any],
    *,
    model: Any,
    tokenizer: Any,
    torch_module: Any = None,
    tokenizer_grammar_id: str,
    loaded_model_id: str | None = None,
    loaded_model_revision: str | None = None,
    loaded_tokenizer_revision: str | None = None,
    generate_source_fn: Callable[..., Any] | None = None,
    load_compiled_grammar_fn: Callable[[str, str], Any] | None = None,
    hardware_checker_cls: Callable[..., Any] | None = None,
    verify_g_hashes_fn: Callable[[], dict[str, str]] | None = None,
    modal_function_call_id: str | None = None,
    modal_input_id: str | None = None,
) -> dict[str, Any]:
    """Generate one C2 candidate using already-loaded model objects.

    The dependency injection hooks keep unit tests local and mock-based; the
    default path is used only inside the Modal container.
    """

    request = RemoteC2GenerationRequest(**request_payload)
    _validate_loaded_model_identity(
        request,
        loaded_model_id=loaded_model_id,
        loaded_model_revision=loaded_model_revision,
        loaded_tokenizer_revision=loaded_tokenizer_revision,
    )
    condition = require_c2_generation_condition(request.identity.condition)
    routing = generation_routing_for_condition(
        condition,
        grammar_variant=request.grammar_variant,
    )
    if condition == "G+C":
        if verify_g_hashes_fn is None:
            verify_phase_minus1_g_generation_hashes(
                grammar_variant=routing.grammar_variant
            )
        else:
            verify_g_hashes_fn()

    compiled_grammar = None
    hardware_checker = None
    if routing.grammar_active:
        assert routing.grammar_path is not None
        if load_compiled_grammar_fn is None:
            from cluster1.generation.grammar_loader import load_compiled_grammar

            load_compiled_grammar_fn = load_compiled_grammar
        if hardware_checker_cls is None:
            from cluster1.constraints.hardware_checker import HardwareChecker

            hardware_checker_cls = HardwareChecker

        compiled_grammar = load_compiled_grammar_fn(
            _resolve_grammar_path(routing.grammar_path),
            tokenizer_grammar_id,
        )
        hardware_checker = hardware_checker_cls(
            dtype_bytes=_dtype_name_to_bytes(request.identity.dtype)
        )
        if generate_source_fn is None:
            from cluster1.generation.constrained_gen import generate_source

            generate_source_fn = generate_source

    with _inference_mode(torch_module):
        if routing.grammar_active:
            decoded = generate_source_fn(
                prompt=request.prompt,
                model=model,
                tokenizer=tokenizer,
                grammar_active=True,
                compiled_grammar=compiled_grammar,
                hardware_checker=hardware_checker,
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
                seed=request.generation_seed,
            )
        elif generate_source_fn is not None:
            decoded = generate_source_fn(
                prompt=request.prompt,
                model=model,
                tokenizer=tokenizer,
                grammar_active=False,
                compiled_grammar=None,
                hardware_checker=None,
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
                seed=request.generation_seed,
            )
        else:
            decoded = _generate_unconstrained_source(
                prompt=request.prompt,
                model=model,
                tokenizer=tokenizer,
                torch_module=torch_module,
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
                seed=request.generation_seed,
            )

    result = RemoteC2GenerationResult(
        identity=request.identity,
        source=_decoded_source(decoded),
        model_id=request.model_id,
        model_revision=request.model_revision,
        generation_seed=_decoded_generation_seed(decoded, request.generation_seed),
    )
    return build_success_payload(
        request,
        result,
        routing,
        tokenizer_grammar_id=tokenizer_grammar_id,
        modal_function_call_id=modal_function_call_id,
        modal_input_id=modal_input_id,
    )


def build_success_payload(
    request: RemoteC2GenerationRequest,
    result: RemoteC2GenerationResult,
    routing: C2GenerationRouting,
    *,
    tokenizer_grammar_id: str,
    modal_function_call_id: str | None,
    modal_input_id: str | None,
) -> dict[str, Any]:
    """Return the Phase 7 wrapper around a schema-compatible C2 result."""

    if result.source is None:
        raise ValueError("generated C2 result must include source")
    source_sha256 = hashlib.sha256(result.source.encode("utf-8")).hexdigest()
    payload = {
        "schema_version": C2_GENERATION_PAYLOAD_SCHEMA_VERSION,
        "surface": C2_GENERATION_SURFACE,
        "generation_status": "generated",
        "modal_generation_gpu": REMOTE_C2_GENERATION_GPU,
        "generation_hash_class": C2_GENERATION_HASH_CLASS,
        "identity": request.identity.model_dump(),
        "source": result.source,
        "source_identity": {
            "source_sha256": source_sha256,
            "condition": request.identity.condition,
            "source_class": request.identity.source_class,
            "generation_mode": request.identity.generation_mode,
            "kernel_class": request.identity.kernel_class,
            "kernel_name": request.identity.kernel_name,
            "dtype": request.identity.dtype,
            "sample_index": request.identity.sample_index,
            "base_seed": request.identity.base_seed,
            "attempt_index": request.identity.attempt_index,
        },
        "generation_identity": {
            "grammar_active": routing.grammar_active,
            "grammar_variant": routing.grammar_variant,
            "grammar_path": routing.grammar_path,
            "grammar_claim_scope": routing.grammar_claim_scope,
            "generation_seed": result.generation_seed,
        },
        "model_identity": {
            "model_id": request.model_id,
            "model_revision": request.model_revision,
            "tokenizer_revision": request.tokenizer_revision,
            "tokenizer_grammar_id": tokenizer_grammar_id,
        },
        "generation_result": result.model_dump(),
        "generation_hashes": collect_c2_generation_hashes(request.identity.condition),
        "modal_context": {
            "function_call_id": modal_function_call_id,
            "input_id": modal_input_id,
            "modal_generation_gpu": REMOTE_C2_GENERATION_GPU,
        },
    }
    return validate_remote_c2_generation_payload(payload)


def validate_remote_c2_generation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the Phase 7 remote generation wrapper and nested schema."""

    if not isinstance(payload, dict):
        raise TypeError("remote C2 generation payload must be a dict")
    _reject_forbidden_payload_fields(payload)
    required = {
        "schema_version",
        "surface",
        "generation_status",
        "modal_generation_gpu",
        "generation_hash_class",
        "identity",
        "source",
        "source_identity",
        "generation_identity",
        "model_identity",
        "generation_result",
        "generation_hashes",
        "modal_context",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"missing remote C2 generation fields: {', '.join(missing)}")
    if payload["schema_version"] != C2_GENERATION_PAYLOAD_SCHEMA_VERSION:
        raise ValueError("unsupported remote C2 generation schema_version")
    if payload["surface"] != C2_GENERATION_SURFACE:
        raise ValueError("unsupported remote C2 generation surface")
    if payload["generation_status"] != "generated":
        raise ValueError("unsupported remote C2 generation status")
    if payload["modal_generation_gpu"] != REMOTE_C2_GENERATION_GPU:
        raise ValueError("C2 remote generation must use L4 generation GPU metadata")
    if payload["generation_hash_class"] != C2_GENERATION_HASH_CLASS:
        raise ValueError("unexpected C2 generation hash class")
    if not isinstance(payload["source"], str) or not payload["source"]:
        raise ValueError("remote C2 generation payload must include source text")
    _validate_string_mapping(payload["generation_hashes"], "generation_hashes")

    identity = EvalIdentity(**payload["identity"])
    result = RemoteC2GenerationResult(**payload["generation_result"])
    if result.identity != identity:
        raise ValueError("generation_result identity does not match wrapper identity")
    if result.source != payload["source"]:
        raise ValueError("generation_result source does not match wrapper source")
    _validate_source_identity(payload["source_identity"], identity, payload["source"])
    _validate_generation_identity(payload["generation_identity"], identity)
    _validate_model_identity(payload["model_identity"], result)
    _validate_modal_context(payload["modal_context"])
    return payload


def current_remote_generator_generate_one_hash(
    manifest_path: str | Path = PHASE_MINUS1_MANIFEST_PATH,
) -> str:
    """Return the current Cluster 1 ``RemoteGenerator.generate_one`` hash."""

    modal_generation = _phase_minus1_modal_generation(manifest_path)
    record = modal_generation["RemoteGenerator.generate_one"]
    source_path = REPO_ROOT / record["path"]
    lines = record["lines"]
    return _source_range_sha256(
        source_path,
        start_line=int(lines["start"]),
        end_line=int(lines["end"]),
    )


def expected_phase_minus1_remote_generator_generate_one_hash(
    manifest_path: str | Path = PHASE_MINUS1_MANIFEST_PATH,
) -> str:
    """Return the Phase -1 hash for ``RemoteGenerator.generate_one``."""

    modal_generation = _phase_minus1_modal_generation(manifest_path)
    return str(modal_generation["RemoteGenerator.generate_one"]["source_sha256"])


def verify_phase_minus1_remote_generator_hash(
    manifest_path: str | Path = PHASE_MINUS1_MANIFEST_PATH,
) -> dict[str, str]:
    """Validate that the frozen Cluster 1 remote generation method is unchanged."""

    modal_generation = _phase_minus1_modal_generation(manifest_path)
    expected_hash = str(
        modal_generation["RemoteGenerator.generate_one"]["source_sha256"]
    )
    current_hash = current_remote_generator_generate_one_hash(manifest_path)
    if current_hash != expected_hash:
        raise ValueError(
            "RemoteGenerator.generate_one hash mismatch against Phase -1: "
            f"expected {expected_hash}, got {current_hash}"
        )

    expected_gpu = str(modal_generation["DEFAULT_GENERATION_GPU"])
    current_gpu = str(
        _literal_assignment_value(
            REPO_ROOT / "shared" / "modal_harness" / "generation.py",
            "DEFAULT_GENERATION_GPU",
        )
    )
    if current_gpu != expected_gpu:
        raise ValueError(
            "DEFAULT_GENERATION_GPU mismatch against Phase -1: "
            f"expected {expected_gpu!r}, got {current_gpu!r}"
        )
    return {"RemoteGenerator.generate_one": current_hash}


def verify_phase_minus1_g_generation_hashes(
    *,
    grammar_variant: str = C2_G_PLUS_C_GRAMMAR_VARIANT,
) -> dict[str, str]:
    """Hash gate required before any ``G+C`` generation call."""

    hashes = verify_phase_minus1_remote_generator_hash()
    hashes.update(_verify_phase_minus1_frozen_g_source_hashes())
    hashes["frozen_cluster1_artifacts_manifest"] = (
        _verify_phase_minus1_frozen_g_manifest(grammar_variant=grammar_variant)
    )
    return hashes


def _verify_phase_minus1_frozen_g_source_hashes(
    expected_hashes: Mapping[str, str] | None = None,
) -> dict[str, str]:
    expected = expected_hashes or PHASE_MINUS1_G_GENERATION_SOURCE_HASHES
    current_hashes: dict[str, str] = {}
    for rel_path, expected_hash in expected.items():
        source_path = REPO_ROOT / rel_path
        if not source_path.is_file():
            raise FileNotFoundError(f"frozen Cluster 1 G asset not found: {rel_path}")
        current_hash = _file_sha256(source_path)
        if current_hash != expected_hash:
            raise ValueError(
                "Cluster 1 frozen G asset hash mismatch against Phase -1: "
                f"{rel_path} expected {expected_hash}, got {current_hash}"
            )
        current_hashes[f"frozen_g_asset:{rel_path}"] = current_hash
    return current_hashes


def _phase_minus1_modal_generation(manifest_path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    return manifest["cluster1_invariants"]["modal_generation"]


def _phase_minus1_manifest(
    manifest_path: str | Path = PHASE_MINUS1_MANIFEST_PATH,
) -> dict[str, Any]:
    return json.loads(Path(manifest_path).read_text(encoding="utf-8"))


def _verify_phase_minus1_frozen_g_manifest(
    *,
    grammar_variant: str = C2_G_PLUS_C_GRAMMAR_VARIANT,
) -> str:
    if grammar_variant not in C2_FROZEN_G_ARTIFACT_BY_GRAMMAR_VARIANT:
        allowed = ", ".join(sorted(C2_FROZEN_G_ARTIFACT_BY_GRAMMAR_VARIANT))
        raise ValueError(
            f"unsupported frozen G grammar_variant {grammar_variant!r}; "
            f"expected one of: {allowed}"
        )
    expected_artifact_id = C2_FROZEN_G_ARTIFACT_BY_GRAMMAR_VARIANT[grammar_variant]
    phase_manifest = _phase_minus1_manifest()
    manifest_record = phase_manifest["frozen_cluster1_artifacts_manifest"]
    manifest_path = REPO_ROOT / manifest_record["path"]
    expected_hash = str(manifest_record["sha256"])
    current_hash = _file_sha256(manifest_path)
    if current_hash != expected_hash:
        raise ValueError(
            "frozen Cluster 1 artifact manifest hash mismatch against Phase -1: "
            f"expected {expected_hash}, got {current_hash}"
        )

    frozen_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in frozen_manifest.get("artifacts", []):
        if artifact.get("artifact_id") != expected_artifact_id:
            continue
        if artifact.get("condition") != "G":
            raise ValueError("frozen G artifact must record condition 'G'")
        flag_check = artifact.get("condition_flag_check", {})
        if flag_check.get("passed") is not True:
            raise ValueError("frozen G artifact flag check did not pass")
        if flag_check.get("expected_grammar_active") is not True:
            raise ValueError("frozen G artifact must be grammar-active")
        if flag_check.get("expected_grammar_variant") != grammar_variant:
            raise ValueError(
                "frozen G artifact grammar_variant mismatch: "
                f"expected {grammar_variant!r}"
            )
        return current_hash
    raise ValueError(
        "frozen G artifact not found in Phase -1 manifest: "
        f"{expected_artifact_id}"
    )


def _source_range_sha256(
    path: str | Path,
    *,
    start_line: int,
    end_line: int,
) -> str:
    lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    source = "".join(lines[start_line - 1 : end_line]).strip()
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _literal_assignment_value(path: str | Path, name: str) -> Any:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name and node.value is not None:
                return ast.literal_eval(node.value)
    raise ValueError(f"{name} assignment not found in {path}")


def _file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _validate_loaded_model_identity(
    request: RemoteC2GenerationRequest,
    *,
    loaded_model_id: str | None,
    loaded_model_revision: str | None,
    loaded_tokenizer_revision: str | None,
) -> None:
    if loaded_model_id is not None and request.model_id != loaded_model_id:
        raise ValueError(
            f"request model_id {request.model_id!r} does not match loaded model "
            f"{loaded_model_id!r}"
        )
    if (
        loaded_model_revision is not None
        and request.model_revision != loaded_model_revision
    ):
        raise ValueError(
            "request model_revision "
            f"{request.model_revision!r} does not match loaded revision "
            f"{loaded_model_revision!r}"
        )
    if (
        loaded_tokenizer_revision is not None
        and request.tokenizer_revision != loaded_tokenizer_revision
    ):
        raise ValueError(
            "request tokenizer_revision "
            f"{request.tokenizer_revision!r} does not match loaded tokenizer revision "
            f"{loaded_tokenizer_revision!r}"
        )


def _generate_unconstrained_source(
    *,
    prompt: str,
    model: Any,
    tokenizer: Any,
    torch_module: Any,
    max_new_tokens: int,
    temperature: float,
    seed: int | None,
) -> _DecodedC2Kernel:
    if seed is not None:
        _manual_seed(torch_module, seed)

    encoded = _move_encoded_to_model_device(
        tokenizer(prompt, return_tensors="pt"),
        model,
    )
    input_ids = encoded["input_ids"]
    prompt_len = _sequence_length(input_ids)
    generate_kwargs = {
        "max_new_tokens": max_new_tokens,
        "temperature": temperature,
        "do_sample": True,
    }
    generate_kwargs.update(encoded)

    output_ids = model.generate(**generate_kwargs)
    return _DecodedC2Kernel(
        source=_decode_new_tokens(tokenizer, output_ids, prompt_len),
        generation_seed=seed,
        temperature=temperature,
    )


def _resolve_tokenizer_grammar_id(model_id: str, tokenizer_revision: str) -> str:
    """Return a local tokenizer snapshot path for frozen Cluster 1 grammar loading."""

    from huggingface_hub import snapshot_download

    return snapshot_download(
        repo_id=model_id,
        revision=tokenizer_revision,
        allow_patterns=list(_TOKENIZER_SNAPSHOT_ALLOW_PATTERNS),
    )


def _resolve_grammar_path(grammar_path: str) -> str:
    requested = Path(grammar_path)
    if requested.is_file():
        return str(requested)

    resource_parts = requested.parts
    if resource_parts and resource_parts[0] == "cluster1":
        resource_parts = resource_parts[1:]

    candidate = resources.files("cluster1").joinpath(*resource_parts)
    if candidate.is_file():
        return str(candidate)

    raise FileNotFoundError(f"grammar file not found: {grammar_path}")


def _dtype_name_to_bytes(dtype: str) -> int:
    dtype_bytes = {
        "fp32": 4,
        "fp16": 2,
        "bf16": 2,
    }.get(dtype)
    if dtype_bytes is None:
        raise ValueError(f"unsupported dtype for hardware masks: {dtype!r}")
    return dtype_bytes


def _manual_seed(torch_module: Any, seed: int) -> None:
    manual_seed = getattr(torch_module, "manual_seed", None)
    if callable(manual_seed):
        manual_seed(seed)


def _move_encoded_to_model_device(encoded: Any, model: Any) -> dict[str, Any]:
    device = _model_device(model)
    if device is None:
        return dict(encoded)
    return {
        key: value.to(device) if hasattr(value, "to") else value
        for key, value in encoded.items()
    }


def _model_device(model: Any) -> Any:
    device = getattr(model, "device", None)
    if device is not None:
        return device
    parameters = getattr(model, "parameters", None)
    if callable(parameters):
        try:
            first_param = next(parameters())
        except (StopIteration, TypeError):
            return None
        return getattr(first_param, "device", None)
    return None


def _sequence_length(input_ids: Any) -> int:
    shape = getattr(input_ids, "shape", None)
    if shape is not None:
        return int(shape[-1])
    first = input_ids[0] if input_ids and isinstance(input_ids[0], list) else input_ids
    return len(first)


def _decode_new_tokens(tokenizer: Any, output_ids: Any, prompt_len: int) -> str:
    if isinstance(output_ids, str):
        return output_ids

    sequence = output_ids[0] if _is_batched(output_ids) else output_ids
    try:
        new_tokens = sequence[prompt_len:]
    except TypeError:
        new_tokens = sequence[:, prompt_len:]
    if hasattr(new_tokens, "tolist"):
        new_tokens = new_tokens.tolist()
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


def _is_batched(output_ids: Any) -> bool:
    shape = getattr(output_ids, "shape", None)
    if shape is not None:
        return len(shape) == 2
    return bool(output_ids and isinstance(output_ids[0], list))


def _decoded_source(decoded: Any) -> str:
    if isinstance(decoded, str):
        return decoded
    if isinstance(decoded, dict):
        source = decoded.get("source")
    else:
        source = getattr(decoded, "source", None)
    if not isinstance(source, str) or not source:
        raise ValueError("generation returned no source text")
    return source


def _decoded_generation_seed(decoded: Any, fallback: int | None) -> int | None:
    if isinstance(decoded, dict):
        value = decoded.get("generation_seed", fallback)
    else:
        value = getattr(decoded, "generation_seed", fallback)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("generation_seed must be an int or None")
    if value < 0:
        raise ValueError("generation_seed must be non-negative")
    return value


def _inference_mode(torch_module: Any):
    inference_mode = getattr(torch_module, "inference_mode", None)
    if callable(inference_mode):
        return inference_mode()
    return nullcontext()


def _validate_source_identity(
    source_identity: Any,
    identity: EvalIdentity,
    source: str,
) -> None:
    if not isinstance(source_identity, dict):
        raise TypeError("source_identity must be a dict")
    expected_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if source_identity.get("source_sha256") != expected_sha:
        raise ValueError("source_identity source_sha256 does not match source")
    _validate_sidecar_identity_fields(
        source_identity,
        identity,
        field_name="source_identity",
        fields=(
            "condition",
            "source_class",
            "generation_mode",
            "kernel_class",
            "kernel_name",
            "dtype",
            "sample_index",
            "base_seed",
            "attempt_index",
        ),
    )


def _validate_generation_identity(
    generation_identity: Any,
    identity: EvalIdentity,
) -> None:
    if not isinstance(generation_identity, dict):
        raise TypeError("generation_identity must be a dict")
    requested_variant = generation_identity.get("grammar_variant")
    if requested_variant is not None and not isinstance(requested_variant, str):
        raise TypeError("generation_identity grammar_variant must be a string or None")
    routing = generation_routing_for_condition(
        identity.condition,
        grammar_variant=requested_variant,
    )
    if generation_identity.get("grammar_active") is not routing.grammar_active:
        raise ValueError("generation_identity grammar_active does not match condition")
    if generation_identity.get("grammar_variant") != routing.grammar_variant:
        raise ValueError("generation_identity grammar_variant does not match condition")
    if generation_identity.get("grammar_path") != routing.grammar_path:
        raise ValueError("generation_identity grammar_path does not match condition")
    if generation_identity.get("grammar_claim_scope") != routing.grammar_claim_scope:
        raise ValueError(
            "generation_identity grammar_claim_scope does not match condition"
        )
    generation_seed = generation_identity.get("generation_seed")
    if generation_seed is not None and (
        not isinstance(generation_seed, int) or isinstance(generation_seed, bool)
    ):
        raise TypeError("generation_identity generation_seed must be an int or None")


def _validate_model_identity(
    model_identity: Any,
    result: RemoteC2GenerationResult,
) -> None:
    if not isinstance(model_identity, dict):
        raise TypeError("model_identity must be a dict")
    for field_name in (
        "model_id",
        "model_revision",
        "tokenizer_revision",
        "tokenizer_grammar_id",
    ):
        value = model_identity.get(field_name)
        if not isinstance(value, str) or not value:
            raise ValueError(f"model_identity must include non-empty {field_name}")
    if model_identity["model_id"] != result.model_id:
        raise ValueError("model_identity model_id does not match generation_result")
    if model_identity["model_revision"] != result.model_revision:
        raise ValueError(
            "model_identity model_revision does not match generation_result"
        )


def _validate_modal_context(modal_context: Any) -> None:
    if not isinstance(modal_context, dict):
        raise TypeError("modal_context must be a dict")
    if modal_context.get("modal_generation_gpu") != REMOTE_C2_GENERATION_GPU:
        raise ValueError("modal_context must record L4 modal_generation_gpu")
    for field_name in ("function_call_id", "input_id"):
        value = modal_context.get(field_name)
        if value is not None and not isinstance(value, str):
            raise TypeError(f"modal_context {field_name} must be a string or None")


def _validate_sidecar_identity_fields(
    sidecar: dict[str, Any],
    identity: EvalIdentity,
    *,
    field_name: str,
    fields: tuple[str, ...],
) -> None:
    for field in fields:
        if sidecar.get(field) != getattr(identity, field):
            raise ValueError(f"{field_name} {field} does not match identity")


def _validate_string_mapping(value: Any, field_name: str) -> None:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{field_name} must be a non-empty dict")
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field_name} keys must be non-empty strings")
        if not isinstance(item, str) or not item:
            raise ValueError(f"{field_name} values must be non-empty strings")


def _reject_forbidden_payload_fields(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}" if isinstance(key, str) else path
            if (
                key in FORBIDDEN_REQUEST_RESULT_FIELD_NAMES
                or key in _C2_REMOTE_GENERATION_FORBIDDEN_EXTRA_FIELDS
            ):
                raise ValueError(f"forbidden remote C2 generation field: {key_path}")
            _reject_forbidden_payload_fields(item, key_path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_forbidden_payload_fields(item, f"{path}[{index}]")
