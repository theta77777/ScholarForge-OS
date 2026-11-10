"""Create a review project without replacing existing work. Python standard library only."""
import argparse,csv,json
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1]
HEADERS={
'SOURCE_REGISTER.csv':['report_id','study_id','citation_number','title','doi_or_identifier','authoritative_url','identity_status','identity_checked_at','identity_source','access_level','read_status','extraction_status','appraisal_status','publication_status','limits'],
'SCREENING.csv':['report_id','stage','decision','reason','reviewer_type','decision_date','retrieval_status','related_reports','uncertainty'],
'STUDY_FAMILIES.csv':['study_id','report_ids','overlap_basis','independence_status','source_locator','limits'],
'EVIDENCE.csv':['outcome_id','study_id','report_id','source_locator','design_context','population_or_object','exposure_settings','comparator','endpoint','n','analytical_unit','follow_up','estimate','units','uncertainty','reported_or_calculated','calculation','limits','verification_status'],
'CLAIM_LEDGER.csv':['claim_id','location','claim','report_or_outcome_ids','citation_numbers','support_type','source_locator','limits','verification_status'],
'EXECUTED_SEARCHES.csv':['search_id','source_interface','exact_query','run_date','date_field','filters','returned_count','exported_count','truncation','raw_file','retrieval_problems']}
DOCS={
'PROJECT_CONTROL.md':'# Project control\n\nRecord scope, review type, decisions, explicit user overrides, word-count basis, tools/access and completion gates.\n',
'PROTOCOL.md':'# Protocol\n\nRecord planned eligibility, search, screening, extraction, analytical units, appraisal and synthesis before formal selection. Distinguish plans from completed procedures; append dated amendments with reasons.\n',
'SEARCH_LOG.md':'# Search execution\n\nPreserve exact executed searches and raw exports. Not yet executed.\n',
'NOVELTY.md':'# Competing reviews and contribution\n\nNot yet assessed. Record sources and exact supporting locations.\n',
'JOURNAL_CHECK.md':'# Journal comparison\n\nCurrent official requirements not yet checked. Record five realistic candidates or explain fewer, precise word scopes, eligibility, routes/charges, metrics/year and AI/artwork policies.\n',
'APPRAISAL.md':'# Source appraisal\n\nNot yet performed. Record current appropriate instruments and source-supported judgments, applicability, precision, reviewer type and unassessable domains.\n',
'AUDIT_LOG.md':'# Audit and repairs\n\nRecord defect, severity, evidence/location, root cause, repair, dependent checks and remaining uncertainty.\n',
'FIGURE_PROVENANCE.md':'# Figure provenance\n\nRecord status (conceptual/empirical), input sources/data, code/editable master, caption/callout, policy, assistance and actual verification. No figures created yet.\n',
'SUPPORTING_MATERIAL.md':'# Supporting material\n\n## Part A Scientific supplement\n\nOnly completed methods and source-supported evidence belong here.\n\n## Part B Author and audit working records\n\nAuthor identities/declarations and human scientific validation remain unknown until supplied/completed. Part B is not automatically a journal supplement.\n',
'STATUS.md':'# Project checkpoint\n\nStage: initialized only. No research, screening, source verification or visual QA completed. Next: interpret question, assess feasibility/contribution and verify journals.\n'}
def create(out,title,field):
    out=Path(out).resolve()
    existing=out/'project.json'
    if existing.exists():
        config=json.loads(existing.read_text(encoding='utf-8-sig'))
        if config.get('title')!=title:raise ValueError('Existing project has another title; choose a separate folder.')
    else:
        config=json.loads((SKILL/'assets/defaults.json').read_text(encoding='utf-8'))
        config.update(title=title,field=field,review_type='undecided',journal='unselected',figure_label_words=0)
    out.mkdir(parents=True,exist_ok=True)
    for folder in ['raw','figures','qa','output']:(out/folder).mkdir(exist_ok=True)
    def put(name,value):
        path=out/name
        if not path.exists():
            with path.open('x',encoding='utf-8',newline='') as f:f.write(value)
    put('project.json',json.dumps(config,indent=2,ensure_ascii=False)+'\n')
    for name,body in DOCS.items():put(name,body)
    for name,headers in HEADERS.items():
        if not (out/name).exists():
            with (out/name).open('x',encoding='utf-8',newline='') as f:csv.writer(f).writerow(headers)
    put('references.json','[]\n');put('REFERENCES.ris','')
    put('MANUSCRIPT.md','# '+title+'\n\n## Abstract\n\n## Keywords\n\n## Introduction\n\n## Conclusions\n\n## Statements and Declarations\n\n## References\n')
    return out
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);ap.add_argument('--title',required=True);ap.add_argument('--field',default='infer from title')
    a=ap.parse_args();print(create(a.out,a.title,a.field))
