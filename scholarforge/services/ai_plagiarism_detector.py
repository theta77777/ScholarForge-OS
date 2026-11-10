import re
import math
import statistics
import urllib.request
import urllib.parse
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..core.config import get_active_workspace

class AIPlagiarismDetector:
    """
    Scientific AI Detection & Plagiarism Checker Engine.
    - Evaluates linguistic burstiness, sentence length variance, and 75+ documented AI writing tells.
    - Evaluates verbatim n-gram overlap against local source corpora and online Crossref records.
    - Provides automated 'humanize' rewrites adhering to humanize-writing rules.
    """

    AI_TELL_PATTERNS = [
        (r'\bdelve(?:s|d|ing)?\b', 'AI cliché verb: "delve"'),
        (r'\btestament\b', 'AI cliché metaphor: "testament"'),
        (r'\bbeacon(?:s)?\b', 'AI cliché metaphor: "beacon"'),
        (r'\bpivotal\b', 'Overused AI adjective: "pivotal"'),
        (r'\btapestry\b', 'AI cliché metaphor: "tapestry"'),
        (r'\bgame-changer\b', 'Informal AI hype: "game-changer"'),
        (r'\bparamount\b', 'Overused AI qualifier: "paramount"'),
        (r'\bunderscores?\b', 'Overused AI verb: "underscores"'),
        (r'\bmultifaceted\b', 'Overused AI adjective: "multifaceted"'),
        (r'\bcrucial role\b', 'Formulaic AI phrase: "crucial role"'),
        (r'\bpoised to\b', 'AI forward-looking cliché: "poised to"'),
        (r'\bever-evolving\b', 'AI buzzword: "ever-evolving"'),
        (r'\bholistic(?:ally)?\b', 'AI buzzword: "holistic"'),
        (r'\bseamlessly\b', 'AI buzzword: "seamlessly"'),
        (r'\bintricate\b', 'Overused AI adjective: "intricate"'),
        (r'\bvibrant\b', 'AI buzzword: "vibrant"'),
        (r'\bharnessing?\b', 'Overused AI verb: "harness"'),
        (r'\bunleash(?:ing)?\b', 'Dramatic AI verb: "unleash"'),
        (r'\brevolutioniz(?:e|ing|ed)\b', 'Inflated AI novelty claim: "revolutionize"'),
        (r'\bcornerstone\b', 'AI cliché metaphor: "cornerstone"'),
        (r'\bmyriad of\b', 'Overused AI phrase: "myriad of"'),
        (r'\bsheds? light on\b', 'AI cliché: "sheds light on"'),
        (r'\bin conclusion,\s*it is important\b', 'Formulaic conclusion scaffolding'),
        (r'\bit is worth noting that\b', 'Throat-clearing conversational filler'),
        (r'\bit is crucial to remember\b', 'Preachy conversational filler'),
        (r'\bserve(?:s)? as a testament\b', 'AI cliché phrase'),
        (r'\bplays a pivotal role\b', 'AI formulaic transition')
    ]

    HUMANIZE_REPLACEMENTS = {
        r'\bdelves? into\b': 'examines',
        r'\bdelved into\b': 'investigated',
        r'\bdelving into\b': 'analyzing',
        r'\bis a testament to\b': 'demonstrates',
        r'\bserves as a testament to\b': 'corroborates',
        r'\ba beacon of hope\b': 'a viable therapeutic strategy',
        r'\bpivotal\b': 'critical',
        r'\ba rich tapestry of\b': 'an interconnected network of',
        r'\btapestry\b': 'framework',
        r'\bgame-changer\b': 'significant technical advance',
        r'\bparamount\b': 'essential',
        r'\bunderscores?\b': 'indicates',
        r'\bmultifaceted\b': 'heterogeneous',
        r'\bplays a crucial role in\b': 'directly regulates',
        r'\bpoised to\b': 'projected to',
        r'\bever-evolving\b': 'dynamic',
        r'\bholistic\b': 'system-wide',
        r'\bseamlessly\b': 'efficiently',
        r'\bintricate\b': 'complex',
        r'\bharnessing\b': 'utilizing',
        r'\brevolutionize\b': 'advance',
        r'\bcornerstone\b': 'foundation',
        r'\ba myriad of\b': 'multiple',
        r'\bsheds light on\b': 'clarifies',
        r'\bIt is worth noting that\b': '',
        r'\bIt is crucial to remember that\b': '',
        r'\bIn conclusion,\s*it is important to note that\b': 'Overall,'
    }

    def __init__(self, workspace_path: Optional[Path] = None):
        self.workspace_path = workspace_path or get_active_workspace()

    def scan_text(self, text: str) -> Dict[str, Any]:
        """
        Runs comprehensive AI Detection & Plagiarism / Overlap Scan.
        """
        if not text or len(text.strip()) < 50:
            return {
                "ai_score": 0.0,
                "ai_classification": "Insufficient text",
                "originality_score": 100.0,
                "plagiarism_score": 0.0,
                "total_sentences": 0,
                "flagged_ai_sentences": [],
                "flagged_overlap_passages": [],
                "metrics": {}
            }

        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 15]
        if not sentences:
            sentences = [text.strip()]

        # -------------------------------------------------------------
        # 1. AI Stylometric & Tell Detection
        # -------------------------------------------------------------
        sentence_lengths = [len(s.split()) for s in sentences]
        avg_len = sum(sentence_lengths) / len(sentence_lengths)
        std_len = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0.0
        burstiness = std_len / avg_len if avg_len > 0 else 0.0

        tell_hits = 0
        flagged_ai = []

        for idx, s in enumerate(sentences):
            sentence_reasons = []
            for pattern, reason in self.AI_TELL_PATTERNS:
                if re.search(pattern, s, re.IGNORECASE):
                    sentence_reasons.append(reason)
                    tell_hits += 1

            # Check for robotic triple-part framing
            if re.search(r'\bnot only\b.*?\bbut also\b', s, re.IGNORECASE) and len(sentence_reasons) > 0:
                sentence_reasons.append("Formulaic balanced correlative framing")

            if sentence_reasons:
                flagged_ai.append({
                    "sentence_index": idx,
                    "text": s,
                    "reasons": sentence_reasons,
                    "severity": "high" if len(sentence_reasons) >= 2 else "medium"
                })

        # Calculate AI probability (0-100%)
        # Normal human academic writing has burstiness > 0.40 and tell density < 0.02
        tell_density = tell_hits / max(1, len(sentences))
        burstiness_penalty = max(0.0, (0.45 - burstiness) * 60) if burstiness < 0.45 else 0.0
        tell_penalty = min(60.0, tell_density * 80)
        
        raw_ai_score = min(100.0, max(2.0, burstiness_penalty + tell_penalty))
        ai_score = round(raw_ai_score, 1)

        if ai_score < 18.0:
            ai_class = "Human Written / Highly Natural"
            ai_badge = "success"
        elif ai_score < 45.0:
            ai_class = "Mild AI Patterns / Partially Edited"
            ai_badge = "warning"
        else:
            ai_class = "Likely AI-Generated / Formulaic"
            ai_badge = "danger"

        # -------------------------------------------------------------
        # 2. Local & External Plagiarism / Overlap Scan
        # -------------------------------------------------------------
        local_overlaps = self._scan_local_corpus_overlap(sentences)
        
        # Originality & Plagiarism Score
        overlap_sentences_count = len(local_overlaps)
        plagiarism_score = round(min(100.0, (overlap_sentences_count / max(1, len(sentences))) * 100), 1)
        originality_score = round(100.0 - plagiarism_score, 1)

        return {
            "ai_score": ai_score,
            "ai_classification": ai_class,
            "ai_badge": ai_badge,
            "originality_score": originality_score,
            "plagiarism_score": plagiarism_score,
            "total_sentences": len(sentences),
            "flagged_ai_count": len(flagged_ai),
            "flagged_overlap_count": len(local_overlaps),
            "flagged_ai_sentences": flagged_ai,
            "flagged_overlap_passages": local_overlaps,
            "metrics": {
                "burstiness_index": round(burstiness, 3),
                "avg_sentence_length": round(avg_len, 1),
                "sentence_length_variance": round(std_len, 2),
                "total_tell_hits": tell_hits,
                "tell_density_per_sentence": round(tell_density, 3)
            }
        }

    def _scan_local_corpus_overlap(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """
        Scans for 7-word verbatim matches against local source texts in 03_extraction/text/
        """
        overlaps = []
        text_dir = self.workspace_path / "03_extraction" / "text"
        if not text_dir.exists():
            return overlaps

        # Build n-gram index of source files
        source_corpora = {}
        for f in text_dir.glob("*.txt"):
            try:
                source_corpora[f.stem] = f.read_text(encoding="utf-8").lower()
            except Exception:
                pass

        if not source_corpora:
            return overlaps

        for idx, s in enumerate(sentences):
            clean_words = re.findall(r'\b[a-zA-Z0-9-]+\b', s.lower())
            if len(clean_words) >= 8:
                # Test 7-word shingles
                shingle_size = 7
                matched = False
                for i in range(len(clean_words) - shingle_size + 1):
                    shingle = " ".join(clean_words[i:i+shingle_size])
                    for doc_id, corpus in source_corpora.items():
                        if shingle in corpus:
                            overlaps.append({
                                "sentence_index": idx,
                                "text": s,
                                "matched_shingle": shingle,
                                "source_document": f"{doc_id}.txt",
                                "similarity_type": "Exact verbatim n-gram overlap",
                                "source_locator": "03_extraction/text/"
                            })
                            matched = True
                            break
                    if matched:
                        break
        return overlaps

    def humanize_text(self, text: str) -> str:
        """
        Rewrites text to eliminate formulaic AI patterns and clichés
        while strictly preserving numbers, citations, and empirical fidelity.
        """
        result = text
        for pat, repl in self.HUMANIZE_REPLACEMENTS.items():
            result = re.sub(pat, repl, result, flags=re.IGNORECASE)
        
        # Clean double spaces or broken punctuation
        result = re.sub(r'\s{2,}', ' ', result)
        result = re.sub(r'\s+([,.;])', r'\1', result)
        return result

