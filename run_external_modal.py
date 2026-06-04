"""Modal entry point for external API baseline generation.

Currently supports OpenAI GPT models through the Responses API. Output rows use
the same JSONL shape as ``run_external_baselines.py`` so
``eval_external_modal.py`` can compile/evaluate them without a separate path.

Setup:
    modal secret create openai-api-key OPENAI_API_KEY=<token>
    export TRITONGEN_MODAL_OPENAI_SECRET=openai-api-key

Usage:
    modal run -m run_external_modal --models openai --n-seeds 1
    modal run -m run_external_modal --models openai --openai-model gpt-5.1
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from shared.modal_harness.app import app
from shared.modal_harness.openai_generation import (
    DEFAULT_OPENAI_MODEL,
    remote_openai_generate_one,
)

from run_external_baselines import (
    DTYPES,
    KERNEL_SPECS,
    MAX_TOKENS,
    N_SEEDS,
    TEMPERATURE,
    _append_row,
    _build_row,
    _load_existing_keys,
    build_prompt,
)


def _validate_modal_openai_secret() -> None:
    if not os.environ.get("TRITONGEN_MODAL_OPENAI_SECRET"):
        raise RuntimeError(
            "TRITONGEN_MODAL_OPENAI_SECRET is not set. Create a Modal secret with "
            "`modal secret create openai-api-key OPENAI_API_KEY=<token>` and then "
            "`export TRITONGEN_MODAL_OPENAI_SECRET=openai-api-key`."
        )


def _call_openai_modal(
    *,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> tuple[str, dict[str, Any]]:
    req = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
    }
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            payload = remote_openai_generate_one.remote(req)
            usage = dict(payload.get("usage") or {})
            usage["api_surface"] = payload.get("api_surface")
            usage["modal_function_call_id"] = payload.get("modal_function_call_id")
            usage["modal_input_id"] = payload.get("modal_input_id")
            return str(payload.get("source", "")), usage
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                wait = retry_delay * (2**attempt)
                print(
                    f"    OpenAI Modal error (attempt {attempt + 1}/{max_retries}): "
                    f"{exc}. Retrying in {wait:.0f}s..."
                )
                time.sleep(wait)
    raise RuntimeError(f"OpenAI Modal generation failed after {max_retries} attempts: {last_exc}")


def run_openai_modal(
    output_path: Path,
    *,
    model: str = DEFAULT_OPENAI_MODEL,
    resume: bool = True,
    rate_limit_delay: float = 0.5,
    n_seeds: int = N_SEEDS,
    reasoning_effort: str | None = None,
) -> None:
    _validate_modal_openai_secret()
    existing = _load_existing_keys(output_path) if resume else set()
    total = len(KERNEL_SPECS) * len(DTYPES) * n_seeds
    done = len(existing)
    print(f"\n[OpenAI via Modal] model={model}  output={output_path}")
    print(f"  Total cells: {total}  Already done: {done}  Remaining: {total - done}")

    run_id = str(uuid.uuid4())
    n_written = 0

    for spec in KERNEL_SPECS:
        for dtype in DTYPES:
            for seed in range(n_seeds):
                key = (spec["name"], dtype, seed)
                if key in existing:
                    continue

                prompt = build_prompt(spec, dtype)
                cell_label = f"{spec['name']} × {dtype} × seed={seed}"
                print(
                    f"  [{n_written + done + 1}/{total}] OpenAI: {cell_label}",
                    end=" ",
                    flush=True,
                )
                try:
                    source, usage = _call_openai_modal(
                        model=model,
                        prompt=prompt,
                        temperature=TEMPERATURE,
                        max_tokens=MAX_TOKENS,
                        reasoning_effort=reasoning_effort,
                    )
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
                row["provider"] = "openai"
                row["condition"] = "external_openai_baseline"
                row["api_surface"] = "openai_responses"
                _append_row(output_path, row)
                n_written += 1
                time.sleep(rate_limit_delay)

    print(f"[OpenAI via Modal] Done. Wrote {n_written} new rows to {output_path}")


@app.local_entrypoint()
def modal_main(
    models: str = "openai",
    openai_model: str = DEFAULT_OPENAI_MODEL,
    output_dir: str = "outputs/external",
    resume: bool = True,
    rate_limit_delay: float = 0.5,
    n_seeds: int = N_SEEDS,
    reasoning_effort: str = "",
) -> None:
    selected = [item.strip() for item in models.split(",") if item.strip()]
    if selected != ["openai"]:
        raise ValueError("run_external_modal currently supports only models=openai")

    output_path = Path(output_dir) / "openai_baseline_n20.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_openai_modal(
        output_path,
        model=openai_model,
        resume=resume,
        rate_limit_delay=rate_limit_delay,
        n_seeds=n_seeds,
        reasoning_effort=reasoning_effort or None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run OpenAI external baseline generation through Modal."
    )
    parser.add_argument("--models", nargs="+", choices=["openai"], default=["openai"])
    parser.add_argument("--openai-model", default=DEFAULT_OPENAI_MODEL)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/external"))
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument("--rate-limit-delay", type=float, default=0.5)
    parser.add_argument("--n-seeds", type=int, default=N_SEEDS)
    parser.add_argument(
        "--reasoning-effort",
        default=None,
        choices=[None, "none", "low", "medium", "high", "xhigh"],
    )
    args = parser.parse_args()

    if args.models != ["openai"]:
        raise ValueError("run_external_modal currently supports only --models openai")

    output_path = args.output_dir / "openai_baseline_n20.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_openai_modal(
        output_path,
        model=args.openai_model,
        resume=args.resume,
        rate_limit_delay=args.rate_limit_delay,
        n_seeds=args.n_seeds,
        reasoning_effort=args.reasoning_effort,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
