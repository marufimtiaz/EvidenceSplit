import asyncio
import logging
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from evidencesplit.config import settings
from evidencesplit.discovery.openalex import OpenAlexClient
from evidencesplit.discovery.schemas import CandidatePaper
from evidencesplit.discovery.unpaywall import UnpaywallClient
from evidencesplit.documents.chunker import Chunker
from evidencesplit.documents.downloader import SafePDFDownloader
from evidencesplit.documents.pdf_parser import PDFParser
from evidencesplit.documents.repository import ChunkRepository, DocumentRepository
from evidencesplit.shared.types import SourceType

logger = logging.getLogger(__name__)


class DiscoveryService:
    def __init__(self) -> None:
        self.openalex = OpenAlexClient()
        self.unpaywall = UnpaywallClient()
        self.downloader = SafePDFDownloader()

    async def discover_and_store(
        self,
        db: AsyncSession,
        analysis_id: uuid.UUID,
        claim: str,
    ) -> list[str]:
        if not settings.OPENALEX_API_KEY:
            logger.warning("discovery_skipped analysis_id=%s reason=openalex_key_missing", analysis_id)
            return ["Live discovery skipped because OPENALEX_API_KEY is not configured."]
        logger.info("discovery_start analysis_id=%s claim_chars=%s", analysis_id, len(claim))
        try:
            candidates = await self.openalex.search(claim)
        except Exception:
            logger.exception("OpenAlex search failed for analysis %s", analysis_id)
            return ["Live scholarly search was unavailable; uploaded sources were still analyzed."]

        warnings: list[str] = []
        full_text_count = 0
        abstract_count = 0
        attempted_count = 0
        logger.info("discovery_candidates analysis_id=%s count=%s", analysis_id, len(candidates))
        for candidate in candidates:
            if full_text_count + abstract_count >= settings.TARGET_LIVE_PAPERS:
                break
            attempted_count += 1
            stored_full_text = False
            full_text_error: Exception | None = None
            if candidate.doi and full_text_count < settings.MAX_LIVE_FULL_TEXT_PAPERS:
                try:
                    pdf_urls = await self.unpaywall.resolve_pdf_urls(candidate.doi)
                except Exception as exc:
                    logger.warning("Unpaywall lookup failed for %s: %s", candidate.doi, exc)
                    pdf_urls = []
                    full_text_error = exc

                for pdf_url in pdf_urls:
                    temp_path: str | None = None
                    try:
                        temp_path = await self.downloader.download(pdf_url)
                        await self._store_full_text(db, analysis_id, candidate, temp_path, pdf_url)
                        full_text_count += 1
                        stored_full_text = True
                        break
                    except Exception as exc:
                        full_text_error = exc
                        await db.rollback()
                        logger.warning("Live PDF failed for %s from %s: %s", candidate.title, pdf_url, exc)
                    finally:
                        if temp_path and os.path.exists(temp_path):
                            os.remove(temp_path)

            if stored_full_text:
                continue
            if candidate.abstract:
                try:
                    await self._store_abstract(db, analysis_id, candidate)
                    abstract_count += 1
                    if full_text_error:
                        warnings.append(f"{candidate.title}: full text failed; the abstract was used.")
                except Exception:
                    await db.rollback()
                    logger.exception("Abstract persistence failed for %s", candidate.title)
                    warnings.append(f"{candidate.title}: the live source could not be processed.")
            else:
                logger.info(
                    "discovery_candidate_skipped analysis_id=%s reason=no_full_text_or_abstract title=%s",
                    analysis_id,
                    candidate.title,
                )
        usable_count = full_text_count + abstract_count
        if usable_count < settings.TARGET_LIVE_PAPERS:
            warnings.append(
                f"Live discovery found {usable_count} of {settings.TARGET_LIVE_PAPERS} usable papers "
                f"after checking {attempted_count} candidates."
            )
        logger.info(
            "discovery_complete analysis_id=%s candidates_checked=%s full_text=%s abstracts=%s warnings=%s",
            analysis_id,
            attempted_count,
            full_text_count,
            abstract_count,
            len(warnings),
        )
        return warnings

    @staticmethod
    async def _store_full_text(
        db: AsyncSession,
        analysis_id: uuid.UUID,
        candidate: CandidatePaper,
        file_path: str,
        pdf_url: str,
    ) -> None:
        pages, _ = await asyncio.to_thread(
            PDFParser.parse_pdf,
            file_path,
            candidate.title,
            "application/pdf",
            settings.MAX_REMOTE_PDF_SIZE_MB,
        )
        document = await DocumentRepository.create_document(
            db,
            analysis_id,
            SourceType.LIVE_FULL_TEXT,
            candidate.title,
            candidate.authors,
            candidate.year,
            candidate.doi,
            pdf_url,
            len(pages),
            "COMPLETED",
        )
        chunks = await asyncio.to_thread(Chunker.chunk_document, pages)
        for index, chunk in enumerate(chunks):
            await ChunkRepository.create_chunk(
                db,
                document.id,
                chunk.content,
                chunk.page_start,
                chunk.page_end,
                chunk.section,
                index,
            )
        await db.commit()

    @staticmethod
    async def _store_abstract(
        db: AsyncSession,
        analysis_id: uuid.UUID,
        candidate: CandidatePaper,
    ) -> None:
        if not candidate.abstract:
            return
        document = await DocumentRepository.create_document(
            db,
            analysis_id,
            SourceType.LIVE_ABSTRACT,
            candidate.title,
            candidate.authors,
            candidate.year,
            candidate.doi,
            candidate.source_url,
            None,
            "COMPLETED",
        )
        await ChunkRepository.create_chunk(
            db,
            document.id,
            candidate.abstract,
            None,
            None,
            "Abstract",
            0,
        )
        await db.commit()
