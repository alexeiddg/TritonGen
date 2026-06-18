# Contracts Directory

This directory is split by audience.

## Research-Facing Docs

Research-facing docs live in `.contracts/research/`. These files are intended
to be safe to commit and useful when writing the paper, thesis methodology, or
committee-facing design notes. They should explain design decisions, research
scope, evaluation policy, and non-sensitive methodology.

Rules for research-facing docs:

- no API keys, token values, local credential paths, or account-specific secret
  material;
- no raw experiment outputs or generated kernel batches;
- no AI-agent work queues, prompt instructions, or step-by-step implementation
  delegation notes;
- no stale mechanisms outside the current scope, except as explicitly labeled
  non-goals or future work;
- use Triton-only research language. Infrastructure may mention GPU workers or
  vendor runtime details only when needed for reproducibility.

Current research-facing docs:

- `.contracts/research/research_scope.md`
- `.contracts/research/scale_policy.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/cluster1_generated_surface.md`

## Agentic/Internal Docs

Agentic docs live in `.contracts/agentic/`. They are implementation aids for
Codex, Claude Code, or future engineering agents. They may include local Modal
setup notes, execution order, scratch plans, stale drafts, or operational
details that are not part of the research paper narrative.

`.contracts/agentic/` is intentionally ignored by git through the root
`.gitignore`. Do not cite these files in the paper. If an internal note contains
a research decision worth preserving, promote the sanitized decision into
`.contracts/research/` instead of committing the operational note.

Typical internal examples in this workspace:

- `.contracts/agentic/post_cluster1_scope_and_execution_plan.md`
- `.contracts/agentic/modal_integration_plan.md`
- `.contracts/agentic/modal_harness_draft.md`
- `.contracts/agentic/cluster1_contract.md`
- `.contracts/agentic/cluster1_plan.md`
- `.contracts/agentic/reference/`

## Commit Guidance

For a normal research commit, include:

- repo and cluster README files;
- `.contracts/README.md`;
- `.contracts/research/**`;
- code or config changes needed to make the docs true.

Do not include `.contracts/agentic/**` unless the explicit goal is to version
internal implementation instructions.
