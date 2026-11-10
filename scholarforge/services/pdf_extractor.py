import hashlib
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF

class PDFExtractor:
    """
    Layout-aware scholarly PDF text extraction using PyMuPDF (fitz).
    - Sorts reading order across dense two-column layouts.
    - Strips running headers and footers to prevent sentence fragmentation.
    - Extracts section boundaries (Abstract, Methods, Results, Discussion).
    """

    DOI_REGEX = re.compile(r'\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b')

    def __init__(self):
        pass

    def compute_sha256(self, filepath: Path) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def extract_layout_aware_text(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extracts text respecting column layout, stripping recurring headers and footers.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        doc = fitz.open(str(pdf_path))
        num_pages = len(doc)
        full_text_pages = []
        found_dois = set()

        for page_idx in range(num_pages):
            page = doc[page_idx]
            page_height = page.rect.height
            
            # Extract text blocks with layout sorting: (x0, y0, x1, y1, text, block_no, block_type)
            blocks = page.get_text("blocks", sort=True)
            page_lines = []

            for b in blocks:
                # b[4] is text, b[1] is y0, b[3] is y1
                block_text = b[4].strip()
                y0, y1 = b[1], b[3]

                # Filter out running header (top 5% of page) and running footer (bottom 5% of page)
                # except on page 0 where title and DOI usually sit
                if page_idx > 0:
                    if y0 < (page_height * 0.05) and len(block_text.splitlines()) <= 2:
                        continue  # Header
                    if y1 > (page_height * 0.95) and len(block_text.splitlines()) <= 2:
                        continue  # Footer

                if block_text:
                    page_lines.append(block_text)
                    # Check for DOI
                    matches = self.DOI_REGEX.findall(block_text)
                    for m in matches:
                        found_dois.add(m.rstrip("."))

            page_content = f"--- [Page {page_idx + 1}] ---\n" + "\n\n".join(page_lines)
            full_text_pages.append(page_content)

        doc.close()
        combined_text = "\n\n".join(full_text_pages)

        # Detect primary sections
        sections = self._segment_sections(combined_text)

        return {
            "page_count": num_pages,
            "char_count": len(combined_text),
            "full_text": combined_text,
            "sections": sections,
            "detected_dois": list(found_dois)
        }

    def _segment_sections(self, text: str) -> Dict[str, str]:
        """Identifies standard academic sections for primary vs secondary isolation."""
        section_headers = {
            "abstract": re.compile(r'(?i)\babstract\b'),
            "introduction": re.compile(r'(?i)\b(?:1\.?\s+)?introduction\b|\bbackground\b'),
            "methods": re.compile(r'(?i)\b(?:2\.?\s+)?(?:materials\s+and\s+methods|methodology|methods)\b'),
            "results": re.compile(r'(?i)\b(?:3\.?\s+)?results\b|\bfindings\b'),
            "discussion": re.compile(r'(?i)\b(?:4\.?\s+)?discussion\b'),
            "conclusion": re.compile(r'(?i)\b(?:5\.?\s+)?conclusion(?:s)?\b')
        }

        found_positions = {}
        for sec, pattern in section_headers.items():
            match = pattern.search(text)
            if match:
                found_positions[sec] = match.start()

        # Sort by position in text
        sorted_secs = sorted(found_positions.items(), key=lambda x: x[1])
        segmented = {}

        for i, (sec_name, pos) in enumerate(sorted_secs):
            end_pos = sorted_secs[i + 1][1] if i + 1 < len(sorted_secs) else len(text)
            segmented[sec_name] = text[pos:end_pos].strip()

        return segmented

