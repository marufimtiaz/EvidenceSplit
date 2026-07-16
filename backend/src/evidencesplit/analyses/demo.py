import asyncio
import logging
import uuid
from dataclasses import dataclass

from evidencesplit.analyses.pipeline import cleanup_temp_files
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.database import async_session
from evidencesplit.documents.repository import ChunkRepository, DocumentRepository
from evidencesplit.evidence.models import EvidenceFinding, PaperAssessment
from evidencesplit.shared.types import AnalysisStatus, SourceType, Stance
from evidencesplit.synthesis.repository import SynthesisRepository
from evidencesplit.synthesis.schemas import ComparisonReport, OverallAssessment

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemoPaper:
    title: str
    authors: list[str]
    year: int
    stance: Stance
    summary: str
    quote: str
    explanation: str
    conditions: str | None


@dataclass(frozen=True)
class DemoFixture:
    overall_assessment: OverallAssessment
    summary: str
    papers: list[DemoPaper]


DEMO_FIXTURES = {
    "Regular aerobic exercise reduces resting blood pressure in adults with hypertension.": DemoFixture(
        overall_assessment=OverallAssessment.SUPPORTED,
        summary="The prepared evidence mostly supports a blood-pressure benefit, with the size of the effect varying by program and population.",
        papers=[
            DemoPaper(
                "Demo fixture — supervised aerobic exercise trial",
                ["EvidenceSplit Demo Team"],
                2024,
                Stance.SUPPORTING,
                "The supervised program reported lower resting blood pressure.",
                "Participants assigned to aerobic exercise had lower resting systolic blood pressure after twelve weeks.",
                "This directly supports the submitted claim.",
                "Adults with diagnosed hypertension; supervised exercise three times weekly.",
            ),
            DemoPaper(
                "Demo fixture — home walking program",
                ["EvidenceSplit Demo Team"],
                2023,
                Stance.QUALIFYING,
                "Benefits depended on adherence to the walking program.",
                "Blood pressure improved among participants completing at least four walking sessions each week.",
                "The finding supports the claim only under adequate adherence.",
                "Effect was limited to participants meeting the adherence threshold.",
            ),
            DemoPaper(
                "Demo fixture — short-duration exercise study",
                ["EvidenceSplit Demo Team"],
                2022,
                Stance.CONTRADICTING,
                "A short intervention did not detect a meaningful reduction.",
                "No significant change in resting blood pressure was observed after the four-week program.",
                "This result contradicts an unconditional version of the claim.",
                "Four-week intervention with a small sample.",
            ),
        ],
    ),
    "Vitamin D supplementation prevents acute respiratory infections in adults.": DemoFixture(
        overall_assessment=OverallAssessment.CONDITIONAL,
        summary="The prepared evidence is conditional: benefit appears concentrated in deficient adults and is not consistent across broad populations.",
        papers=[
            DemoPaper(
                "Demo fixture — vitamin D deficiency trial",
                ["EvidenceSplit Demo Team"],
                2024,
                Stance.SUPPORTING,
                "Deficient adults receiving regular supplementation experienced fewer infections.",
                "Participants with baseline vitamin D deficiency reported fewer acute respiratory infections during supplementation.",
                "This supports the claim in a deficient population.",
                "Adults with confirmed baseline vitamin D deficiency.",
            ),
            DemoPaper(
                "Demo fixture — community supplementation study",
                ["EvidenceSplit Demo Team"],
                2023,
                Stance.CONTRADICTING,
                "The broad community sample showed no preventive effect.",
                "The infection rate did not differ between vitamin D and placebo groups.",
                "This contradicts a general preventive claim.",
                "Adults were not selected for vitamin D deficiency.",
            ),
            DemoPaper(
                "Demo fixture — dosing schedule comparison",
                ["EvidenceSplit Demo Team"],
                2022,
                Stance.QUALIFYING,
                "Outcomes varied with dose timing.",
                "Daily dosing was associated with benefit, whereas intermittent high-dose treatment was not.",
                "The claim depends on the supplementation schedule.",
                "Daily dosing compared with intermittent bolus dosing.",
            ),
        ],
    ),
    "Magnesiothermic reduction can produce high-purity porous silicon from silica.": DemoFixture(
        overall_assessment=OverallAssessment.CONDITIONAL,
        summary="The prepared evidence supports the production route while emphasizing temperature control and post-reaction leaching.",
        papers=[
            DemoPaper(
                "Demo fixture — silica-to-porous-silicon experiment",
                ["EvidenceSplit Demo Team"],
                2024,
                Stance.SUPPORTING,
                "Reduction followed by leaching produced high-purity porous silicon.",
                "After acid leaching, the recovered porous silicon reached a reported purity of 99.6 percent.",
                "The result directly supports the production claim.",
                "Magnesiothermic reduction followed by hydrochloric and hydrofluoric acid leaching.",
            ),
            DemoPaper(
                "Demo fixture — temperature-control study",
                ["EvidenceSplit Demo Team"],
                2023,
                Stance.QUALIFYING,
                "Purity depended strongly on reaction temperature.",
                "Excessive reaction temperature increased magnesium silicide byproduct formation.",
                "The method works only when reaction conditions limit unwanted byproducts.",
                "Controlled heating rate and reaction temperature.",
            ),
            DemoPaper(
                "Demo fixture — unleached reduction product",
                ["EvidenceSplit Demo Team"],
                2022,
                Stance.CONTRADICTING,
                "Reduction alone left substantial oxide and magnesium-containing residues.",
                "The product collected before leaching contained substantial residual magnesium oxide and silica.",
                "This contradicts the claim if purification is omitted.",
                "Product measured before acid leaching.",
            ),
        ],
    ),
}

