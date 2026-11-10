"""Build basic matching-content PDF/DOCX from Markdown. Rich maths/templates require another typesetter."""
import argparse,html,json,os,re
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4,letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image as RLImage,PageBreak,KeepTogether
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image
def locate_fonts(font_dir=None):
    dirs=[Path(font_dir)] if font_dir else [Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts',Path('/Library/Fonts'),Path('/usr/share/fonts/truetype/msttcorefonts')]
    choices=[['times.ttf','Times_New_Roman.ttf','Times New Roman.ttf'],['timesbd.ttf','Times_New_Roman_Bold.ttf','Times New Roman Bold.ttf'],['timesi.ttf','Times_New_Roman_Italic.ttf','Times New Roman Italic.ttf'],['timesbi.ttf','Times_New_Roman_Bold_Italic.ttf','Times New Roman Bold Italic.ttf']]
    found=[]
    for names in choices:
        path=next((d/name for d in dirs for name in names if (d/name).is_file()),None)
        if path is None:raise FileNotFoundError('Actual Times New Roman regular/bold/italic/bold-italic font files required. Pass --font-dir; do not silently substitute Times-Roman.')
        found.append(path)
    return found
def atoms(s):return re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*)',s)
def rich(s):
    s=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',s);out=''
    for a in atoms(s):
        if a.startswith('**'):out+='<b>'+html.escape(a[2:-2])+'</b>'
        elif a.startswith('*'):out+='<i>'+html.escape(a[1:-1])+'</i>'
        else:out+=html.escape(a)
    return out
def runs(p,s):
    s=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',s)
    for a in atoms(s):
        r=p.add_run(a[2:-2] if a.startswith('**') else a[1:-1] if a.startswith('*') else a);r.bold=a.startswith('**');r.italic=a.startswith('*') and not a.startswith('**')
def blocks(md):
    lines=md.splitlines();i=0
    while i<len(lines):
        s=lines[i].strip();i+=1
        if not s:continue
        if s.startswith('|'):
            rows=[s]
            while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i].strip());i+=1
            vals=[[c.strip() for c in row.strip('|').split('|')] for row in rows if not re.fullmatch(r'[|:\- ]+',row)]
            if len({len(r) for r in vals})!=1:raise ValueError('Table rows have inconsistent columns.')
            yield 'table',vals
        elif s.startswith('#'):yield 'heading',(len(s)-len(s.lstrip('#')),s.lstrip('# '))
        elif re.fullmatch(r'!\[[^\]]*\]\(.+\)',s):yield 'image',re.match(r'!\[([^\]]*)\]\((.+)\)',s).groups()
        else:
            # Treat a paragraph as one logical record; numbered references stay separate.
            while i<len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(('#','|','![')) and not re.match(r'^\d+\. ',lines[i].strip()):s+=' '+lines[i].strip();i+=1
            yield 'paragraph',s
def widths(rows,total):
    n=len(rows[0]);weights=[max(8,sum(min(len(row[j]),120) for row in rows)/len(rows))**0.5 for j in range(n)]
    if n==3 and rows[0][1].lower()=='score':return [total*.29,total*.115,total*.595]
    return [total*w/sum(weights) for w in weights]
