# Modal Image SHA Provenance Fix Report

## 1. Executive summary

Root cause: `cluster1.generation.provenance.modal_image_provenance()` computed `modal_image_sha` only from SHA-shaped environment variables (`MODAL_IMAGE_SHA`, `MODAL_IMAGE_DIGEST`). It computed `modal_image_provenance_sha256` and recorded `MODAL_IMAGE_ID` inside `modal_image_provenance_components`, but did not promote either value into the top-level `modal_image_sha` field. This produced rows with `modal_image_sha="unknown"` even when deterministic image provenance was present.

Selected path: Path A. `modal_image_sha` is treated as the canonical stable image provenance identifier. A real Modal runtime image identifier wins when present; otherwise the deterministic provenance SHA is used. Mutable tags are not promoted.

Final classification: `FIX_VERIFIED` for the provenance fix. Focused provenance, C1 metadata, and C2 result/schema tests pass. The broad regression command still reports two unrelated Phase -1/frozen hash failures in files not modified by this change.

## 2. Current behavior

`modal_image_sha` was computed in `cluster1/generation/provenance.py` by `_first_stable_image_digest()` using only `MODAL_IMAGE_SHA` and `MODAL_IMAGE_DIGEST`.

`modal_image_provenance_sha256` was computed in the same helper from `modal_image_provenance_components()` via `shared.generation_metadata.modal_image_provenance_digest()`.

C1 rows consume this helper through `shared/modal_harness/generation.py` and local C1 paths. C2 generated rows consume the same helper through `cluster2/modal/generation.py`.

Strict metadata validation lives in `cluster1/results/dataclass.py`, `cluster2/results/dataclass.py`, `shared/modal_harness/schemas.py`, `cluster2/modal/schemas.py`, and the C2 remote payload validator in `cluster2/modal/generation.py`.

The observed smoke had `modal_image_provenance_sha256` populated and `MODAL_IMAGE_ID` recorded inside components, while top-level `modal_image_sha` remained `unknown`.

## 3. Modal docs interpretation

The Modal docs establish that Modal image objects expose IDs through `.object_id` and that `Image.from_id()` can reconstruct an image from that ID.

They do not establish that `MODAL_IMAGE_ID` is always present as a runtime environment variable.

Using a deterministic content/provenance SHA as a fallback is therefore methodologically defensible for the smoke unblock: it records reproducible image provenance without inventing a Modal object ID.

## 4. Fix implementation

Fallback order implemented:

1. SHA-shaped runtime env vars: `MODAL_IMAGE_SHA`, `MODAL_IMAGE_DIGEST`.
2. Modal image ID env vars when stable: `MODAL_IMAGE_ID`, `MODAL_CONTAINER_IMAGE_ID`.
3. Modal image object ID if already available in code: none was available without runtime calls, so no object lookup was added.
4. Deterministic `modal_image_provenance_sha256`.
5. `unknown` only if no stable identifier or provenance digest can be produced.

Files modified:

- `shared/generation_metadata.py`
- `cluster1/generation/provenance.py`
- `cluster1/results/dataclass.py`
- `shared/modal_harness/schemas.py`
- `cluster2/modal/generation.py`
- `cluster2/modal/schemas.py`
- `cluster2/results/dataclass.py`
- tests under `shared/tests`, `cluster1/tests`, and `cluster2/tests`

C1 and C2 now share the same provenance helper and the same stable identifier predicate. `modal_image_provenance_sha256` and `modal_image_provenance_components` remain serialized alongside `modal_image_sha`.

## 5. Metadata gate behavior

The metadata gate was not weakened.

`unknown` is still rejected when no fallback provenance is present.

Fallback SHA values are accepted as non-unknown `modal_image_sha` values.

Modal object IDs are accepted only when they match the stable `im-...` identifier form. Mutable tags such as `mutable-tag` are still rejected and are only retained inside provenance components.

When provenance components are present, their digest must still match `modal_image_provenance_sha256`.

## 6. Tests added/updated

Added or updated tests for:

- env present: `MODAL_IMAGE_ID="im-123"` wins over fallback provenance.
- env absent plus provenance SHA: `modal_image_sha == modal_image_provenance_sha256`.
- no provenance: strict metadata gates reject `unknown` without fallback components/digest.
- row serialization: C2 generated row JSON round-trip preserves `modal_image_sha` and `modal_image_provenance_sha256`.
- strict gate behavior: C1/C2 accept fallback SHA and Modal object IDs, reject mutable tags, and reject mismatched fallback components.

## 7. Validation results

Passed:

- `.venv/bin/python -m pytest shared/tests cluster1/tests cluster2/tests -k "modal_image or image_provenance or provenance or generation_metadata" -q`
  - `61 passed, 2052 deselected`
- `.venv/bin/python -m pytest cluster1/tests/test_validate_cluster1_results.py cluster1/tests/test_results.py -q`
  - `71 passed`
- `.venv/bin/python -m pytest cluster2/tests/test_results_logger.py cluster2/tests/test_modal_schemas.py -q`
  - `83 passed`

Broad relevant regression:

- `.venv/bin/python -m pytest shared/tests cluster1/tests cluster2/tests -k "metadata or provenance or result or modal" -q`
  - `557 passed, 1 skipped, 1553 deselected, 2 failed`
  - Failures:
    - `cluster2/tests/test_cluster2_boundary.py::test_shared_modal_files_match_phase_minus1_git_head[shared/modal_harness/smoke.py]`
    - `cluster2/tests/test_modal_generation_c2.py::test_g_hash_gate_passes_current_approved_surface`
  - The failing files/hashes are not modified by this patch. `git diff -- shared/modal_harness/smoke.py cluster2/contracts/phase_minus1_manifest.json cluster2/contracts/frozen_cluster1_artifacts_manifest.json` is empty.

`git diff --check` passed.

## 8. Optional Modal smoke status

Not run. The task explicitly forbids Modal by default and requires approval before rerunning C n=1.

## 9. Next recommendation

`RUN_C_N1_SMOKE_AGAIN`

The provenance blocker is locally fixed and focused tests pass. Before using the broad regression command as a release gate, separately resolve or waive the existing Phase -1/frozen hash mismatches without re-recording hashes as part of this provenance patch.