DEMO_CLAIMS = list(DEMO_FIXTURES)


def is_demo_claim(claim: str) -> bool:
    return claim.strip() in DEMO_FIXTURES


def format_citations(ids: list[str]) -> str:
    return " ".join(f"[{item}]" for item in ids)


async def run_demo_pipeline(
    analysis_id: uuid.UUID,
    uploaded_files: list[tuple[str, str, str]],
) -> None:
    try:
        for status, progress in [
            (AnalysisStatus.PROCESSING_UPLOADS, 15),
            (AnalysisStatus.SEARCHING, 30),
            (AnalysisStatus.INDEXING, 55),
            (AnalysisStatus.ANALYZING_EVIDENCE, 82),
        ]:
            async with async_session() as db:
                await AnalysisRepository.update(db, analysis_id, status=status, progress=progress)
            await asyncio.sleep(0.2)

        async with async_session() as db:
            analysis = await AnalysisRepository.get(db, analysis_id)
            if analysis is None or not is_demo_claim(analysis.claim):
                raise RuntimeError("Unsupported prepared demo claim.")
            fixture = DEMO_FIXTURES[analysis.claim.strip()]
            finding_ids: dict[Stance, list[str]] = {
                Stance.SUPPORTING: [],
                Stance.CONTRADICTING: [],
                Stance.QUALIFYING: [],
            }

            for paper in fixture.papers:
                document = await DocumentRepository.create_document(
                    db,
                    analysis_id,
                    SourceType.UPLOADED_PDF,
                    paper.title,
                    paper.authors,
                    paper.year,
                    None,
                    None,
                    1,
                    "COMPLETED",
                )
                chunk = await ChunkRepository.create_chunk(
                    db,
                    document.id,
                    paper.quote,
                    1,
                    1,
                    "Demo fixture",
                    0,
                )
                finding = EvidenceFinding(
                    analysis_id=analysis_id,
                    document_id=document.id,
                    chunk_id=chunk.id,
                    stance=paper.stance,
                    evidence_quote=paper.quote,
                    explanation=paper.explanation,
                    conditions=paper.conditions,
                    confidence=0.9,
                )
                db.add(finding)
                await db.flush()
                finding_id = str(finding.id)
                finding_ids[paper.stance].append(finding_id)
                db.add(
                    PaperAssessment(
                        analysis_id=analysis_id,
                        document_id=document.id,
                        stance=paper.stance,
                        summary=paper.summary,
                        finding_ids=[finding_id],
                    )
                )
            await db.commit()

            all_ids = [item for ids in finding_ids.values() for item in ids]
            report = ComparisonReport(
                overall_assessment=fixture.overall_assessment,
                summary=f"{fixture.summary} {format_citations(all_ids)}",
                supporting_summary=f"Prepared supporting evidence. {format_citations(finding_ids[Stance.SUPPORTING])}",
                contradicting_summary=f"Prepared contradicting evidence. {format_citations(finding_ids[Stance.CONTRADICTING])}",
                qualifying_summary=f"Prepared qualifying evidence. {format_citations(finding_ids[Stance.QUALIFYING])}",
                limitations=[
                    "Prepared demonstration data; this is not a live literature review.",
                    "Gemini and external scholarly APIs were bypassed in demo mode.",
                ],
                citation_ids=all_ids,
            )
            await SynthesisRepository.save_report(db, analysis_id, report)

        async with async_session() as db:
            await AnalysisRepository.update(
                db,
                analysis_id,
                status=AnalysisStatus.SYNTHESIZING,
                progress=96,
            )
        await asyncio.sleep(0.2)
        async with async_session() as db:
            await AnalysisRepository.update(
                db,
                analysis_id,
                status=AnalysisStatus.COMPLETED,
                progress=100,
                warning_message="Demo mode: prepared fixture evidence was used.",
                completed=True,
            )
    except Exception:
        logger.exception("Demo pipeline failed for analysis %s", analysis_id)
        async with async_session() as db:
            await AnalysisRepository.update(
                db,
                analysis_id,
                status=AnalysisStatus.FAILED,
                progress=100,
                error_message="Prepared demo analysis failed.",
                completed=True,
            )
    finally:
        cleanup_temp_files(uploaded_files)
