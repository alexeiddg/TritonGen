"""External API baseline runner for TritonGen.

Generates Triton kernels using Claude and Gemini APIs with the exact same
prompt template as the existing HuggingFace baseline (cluster1/data/prompts/
prompt_contract.py). No grammar, no repair loop — pure single-shot generation.

Setup:
    pip install anthropic google-generativeai python-dotenv

    Create a .env file in the project root:
        ANTHROPIC_API_KEY=...
        GOOGLE_API_KEY=...

    Or export them manually:
        export ANTHROPIC_API_KEY=...
        export GOOGLE_API_KEY=...

Usage:
    python run_external_baselines.py --models claude gemini
    python run_external_baselines.py --models claude
    python run_external_baselines.py --models gemini --resume

Output:
    outputs/external/claude_baseline_n20.jsonl
    outputs/external/gemini_baseline_n20.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Kernel specs — mirrors cluster1/data/kernels/*.py and prompt_contract.py
# ---------------------------------------------------------------------------

KERNEL_SPECS: list[dict[str, Any]] = [
    {
        "name": "relu",
        "kernel_class": "elementwise",
        "launcher_name": "relu",
        "helper_name": "_relu_kernel",
        "signature": "relu(x: torch.Tensor) -> torch.Tensor",
        "description": (
            "Applies elementwise ReLU activation: output = max(0, x). "
            "Input is a 1D or 2D tensor of arbitrary shape."
        ),
        "autotune_configs": [
            {"BLOCK_SIZE": 64,  "num_warps": 2, "num_stages": 3},
            {"BLOCK_SIZE": 128, "num_warps": 4, "num_stages": 3},
            {"BLOCK_SIZE": 256, "num_warps": 4, "num_stages": 3},
            {"BLOCK_SIZE": 512, "num_warps": 8, "num_stages": 3},
        ],
        "dataset_problem_id": 19,
    },
    {
        "name": "softmax",
        "kernel_class": "reduction",
        "launcher_name": "softmax",
        "helper_name": "_softmax_kernel",
        "signature": "softmax(x: torch.Tensor) -> torch.Tensor",
        "description": (
            "Computes row-wise softmax along dim=1 for a 2D input tensor. "
            "Each row is independently normalized to sum to 1."
        ),
        "autotune_configs": [
            {"BLOCK_SIZE": 64,  "num_warps": 2, "num_stages": 3},
            {"BLOCK_SIZE": 128, "num_warps": 4, "num_stages": 3},
            {"BLOCK_SIZE": 256, "num_warps": 4, "num_stages": 4},
            {"BLOCK_SIZE": 512, "num_warps": 8, "num_stages": 4},
        ],
        "dataset_problem_id": 23,
    },
    {
        "name": "gemm",
        "kernel_class": "matmul",
        "launcher_name": "matmul",
        "helper_name": "_matmul_kernel",
        "signature": "matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor",
        "description": (
            "Computes C = A @ B for 2D matrices A (M x K) and B (K x N), "
            "producing output C (M x N). Uses tiled matrix multiplication with shared memory."
        ),
        "autotune_configs": [
            {"BLOCK_M": 32,  "BLOCK_N": 32,  "BLOCK_K": 32, "num_warps": 4, "num_stages": 2},
            {"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 32, "num_warps": 4, "num_stages": 3},
            {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "num_warps": 8, "num_stages": 3},
            {"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 64, "num_warps": 8, "num_stages": 4},
        ],
        "dataset_problem_id": 1,
    },
]

DTYPES = ["fp32", "fp16", "bf16"]
N_SEEDS = 20
TEMPERATURE = 0.2
MAX_TOKENS = 2048

# ---------------------------------------------------------------------------
# Prompt construction — exact replica of cluster1/data/prompts/prompt_contract.py
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
You are a Triton GPU kernel engineer. Write a complete Python module.

Public launcher signature: def {signature}:
Private Triton helper name: {helper_name}
Kernel description: {description}
Input dtype: {dtype}  |  Device: CUDA

Required module surface:
- Start with exactly these imports:
  import torch
  import triton
  import triton.language as tl
- Define one private @triton.jit helper named {helper_name}.
- Define one public Python launcher named exactly {launcher_name}.
- The public launcher signature must be exactly: def {signature}:
- The public launcher must allocate the output tensor.
- The public launcher must define an explicit grid.
- The public launcher must launch {helper_name} with bracket syntax.
- The public launcher must return the output tensor.

Allowed block configurations:
{autotune_configs}

Return ONLY the Python module. No explanation. No markdown fences. No prose.
"""


