# Claim-Gated Math Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement MathForge as a standalone Python CLI that runs role-specific
math agents and blocks immature claims from final synthesis.

**Architecture:** A small standard-library Python package owns run state,
schemas, providers, worker execution, review decisions, promotion gates, and
report synthesis. Workers return structured outputs through a provider
interface; only the runner writes artifacts and changes lifecycle state.

**Tech Stack:** Python 3.12+, standard library, `unittest` test runner, Codex
CLI subprocess provider, deterministic mock provider, JSON and Markdown
artifacts.

**Spec:** `docs/superpowers/specs/2026-10-09-claim-gated-math-agent-design.md`

## Global Constraints

- No runtime dependency on the original Comath repository.
- No production code before a failing test.
- Only approved claims may enter the final report.
- Workers may not mark runs complete.
- Failed and blocked reasoning must remain in the run directory.
- The mock provider must run without credentials.
- The Codex provider must be optional and fail with a recorded structured error.
- Source files use ASCII unless a clear project need requires otherwise.

## Review Focus

- A plausible proof sketch must never be promoted as a verified claim.
- A reviewer approving one claim must not implicitly approve other claims.
- A computation-required claim must fail promotion without passing computation evidence.
- A final report must exclude blocked and unapproved claims.
- A worker output path must not escape its assigned run directory.

---

### Task 1: Project Skeleton And Domain Models

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.gitignore`
- Create: `src/mathforge/__init__.py`
- Create: `src/mathforge/models.py`
- Create: `src/mathforge/errors.py`
- Test: `tests/test_models.py`

**Interfaces:**
- `Claim.from_dict(data: dict) -> Claim`
- `Claim.to_dict() -> dict`
- `ReviewDecision.from_dict(data: dict) -> ReviewDecision`
- `RunManifest.from_dict(data: dict) -> RunManifest`
- `validate_claim(claim: Claim) -> list[str]`

- [ ] **Step 1: Write failing model validation tests** for missing claim ids,
  invalid maturity values, invalid review decisions, and round-trip serialization.
- [ ] **Step 2: Run `python -m unittest tests.test_models -v` and confirm the
  tests fail because the package is absent.
- [ ] **Step 3: Implement typed dataclasses, enums, validation errors, and
  JSON serialization.
- [ ] **Step 4: Run the focused tests and then `python -m unittest discover -v`.
- [ ] **Step 5: Add project metadata and a README skeleton describing the
  claim-gated purpose.

### Task 2: Run Storage, Events, And Promotion State Machine

**Files:**
- Create: `src/mathforge/storage.py`
- Create: `src/mathforge/state.py`
- Test: `tests/test_state_and_storage.py`

**Interfaces:**
- `create_run(root: Path, objective: str, provider: str) -> RunContext`
- `load_run(root: Path, run_id: str) -> RunContext`
- `append_event(context: RunContext, event_type: str, details: dict) -> None`
- `transition_run(context: RunContext, target: RunStatus) -> None`
- `safe_output_path(context: RunContext, relative: str) -> Path`

- [ ] **Step 1: Write failing tests for run creation, event persistence,
  legal lifecycle transitions, and path escape rejection.
- [ ] **Step 2: Run the focused tests and observe the expected import/failure.
- [ ] **Step 3: Implement run directories, manifest persistence, JSONL events,
  state transitions, and path containment checks.
- [ ] **Step 4: Run focused and full tests.

### Task 3: Providers And Worker Contracts

**Files:**
- Create: `src/mathforge/providers.py`
- Create: `src/mathforge/prompts.py`
- Create: `src/mathforge/workers.py`
- Test: `tests/test_providers_and_workers.py`

**Interfaces:**
- `class Provider: run(self, task: TaskSpec) -> ProviderResult`
- `MockProvider.run(task: TaskSpec) -> ProviderResult`
- `CodexProvider.run(task: TaskSpec) -> ProviderResult`
- `build_task(role: str, objective: str, input_files: list[str]) -> TaskSpec`
- `validate_worker_result(result: ProviderResult, task: TaskSpec) -> list[str]`

- [ ] **Step 1: Write failing tests showing the mock provider emits one
  immature proof claim and one approved empirical claim, and the Codex provider
  reports an unavailable executable as a structured error.
- [ ] **Step 2: Run the focused tests and confirm failure.
- [ ] **Step 3: Implement provider interfaces, deterministic mock scenarios,
  prompt assembly, optional Codex subprocess execution, and worker-output
  validation.
- [ ] **Step 4: Run focused and full tests.

### Task 4: Claim Review And Promotion Gates

**Files:**
- Create: `src/mathforge/claims.py`
- Create: `src/mathforge/review.py`
- Create: `src/mathforge/gates.py`
- Test: `tests/test_claim_gates.py`

**Interfaces:**
- `load_claims(run: RunContext) -> list[Claim]`
- `apply_review(run: RunContext, decision: ReviewDecision) -> None`
- `build_claim_registry(run: RunContext) -> ClaimRegistry`
- `check_promotion(run: RunContext) -> GateReport`
- `promote(run: RunContext) -> ClaimRegistry`

- [ ] **Step 1: Write failing tests for:
  - plausible sketches being rejected;
  - reviewer approval being limited to explicit ids;
  - blocked claims preventing promotion;
  - missing computation evidence preventing promotion;
  - malformed claims producing structured gate errors.
- [ ] **Step 2: Run the focused tests and confirm each fails for the missing
  gate behavior.
- [ ] **Step 3: Implement claim loading, review application, registry creation,
  evidence checks, maturity checks, computation checks, and structured
  `GateError` reports.
- [ ] **Step 4: Run focused and full tests.

### Task 5: Planner, Reviewer, And Synthesis Pipeline

**Files:**
- Create: `src/mathforge/planner.py`
- Create: `src/mathforge/synthesis.py`
- Create: `src/mathforge/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- `plan_objective(objective: str) -> ResearchPlan`
- `run_cycle(root: Path, objective: str, provider_name: str) -> RunContext`
- `synthesize_final_report(run: RunContext) -> Path`

