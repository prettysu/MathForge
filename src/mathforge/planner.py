from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ResearchPlan:
    research_question: str
    roles: list[str]
    requires_computation: bool
    risk_flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def plan_objective(objective: str) -> ResearchPlan:
    lowered = objective.lower()
    computation_terms = (
        "formula",
        "asymptotic",
        "convergence",
        "deterministic",
        "resolvent",
        "bound",
        "scaling",
    )
    requires_computation = any(term in lowered for term in computation_terms)
    risk_flags = []
    if requires_computation:
        risk_flags.append("formula_or_asymptotic_claim_requires_computation_gate")
    if "prove" in lowered or "proof" in lowered:
        risk_flags.append("proof_completeness_and_overclaiming")
    return ResearchPlan(
        research_question=objective.strip(),
        roles=["proof", "computation", "reviewer", "synthesis"],
        requires_computation=requires_computation,
        risk_flags=risk_flags,
    )
