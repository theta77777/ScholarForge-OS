import re
from typing import Dict, Any, List, Optional
from ..core.config import get_settings

class JEVDecisionEngine:
    """
    JEV (Judgment, Evaluation & Vectoring) Decision Engine:
    Intelligently routes, selects, and configures the optimal combination of cloud APIs
    from the curated 122-API catalog based on:
    - Vector 1: Research Domain (Biomedical, Materials, CS/AI, Pharma, Chemistry, Social)
    - Vector 2: User Execution Profile (Turbo Speed, Gold PRISMA, Omics, Materials, Audit)
    - Vector 3: Credential State (Free Open Defaults vs BYOK active keys)
    """

    PROFILES = {
        "auto": {
            "name": "Intelligent Auto-Select (JEV)",
            "description": "Dynamically inspects the review paper title and research domain to assemble the best API combination.",
            "target_time": "Varies by scope",
            "tier": "Free Defaults"
        },
        "turbo": {
            "name": "Turbo / Lightning Speed (< 2 Mins)",
            "description": "Ultra-fast synthesis using Groq LPU inference, OpenAlex, Crossref, Unpaywall, and QuickChart.",
            "target_time": "< 120 seconds",
            "tier": "100% Free Cloud"
        },
        "gold_prisma": {
            "name": "Gold-Standard PRISMA 2020 Systematic Review",
            "description": "Comprehensive multi-database discovery (PubMed, Crossref, Europe PMC), ClinicalTrials.gov, RobotReviewer RoB, and Kroki PRISMA flowchart.",
            "target_time": "5-8 minutes",
            "tier": "100% Free Cloud"
        },
        "omics": {
            "name": "Deep Omics, Proteomics & Molecular Biology",
            "description": "Integrates UniProt, RCSB PDB, AlphaFold DB, STRING PPI networks, Reactome pathways, and Ensembl.",
            "target_time": "4-6 minutes",
            "tier": "100% Free Cloud"
        },
        "materials": {
            "name": "Materials Science, Batteries & Physical Chemistry",
            "description": "Integrates Materials Project, OQMD, Crystallography Open Database (COD), ChemRxiv, and ChemDoodle.",
            "target_time": "3-5 minutes",
            "tier": "100% Free Cloud"
        },
        "cs_ai": {
            "name": "Computer Science, AI & Engineering",
            "description": "Leverages arXiv HTML5/PDF, DBLP, Semantic Scholar TLDRs, Cerebras Cloud, and GitHub Models.",
            "target_time": "2-4 minutes",
            "tier": "100% Free Cloud"
        },
        "pharma": {
            "name": "Pharmacology, Drug Repurposing & Safety",
            "description": "Integrates PubChem, ChEMBL, OpenFDA adverse events, DailyMed, RxNav, and PharmGKB.",
            "target_time": "4-6 minutes",
            "tier": "100% Free Cloud"
        },
        "audit": {
            "name": "Integrity, Retraction & Anti-Paper-Mill Audit",
            "description": "Screening via Retraction Watch, PubPeer, Problematic Paper Screener (PPS), RoBERTa AI Detector, and Crossref Shingles.",
            "target_time": "2-3 minutes",
            "tier": "100% Free Cloud"
        },
        "manual": {
            "name": "Direct Manual Mode (JEV OFF)",
            "description": "Completely disables JEV autonomous routing. Directly executes using your manually selected APIs and custom Gateway configurations.",
            "target_time": "Deterministic / Manual",
            "tier": "Full User Control"
        }
    }

    DOMAIN_KEYWORDS = {
        "gaming_strategy": [
            "game", "gaming", "play", "player", "players", "strategy", "strategies",
            "match", "matches", "tournament", "esports", "minimax", "game theory",
            "team building", "type matchup", "battle", "battles", "video game", "gameplay", "multi-agent"
        ],
        "materials": [
            "battery", "batteries", "solid-state", "electrolyte", "cathode", "anode",
            "perovskite", "graphene", "alloy", "catalyst", "crystal", "semiconductor",
            "dielectric", "photovoltaic", "metallurgy", "polymer", "ceramic", "interfacial"
        ],
        "cs_ai": [
            "deep learning", "neural", "transformer", "llm", "large language", "machine learning",
            "reinforcement learning", "computer vision", "nlp", "quantum computing", "algorithm",
            "diffusion model", "generative ai", "robotics", "compiler", "blockchain"
        ],
        "pharma": [
            "drug", "pharmacology", "pharmacokinetics", "fda", "inhibitor", "adverse event",
            "dosage", "therapeutic", "chembl", "pubchem", "target", "toxicity", "pharmacogenomics",
            "repurposing", "small molecule", "bioavailability"
        ],
        "omics": [
            "crispr", "mrna", "gene", "protein", "proteomics", "genomics", "uniprot", "pdb",
            "alphafold", "structure", "amino acid", "sequencing", "rna-seq", "transcription",
            "pathway", "mutation", "cancer", "antibody", "tropism"
        ],
        "biomedical": [
            "clinical", "patient", "trial", "disease", "therapy", "medical", "hospital",
            "cardiology", "oncology", "neurology", "health", "infection", "vaccine", "biomarker"
        ]
    }

    @classmethod
    def classify_domain(cls, title: str, description: str = "") -> str:
        """Classifies a research title into one of the core domains."""
        text = f"{title} {description}".lower()
        
        scores = {d: 0 for d in cls.DOMAIN_KEYWORDS}
        for domain, keywords in cls.DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', text):
                    scores[domain] += 2
                elif kw in text:
                    scores[domain] += 1
        
        best_domain = max(scores, key=scores.get)
        if scores[best_domain] > 0:
            return best_domain
        return "general"

    @classmethod
    def resolve_active_apis(cls, title: str, description: str = "") -> Dict[str, Any]:
        """
        Determines the exact active API bundle for the current project.
        Evaluates JEV profile setting, domain classification, and user manual overrides.
        """
        cfg = get_settings()
        is_jev_enabled = getattr(cfg, "enable_jev", True)
        profile_key = getattr(cfg, "jev_profile", "auto")
        domain = cls.classify_domain(title, description)

        if not is_jev_enabled or profile_key == "manual":
            resolved_profile = "manual"
            domain = "manual"
        elif profile_key == "auto":
            if domain == "materials":
                resolved_profile = "materials"
            elif domain in ["cs_ai", "gaming_strategy"]:
                resolved_profile = "cs_ai"
            elif domain == "pharma":
                resolved_profile = "pharma"
            elif domain == "omics":
                resolved_profile = "omics"
            else:
                resolved_profile = "gold_prisma"
        else:
            resolved_profile = profile_key

        # Define default API rosters per resolved profile
        rosters = {
            "manual": [
                {"id": "openalex", "name": "OpenAlex REST API", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "crossref", "name": "Crossref REST API", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "pubmed", "name": "PubMed / NCBI E-Utilities", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "unpaywall", "name": "Unpaywall Legal PDF Locator", "category": "OA Full-Text", "status": "active", "tier": "Free Public"},
                {"id": "quickchart", "name": "QuickChart 300 DPI Vector Plots", "category": "Visuals", "status": "active", "tier": "Free Public"},
                {"id": "kroki", "name": "Kroki Multi-Diagram Engine", "category": "Visuals", "status": "active", "tier": "Free Public"},
                {"id": "retractionwatch", "name": "Retraction Watch Screening DB", "category": "Integrity", "status": "active", "tier": "Free Public"}
            ],
            "turbo": [
                {"id": "openalex", "name": "OpenAlex REST API", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "crossref", "name": "Crossref REST API", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "unpaywall", "name": "Unpaywall OA Resolver", "category": "OA Full-Text", "status": "active", "tier": "Free Public"},
                {"id": "groq", "name": "Groq Cloud LPU Inference", "category": "LLM Inference", "status": "active", "tier": "Free Key"},
                {"id": "quickchart", "name": "QuickChart 300 DPI Vector Plots", "category": "Visuals", "status": "active", "tier": "Free Public"},
                {"id": "languagetool", "name": "LanguageTool Grammar Engine", "category": "Copyediting", "status": "active", "tier": "Free Public"}
            ],
            "gold_prisma": [
                {"id": "pubmed", "name": "PubMed / NCBI E-Utilities", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "crossref", "name": "Crossref Works API", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "openalex", "name": "OpenAlex Global Scholarly Graph", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "europepmc", "name": "Europe PMC BioC & Full-Text", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "clinicaltrials", "name": "ClinicalTrials.gov API v2", "category": "Clinical Trials", "status": "active", "tier": "Free Public"},
                {"id": "robotreviewer", "name": "RobotReviewer Cochrane RoB", "category": "Synthesis", "status": "active", "tier": "Free Academic"},
                {"id": "unpaywall", "name": "Unpaywall Legal PDF Locator", "category": "OA Full-Text", "status": "active", "tier": "Free Public"},
                {"id": "opencitations", "name": "OpenCitations COCI Citation Graph", "category": "Citations", "status": "active", "tier": "Free Public"},
                {"id": "kroki", "name": "Kroki PRISMA 2020 Flowchart Engine", "category": "Visuals", "status": "active", "tier": "Free Public"},
                {"id": "retractionwatch", "name": "Retraction Watch Screening DB", "category": "Integrity", "status": "active", "tier": "Free Public"},
                {"id": "zenodo", "name": "Zenodo Evidence Data Archiving", "category": "Archival", "status": "active", "tier": "Free Public"}
            ],
            "omics": [
                {"id": "pubmed", "name": "PubMed Life Sciences Index", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "uniprot", "name": "UniProt Knowledgebase REST API", "category": "Proteomics", "status": "active", "tier": "Free Public"},
                {"id": "rcsb_pdb", "name": "RCSB Protein Data Bank 3D API", "category": "Structural Biology", "status": "active", "tier": "Free Public"},
                {"id": "alphafold_db", "name": "AlphaFold Structure DB API", "category": "Structural Biology", "status": "active", "tier": "Free Public"},
                {"id": "string_db", "name": "STRING Protein Interaction Networks", "category": "Pathways", "status": "active", "tier": "Free Public"},
                {"id": "reactome", "name": "Reactome Pathway Content Service", "category": "Pathways", "status": "active", "tier": "Free Public"},
                {"id": "ensembl", "name": "Ensembl Genomic Coordinates API", "category": "Genomics", "status": "active", "tier": "Free Public"},
                {"id": "quickgo", "name": "QuickGO Gene Ontology Annotations", "category": "Ontology", "status": "active", "tier": "Free Public"},
                {"id": "quickchart", "name": "QuickChart Multi-Study Volcano Plots", "category": "Visuals", "status": "active", "tier": "Free Public"}
            ],
            "materials": [
                {"id": "crossref", "name": "Crossref Physical Sciences Search", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "arxiv", "name": "arXiv Condensed Matter & Physics API", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "chemrxiv", "name": "ChemRxiv Preprint Gateway", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "materials_project", "name": "Materials Project NextGen DFT API", "category": "Materials", "status": "active", "tier": "Free Key"},
                {"id": "oqmd", "name": "Open Quantum Materials DB (OQMD)", "category": "Materials", "status": "active", "tier": "Free Public"},
                {"id": "cod", "name": "Crystallography Open Database (COD)", "category": "Crystallography", "status": "active", "tier": "Free Public"},
                {"id": "chemdoodle", "name": "ChemDoodle Reaction Formula Engine", "category": "Visuals", "status": "active", "tier": "Free Public"},
                {"id": "quickchart", "name": "QuickChart Materials Kinetic & Degradation Curves", "category": "Visuals", "status": "active", "tier": "Free Public"}
            ],
            "cs_ai": [
                {"id": "arxiv", "name": "arXiv CS & Machine Learning API", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "dblp", "name": "DBLP Computer Science Bibliography", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "openalex", "name": "OpenAlex AI Concept Hierarchy", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "semantic_scholar", "name": "Semantic Scholar TLDR & Graph API", "category": "Summarization", "status": "active", "tier": "Free Public"},
                {"id": "cerebras", "name": "Cerebras Ultra-Fast Cloud Inference", "category": "LLM Inference", "status": "active", "tier": "Free Key"},
                {"id": "github_models", "name": "GitHub Models Serverless Azure API", "category": "LLM Inference", "status": "active", "tier": "Free with GitHub"},
                {"id": "kroki", "name": "Kroki Architecture Block Diagrams", "category": "Visuals", "status": "active", "tier": "Free Public"}
            ],
            "pharma": [
                {"id": "pubmed", "name": "PubMed Pharmacotherapy Search", "category": "Discovery", "status": "active", "tier": "Free Public"},
                {"id": "pubchem", "name": "PubChem PUG-REST Chemical Database", "category": "Chemistry", "status": "active", "tier": "Free Public"},
                {"id": "chembl", "name": "ChEMBL Bioactive Molecules API", "category": "Bioactivity", "status": "active", "tier": "Free Public"},
                {"id": "openfda", "name": "OpenFDA Adverse Drug Events (FAERS)", "category": "Regulatory", "status": "active", "tier": "Free Public"},
                {"id": "dailymed", "name": "DailyMed FDA Drug Labels (SPL)", "category": "Regulatory", "status": "active", "tier": "Free Public"},
                {"id": "rxnav", "name": "NIH RxNav Drug Interaction API", "category": "Pharmacology", "status": "active", "tier": "Free Public"},
                {"id": "dgidb", "name": "Drug-Gene Interaction Database (DGIdb)", "category": "Targeting", "status": "active", "tier": "Free Public"},
                {"id": "pharmgkb", "name": "PharmGKB Pharmacogenomics API", "category": "Pharmacogenomics", "status": "active", "tier": "Free Key"}
            ],
            "audit": [
                {"id": "retractionwatch", "name": "Retraction Watch Database", "category": "Retraction", "status": "active", "tier": "Free Public"},
                {"id": "pubpeer", "name": "PubPeer Post-Publication Comments", "category": "Integrity", "status": "active", "tier": "Free Public"},
                {"id": "pps", "name": "Problematic Paper Screener (Tortured Phrases)", "category": "Fraud Detection", "status": "active", "tier": "Free Academic"},
                {"id": "roberta_cloud", "name": "RoBERTa AI Detector (Hugging Face Cloud)", "category": "AI Detection", "status": "active", "tier": "Free Public"},
                {"id": "crossref_shingles", "name": "Crossref Shingle Verifier (7-Word Verbatim)", "category": "Plagiarism", "status": "active", "tier": "Free Built-in"},
                {"id": "sapling_byok", "name": "Sapling Content Detector (BYOK)", "category": "AI Detection", "status": "optional", "tier": "BYOK"},
                {"id": "copyleaks_byok", "name": "CopyLeaks Plagiarism Engine (BYOK)", "category": "Plagiarism", "status": "optional", "tier": "BYOK"}
            ]
        }

        active_list = rosters.get(resolved_profile, rosters["gold_prisma"])
        return {
            "selected_profile": resolved_profile,
            "profile_meta": cls.PROFILES.get(resolved_profile, cls.PROFILES["gold_prisma"]),
            "classified_domain": domain,
            "auto_selected": (profile_key == "auto"),
            "total_active_apis": len(active_list),
            "apis": active_list
        }

