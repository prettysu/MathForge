# MathForge Claim-Gated Math Agent Design

**Status:** Draft for implementation

## Goal

Build a standalone, Git-ready Python tool that turns a mathematical question
into a file-backed multi-agent research run and prevents immature, unsupported,
or over-claimed reasoning from entering the final report.

MathForge is inspired by the workflow ideas in Comath, but is an independent
implementation with a smaller public surface and a provider-neutral runtime.

## Core Promise

Every substantive conclusion is represented as a claim. A claim begins as
untrusted candidate reasoning and can enter the final report only after:

1. its assumptions and evidence are explicit;
2. its maturity is classified;
3. the required proof, literature, or computation evidence exists;
4. an independent reviewer approves the specific claim id;
5. all applicable promotion gates pass.

The system must preserve rejected, incomplete, and blocked reasoning instead of
silently deleting it.

## Users And Use Cases

The primary user is a researcher or engineer who wants to use several
specialized language-model workers on a mathematical problem while retaining
an auditable record of what was proved, tested, blocked, or left open.

The first release must support:

- running a complete research cycle from one command;
- running without credentials through a deterministic mock provider;
- running real workers through an installed Codex CLI provider;
- inspecting work-in-progress and completed runs from the filesystem;
- reviewing claims independently from worker drafts;
- producing a final Markdown report containing only approved claims.

## Non-Goals

The first release will not:

- guarantee mathematical truth;
- replace a human mathematician;
- scrape the open web directly;
- edit external paper source files;
- implement a full theorem prover;
- provide a web UI;
- require a database or hosted service;
- support arbitrary model-provider SDKs.

## Design Principles

### Claims before prose

Workers may write explanatory prose, but the unit of promotion is a
machine-readable claim, not a paragraph or an entire worker response.

### Maturity is explicit

Every proof-related claim must use one of:

- `verified_by_reviewer`
- `plausible_sketch`
- `incomplete`
- `likely_false`
- `counterexample_found`

Only proof-like claims require `verified_by_reviewer` before entering the final
claim registry. Empirical and diagnostic claims may be approved when their
tests and scope are explicit, but they must remain labeled empirical or
diagnostic. Workers may never author the `verified_by_reviewer` maturity; that
status is meaningful only after an independent reviewer has approved the claim.

### Evidence is typed

Evidence must be labeled as one or more of:

- `proof`
- `computation`
- `literature`
- `counterexample`
- `diagnostic`
- `source_context`

Numerical or diagnostic evidence must not be treated as a proof unless a
reviewer explicitly approves a narrower empirical claim.

### Gates are executable

The system must reject promotion when a required artifact, review decision,
test result, or provenance record is missing. A worker cannot mark its own
workstream complete.

### Failure is data

Failed proof paths, incomplete arguments, contradictory computations, provider
failures, and blocked claims remain visible under the run directory.

### Scoped writes

Each worker receives a task manifest with an assigned output directory. The
runner validates that worker output stays inside that directory.

## Architecture

```text
CLI
 |
 v
Run Manager
 |
 +--> Planner ---------> plan.json
 |
 +--> Proof Worker ----> workers/proof/
 +--> Literature ------> workers/literature/
 +--> Computation ------> workers/computation/
 |
 +--> Reviewer --------> review/decision.json
 |
 +--> Promotion Gates -> claims/registry.json
 |
 +--> Synthesizer -----> final/report.md
```

The runtime is provider-neutral. A provider receives a task prompt and returns
structured JSON or Markdown. The first release includes:

- `mock`: deterministic, credential-free provider used by tests and demos;
- `codex`: subprocess provider that invokes `codex exec` with an assembled
  task prompt.

The provider must not be allowed to mutate the run directory directly. The
runner owns persistence and validation.

## Run Layout

Each run is stored in a unique directory:

```text
runs/<run-id>/
  manifest.json
  plan.json
  events.jsonl
  tasks/
    proof.json
    literature.json
    computation.json
    reviewer.json
    synthesis.json
  workers/
    proof/
      response.md
      claims.json
      evidence/
      failed_attempts.md
    literature/
      response.md
      claims.json
      evidence/
    computation/
      response.md
      claims.json
      evidence/
      tests.json
  review/
    packet.md
    decision.json
  claims/
    registry.json
  failed_explorations/
  final/
    report.md
```

The directory is self-contained and can be committed or attached to an issue
as an auditable research artifact.

## Data Contracts

### Run manifest

```json
{
  "run_id": "20261009-120000-ab12",
  "objective": "Prove ...",
  "provider": "mock",
  "status": "RUNNING",
  "created_at": "2026-10-09T12:00:00Z",
  "required_roles": ["proof", "reviewer", "synthesis"]
}
```

Allowed run statuses:

```text
CREATED, RUNNING, REVIEWING, BLOCKED, COMPLETE
```

### Claim

```json
{
  "id": "C-001",
  "statement": "Under assumptions A1-A3, ...",
  "kind": "theorem",
  "maturity": "plausible_sketch",
  "status": "PROPOSED",
  "assumptions": ["A1", "A2", "A3"],
  "evidence": [
    {
      "path": "workers/proof/response.md",
      "type": "proof"
    }
  ],
  "dependencies": [],
  "known_gaps": [
    "The interchange of limits is not justified."
  ],
  "source": {
    "worker_role": "proof",
    "task_id": "task-proof"
  }
}
```

Allowed claim statuses:

```text
PROPOSED, REVIEWING, REQUEST_CHANGES, BLOCKED, APPROVED
```

Claim ids are unique within a run. The registry derives a global key:

```text
<run-id>:<claim-id>
```

### Reviewer decision

