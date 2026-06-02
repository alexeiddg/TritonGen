"""Create a tiny synthetic MLflow run for onboarding.

This script does not load models, use Triton, or require a GPU. It exercises the
same `shared.tracking` run boundary used by real launchers, then logs a few demo
metrics so teammates can verify that the MLflow UI is reading `./mlruns`.
"""

from __future__ import annotations

from shared import tracking


def main() -> int:
    run_config = {
        "condition": "demo",
        "scale_tier": "smoke",
        "model_id": "synthetic-mlflow-demo",
        "source_class": "synthetic",
    }
    with tracking.run_context(
        run_config=run_config,
        cli_args={"demo": True},
        backend="local",
        cluster="cluster1",
    ):
        for step, compile_success in enumerate((1.0, 0.0, 1.0)):
            tracking.log_metrics(
                {
                    "gen.compile_success": compile_success,
                    "gen.n_shapes_tested": 3.0,
                },
                step=step,
            )
    print("Demo MLflow run written if TRITONGEN_MLFLOW=1 and mlflow is installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
