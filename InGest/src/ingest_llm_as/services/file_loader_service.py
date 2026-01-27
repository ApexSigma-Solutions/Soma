import io
import logging
import os
import tempfile


# Parsers
from pypdf import PdfReader
from docx import Document
from bs4 import BeautifulSoup
from ebooklib import epub
import ebooklib
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class FileLoaderService:
    """
    The Stomach Acid.
    Extracts raw text from binary file streams.
    """

    @staticmethod
    async def process_file(file: UploadFile) -> str:
        filename = file.filename.lower()
        if not filename:
            raise ValueError("Filename is empty")

        content = await file.read()
        file_stream = io.BytesIO(content)

        try:
            # 1. PDF
            if filename.endswith(".pdf"):
                return FileLoaderService._extract_pdf(file_stream)

            # 2. Word Docs
            elif filename.endswith(".docx"):
                return FileLoaderService._extract_docx(file_stream)

            # 3. eBooks (EPUB)
            elif filename.endswith(".epub"):
                return FileLoaderService._extract_epub(content)

            # 4. Web / HTML
            elif filename.endswith(".html") or filename.endswith(".htm"):
                return FileLoaderService._extract_html(content)

            # 5. Plain Text / Markdown
            elif filename.endswith(".txt") or filename.endswith(".md"):
                return content.decode("utf-8")

            else:
                logger.warning(f"Unsupported file type: {filename}")
                raise ValueError(f"Unsupported file type: {filename}")

        except Exception as e:
            logger.error(f"Failed to digest {filename}: {e}")
            raise ValueError(f"Digestion failed: {str(e)}")
        finally:
            await file.seek(0)

    @staticmethod
    def _extract_pdf(stream: io.BytesIO) -> str:
        reader = PdfReader(stream)
        text = []
        for page in reader.pages:
            try:
                extracted = page.extract_text()
                if extracted:
                    text.append(extracted)
            except Exception as e:
                logger.warning(
                    f"Failed to extract text from page {reader.pages.index(page)}: {e}"
                )
        return "\n".join(text)

    @staticmethod
    def _extract_docx(stream: io.BytesIO) -> str:
        doc = Document(stream)
        return "\n".join([para.text for para in doc.paragraphs])

    @staticmethod
    def _extract_html(content: bytes) -> str:
        soup = BeautifulSoup(content, "html.parser")
        return soup.get_text(separator="\n")

    @staticmethod
    def _extract_epub(content: bytes) -> str:
        # EbookLib requires a physical file path
        with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        text_content = []
        try:
            book = epub.read_epub(tmp_path)
            for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                raw_html = item.get_body_content()
                soup = BeautifulSoup(raw_html, "html.parser")
                text_content.append(soup.get_text(separator="\n"))
        except Exception as e:
            logger.error(f"Failed to read EPUB: {e}")
            raise
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        return "\n\n".join(text_content)