```json
{
  "reviewer_id": "reviewer-001",
  "decision": "REQUEST_CHANGES",
  "approved_claims": [],
  "blocked_claims": ["C-001"],
  "required_changes": [
    "Supply the missing uniform integrability argument."
  ],
  "checks": {
    "assumptions": "PASS",
    "proof_completeness": "FAIL",
    "source_fidelity": "PASS",
    "computation": "NOT_APPLICABLE",
    "overclaiming": "FAIL"
  }
}
```

Allowed reviewer decisions:

```text
APPROVE, REQUEST_CHANGES, BLOCK
```

### Task manifest

```json
{
  "task_id": "task-proof",
  "role": "proof",
  "objective": "Explore and classify proof routes.",
  "input_files": ["plan.json"],
  "output_dir": "workers/proof",
  "required_outputs": ["response.md", "claims.json"],
  "allowed_statuses": ["PROPOSED", "BLOCKED"]
}
```

## Worker Contracts

### Planner

The planner receives the user objective and creates:

- a concise research question;
- role-specific objectives;
- likely dependencies;
- target claim types;
- whether literature or computation evidence is required;
- known risk flags such as asymptotic, formula, or source-fidelity claims.

The planner must not assert that the objective is solved.

### Proof worker

The proof worker must produce:

- proof strategy;
- assumptions;
- verified steps;
- plausible steps;
- missing steps;
- counterexamples or obstructions;
- failed attempts;
- structured claims.

It must downgrade a claim to `plausible_sketch` or `incomplete` when a proof
step is missing. It must never label a claim `verified_by_reviewer`.

### Literature worker

The literature worker must produce:

- search queries;
- sources actually consulted;
- exact statements when available;
- hypothesis comparison;
- unavailable or unverified source notes;
- literature claims with citations or explicit `not_verified` status.

A title, abstract, or search result cannot by itself prove theorem applicability.

### Computation worker

The computation worker must produce:

- source-setting description;
- implementation/result description;
- reproducibility instructions;
- tests or checks;
- error decomposition;
- claims labeled as diagnostic, empirical, or mathematical.

Formula, asymptotic, deterministic-equivalent, or decomposition claims require
computation evidence unless the user explicitly disables that gate.

### Reviewer

The reviewer receives a sanitized packet containing the plan, worker outputs,
claims, and evidence references. It must not receive hidden worker reasoning.

It must:

- inspect each claim independently;
- verify assumptions and evidence;
- detect overclaiming;
- distinguish proof from diagnostic evidence;
- return exactly one decision;
- approve claims only by explicit claim id.

### Synthesizer

The synthesizer may read only approved claims, reviewer decisions, evidence
artifacts, and uncertainty records. It must preserve limitations and label
open or blocked conclusions. It cannot promote or rewrite claim status.

## Promotion Gates

`promote_run()` must fail unless all applicable checks pass:

1. The manifest is valid.
2. The plan exists and names the required roles.
3. Required worker outputs exist and validate against their schemas.
4. Every substantive conclusion has a claim id.
5. Every claim has assumptions, maturity, evidence, and source metadata.
6. Every proof-like claim intended for approval has maturity
   `verified_by_reviewer`; empirical and diagnostic claims have passing evidence
   for their narrower scope.
7. Every required computation gate has passing test evidence.
8. Every exact literature claim has source and applicability evidence.
9. A reviewer decision exists for the current review round.
10. The reviewer decision is `APPROVE`.
11. Every claim in the report is listed in `approved_claims`.
12. `blocked_claims` is empty.
13. No unresolved `REQUEST_CHANGES` remains.
14. No worker output violates its allowed output directory.
15. The final report is generated only after the registry is written.

The code must expose gate failures as structured errors, for example:

```text
GateError:
  code: CLAIM_NOT_REVIEWED
  claim_id: C-001
  message: Claim has no approved reviewer decision.
```

## Review Loop

The first release supports one repair loop:

```text
worker output
    ↓
review
    ↓
REQUEST_CHANGES
    ↓
worker revision
    ↓
review round 2
```

If the configured maximum review rounds are exhausted, the run becomes
`BLOCKED` and records the unresolved changes. The system must not silently
convert the result to `COMPLETE`.

## CLI

```text
mathforge init <directory>
mathforge run "<objective>" [--provider mock|codex] [--max-review-rounds N]
mathforge status <run-id>
mathforge review <run-id>
mathforge promote <run-id>
mathforge synthesize <run-id>
```

`mathforge run` executes the complete cycle by default. The lower-level
commands exist for inspection and recovery.

## Error Handling

The runner must record:

- provider command failures;
- invalid JSON;
- missing required outputs;
- malformed claims;
- reviewer disagreement;
- failed tests;
- gate failures;
- worker timeout;
- unknown task status.

Each event is appended to `events.jsonl` with timestamp, task id, severity, and
structured details.

## Testing Requirements

The first release must include tests for:

1. claim schema validation;
2. incomplete proofs being rejected from promotion;
3. `plausible_sketch` claims not entering the approved registry;
4. a reviewer approving only explicit claim ids;
5. blocked claims preventing promotion;
6. computation-required claims without tests being rejected;
7. malformed worker output being rejected;
8. output path escape being rejected;
9. failed review rounds producing `BLOCKED`;
10. approved claims appearing in the final report with provenance;
11. mock provider running end to end;
12. a deterministic demo containing one approved and one blocked claim.

## Acceptance Criteria

The project is ready for its first GitHub commit when:

- `python -m mathforge --help` works;
- a fresh directory can run the mock demo without external credentials;
- the demo visibly blocks an immature proof;
- the demo produces an approved claim registry;
- the final report includes only approved mathematical claims;
- all tests pass;
- README explains the state machine and shows the gate failure;
- no source file depends on the original Comath repository at runtime.
