import re
import uuid

from evidencesplit.synthesis.schemas import CitedStatement, ComparisonReport, GeminiComparisonOutput


def _render_statements(
    statements: list[CitedStatement],
    allowed_ids: set[uuid.UUID],
) -> tuple[str | None, set[uuid.UUID]]:
    rendered: list[str] = []
    used: set[uuid.UUID] = set()
    for statement in statements:
        citations = set(statement.citation_ids)
        if not citations or not citations.issubset(allowed_ids):
            raise ValueError("Synthesis returned an unknown or missing citation ID.")
        citation_text = " ".join(f"[{citation_id}]" for citation_id in sorted(citations, key=str))
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", statement.text) if part.strip()]
        rendered.extend(f"{sentence} {citation_text}" for sentence in sentences)
        used.update(citations)
    return (" ".join(rendered) or None), used


def format_comparison_report(
    output: GeminiComparisonOutput,
    allowed_ids: set[uuid.UUID],
) -> ComparisonReport:
    summary, used = _render_statements(output.summary, allowed_ids)
    supporting, supporting_ids = _render_statements(output.supporting_summary, allowed_ids)
    contradicting, contradicting_ids = _render_statements(output.contradicting_summary, allowed_ids)
    qualifying, qualifying_ids = _render_statements(output.qualifying_summary, allowed_ids)
    limitations_text, limitation_ids = _render_statements(output.limitations, allowed_ids)
    used.update(supporting_ids | contradicting_ids | qualifying_ids | limitation_ids)

    if not summary:
        raise ValueError("Synthesis returned no cited summary.")
    return ComparisonReport(
        overall_assessment=output.overall_assessment,
        summary=summary,
        supporting_summary=supporting,
        contradicting_summary=contradicting,
        qualifying_summary=qualifying,
        limitations=[limitations_text] if limitations_text else [],
        citation_ids=[str(citation_id) for citation_id in sorted(used, key=str)],
    )
