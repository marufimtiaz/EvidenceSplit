import re
from pydantic import BaseModel
from evidencesplit.documents.pdf_parser import ParsedPage


class ChunkItem(BaseModel):
    content: str
    page_start: int
    page_end: int
    section: str | None


class Chunker:
    @staticmethod
    def chunk_document(pages: list[ParsedPage]) -> list[ChunkItem]:
        chunks: list[ChunkItem] = []
        if not pages:
            return chunks

        target_chunk_words = 600  # ~800 tokens
        overlap_words = 100  # ~130 tokens

        # Detect section headers
        section_patterns = [
            r"^(?:I|II|III|IV|V|VI|VII|VIII|IX|X|\d+)?\.?\s*(ABSTRACT|INTRODUCTION|METHODS|METHODOLOGY|MATERIALS AND METHODS|RESULTS|DISCUSSION|CONCLUSION|CONCLUSIONS|REFERENCES)\s*$"
        ]

        # Extract words with page and section tags
        words_with_meta = []
        active_section = None

        for page in pages:
            # Split page text into lines
            lines = page.text.split("\n")
            for line in lines:
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                # Check for section header change
                clean_line = re.sub(r"\s+", " ", stripped_line).upper()
                for pattern in section_patterns:
                    match = re.match(pattern, clean_line)
                    if match:
                        active_section = match.group(1).title()
                        break

                # Split line into words
                line_words = stripped_line.split()
                for w in line_words:
                    words_with_meta.append((w, page.page_number, active_section))

        if not words_with_meta:
            return chunks

        # Sliding window chunking
        i = 0
        total_words = len(words_with_meta)

        while i < total_words:
            # Get slice for chunk
            chunk_slice = words_with_meta[i : i + target_chunk_words]
            if not chunk_slice:
                break

            # Join content
            content = " ".join(w[0] for w in chunk_slice)
            page_start = chunk_slice[0][1]
            page_end = chunk_slice[-1][1]
            # Use section of the middle/first word
            section = chunk_slice[0][2]

            chunks.append(
                ChunkItem(
                    content=content,
                    page_start=page_start,
                    page_end=page_end,
                    section=section,
                )
            )

            # Shift index by target_chunk_words - overlap_words
            shift = target_chunk_words - overlap_words
            if shift <= 0:
                shift = 1
            i += shift

            # If remaining words are less than overlap, we can stop to avoid duplicates
            if i >= total_words - overlap_words:
                # Add remainder if we are not at the very end
                if i < total_words:
                    remainder_slice = words_with_meta[i:]
                    content = " ".join(w[0] for w in remainder_slice)
                    chunks.append(
                        ChunkItem(
                            content=content,
                            page_start=remainder_slice[0][1],
                            page_end=remainder_slice[-1][1],
                            section=remainder_slice[0][2],
                        )
                    )
                break

        return chunks
