from __future__ import annotations

from pathlib import Path

import eval_external_modal


def test_external_modal_evaluator_knows_openai_output_file() -> None:
    assert eval_external_modal.FILES["openai"] == Path(
        "outputs/external/openai_baseline_n20.jsonl"
    )
