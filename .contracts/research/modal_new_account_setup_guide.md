# Modal New Account Setup Guide

This guide reconstructs the TritonGen Modal infrastructure in a new Modal
account/workspace. Run these commands manually from the repository root:

```bash
cd /Users/alexeidelgado/Desktop/TritonGen
```

Use the existing Modal CLI if present:

```bash
export MODAL=/Users/alexeidelgado/miniconda3/bin/modal
$MODAL --version
```

If that binary is missing, install or expose Modal in your normal local Python
tooling first. Do not create a project venv just for Modal setup.

## Resource Model

The project owns one Modal app:

- `tritongen-gpu-harness`

The app is defined in:

- `shared/modal_harness/app.py`

The volumes are created lazily by code on first remote use with
`create_if_missing=True`; do not pre-create them by hand:

- `tritongen-hf-cache`
- `tritongen-eval-artifacts`

The optional Hugging Face secret is:

- `huggingface-token`

It is only needed for gated/private models. The current development model,
`Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`, is public.

## Account And Environment Bootstrap

Authenticate the new account:

```bash
$MODAL setup
```

Inspect the available profiles/workspaces:

```bash
$MODAL profile list
$MODAL config show
```

Activate the profile that points to the new TritonGen workspace. If you named
the workspace/profile `tritongen-lab`, run:

```bash
$MODAL profile activate tritongen-lab
```

If the profile has a different name, use that name instead:

```bash
$MODAL profile activate <profile-that-points-to-the-new-workspace>
```

Create and select the project development environment:

```bash
$MODAL environment create tritongen-dev
$MODAL config set-environment tritongen-dev
$MODAL config show
```

Expected result:

- Active profile points to the new Modal workspace.
- Default environment is `tritongen-dev`.
- `$MODAL app list` works without `Token not found`.

```bash
$MODAL app list
```

If you do not set `tritongen-dev` as the default environment, pass
`--env tritongen-dev` to every `modal run`, `modal deploy`, and `modal app logs`
command below.

## Optional Hugging Face Secret

Skip this section for public-model smoke tests. If a gated model is required,
create the secret manually:

```bash
$MODAL secret create huggingface-token HF_TOKEN=<your-hugging-face-token>
export TRITONGEN_MODAL_HF_SECRET=huggingface-token
```

Do not commit tokens or token-derived values.

## Local Import Preflight

Use the repository venv for local Python validation:

```bash
.venv/bin/python -c "import cluster1, cluster2, shared"
.venv/bin/python -m pytest shared/tests/test_eval_imports.py -q
```

## Modal Smoke Sequence

Start with import-only. This verifies the app, image build path, source
packaging, and the new account token without generation:

```bash
$MODAL run -m shared.modal_harness.smoke --case import-only
```

Then verify compile-only GPU execution on L4:

```bash
$MODAL run -m shared.modal_harness.smoke --case good-relu-compile
$MODAL run -m shared.modal_harness.smoke --case bad-triton-compile
```

These commands may create the lazy volumes and build the compile image. They do
not run generation.

## Optional Generation Smoke

Run generation smoke only after the compile smoke succeeds and only if you are
ready to spend L4 generation time:

```bash
$MODAL run -m shared.modal_harness.smoke --case generate-baseline-one
```

If task-agnostic grammar generation is explicitly needed later:

```bash
$MODAL run -m shared.modal_harness.smoke --case generate-g-one
```

Do not use these generation smokes as a substitute for the current
cross-cluster Phase 4 baseline revalidation.

## Phase 4 Modal Revalidation Command

After Modal auth and compile smoke are working, rerun the Phase 4 evidence
command:

```bash
$MODAL run -m cluster1.diagnostics.revalidate_baseline_aligned_pipeline \
  --input outputs/cluster1/baseline_repaired_l4_n20.jsonl \
  --output outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline.jsonl
```

Expected behavior:

- Reads `outputs/cluster1/baseline_repaired_l4_n20.jsonl`.
- Writes only
  `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline.jsonl`.
- Runs each baseline source through both C1-entrypoint and C2-entrypoint aligned
  evaluation paths.
- Fails the Modal entrypoint if any C1/C2 entrypoint result differs after
  canonicalization.
- Records Modal call ids, L4 GPU class, and Modal image provenance in diagnostic
  rows.

If the command fails because the output already exists, inspect the existing
diagnostic before deciding whether to move it aside. Do not overwrite evidence
without recording why.

## Logs

Stream app logs:

```bash
$MODAL app logs tritongen-gpu-harness -f --timestamps --show-function-call-id
```

Inspect a specific function call if Modal prints one:

```bash
$MODAL app logs tritongen-gpu-harness --function-call <fc-id> --timestamps
```

## What Not To Do During Bootstrap

- Do not run n=5 or n=20 generation while reconstructing the account.
- Do not re-record grammar hashes.
- Do not edit frozen JSONL artifacts or manifests.
- Do not pre-create the project volumes manually; the code creates them lazily.
- Do not use the workspace `main` environment for research evidence unless
  there is an explicit reason and the command records that environment choice.

## Recovery Checklist

If Modal reports `Token not found`:

1. Run `$MODAL setup`.
2. Run `$MODAL profile list`.
3. Activate the profile for the new workspace.
4. Run `$MODAL config set-environment tritongen-dev`.
5. Confirm `$MODAL app list` works.
6. Retry the import-only smoke.

If `modal profile list` shows a profile like
`tritongen-lab | Unknown (authentication failure)`, the local profile exists but
its stored token is stale, revoked, or tied to the old account. The installed
Modal CLI on this machine does not expose `profile delete`, so create a new
profile name and use that profile for this account:

```bash
export MODAL=/Users/alexeidelgado/miniconda3/bin/modal
$MODAL setup --profile tritongen-lab-new
$MODAL profile activate tritongen-lab-new
$MODAL token info
$MODAL config show
$MODAL environment create tritongen-dev
$MODAL config set-environment tritongen-dev
$MODAL app list
```

If the browser setup flow is awkward, create a token from the Modal dashboard
for the new account and paste it into:

```bash
$MODAL token set --profile tritongen-lab-new --activate
```

Do not reuse the old `tritongen-lab` profile until it shows a known workspace
and `$MODAL token info` succeeds.

If image build fails:

1. Check whether the active environment is `tritongen-dev`.
2. Confirm `shared/modal_harness/images.py` still pins the expected packages.
3. Retry `import-only` before compile or generation smokes.

If compile smoke fails:

1. Capture the Modal function call id.
2. Inspect logs with `$MODAL app logs`.
3. Do not proceed to Phase 4 Modal revalidation until compile smoke is clean.
