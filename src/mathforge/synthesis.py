from __future__ import annotations

from pathlib import Path

from .claims import build_claim_registry, load_claims
from .storage import RunContext


def synthesize_final_report(run: RunContext) -> Path:
    registry = build_claim_registry(run)
    all_claims = load_claims(run)
    approved_ids = {item["id"] for item in registry["claims"]}
    blocked_count = sum(claim.id not in approved_ids for claim in all_claims)
    lines = [
        "# MathForge Research Report",
        "",
        f"- Run: `{run.manifest.run_id}`",
        f"- Status: `{run.manifest.status.value}`",
        f"- Approved claims: `{len(registry['claims'])}`",
        f"- Omitted or blocked claims: `{blocked_count}`",
        "",
        "## Approved Claims",
        "",
    ]
    if not registry["claims"]:
        lines.append("No claims passed the promotion gates.")
    for item in registry["claims"]:
        lines.extend(
            [
                f"### {item['global_id']}",
                "",
                item["statement"],
                "",
                f"**Kind:** `{item['kind']}`  ",
                f"**Maturity:** `{item['maturity']}`",
                "",
                "Evidence:",
            ]
        )
        lines.extend(f"- `{evidence['path']}` ({evidence['type']})" for evidence in item["evidence"])
        if item["known_gaps"]:
            lines.append("")
            lines.append("Known limitations:")
            lines.extend(f"- {gap}" for gap in item["known_gaps"])
        lines.append("")
    lines.extend(
        [
            "## Research Hygiene",
            "",
            "Claims omitted from this report remain in the run artifacts and were not promoted.",
        ]
    )
    path = run.path / "final" / "report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