def _format_autotune_configs(configs: list[dict]) -> str:
    lines = []
    for cfg in configs:
        block_items = {
            key: value
            for key, value in cfg.items()
            if key not in {"num_warps", "num_stages"}
        }
        block_parts = ", ".join(f'"{key}": {value}' for key, value in block_items.items())
        lines.append(
            f'        triton.Config({{{block_parts}}}, '
            f'num_warps={cfg["num_warps"]}, '
            f'num_stages={cfg["num_stages"]})'
        )
    return "[\n" + ",\n".join(lines) + "\n    ]"


def build_prompt(spec: dict, dtype: str) -> str:
    return _PROMPT_TEMPLATE.format(
        signature=spec["signature"],
        launcher_name=spec["launcher_name"],
        helper_name=spec["helper_name"],
        description=spec["description"],
        dtype=dtype,
        autotune_configs=_format_autotune_configs(spec["autotune_configs"]),
    )


def _source_hash(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()


# ---------------------------------------------------------------------------
# API clients
# ---------------------------------------------------------------------------

def _claude_client():
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY env var not set")
    return anthropic.Anthropic(api_key=api_key)


def _gemini_model(model_name: str):
    import google.generativeai as genai
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY env var not set")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def _call_claude(
    client,
    model: str,
    prompt: str,
    *,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> tuple[str, dict]:
    """Call Claude API and return (source_text, usage_dict)."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            return text, usage
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                wait = retry_delay * (2 ** attempt)
                print(f"    Claude API error (attempt {attempt+1}/{max_retries}): {exc}. "
                      f"Retrying in {wait:.0f}s...")
                time.sleep(wait)
    raise RuntimeError(f"Claude API failed after {max_retries} attempts: {last_exc}")


def _call_gemini(
    model_obj,
    prompt: str,
    *,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> tuple[str, dict]:
    """Call Gemini API and return (source_text, usage_dict)."""
    import google.generativeai as genai

    generation_config = genai.types.GenerationConfig(
        temperature=TEMPERATURE,
        max_output_tokens=MAX_TOKENS,
    )
    last_exc = None
    for attempt in range(max_retries):
        try:
            response = model_obj.generate_content(
                prompt,
                generation_config=generation_config,
            )
            text = response.text
            usage = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = {
                    "input_tokens": getattr(response.usage_metadata, "prompt_token_count", None),
                    "output_tokens": getattr(response.usage_metadata, "candidates_token_count", None),
                }
            return text, usage
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                wait = retry_delay * (2 ** attempt)
                print(f"    Gemini API error (attempt {attempt+1}/{max_retries}): {exc}. "
                      f"Retrying in {wait:.0f}s...")
                time.sleep(wait)
    raise RuntimeError(f"Gemini API failed after {max_retries} attempts: {last_exc}")


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------

def _load_existing_keys(path: Path) -> set[tuple]:
    """Return (kernel_name, dtype, seed) tuples already written."""
    if not path.exists():
        return set()
    keys = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                keys.add((row["kernel_name"], row["dtype"], row["generation_seed"]))
            except Exception:
                pass
    return keys


def _append_row(path: Path, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _build_row(
    *,
    spec: dict,
    dtype: str,
    seed: int,
    source: str,
    model_name: str,
    usage: dict,
    run_id: str,
    prompt: str,
) -> dict:
    return {
        "kernel_class": spec["kernel_class"],
        "kernel_name": spec["name"],
        "dtype": dtype,
        "generation_seed": seed,
        "source": source,
        "compile_success": None,
        "failure_code": None,
        "compile_error_type": None,
        "compile_error_msg": None,
        "model_name": model_name,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "grammar_active": False,
        "grammar_variant": None,
        "condition": "external_baseline",
        "dataset_problem_id": spec["dataset_problem_id"],
        "unique_solution_hash": _source_hash(source),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "usage": usage,
        "run_id": run_id,
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# Generation loop
# ---------------------------------------------------------------------------

def run_claude(
    output_path: Path,
    model: str = "claude-sonnet-4-6",
    resume: bool = True,
    rate_limit_delay: float = 0.5,
) -> None:
    client = _claude_client()
    existing = _load_existing_keys(output_path) if resume else set()
    total = len(KERNEL_SPECS) * len(DTYPES) * N_SEEDS
    done = len(existing)
    print(f"\n[Claude] model={model}  output={output_path}")
    print(f"  Total cells: {total}  Already done: {done}  Remaining: {total - done}")

    import uuid
    run_id = str(uuid.uuid4())
    n_written = 0

    for spec in KERNEL_SPECS:
        for dtype in DTYPES:
            for seed in range(N_SEEDS):
                key = (spec["name"], dtype, seed)
                if key in existing:
                    continue
                prompt = build_prompt(spec, dtype)
                cell_label = f"{spec['name']} × {dtype} × seed={seed}"
                print(f"  [{n_written + done + 1}/{total}] Claude: {cell_label}", end=" ", flush=True)
                try:
                    source, usage = _call_claude(client, model, prompt)
                    print(f"→ {usage.get('output_tokens', '?')} tokens")
                except Exception as exc:
                    print(f"→ ERROR: {exc}")
                    source = ""
                    usage = {}

                row = _build_row(
                    spec=spec,
                    dtype=dtype,
                    seed=seed,
                    source=source,
                    model_name=model,
                    usage=usage,
                    run_id=run_id,
                    prompt=prompt,
                )
                _append_row(output_path, row)
                n_written += 1
                time.sleep(rate_limit_delay)

    print(f"[Claude] Done. Wrote {n_written} new rows to {output_path}")


def run_gemini(
    output_path: Path,
    model: str = "gemini-2.5-flash",
    resume: bool = True,
    rate_limit_delay: float = 1.0,
) -> None:
    model_obj = _gemini_model(model)
    existing = _load_existing_keys(output_path) if resume else set()
    total = len(KERNEL_SPECS) * len(DTYPES) * N_SEEDS
    done = len(existing)
    print(f"\n[Gemini] model={model}  output={output_path}")
    print(f"  Total cells: {total}  Already done: {done}  Remaining: {total - done}")

    import uuid
    run_id = str(uuid.uuid4())
    n_written = 0

    for spec in KERNEL_SPECS:
        for dtype in DTYPES:
            for seed in range(N_SEEDS):
                key = (spec["name"], dtype, seed)
                if key in existing:
                    continue
                prompt = build_prompt(spec, dtype)
                cell_label = f"{spec['name']} × {dtype} × seed={seed}"
                print(f"  [{n_written + done + 1}/{total}] Gemini: {cell_label}", end=" ", flush=True)
                try:
                    source, usage = _call_gemini(model_obj, prompt)
                    print(f"→ {usage.get('output_tokens', '?')} tokens")
                except Exception as exc:
                    print(f"→ ERROR: {exc}")
                    source = ""
                    usage = {}

                row = _build_row(
                    spec=spec,
                    dtype=dtype,
                    seed=seed,
                    source=source,
                    model_name=model,
                    usage=usage,
                    run_id=run_id,
                    prompt=prompt,
                )
                _append_row(output_path, row)
                n_written += 1
                time.sleep(rate_limit_delay)

    print(f"[Gemini] Done. Wrote {n_written} new rows to {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Claude and/or Gemini external baseline generation for TritonGen."
    )
    parser.add_argument(
        "--models",
        nargs="+",
        choices=["claude", "gemini"],
        default=["claude", "gemini"],
        help="Which model(s) to run (default: both)",
    )
    parser.add_argument(
        "--claude-model",
        default="claude-sonnet-4-6",
        help="Claude model identifier",
    )
    parser.add_argument(
        "--gemini-model",
        default="gemini-2.5-flash",
        help="Gemini model identifier (e.g. gemini-2.5-flash, gemini-2.5-pro)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/external"),
        help="Directory for output JSONL files",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Skip already-generated rows (default: True)",
    )
    parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Overwrite and regenerate all rows",
    )
    parser.add_argument(
        "--rate-limit-delay",
        type=float,
        default=0.5,
        help="Seconds to wait between API calls (default: 0.5)",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if "claude" in args.models:
        out = args.output_dir / "claude_baseline_n20.jsonl"
        run_claude(
            out,
            model=args.claude_model,
            resume=args.resume,
            rate_limit_delay=args.rate_limit_delay,
        )

    if "gemini" in args.models:
        out = args.output_dir / "gemini_baseline_n20.jsonl"
        run_gemini(
            out,
            model=args.gemini_model,
            resume=args.resume,
            rate_limit_delay=args.rate_limit_delay,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
