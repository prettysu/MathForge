# MathForge

MathForge is a file-backed, claim-gated multi-agent workspace for auditable
mathematical reasoning.

It is not designed to make a language model sound more confident. Its central
job is to stop immature proof sketches, unsupported claims, and over-claimed
computational results from entering a final report.

## Why It Exists

Open-ended mathematical agents often mix:

- a plausible proof idea with a complete proof;
- a finite numerical experiment with an asymptotic theorem;
- a citation with a verified theorem hypothesis;
- an unresolved gap with a polished conclusion.

MathForge makes these distinctions explicit and executable.

## Core Workflow

```text
objective
   |
   v
planner
   |
   +--> proof worker -----------+
   +--> computation worker -----+--> independent reviewer
                                  |
                                  v
                           claim-level gates
                                  |
                    +-------------+-------------+
                    |                           |
                 COMPLETE                    BLOCKED
                    |                           |
                    v                           v
             approved registry          preserved artifacts
                    |
                    v
              final report
```

Every substantive conclusion is a claim with:

- a stable id such as `C-001`;
- explicit assumptions;
- typed evidence;
- a maturity label;
- known gaps;
- worker provenance;
- an independent review decision.

## Proof Maturity

Proof-like claims must be classified as one of:

```text
verified_by_reviewer
plausible_sketch
incomplete
likely_false
counterexample_found
```

Only a proof-like claim with `verified_by_reviewer` maturity and an explicit
reviewer approval can enter the approved registry. A worker cannot author that
maturity as a shortcut.

Empirical and diagnostic claims can be approved when their narrower scope and
test evidence are explicit. They remain labeled empirical or diagnostic and
cannot silently become theorem claims.

## Review Decisions

The reviewer returns exactly one:

```text
APPROVE
REQUEST_CHANGES
BLOCK
```

Approval is claim-specific. Approving `C-002` does not approve `C-001`.
`REQUEST_CHANGES` preserves the current evidence and allows a later repair
round. `BLOCK` records the reason and prevents promotion.

## Promotion Gates

An entire run can become `COMPLETE` only when:

1. worker outputs and claims validate;
2. every claim has assumptions, evidence, and provenance;
3. all claims are explicitly approved;
4. proof-like claims have reviewer maturity;
5. theorem/formula/asymptotic claims have passing computation evidence;
6. no claim is blocked or awaiting changes;
7. the review decision is `APPROVE`;
8. all evidence paths remain inside the run directory.

The transition to `COMPLETE` is available only through `promote()`. A worker
cannot mark its own run complete.

## Quick Start

The project has no required runtime dependency beyond Python 3.12.

```powershell
$env:PYTHONPATH = "src"
python -m mathforge --help
python -m mathforge run "Study convergence." --root . --provider mock
```

The deterministic mock provider intentionally creates:

- `C-001`: an incomplete proof sketch that is blocked;
- `C-002`: a narrow empirical computation claim that is approved.

The run remains `BLOCKED` because the proof claim is immature, but the final
report contains only the approved empirical claim. All blocked evidence remains
under `runs/<run-id>/`.

Inspect a run:

```powershell
python -m mathforge status <run-id> --root .
python -m mathforge synthesize <run-id> --root .
python -m mathforge promote <run-id> --root .
```

The last command intentionally fails for the demo run and prints the promotion
gate error.

## Run Artifacts

```text
runs/<run-id>/
  manifest.json
  plan.json
  events.jsonl
  tasks/
  workers/
    proof/
    computation/
  review/
    decision.json
  claims/
    registry.json
  failed_explorations/
  final/
    report.md
```

The artifacts are designed to be committed to Git, attached to a research
issue, or inspected after a failed run.

## Providers

`mock` is deterministic and requires no credentials:

```powershell
python -m mathforge run "Study convergence." --provider mock
```

`codex` is optional and invokes an installed `codex` executable:

```powershell
python -m mathforge run "Study convergence." --provider codex
```

Provider failures are recorded as structured run failures. The project does not
pretend a missing provider produced mathematical evidence.

## Development

Run the full test suite:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

The test suite covers claim schemas, state transitions, path containment,
reviewer-specific approval, computation gates, blocked proof promotion, mock
end-to-end runs, and CLI behavior.

## Limitations

MathForge does not prove that an approved claim is mathematically true. It
provides an explicit evidence and review protocol that makes unsupported
reasoning visible and prevents it from being silently promoted.
