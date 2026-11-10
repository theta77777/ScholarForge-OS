"""Mechanical checks only. Does not independently verify reference identity or scientific claims."""
import argparse,json,re
from pathlib import Path
def heading(s):return re.sub(r'^\d+(?:\.\d+)*[ .]*','',s.lstrip('#').strip()).lower()
def groups(text):
    result=[]
    for g in re.findall(r'\[([\d,; \-–]+)\]',text):
        for item in re.split(r'[,;]',g):
            item=item.strip()
            if re.fullmatch(r'\d+',item):result.append(int(item))
            elif re.fullmatch(r'\d+\s*[-–]\s*\d+',item):
                lo,hi=map(int,re.split(r'[-–]',item))
                if lo>hi or hi-lo>1000:raise ValueError('Descending or implausibly large citation range: '+item)
                result.extend(range(lo,hi+1))
    return result
def words(text):
    text=re.sub(r'!\[[^\]]*\]\([^\n]*\)','',text)
    text=re.sub(r'\[([^\]]+)\]\([^\n]*?\)',r'\1',text)
    text=re.sub(r'^[#|*` -]+','',text,flags=re.M)
    return len(text.split())
def check(project):
    p=Path(project);cfg=json.loads((p/'project.json').read_text(encoding='utf-8-sig'));md=(p/'MANUSCRIPT.md').read_text(encoding='utf-8-sig')
    refs=json.loads((p/'references.json').read_text(encoding='utf-8-sig'));errors=[];warnings=[]
    def require(cond,msg):
        if not cond:errors.append(msg)
    require(bool(md.strip()),'Manuscript is empty.')
    require(bool(md.splitlines()) and md.splitlines()[0].lstrip('# ').strip()==cfg['title'],'Title differs from recorded project title; record an authorized change.')
    require(not re.search(r'\[TODO|\[\[|turn\d+(?:search|view)|cite|TITLE OF THE REVIEW PAPER',md),'Unresolved drafting/tool tokens found.')
    h=[(m.start(),m.end(),heading(m[0])) for m in re.finditer(r'^## .+$',md,re.M)]
    rhead=[x for x in h if x[2]=='references'];require(len(rhead)==1,'Exactly one References heading is required.')
    if not rhead:return {'mechanical_status':'FAIL','errors':errors,'warnings':warnings}
    body=md[:rhead[0][0]];bib=md[rhead[0][1]:].strip()
    lines=[l.strip() for l in bib.splitlines() if l.strip()]
    bibnums=[]
    for line in lines:
        m=re.match(r'^(\d+)\.\s+\S',line)
        require(bool(m),'References must be one paragraph per line with no notes after the final reference.')
        if m:bibnums.append(int(m[1]))
    require(bool(refs),'No verified reference records supplied.')
    require(bibnums==list(range(1,len(refs)+1)),'Bibliography numbering/record count does not reconcile.')
    numbers=[r.get('number') for r in refs]
    require(numbers==list(range(1,len(refs)+1)),'references.json must be in citation order with consecutive number fields.')
    ids=[r.get('report_id') for r in refs];require(all(ids) and len(set(ids))==len(ids),'Stable report IDs missing or duplicated.')
    dois=[r.get('doi','').lower().removeprefix('https://doi.org/') for r in refs if r.get('doi')]
    require(len(set(dois))==len(dois),'Duplicate DOI identities detected.')
    for r in refs:
        require(r.get('identity_status')=='verified' and bool(r.get('identity_source')) and bool(r.get('identity_checked_at')),f"Reference {r.get('number')} lacks a documented identity verification state/source/date.")
        require(bool(r.get('title')) and bool(r.get('citation')),f"Reference {r.get('number')} lacks title/citation.")
        if r.get('citation'):require(f"{r['number']}. {r['citation']}" in lines,f"Reference {r['number']} differs from its supplied citation record.")
    if cfg.get('citation_style','numbered')=='numbered':
        try:cited=groups(body)
        except ValueError as exc:errors.append(str(exc));cited=[]
        unique=list(dict.fromkeys(cited))
        require(set(cited)==set(numbers),'Citations include unknown references or omit supplied references.')
        require(unique==numbers,'First-appearance citation order differs from bibliography.')
    else:errors.append('This helper supports numbered citations only; use and document a suitable citation-style check.')
    intro=[x for x in h if x[2]=='introduction'];require(len(intro)==1,'A recognizable Introduction heading is required for counting.')
    prose=''
    if intro:
        active=False;started=False;paragraphs=[]
        for line in md.splitlines():
            if line.startswith('## '):
                name=heading(line)
                if name=='references':break
                if name=='introduction':started=True
                active=started and name not in {'tables','figures','statements and declarations','declarations'}
            elif active and line.strip() and not line.startswith(('#','|','![')):paragraphs.append(line)
        prose='\n'.join(paragraphs)
        prose=re.sub(r'\[[\d,; \-–]+\]','',prose)
    labels=cfg.get('figure_label_words',0)
    require(isinstance(labels,int) and not isinstance(labels,bool) and labels>=0,'Figure label count must be a nonnegative actual integer count.')
    if not isinstance(labels,int) or isinstance(labels,bool) or labels<0:labels=0
    counts={'main_prose_words':words(prose),'whole_text_words':words(md),'figure_label_words':labels,'references':len(refs)}
    counts['whole_words_with_figure_labels']=counts['whole_text_words']+counts['figure_label_words']
    if cfg.get('whole_words_max') is not None:require(counts['whole_words_with_figure_labels']<=cfg['whole_words_max'],'Whole-document word ceiling exceeded.')
    if not cfg['main_words_min']<=counts['main_prose_words']<=cfg['main_words_max']:warnings.append('Main prose outside the current requested range; resolve or explain the recorded override.')
    if not cfg['references_target_min']<=len(refs)<=cfg['references_target_max']:warnings.append('Reference count outside preference; justify evidence coverage instead of padding.')
    warnings.append('Verification states are supplied records, not independent source checks. Layout and scientific validity require separate audits.')
    return {'mechanical_status':'PASS' if not errors else 'FAIL','count_method':'Whitespace tokens after basic Markdown/image/citation removal; main prose excludes headings, table rows and citation groups. Figure labels added separately.','counts':counts,'errors':errors,'warnings':warnings}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--project',required=True);a=ap.parse_args();result=check(a.project)
    (Path(a.project)/'MECHANICAL_CHECKS.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(result,indent=2,ensure_ascii=False));raise SystemExit(0 if result['mechanical_status']=='PASS' else 1)