- [ ] **Step 1: Write failing end-to-end tests asserting that a demo run
  creates proof/computation/reviewer artifacts, blocks the immature proof,
  registers only approved claims, and writes a final report without the blocked
  claim.
- [ ] **Step 2: Run the end-to-end tests and confirm failure.
- [ ] **Step 3: Implement role planning, worker sequencing, sanitized review
  packet generation, review application, promotion, and final synthesis.
- [ ] **Step 4: Run focused and full tests.

### Task 6: CLI, Demo, Documentation, And Release Checks

**Files:**
- Create: `src/mathforge/cli.py`
- Create: `src/mathforge/__main__.py`
- Create: `examples/demo_objective.txt`
- Modify: `README.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- `python -m mathforge --help`
- `python -m mathforge run "<objective>" --provider mock`
- `python -m mathforge status <run-id>`
- `python -m mathforge promote <run-id>`
- `python -m mathforge synthesize <run-id>`

- [ ] **Step 1: Write failing CLI tests for help, mock run, status, and
  blocked-claim exit behavior.
- [ ] **Step 2: Run the focused CLI tests and confirm failure.
- [ ] **Step 3: Implement the CLI and human-readable gate output.
- [ ] **Step 4: Add README architecture, state machine, demo transcript,
  provider instructions, and limitations.
- [ ] **Step 5: Run `python -m unittest discover -v`, the mock demo, and
  `python -m mathforge --help`.
- [ ] **Step 6: Run a final review of the full diff and record any deferred
  limitations.

## Commit Sequence

1. `feat: add claim and run domain models`
2. `feat: add file-backed run state`
3. `feat: add mock and codex providers`
4. `feat: enforce claim review gates`
5. `feat: add end-to-end research pipeline`
6. `docs: add MathForge demo and usage guide`

