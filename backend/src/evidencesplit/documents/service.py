import asyncio
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from evidencesplit.shared.types import SourceType
from evidencesplit.documents.pdf_parser import PDFParser
from evidencesplit.documents.chunker import Chunker
from evidencesplit.documents.repository import DocumentRepository, ChunkRepository

logger = logging.getLogger(__name__)


class DocumentService:
    @staticmethod
    async def process_uploads(
        db: AsyncSession,
        analysis_id: uuid.UUID,
        uploaded_files: list[tuple[str, str, str]],
    ) -> list[str]:
        warnings = []

        for file_path, filename, content_type in uploaded_files:
            try:
                # 1. Parse PDF and extract page-aware text
                pages, warning = await asyncio.to_thread(PDFParser.parse_pdf, file_path, filename, content_type)
                if warning:
                    warnings.append(f"{filename}: {warning}")

                # 2. Create Document database record
                doc = await DocumentRepository.create_document(
                    db=db,
                    analysis_id=analysis_id,
                    source_type=SourceType.UPLOADED_PDF,
                    title=filename,
                    authors=[],
                    year=None,
                    doi=None,
                    source_url=None,
                    page_count=len(pages),
                    processing_status="COMPLETED",
                )

                # 3. Chunk and persist chunks in database
                chunks = await asyncio.to_thread(Chunker.chunk_document, pages)
                for index, chunk in enumerate(chunks):
                    await ChunkRepository.create_chunk(
                        db=db,
                        document_id=doc.id,
                        content=chunk.content,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        section=chunk.section,
                        chunk_index=index,
                    )
                await db.commit()

            except Exception as e:
                logger.error(f"Failed to process upload {filename}: {e}")
                warnings.append(f"{filename}: PDF could not be processed.")
                await db.rollback()

                # Persist FAILED document placeholder for diagnostic tracing
                await DocumentRepository.create_document(
                    db=db,
                    analysis_id=analysis_id,
                    source_type=SourceType.UPLOADED_PDF,
                    title=filename,
                    authors=[],
                    year=None,
                    doi=None,
                    source_url=None,
                    page_count=None,
                    processing_status="FAILED",
                )
                await db.commit()

        return warnings