def build(source,out,cfg,font_dir=None):
    source=Path(source).resolve();out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True);md=source.read_text(encoding='utf-8-sig')
    if out.with_suffix('.pdf').exists() or out.with_suffix('.docx').exists():raise FileExistsError('Preserve existing deliverables: choose a new version/output stem rather than overwriting them.')
    if re.search(r'(?<!\\)\$(?!\d)[^$\n]+\$|(?<!\\)\$\d[^$\n]*\$(?!\d)|\\\(|\\\[|```',md):raise ValueError('Raw maths/code fences need a suitable rich scientific typesetter; resolve before building.')
    if cfg.get('font_family','Times New Roman')!='Times New Roman':raise ValueError('This helper supports Times New Roman; use an appropriate renderer for another requested family.')
    for name,path in zip(['TNR','TNR-Bold','TNR-Italic','TNR-BoldItalic'],locate_fonts(font_dir)):pdfmetrics.registerFont(TTFont(name,str(path)))
    pdfmetrics.registerFontFamily('TNR',normal='TNR',bold='TNR-Bold',italic='TNR-Italic',boldItalic='TNR-BoldItalic')
    page=A4 if cfg.get('page_size','A4')=='A4' else letter;margin=61.2;width=page[0]-2*margin
    body=cfg.get('body_pt',12);spacing=cfg.get('line_spacing',1.15);head=cfg.get('heading_pt',14);title=cfg.get('title_pt',18)
    styles={k:ParagraphStyle(k,fontName='TNR-Bold' if k in ['title','heading'] else 'TNR',fontSize=size,leading=size*spacing,spaceAfter=6,spaceBefore=8 if k in ['title','heading'] else 0,keepWithNext=k in ['title','heading']) for k,size in [('body',body),('heading',head),('title',title),('ref',body)]}
    styles['ref'].leftIndent=12;styles['ref'].firstLineIndent=-12
    doc=Document();sec=doc.sections[0];sec.page_width=Pt(page[0]);sec.page_height=Pt(page[1]);sec.left_margin=sec.right_margin=Pt(margin);sec.top_margin=sec.bottom_margin=Pt(57.6)
    for st in doc.styles:
        if st.type in [1,2]:
            st.font.name='Times New Roman';st.font.size=Pt(body);st.font.color.rgb=RGBColor(0,0,0)
            rp=st.element.get_or_add_rPr();rf=rp.find(qn('w:rFonts'))
            if rf is None:rf=OxmlElement('w:rFonts');rp.insert(0,rf)
            for key in list(rf.attrib):
                if key.endswith('Theme'):del rf.attrib[key]
            for key in ['ascii','hAnsi','eastAsia','cs']:rf.set(qn('w:'+key),'Times New Roman')
            if st.type==1:st.paragraph_format.line_spacing=spacing;st.paragraph_format.space_after=Pt(6)
    for name,size in [('Title',title),('Heading 1',head),('Heading 2',head)]:
        st=doc.styles[name];st.font.size=Pt(size);st.font.bold=True;st.paragraph_format.keep_with_next=True
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    story=[];content=[]
    for kind,value in blocks(md):
        if kind=='heading':
            level,text=value
            if text.lower() in ['tables','figures','references','part b author and audit working records']:
                if story:story.append(PageBreak())
            p=doc.add_paragraph(text,style='Title' if level==1 else 'Heading 1' if level==2 else 'Heading 2')
            if text.lower() in ['tables','figures','references','part b author and audit working records']:p.paragraph_format.page_break_before=True
            story.append(Paragraph(rich(text),styles['title' if level==1 else 'heading']));content.append(text)
        elif kind=='paragraph':
            text=value;p=doc.add_paragraph();p.paragraph_format.widow_control=True;runs(p,text)
            isref=bool(re.match(r'^\d+\. ',text))
            if isref:p.paragraph_format.left_indent=Pt(12);p.paragraph_format.first_line_indent=Pt(-12)
            story.append(Paragraph(rich(text),styles['ref' if isref else 'body']));content.append(text)
        elif kind=='image':
            alt,path=value;imgpath=(source.parent/path).resolve()
            if not imgpath.is_file():raise FileNotFoundError(imgpath)
            with Image.open(imgpath) as im:iw,ih=im.size
            w=width;h=w*ih/iw
            if h>page[1]*.68:w*=page[1]*.68/h;h=page[1]*.68
            shape=doc.add_paragraph().add_run().add_picture(str(imgpath),width=Pt(w));shape._inline.docPr.set('descr',alt)
            story.extend([RLImage(str(imgpath),width=w,height=h),Spacer(1,6)])
        else:
            rows=value;ws=widths(rows,width);table=doc.add_table(rows=1,cols=len(rows[0]));table.autofit=False;table.style='Table Grid'
            for col,w in zip(table.columns,ws):col.width=Pt(w)
            for n,row in enumerate(rows):
                tr=table.rows[0] if n==0 else table.add_row();pr=tr._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
                if n==0:pr.append(OxmlElement('w:tblHeader'))
                for cell,text,w in zip(tr.cells,row,ws):
                    cell.width=Pt(w);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER;runs(cell.paragraphs[0],text)
                    if n==0:
                        for run in cell.paragraphs[0].runs:run.bold=True
                        sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E7E6E6');cell._tc.get_or_add_tcPr().append(sh)
            pdfrows=[[Paragraph('<b>'+rich(t)+'</b>' if n==0 else rich(t),styles['body']) for t in row] for n,row in enumerate(rows)]
            tab=Table(pdfrows,colWidths=ws,repeatRows=1,hAlign='LEFT');tab.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D9D9D9')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7E6E6')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            story.extend([tab,Spacer(1,8)]);content.extend(t for row in rows for t in row)
    doc.core_properties.title=md.splitlines()[0].lstrip('# ');doc.core_properties.author='';doc.save(out.with_suffix('.docx'))
    def foot(canvas,pdfdoc):canvas.setFont('TNR',body);canvas.drawCentredString(page[0]/2,25,str(pdfdoc.page))
    SimpleDocTemplate(str(out.with_suffix('.pdf')),pagesize=page,leftMargin=margin,rightMargin=margin,topMargin=57.6,bottomMargin=57.6,title=doc.core_properties.title,author='').build(story,onFirstPage=foot,onLaterPages=foot)
    return {'pdf':str(out.with_suffix('.pdf')),'docx':str(out.with_suffix('.docx')),'content_records':len(content),'font':'actual embedded Times New Roman','visual_qa':'pending; render and inspect every page','limitations':'basic layout; bitmap image embedding, with editable figure masters supplied separately; PDF/Word pagination may differ'}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);ap.add_argument('--config',required=True);ap.add_argument('--font-dir')
    a=ap.parse_args();cfg=json.loads(Path(a.config).read_text(encoding='utf-8-sig'));print(json.dumps(build(a.source,a.out,cfg,a.font_dir),indent=2))
