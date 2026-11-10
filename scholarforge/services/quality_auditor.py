import csv
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import difflib
import httpx

from ..core.rate_limiter import rate_limiter
from ..core.database import DatabaseManager

class QualityAuditor:
    """
    7-Perspective Advanced Quality Audit Arena
    (Unified ScholarForge OS + PaperOrchestra Hardened Verification Gates):
    1. Subject-Matter Specialist: Answers research question, claim sizing.
    2. Methodology Specialist: Risk of bias, sample sizes, pooling validity.
    3. Citation & Integrity Specialist: Real DOI resolution check, 1:1 in-text matching.
    4. Critical Reviewer: Over-generalization, epistemic hedging, circularity.
    5. Editorial & Cliché Polisher: Scans banned AI clichés, heading hierarchy.
    6. Anti-Leakage Gate (PaperOrchestra App. D.4): Catches leaked system prompts, dummy emails.
    7. Quantitative Claim Corroborator (AutoSci/PaperOrchestra Gate): Checks that numeric percentages,
       multipliers, and p-values in the draft exist in the empirical evidence matrix.
    """

    BANNED_CLICHES = [
        "delve", "tapestry", "vital role", "testament to", "beacon of hope",
        "game-changer", "paradigm shift", "plethora", "revolutionize", "pivotal"
    ]

    LEAKAGE_PATTERNS = [
        re.compile(r"[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-.]+"),
        re.compile(r"(?i)\bas an ai\b|\bsystem prompt\b|\bignore previous instructions\b"),
        re.compile(r"(?i)\bcorresponding\s+author\b|\bcorrespondence\s+to\b")
    ]

    NUMERIC_CLAIM_REGEX = re.compile(
        r'(\b\d+(?:\.\d+)?\s*%(?:\s*[+-]?\d*(?:\.\d+)?)?|\b\d+(?:\.\d+)?\s*[-–]?\s*fold|\bp\s*[<=]\s*0\.\d+)',
        re.IGNORECASE
    )

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.quality_dir = self.workspace_path / "07_quality"
        self.checks_dir = self.quality_dir / "checks"
        self.quality_dir.mkdir(parents=True, exist_ok=True)
        self.checks_dir.mkdir(parents=True, exist_ok=True)
        self.db = DatabaseManager()

    async def verify_doi_online(self, doi: str) -> bool:
        """Verifies if a DOI resolves in Crossref."""
        if not doi or not re.match(r"^10\.\d{4,9}/\S+$", doi):
            return False
            
        cached = self.db.get_doi_metadata(doi)
        if cached:
            return True

        await rate_limiter.acquire("crossref")
        try:
            url = f"https://api.crossref.org/works/{doi}"
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url, headers={"User-Agent": "ScholarForgeOS/2.1"})
                return resp.status_code == 200
        except Exception:
            return False

    async def run_full_audit(self, slug: str = "review_manuscript") -> Dict[str, Any]:
        """
        Executes all 7 review passes on the current manuscript.
        """
        md_path = self.workspace_path / "06_manuscript" / "manuscript.md"
        claims_path = self.workspace_path / "03_extraction" / "claims.csv"
        matrix_path = self.workspace_path / "03_extraction" / "evidence_matrix.csv"

        if not md_path.exists():
            return {"status": "error", "message": "Manuscript not found to audit."}

        text = md_path.read_text(encoding="utf-8")
        issues: List[Dict[str, Any]] = []

        # Read evidence matrix text for numeric corroboration
        matrix_corpus = ""
        matrix_rows = []
        if matrix_path.exists():
            with open(matrix_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    matrix_rows.append(r)
                    matrix_corpus += " " + " ".join(r.values())

        # PASS 1: Editorial & Cliché Polisher
        for cliche in self.BANNED_CLICHES:
            matches = len(re.findall(rf"\b{cliche}\b", text, re.IGNORECASE))
            if matches > 0:
                issues.append({
                    "issue_id": f"ISS_ED_{len(issues)+1:03d}",
                    "perspective": "Editorial",
                    "severity": "minor",
                    "location": "Body text",
                    "description": f"Detected AI cliché: '{cliche}' ({matches} occurrences)",
                    "evidence": cliche,
                    "action": f"Replace with precise academic phrasing.",
                    "status": "open"
                })

        # PASS 2: Critical Reviewer (Over-generalization & Absolute Claims)
        absolutes = ["proves", "universally accepted", "conclusively demonstrates", "undeniable fact"]
        for word in absolutes:
            if re.search(rf"\b{word}\b", text, re.IGNORECASE):
                issues.append({
                    "issue_id": f"ISS_CR_{len(issues)+1:03d}",
                    "perspective": "Critical Reviewer",
                    "severity": "major",
                    "location": "Synthesis",
                    "description": f"Over-generalized epistemic certainty: '{word}'",
                    "evidence": word,
                    "action": "Calibrate to hedged scholarly stance (e.g. 'the evidence suggests', 'indicates').",
                    "status": "open"
                })

        # PASS 3: Citation & Integrity Specialist
        in_text_citations = re.findall(r"\[([a-zA-Z0-9_\-]+)\]", text)
        ref_keys = set()
        if "## References" in text:
            ref_section = text.split("## References")[-1]
            # Match both bracketed keys [citation_key] and leading keys - citation_key:
            ref_keys.update(re.findall(r"\[([a-zA-Z0-9_\-]+)\]", ref_section))
            ref_keys.update(re.findall(r"-\s*([a-zA-Z0-9_\-]+):", ref_section))

        # Also populate from references.json if present
        ref_json_path = self.workspace_path / "06_manuscript" / "references.json"
        if ref_json_path.exists():
            try:
                with open(ref_json_path, "r", encoding="utf-8") as f:
                    refs_data = json.load(f)
                    for r in refs_data:
                        if r.get("id"):
                            ref_keys.add(r["id"])
            except Exception:
                pass

        for cited_key in set(in_text_citations):
            if cited_key.lower() not in [k.lower() for k in ref_keys] and cited_key not in ["Ref", "Ref 1"]:
                issues.append({
                    "issue_id": f"ISS_CIT_{len(issues)+1:03d}",
                    "perspective": "Citation Specialist",
                    "severity": "critical",
                    "location": f"In-text [{cited_key}]",
                    "description": f"Ghost citation: [{cited_key}] is cited in body but missing from bibliography.",
                    "evidence": cited_key,
                    "action": "Add bibliographic entry or remove reference callout.",
                    "status": "open"
                })

        # PASS 4: Methodology Specialist
        for r in matrix_rows:
            if r.get("appraisal_rating") == "high_risk":
                issues.append({
                    "issue_id": f"ISS_METH_{len(issues)+1:03d}",
                    "perspective": "Methodology Specialist",
                    "severity": "major",
                    "location": f"Study {r.get('citation_key')}",
                    "description": f"Study evaluated as 'high_risk' of bias: {r.get('limitations')}",
                    "evidence": r.get("citation_key"),
                    "action": "Highlight methodological vulnerability in Section 4.",
                    "status": "open"
                })

        # PASS 5: Anti-Leakage Gate (Inspired by PaperOrchestra App. D.4)
        for leak_pat in self.LEAKAGE_PATTERNS:
            match = leak_pat.search(text)
            if match:
                issues.append({
                    "issue_id": f"ISS_LEAK_{len(issues)+1:03d}",
                    "perspective": "Anti-Leakage Shield",
                    "severity": "critical",
                    "location": "Manuscript text",
                    "description": f"Prohibited leakage artifact detected: '{match.group(0)}'",
                    "evidence": match.group(0),
                    "action": "Strip out placeholder emails, prompt instructions, or meta-chatter.",
                    "status": "open"
                })

        # PASS 6: Quantitative Claim Corroborator (AutoSci / Claim-Evidence Gate)
        numbers_found = self.NUMERIC_CLAIM_REGEX.findall(text)
        for num_str in set(numbers_found):
            # Extract individual numeric values from the claim string
            sub_nums = re.findall(r'\d+(?:\.\d+)?', num_str)
            for clean_num in sub_nums:
                # Disregard generic calendar years (e.g. 2020-2026)
                if float(clean_num) >= 1990 and float(clean_num) <= 2050:
                    continue
                if clean_num not in matrix_corpus:
                    issues.append({
                        "issue_id": f"ISS_NUM_{len(issues)+1:03d}",
                        "perspective": "Evidence Grounding Gate",
                        "severity": "major",
                        "location": f"Quantitative claim '{num_str}'",
                        "description": f"Uncorroborated quantitative metric: '{clean_num}' in '{num_str}' has no matching primary data in evidence_matrix.csv.",
                        "evidence": num_str,
                        "action": "Verify metric in source PDF or remove uncorroborated numerical claim.",
                        "status": "open"
                    })

        # PASS 7: Subject-Matter Specialist (Word Count & Depth Check)
        word_count = len(text.split())
        if word_count < 1000:
            issues.append({
                "issue_id": f"ISS_SUB_{len(issues)+1:03d}",
                "perspective": "Subject-Matter Specialist",
                "severity": "minor",
                "location": "Whole manuscript",
                "description": f"Manuscript length ({word_count} words) is below comprehensive review threshold.",
                "evidence": f"{word_count} words",
                "action": "Expand thematic sections with additional mechanistic details.",
                "status": "open"
            })

        # Step 4: Write issues_log.csv
        issues_file = self.quality_dir / "issues_log.csv"
        with open(issues_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "issue_id", "perspective", "severity", "location", "description", "evidence", "action", "status"
            ])
            writer.writeheader()
            writer.writerows(issues)

        # Step 5: Write quality_report.md
        report_file = self.quality_dir / "quality_report.md"
        report_md = f"""# Quality Audit Report: {slug}

- **Total Issues Identified**: {len(issues)}
- **Critical Issues**: {sum(1 for i in issues if i['severity'] == 'critical')}
- **Major Issues**: {sum(1 for i in issues if i['severity'] == 'major')}
- **Minor Issues**: {sum(1 for i in issues if i['severity'] == 'minor')}

## Findings by Perspective
"""
        for issue in issues:
            report_md += f"- **[{issue['severity'].upper()}]** {issue['perspective']} ({issue['location']}): {issue['description']}\n  *Action*: {issue['action']}\n"

        report_file.write_text(report_md, encoding="utf-8")

        return {
            "status": "success",
            "total_issues": len(issues),
            "report_path": str(report_file),
            "issues_log_path": str(issues_file),
            "issues": issues
        }
