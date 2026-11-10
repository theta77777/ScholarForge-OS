import os
import re
import csv
import json
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import typst
from ..core.agent_logs import AgentLogger

class DocumentBuilder:
    """
    Multi-Format Publication Typesetter:
    1. Camera-Ready Word .docx with Academic Booktabs Tables, OpenXML Formatting & Active Hyperlinked Citations
    2. Instant High-Performance Typst PDF Compilation
    3. Overleaf-Ready LaTeX Package (.zip) with BibTeX References
    4. Deterministic PRISMA 2020 Vector SVG Flowchart
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.final_dir = self.workspace_path / "08_final"
        self.figures_dir = self.workspace_path / "05_figures_tables" / "figures"
        self.final_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)

    def _apply_booktabs_borders(self, table):
        """Applies classic academic 3-line border (top line, header line, bottom line, no verticals)."""
        tblPr = table._tbl.tblPr
        tblBorders = OxmlElement('w:tblBorders')
        
        # Top border (1.5 pt)
        top = OxmlElement('w:top')
        top.set(qn('w:val'), 'single')
        top.set(qn('w:sz'), '12')
        top.set(qn('w:space'), '0')
        top.set(qn('w:color'), '000000')
        tblBorders.append(top)

        # Bottom border (1.5 pt)
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '12')
        bottom.set(qn('w:space'), '0')
        bottom.set(qn('w:color'), '000000')
        tblBorders.append(bottom)

        # Clear vertical and inside borders
        for border_name in ['left', 'right', 'insideV', 'insideH']:
            b = OxmlElement(f'w:{border_name}')
            b.set(qn('w:val'), 'none')
            tblBorders.append(b)

        tblPr.append(tblBorders)

        # Add thin line (0.75 pt) under header row
        if len(table.rows) > 0:
            for cell in table.rows[0].cells:
                tcPr = cell._tc.get_or_add_tcPr()
                tcBorders = OxmlElement('w:tcBorders')
                b_line = OxmlElement('w:bottom')
                b_line.set(qn('w:val'), 'single')
                b_line.set(qn('w:sz'), '6')
                b_line.set(qn('w:space'), '0')
                b_line.set(qn('w:color'), '000000')
                tcBorders.append(b_line)
                tcPr.append(tcBorders)

    @staticmethod
    def _add_docx_hyperlink(paragraph, url: str, text: str, color: str = "004B87", underline: bool = True):
        """Adds a clickable OpenXML hyperlink to a python-docx paragraph."""
        part = paragraph.part
        r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

        hyperlink = OxmlElement('w:hyperlink')
        hyperlink.set(qn('r:id'), r_id)

        new_run = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')

        if color:
            c = OxmlElement('w:color')
            c.set(qn('w:val'), color)
            rPr.append(c)

        if underline:
            u = OxmlElement('w:u')
            u.set(qn('w:val'), 'single')
            rPr.append(u)

        new_run.append(rPr)
        new_run_text = OxmlElement('w:t')
        new_run_text.text = text
        new_run.append(new_run_text)

        hyperlink.append(new_run)
        paragraph._p.append(hyperlink)
        return hyperlink

    def _resolve_citation_urls(self, matrix_rows: Optional[List[Dict[str, Any]]] = None,
                              explicit_urls: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Maps case-insensitive citation keys to active DOIs or publisher landing URLs."""
        urls: Dict[str, str] = {}
        
        # 1. Literature Catalog CSV
        for p in [self.workspace_path / "01_search" / "catalog" / "literature_catalog.csv",
                  self.workspace_path / "01_search" / "candidates.csv"]:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for row in csv.DictReader(f):
                            ck = row.get("citation_key", "").strip()
                            doi = row.get("doi", "").strip()
                            landing = row.get("landing_url", "").strip()
                            pdf = row.get("pdf_url", "").strip()
                            target = f"https://doi.org/{doi}" if doi else (landing or pdf)
                            if ck and target:
                                urls[ck.lower()] = target
                except Exception:
                    pass

        # 2. CSL references.json
        ref_file = self.workspace_path / "06_manuscript" / "references.json"
        if ref_file.exists():
            try:
                with open(ref_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            cid = item.get("id", "").strip()
                            doi = item.get("DOI", "").strip()
                            u = item.get("URL", "").strip()
                            target = f"https://doi.org/{doi}" if doi else u
                            if cid and target:
                                urls[cid.lower()] = target
            except Exception:
                pass

        # 3. Matrix rows
        if matrix_rows:
            for r in matrix_rows:
                ck = r.get("citation_key", "").strip()
                doi = r.get("doi", "").strip()
                target = f"https://doi.org/{doi}" if doi else (r.get("landing_url") or r.get("url") or "")
                if ck and target:
                    urls[ck.lower()] = target

        # 4. Explicit dictionary
        if explicit_urls:
            for k, v in explicit_urls.items():
                if k and v:
                    urls[k.lower()] = v

        return urls

    def _add_paragraph_with_citations(self, doc, text: str, citation_urls: Dict[str, str], is_reference: bool = False):
        """Splits paragraph text, turning [CitationKey] and https:// URLs into clickable hyperlinks."""
        p = doc.add_paragraph()
        if is_reference:
            p.paragraph_format.left_indent = Inches(0.4)
            p.paragraph_format.first_line_indent = Inches(-0.4)
            p.paragraph_format.space_after = Pt(4)
        else:
            p.paragraph_format.space_after = Pt(6)

        # Regex tokenization
        token_regex = re.compile(r'(\[[a-zA-Z0-9_\-\.\:\/]+\]|https?://[^\s\)]+)')
        parts = token_regex.split(text)

        for part in parts:
            if not part:
                continue

            # In-text citation e.g. [Reijm2016]
            m_cit = re.match(r'^\[([a-zA-Z0-9_\-\.\:\/]+)\]$', part)
            if m_cit:
                raw_key = m_cit.group(1)
                url = citation_urls.get(raw_key.lower())
                if url:
                    self._add_docx_hyperlink(p, url, part, color="004B87", underline=True)
                else:
                    run = p.add_run(part)
                    if is_reference:
                        run.font.size = Pt(10)
                continue

            # Direct URL
            if part.startswith("http://") or part.startswith("https://"):
                clean_url = part.rstrip(".,;)")
                trailing = part[len(clean_url):]
                self._add_docx_hyperlink(p, clean_url, clean_url, color="004B87", underline=True)
                if trailing:
                    run = p.add_run(trailing)
                    if is_reference:
                        run.font.size = Pt(10)
                continue

            # Normal text
            run = p.add_run(part)
            if is_reference:
                run.font.size = Pt(10)
        return p

    def build_docx(self, title: str, authors: str, abstract: str, 
                   sections: List[Dict[str, str]], references: List[str], 
                   matrix_rows: Optional[List[Dict[str, Any]]] = None,
                   slug: str = "review_manuscript",
                   citation_urls: Optional[Dict[str, str]] = None) -> Path:
        """
        Builds a styled, submission-ready Word document (.docx) with embedded Table 1 & active clickable citations.
        """
        doc = docx.Document()
        resolved_urls = self._resolve_citation_urls(matrix_rows, citation_urls)
        
        # 1-inch margins
        for section in doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        # Normal Style
        style = doc.styles['Normal']
        style.font.name = 'Times New Roman'
        style.font.size = Pt(12)
        style.paragraph_format.line_spacing = 1.15
        style.paragraph_format.space_after = Pt(6)

        # Title
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_p.add_run(title)
        title_run.font.name = 'Times New Roman'
        title_run.font.size = Pt(18)
        title_run.font.bold = True
        title_p.paragraph_format.space_before = Pt(12)
        title_p.paragraph_format.space_after = Pt(8)

        # Authors
        author_p = doc.add_paragraph()
        author_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        author_run = author_p.add_run(authors)
        author_run.font.name = 'Times New Roman'
        author_run.font.size = Pt(12)
        author_run.font.italic = True
        author_p.paragraph_format.space_after = Pt(18)

        # Abstract Box
        doc.add_heading("Abstract", level=2)
        abs_p = self._add_paragraph_with_citations(doc, abstract, resolved_urls)
        abs_p.paragraph_format.left_indent = Inches(0.4)
        abs_p.paragraph_format.right_indent = Inches(0.4)
        abs_p.paragraph_format.space_after = Pt(18)

        # Body Sections
        for idx, sec in enumerate(sections, start=1):
            doc.add_heading(sec.get("heading", ""), level=1)
            content = sec.get("body", "")
            for para in content.split("\n\n"):
                if para.strip():
                    self._add_paragraph_with_citations(doc, para.strip(), resolved_urls)

            # Embed Table 1 right after Section 3 (Findings / Synthesis)
            if idx == 3 and matrix_rows:
                caption = doc.add_paragraph()
                c_run = caption.add_run("Table 1 | Methodological Characteristics and Quantitative Findings of Included Studies.")
                c_run.font.bold = True
                c_run.font.size = Pt(10)
                caption.paragraph_format.space_before = Pt(12)
                caption.paragraph_format.space_after = Pt(4)

                # Create Table
                cols = ["ID", "Citation", "Design", "System / Population", "N", "Key Finding", "Direction", "Appraisal"]
                table = doc.add_table(rows=1, cols=len(cols))
                hdr_cells = table.rows[0].cells
                for i, col_name in enumerate(cols):
                    hdr_cells[i].text = col_name
                    hdr_cells[i].paragraphs[0].runs[0].font.bold = True
                    hdr_cells[i].paragraphs[0].runs[0].font.size = Pt(9)

                for r in matrix_rows[:15]:
                    row_cells = table.add_row().cells
                    cid = r.get("catalog_id", "")
                    ckey = r.get("citation_key", "")
                    row_cells[0].text = str(cid)
                    
                    # Hyperlink Citation Key in Table if URL exists
                    target_url = resolved_urls.get(ckey.lower())
                    if target_url:
                        self._add_docx_hyperlink(row_cells[1].paragraphs[0], target_url, f"[{ckey}]", color="004B87", underline=True)
                    else:
                        row_cells[1].text = f"[{ckey}]"

                    row_cells[2].text = str(r.get("design", ""))
                    row_cells[3].text = str(r.get("population_or_system", "")[:35])
                    row_cells[4].text = str(r.get("n_or_scale", ""))
                    res = r.get("key_result", "")
                    row_cells[5].text = (res[:65] + "...") if len(res) > 65 else res
                    row_cells[6].text = str(r.get("direction", ""))
                    row_cells[7].text = str(r.get("appraisal_rating", ""))

                    for cell in row_cells:
                        if cell.paragraphs and cell.paragraphs[0].runs:
                            cell.paragraphs[0].runs[0].font.size = Pt(8.5)

                self._apply_booktabs_borders(table)
                table.autofit = True
                
                note = doc.add_paragraph("Note: Evaluated under the Cochrane / ROBINS-I appraisal rubric. Direction indicates reported effect trajectory. Citations are hyperlinked.")
                note.runs[0].font.italic = True
                note.runs[0].font.size = Pt(8.5)
                note.paragraph_format.space_after = Pt(14)

        # Embed Publication Figures
        fig_files = sorted(list(self.figures_dir.glob("fig*.png")))
        if fig_files:
            doc.add_heading("Figures and Quantitative Visualizations", level=1)
            for f_idx, fpath in enumerate(fig_files[:4], start=1):
                try:
                    p_img = doc.add_paragraph()
                    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    doc.add_picture(str(fpath), width=Inches(6.0))

                    caption = doc.add_paragraph()
                    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    clean_name = fpath.stem.replace("_", " ").title()
                    c_run = caption.add_run(f"Figure {f_idx} | {clean_name}.")
                    c_run.font.name = 'Times New Roman'
                    c_run.font.bold = True
                    c_run.font.size = Pt(9.5)
                    caption.paragraph_format.space_after = Pt(14)
                except Exception:
                    pass

        # References Section with Hanging Indent & Hyperlinks
        doc.add_heading("References", level=1)
        for ref in references:
            self._add_paragraph_with_citations(doc, ref, resolved_urls, is_reference=True)

        target_path = self.final_dir / f"{slug}.docx"
        doc.save(str(target_path))
        return target_path

    @staticmethod
    def _clean_for_typst(text: str) -> str:
        if not text:
            return ""
        # Convert Markdown headings in body text to Typst headings
        t = re.sub(r'(?m)^###\s+(.*)$', r'=== \1', text)
        t = re.sub(r'(?m)^##\s+(.*)$', r'== \1', t)
        t = re.sub(r'(?m)^#\s+(.*)$', r'= \1', t)
        
        # Clean LaTeX math commands and backticks
        t = re.sub(r'\\math[a-zA-Z]+\{([^}]+)\}', r'\1', t)
        t = re.sub(r'\\mathcal\{([^}]+)\}', r'\1', t)
        t = re.sub(r'\$([^$]*)\$', r'\1', t)
        t = t.replace('`', "'")
        t = re.sub(r'\[Formula:[^\]]*\]', '(Formula: see text)', t)

        # Convert Markdown bold **text** to Typst bold *text*
        t = t.replace('**', '*')

        # Escape inline underscores and scientific subscripts/superscripts in body text
        t = re.sub(r'([a-zA-Z0-9])_([a-zA-Z0-9])', r'\1\\_\2', t)
        t = re.sub(r'_\{([^}]+)\}', r'\\_(\1)', t)
        t = re.sub(r'\^\{([^}]+)\}', r'\\^(\1)', t)
        t = re.sub(r'\^([a-zA-Z0-9\u0370-\u03ff])', r'\\^\1', t)
        
        # Escape special Typst characters
        t = re.sub(r'<(?=[0-9a-zA-Z])', r'\<', t)
        t = re.sub(r'@(?=[0-9a-zA-Z])', r'\@', t)
        
        # Preserve citation keys [citation_key], replace other brackets with parentheses
        def cit_rep(m):
            return f"__CIT__{m.group(1)}__ENDCIT__"
        t = re.sub(r'\[([a-zA-Z0-9_\-]+)\]', cit_rep, t)
        t = t.replace("[", "(").replace("]", ")")
        t = re.sub(r'__CIT__([a-zA-Z0-9_\-]+)__ENDCIT__', r'[\1]', t)
        
        # Escape lone asterisks (e.g. SSS*) that break Typst bold syntax
        if t.count('*') % 2 != 0:
            t = re.sub(r'(?<=\w)\*(?!\w)', r'\\*', t)

        # Balance lone parentheses per paragraph
        paras = t.split("\n\n")
        fixed = []
        for p in paras:
            po, pc = p.count("("), p.count(")")
            if po > pc:
                p += ")" * (po - pc)
            elif pc > po:
                p = ("(" * (pc - po)) + p
            fixed.append(p)
        return "\n\n".join(fixed)

    def build_typst_pdf(self, title: str, authors: str, abstract: str, 
                        sections: List[Dict[str, str]], 
                        references: Optional[List[str]] = None,
                        matrix_rows: Optional[List[Dict[str, Any]]] = None,
                        slug: str = "review_manuscript",
                        citation_urls: Optional[Dict[str, str]] = None) -> Path:
        """
        Compiles an ultra-fast, modern camera-ready PDF using Typst with embedded tables and linked citations.
        """
        clean_title = self._clean_for_typst(title)
        clean_authors = self._clean_for_typst(authors)
        clean_abstract = self._clean_for_typst(abstract)
        resolved_urls = self._resolve_citation_urls(matrix_rows, citation_urls)

        typst_source = f"""
#set page(paper: "a4", margin: (x: 2.5cm, y: 2.5cm))
#set text(font: ("DejaVu Sans", "Arial", "Liberation Sans", "Helvetica"), size: 10pt, lang: "en")
#set par(justify: true, leading: 0.72em)

#align(center)[
  #v(0.8em)
  #text(size: 16pt, weight: "bold")[{clean_title}]
  #v(0.4em)
  #text(size: 11pt, style: "italic")[{clean_authors}]
  #v(1.0em)
]

#block(
  fill: rgb("f8fafc"),
  inset: 12pt,
  radius: 4pt,
  stroke: 0.5pt + rgb("cbd5e1")
)[
  #text(weight: "bold", fill: rgb("0f172a"))[Abstract] --- {clean_abstract}
]

#v(0.8em)
"""
        for idx, sec in enumerate(sections, start=1):
            h_clean = self._clean_for_typst(sec.get('heading', '').replace("[", "(").replace("]", ")"))
            body_clean = self._clean_for_typst(sec.get('body', ''))
            
            # Format in-text citations into Typst links if URL known
            def typst_link_sub(match):
                cit = match.group(1)
                u = resolved_urls.get(cit.lower())
                if u:
                    return f'#link("{u}")[{cit}]'
                return f'[{cit}]'

            body_with_links = re.sub(r'\[([a-zA-Z0-9_\-]+)\]', typst_link_sub, body_clean)

            typst_source += f"\n== {h_clean}\n\n{body_with_links}\n"
            if idx == 3 and matrix_rows:
                typst_source += """
#v(0.8em)
#align(center)[
  #text(weight: "bold", size: 9pt)[Table 1: Methodological Characteristics and Empirical Findings of Landmark Included Studies]
]
#table(
  columns: (auto, auto, auto, 1fr, auto),
  stroke: (x, y) => if y == 0 { (bottom: 1.2pt + black, top: 1.2pt + black) } else { (bottom: 0.5pt + rgb("e2e8f0")) },
  fill: (col, row) => if row == 0 { rgb("f1f5f9") },
  [ *ID* ], [ *Citation* ], [ *Model / System* ], [ *Key Empirical Finding* ], [ *Appraisal* ],
"""
                for r in matrix_rows[:10]:
                    cid = r.get("catalog_id", "")
                    ckey = r.get("citation_key", "")
                    clean_pop = " ".join(r.get("population_or_system", "Empirical System").split())[:28]
                    clean_res = " ".join(r.get("key_result", "").split())[:65] + "..."
                    des = self._clean_for_typst(clean_pop.replace("[", "(").replace("]", ")"))
                    res = self._clean_for_typst(clean_res.replace("[", "(").replace("]", ")"))
                    app = r.get("appraisal_rating", "")
                    ckey_clean = self._clean_for_typst(ckey)
                    u = resolved_urls.get(ckey.lower())
                    if u:
                        cit_cell = f'#link("{u}")[{ckey_clean}]'
                    else:
                        cit_cell = f'[{ckey_clean}]'
                    typst_source += f"  [{cid}], [ {cit_cell} ], [{des}], [{res}], [{app}],\n"
                typst_source += ")\n#v(0.8em)\n"

        # Embed Publication Figures
        fig_files = sorted(list(self.figures_dir.glob("fig*.png")))
        if fig_files:
            typst_source += "\n== Figures and Quantitative Visualizations\n\n"
            for f_idx, fpath in enumerate(fig_files[:4], start=1):
                try:
                    rel_path = f"/{fpath.relative_to(self.workspace_path).as_posix()}"
                    clean_name = self._clean_for_typst(fpath.stem.replace("_", " ").title())
                    typst_source += f"""
#align(center)[
  #image("{rel_path}", width: 85%)
  #v(0.3em)
  #text(weight: "bold", size: 8.5pt)[Figure {f_idx}: {clean_name}]
]
#v(0.8em)
"""
                except Exception:
                    pass

        if references:
            typst_source += """
#v(1.2em)
== References

#set text(size: 8.5pt)
#set par(hanging-indent: 1.5em)
"""
            for ref in references:
                clean_ref = self._clean_for_typst(ref.replace("[", "(").replace("]", ")"))
                typst_source += f"\n- {clean_ref}\n"

        target_typ = self.final_dir / f"{slug}.typ"
        target_typ.write_text(typst_source, encoding="utf-8")
        target_pdf = self.final_dir / f"{slug}_typst.pdf"
        try:
            typst.compile(str(target_typ), output=str(target_pdf), root=str(self.workspace_path))
        except Exception as e:
            AgentLogger.log("TYPST", f"Typst compilation notice: {e}", "warning")
        return target_pdf

    def build_latex_bundle(self, title: str, authors: str, abstract: str, 
                           sections: List[Dict[str, str]], bib_entries: List[str], 
                           matrix_rows: Optional[List[Dict[str, Any]]] = None,
                           slug: str = "review_manuscript") -> Path:
        """
        Builds an Overleaf-ready LaTeX package (.zip) with manuscript.tex, booktabs tables, and references.bib.
        """
        tex_content = f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{booktabs}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\usepackage{{cite}}

\\title{{\\textbf{{{title}}}}}
\\author{{{authors}}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle

\\begin{{abstract}}
{abstract}
\\end{{abstract}}

"""
        for sec in sections:
            tex_content += f"\\section{{{sec.get('heading', '')}}}\n{sec.get('body', '')}\n\n"

        tex_content += """
\\bibliographystyle{ieeetr}
\\bibliography{references}
\\end{document}
"""
        tex_file = self.final_dir / f"{slug}.tex"
        tex_file.write_text(tex_content, encoding="utf-8")

        bib_content = "\n\n".join(bib_entries)
        bib_file = self.final_dir / "references.bib"
        bib_file.write_text(bib_content, encoding="utf-8")

        # Create Overleaf zip package
        zip_path = self.final_dir / f"{slug}_latex.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(tex_file, arcname="manuscript.tex")
            zipf.write(bib_file, arcname="references.bib")
            for f in self.figures_dir.glob("fig*.png"):
                zipf.write(f, arcname=f"figures/{f.name}")

        return zip_path


    def generate_prisma_svg(self, counts: Dict[str, Any]) -> Path:
        """Generates deterministic PRISMA 2020 SVG flowchart."""
        total = counts.get("total_identified", 24)
        dup = counts.get("duplicates_removed", 4)
        screened = counts.get("records_screened", 20)
        excluded = counts.get("records_excluded", 10)
        assessed = counts.get("reports_assessed", 10)
        included = counts.get("studies_included", 8)
        
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
  <rect width="800" height="600" fill="#ffffff"/>
  <text x="400" y="30" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#0f172a">PRISMA 2020 Flow Diagram</text>
  
  <!-- Identification -->
  <rect x="250" y="60" width="300" height="60" rx="6" fill="#f8fafc" stroke="#3b82f6" stroke-width="2"/>
  <text x="400" y="85" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#1e293b">Identification</text>
  <text x="400" y="105" text-anchor="middle" font-family="Arial" font-size="11" fill="#475569">Records identified from databases (n = {total})</text>

  <!-- Line to Screening -->
  <line x1="400" y1="120" x2="400" y2="160" stroke="#64748b" stroke-width="1.5"/>
  
  <!-- Duplicates removed -->
  <rect x="580" y="130" width="180" height="50" rx="6" fill="#fef2f2" stroke="#ef4444" stroke-width="1.5"/>
  <text x="670" y="150" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#991b1b">Duplicates Removed</text>
  <text x="670" y="168" text-anchor="middle" font-family="Arial" font-size="10" fill="#b91c1c">(n = {dup})</text>
  <line x1="400" y1="140" x2="580" y2="155" stroke="#ef4444" stroke-width="1.5"/>

  <!-- Screening -->
  <rect x="250" y="160" width="300" height="60" rx="6" fill="#f8fafc" stroke="#3b82f6" stroke-width="2"/>
  <text x="400" y="185" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#1e293b">Screening</text>
  <text x="400" y="205" text-anchor="middle" font-family="Arial" font-size="11" fill="#475569">Records screened (n = {screened})</text>

  <!-- Excluded records -->
  <rect x="580" y="230" width="180" height="50" rx="6" fill="#fef2f2" stroke="#ef4444" stroke-width="1.5"/>
  <text x="670" y="250" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#991b1b">Records Excluded</text>
  <text x="670" y="268" text-anchor="middle" font-family="Arial" font-size="10" fill="#b91c1c">(n = {excluded})</text>
  <line x1="400" y1="240" x2="580" y2="255" stroke="#ef4444" stroke-width="1.5"/>

  <!-- Line to Eligibility -->
  <line x1="400" y1="220" x2="400" y2="260" stroke="#64748b" stroke-width="1.5"/>

  <!-- Eligibility -->
  <rect x="250" y="260" width="300" height="60" rx="6" fill="#f8fafc" stroke="#3b82f6" stroke-width="2"/>
  <text x="400" y="285" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#1e293b">Eligibility</text>
  <text x="400" y="305" text-anchor="middle" font-family="Arial" font-size="11" fill="#475569">Reports sought for retrieval (n = {assessed})</text>

  <!-- Line to Included -->
  <line x1="400" y1="320" x2="400" y2="360" stroke="#64748b" stroke-width="1.5"/>

  <!-- Included -->
  <rect x="250" y="360" width="300" height="60" rx="6" fill="#ecfdf5" stroke="#10b981" stroke-width="2"/>
  <text x="400" y="385" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#065f46">Included</text>
  <text x="400" y="405" text-anchor="middle" font-family="Arial" font-size="11" fill="#047857">Studies included in review (n = {included})</text>
</svg>"""
        out_path = self.figures_dir / "prisma_flowchart.svg"
        out_path.write_text(svg, encoding="utf-8")
        try:
            final_out = self.final_dir / "prisma_flowchart.svg"
            final_out.write_text(svg, encoding="utf-8")
        except Exception:
            pass
        return out_path
