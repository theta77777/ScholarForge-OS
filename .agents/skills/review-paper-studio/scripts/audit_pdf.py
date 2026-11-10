"""Audit a PDF mechanically; optionally render all pages. Visual inspection remains a separate action."""
import argparse,hashlib,json
from pathlib import Path
from pypdf import PdfReader
def audit(pdf,qa,render=False,poppler=None):
    pdf=Path(pdf).resolve();qa=Path(qa).resolve();qa.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(pdf.read_bytes()).hexdigest();reader=PdfReader(pdf);fonts=set();errors=[];text=[]
    for n,page in enumerate(reader.pages,1):
        text.append(page.extract_text() or '')
        if not text[-1].strip():errors.append(f'Page {n} has no extractable text; inspect figure/scan status.')
        resources=page.get('/Resources')
        resources=resources.get_object() if resources is not None else {}
        fontdict=resources.get('/Font',{})
        if hasattr(fontdict,'get_object'):fontdict=fontdict.get_object()
        for f in fontdict.values():fonts.add(str(f.get_object().get('/BaseFont')))
    geometry='not checked: pdfplumber unavailable'
    try:
        import pdfplumber
        with pdfplumber.open(pdf) as doc:
            for n,page in enumerate(doc.pages,1):
                for c in page.chars:
                    if c['x0']<-1 or c['x1']>page.width+1 or c['top']<-1 or c['bottom']>page.height+1:errors.append(f'Page {n}: character outside page bounds.');break
        geometry='checked character bounds'
    except ImportError:pass
    if '\ufffd' in '\n'.join(text):errors.append('Replacement glyph found; inspect symbols.')
    pages=[]
    if render:
        from pdf2image import convert_from_path
        for n,im in enumerate(convert_from_path(str(pdf),dpi=150,poppler_path=poppler),1):
            target=qa/f'{digest[:12]}-page-{n:03d}.png';im.save(target);pages.append(target.name)
    result={'pdf':str(pdf),'sha256':digest,'pages':len(reader.pages),'fonts':sorted(fonts),'geometry':geometry,'errors':errors,'rendered_page_files':pages,'visual_review_status':'PENDING: open every latest page image; no automatic visual pass','scientific_validation':'not assessed by this script'}
    (qa/'PDF_MECHANICAL_CHECKS.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (qa/'rendered_text.txt').write_text('\n\n'.join(f'PAGE {n}\n{t}' for n,t in enumerate(text,1)),encoding='utf-8')
    manifest=qa/f'VISUAL_REVIEW.{digest[:12]}.json'
    if not manifest.exists():manifest.write_text(json.dumps({'pdf_sha256':digest,'inspector_type':'not yet recorded','pages':[{'page':n,'inspected':False,'status':'pending','notes':''} for n in range(1,len(reader.pages)+1)]},indent=2),encoding='utf-8')
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--pdf',required=True);ap.add_argument('--qa-dir',required=True);ap.add_argument('--render',action='store_true');ap.add_argument('--poppler-dir')
    a=ap.parse_args();r=audit(a.pdf,a.qa_dir,a.render,a.poppler_dir);print(json.dumps(r,indent=2));raise SystemExit(1 if r['errors'] else 0)
