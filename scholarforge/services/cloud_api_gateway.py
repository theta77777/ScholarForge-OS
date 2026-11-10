import asyncio
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import httpx

from ..core.agent_logs import AgentLogger
from ..core.config import get_settings, PROJECT_ROOT

CONFIG_DIR = PROJECT_ROOT / "config"
OVERRIDES_FILE = CONFIG_DIR / "api_overrides.json"
ALERTS_FILE = CONFIG_DIR / "gateway_alerts.json"

class AsyncTokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = max(0.1, rate)
        self.capacity = max(1.0, capacity)
        self.tokens = capacity
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return

                needed = 1.0 - self.tokens
                wait_time = max(0.01, needed / self.rate)
                await asyncio.sleep(min(wait_time, 2.0))

class CloudApiGateway:
    """
    Central Gateway & Circuit Breaker for ScholarForge Cloud APIs.
    - Manages live endpoints, rate limiters, credential vaults, and circuit breaker health.
    - Automatic fallback cascading on rate limits (429), timeouts, or missing auth (401/403).
    - Emits actionable user alerts with 1-click links to developer credential fixers.
    - Full developer-grade customization: overrides, real-time testing probes, and factory revert.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CloudApiGateway, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.limiters: Dict[str, AsyncTokenBucket] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.overrides: Dict[str, Any] = self._load_overrides()
        self.registry = self._init_registry()

    def _load_overrides(self) -> Dict[str, Any]:
        if OVERRIDES_FILE.exists():
            try:
                with open(OVERRIDES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Gateway] Failed loading overrides: {e}")
        return {}

    def _save_overrides(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(OVERRIDES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.overrides, f, indent=2)

    def _init_registry(self) -> Dict[str, Dict[str, Any]]:
        # Catalog of primary cloud APIs with default parameters
        raw = {
            # --- CLUSTER 1: DISCOVERY ---
            "openalex": {
                "name": "OpenAlex REST API",
                "cluster": "Discovery",
                "endpoint": "https://api.openalex.org/works",
                "rate_rps": 10.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public (100k/day)",
                "key_vault_field": None,
                "fallback_id": "crossref",
                "probe_url": "https://api.openalex.org/works?per_page=1"
            },
            "crossref": {
                "name": "Crossref Works API",
                "cluster": "Discovery",
                "endpoint": "https://api.crossref.org/works",
                "rate_rps": 4.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "openalex",
                "probe_url": "https://api.crossref.org/works?rows=1"
            },
            "pubmed": {
                "name": "PubMed / NCBI E-Utilities",
                "cluster": "Discovery",
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                "rate_rps": 3.0,
                "timeout_sec": 10.0,
                "retries": 2,
                "tier": "Free Public (3-10 req/s)",
                "key_vault_field": "ncbi_api_key",
                "fallback_id": "europepmc",
                "probe_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=science&retmode=json&retmax=1"
            },
            "semanticscholar": {
                "name": "Semantic Scholar Graph API",
                "cluster": "Discovery",
                "endpoint": "https://api.semanticscholar.org/graph/v1/paper/search",
                "rate_rps": 1.0,
                "timeout_sec": 6.0,
                "retries": 1,
                "tier": "Free Tier / BYOK",
                "key_vault_field": None,
                "fallback_id": "openalex",
                "probe_url": "https://api.semanticscholar.org/graph/v1/paper/search?query=biology&limit=1"
            },
            "europepmc": {
                "name": "Europe PMC REST API",
                "cluster": "Discovery",
                "endpoint": "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                "rate_rps": 5.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "openalex",
                "probe_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=gene&format=json&pageSize=1"
            },
            "arxiv": {
                "name": "arXiv Query API",
                "cluster": "Discovery",
                "endpoint": "https://export.arxiv.org/api/query",
                "rate_rps": 0.33,
                "timeout_sec": 10.0,
                "retries": 2,
                "tier": "Free Public (1 req/3s)",
                "key_vault_field": None,
                "fallback_id": "openalex",
                "probe_url": "https://export.arxiv.org/api/query?search_query=all:electron&max_results=1"
            },

            # --- CLUSTER 2: OA FULL-TEXT RESOLUTION ---
            "unpaywall": {
                "name": "Unpaywall Legal OA Resolver",
                "cluster": "OA Full-Text",
                "endpoint": "https://api.unpaywall.org/v2",
                "rate_rps": 5.0,
                "timeout_sec": 6.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "openaccessbutton",
                "probe_url": "https://api.unpaywall.org/v2/10.1038/nature12373?email=researcher@scholarforge.org"
            },
            "openaccessbutton": {
                "name": "Open Access Button API",
                "cluster": "OA Full-Text",
                "endpoint": "https://api.openaccessbutton.org/find",
                "rate_rps": 2.0,
                "timeout_sec": 6.0,
                "retries": 1,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "jinareader",
                "probe_url": "https://api.openaccessbutton.org/find?id=10.1038/nature12373"
            },
            "jinareader": {
                "name": "Jina Reader Cloud Scraper",
                "cluster": "OA Full-Text",
                "endpoint": "https://r.jina.ai",
                "rate_rps": 3.0,
                "timeout_sec": 12.0,
                "retries": 1,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "unpaywall",
                "probe_url": "https://r.jina.ai/https://example.com"
            },

            # --- CLUSTER 3: CLINICAL TRIALS & SYNTHESIS ---
            "clinicaltrials": {
                "name": "ClinicalTrials.gov API v2",
                "cluster": "Clinical Trials",
                "endpoint": "https://clinicaltrials.gov/api/v2/studies",
                "rate_rps": 5.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "pubmed",
                "probe_url": "https://clinicaltrials.gov/api/v2/studies?pageSize=1"
            },
            "robotreviewer": {
                "name": "RobotReviewer Cochrane RoB",
                "cluster": "Clinical Trials",
                "endpoint": "https://robotreviewer.vortext.systems/api",
                "rate_rps": 1.0,
                "timeout_sec": 15.0,
                "retries": 1,
                "tier": "Free Academic",
                "key_vault_field": None,
                "fallback_id": None,
                "probe_url": "https://robotreviewer.vortext.systems/api"
            },

            # --- CLUSTER 4: PHARMA & DRUGS ---
            "pubchem": {
                "name": "PubChem PUG-REST",
                "cluster": "Pharma & Chem",
                "endpoint": "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
                "rate_rps": 5.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public (5 req/s)",
                "key_vault_field": None,
                "fallback_id": "chembl",
                "probe_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aspirin/property/MolecularWeight/JSON"
            },
            "chembl": {
                "name": "ChEMBL Bioactivity REST",
                "cluster": "Pharma & Chem",
                "endpoint": "https://www.ebi.ac.uk/chembl/api/data",
                "rate_rps": 4.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "pubchem",
                "probe_url": "https://www.ebi.ac.uk/chembl/api/data/target.json?limit=1"
            },
            "openfda": {
                "name": "OpenFDA Adverse Drug Events",
                "cluster": "Pharma & Chem",
                "endpoint": "https://api.fda.gov/drug/event.json",
                "rate_rps": 4.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public (240/min)",
                "key_vault_field": None,
                "fallback_id": None,
                "probe_url": "https://api.fda.gov/drug/event.json?limit=1"
            },

            # --- CLUSTER 5: OMICS & STRUCTURAL BIOLOGY ---
            "uniprot": {
                "name": "UniProt Knowledgebase REST",
                "cluster": "Omics & Structures",
                "endpoint": "https://rest.uniprot.org/uniprotkb",
                "rate_rps": 5.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": None,
                "probe_url": "https://rest.uniprot.org/uniprotkb/P04637.json"
            },
            "rcsb_pdb": {
                "name": "RCSB Protein Data Bank 3D",
                "cluster": "Omics & Structures",
                "endpoint": "https://data.rcsb.org/rest/v1/core/entry",
                "rate_rps": 5.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "alphafold",
                "probe_url": "https://data.rcsb.org/rest/v1/core/entry/4HHB"
            },
            "alphafold": {
                "name": "AlphaFold Structure DB",
                "cluster": "Omics & Structures",
                "endpoint": "https://alphafold.ebi.ac.uk/api/prediction",
                "rate_rps": 4.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "rcsb_pdb",
                "probe_url": "https://alphafold.ebi.ac.uk/api/prediction/P04637"
            },
            "string_db": {
                "name": "STRING Protein Interaction Networks",
                "cluster": "Omics & Structures",
                "endpoint": "https://string-db.org/api/json/network",
                "rate_rps": 3.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": None,
                "probe_url": "https://string-db.org/api/json/network?identifiers=TP53&species=9606"
            },
            "reactome": {
                "name": "Reactome Pathway Service",
                "cluster": "Omics & Structures",
                "endpoint": "https://reactome.org/AnalysisService",
                "rate_rps": 3.0,
                "timeout_sec": 10.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": None,
                "probe_url": "https://reactome.org/AnalysisService/token/status"
            },

            # --- CLUSTER 6: MATERIALS SCIENCE ---
            "materials_project": {
                "name": "Materials Project NextGen",
                "cluster": "Materials",
                "endpoint": "https://api.materialsproject.org",
                "rate_rps": 2.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Key / BYOK",
                "key_vault_field": "materials_project_key",
                "fallback_id": "oqmd",
                "probe_url": "https://api.materialsproject.org/materials/summary/?_limit=1"
            },
            "oqmd": {
                "name": "Open Quantum Materials DB",
                "cluster": "Materials",
                "endpoint": "http://oqmd.org/oqmdapi/formationenergy",
                "rate_rps": 2.0,
                "timeout_sec": 10.0,
                "retries": 1,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "cod",
                "probe_url": "http://oqmd.org/oqmdapi/formationenergy?limit=1&format=json"
            },
            "cod": {
                "name": "Crystallography Open DB (COD)",
                "cluster": "Materials",
                "endpoint": "https://www.crystallography.net/cod/result",
                "rate_rps": 3.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": None,
                "probe_url": "https://www.crystallography.net/cod/result?format=json&limit=1"
            },

            # --- CLUSTER 7: INTEGRITY & RETRACTION ---
            "retractionwatch": {
                "name": "Retraction Watch Database",
                "cluster": "Integrity & Retraction",
                "endpoint": "https://api.labs.crossref.org/data/retraction-watch",
                "rate_rps": 4.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "openalex",
                "probe_url": "https://api.labs.crossref.org/data/retraction-watch?rows=1"
            },
            "pubpeer": {
                "name": "PubPeer Public API",
                "cluster": "Integrity & Retraction",
                "endpoint": "https://pubpeer.com/v3/publications",
                "rate_rps": 2.0,
                "timeout_sec": 6.0,
                "retries": 1,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": None,
                "probe_url": "https://pubpeer.com/v3/publications/10.1038/nature12373"
            },
            "opencitations": {
                "name": "OpenCitations (COCI) Index",
                "cluster": "Integrity & Retraction",
                "endpoint": "https://opencitations.net/index/coci/api/v1/citations",
                "rate_rps": 3.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "openalex",
                "probe_url": "https://opencitations.net/index/coci/api/v1/citations/10.1038/nature12373"
            },
            "scite": {
                "name": "Scite.ai Smart Citations",
                "cluster": "Integrity & Retraction",
                "endpoint": "https://api.scite.ai/tallies",
                "rate_rps": 2.0,
                "timeout_sec": 6.0,
                "retries": 1,
                "tier": "BYOK / Paid",
                "key_vault_field": "scite_api_key",
                "fallback_id": "opencitations",
                "probe_url": "https://api.scite.ai/tallies/10.1038/nature12373"
            },

            # --- CLUSTER 8: LLM INFERENCE ---
            "groq": {
                "name": "Groq Cloud LPU Inference",
                "cluster": "LLM Inference",
                "endpoint": "https://api.groq.com/openai/v1/chat/completions",
                "rate_rps": 5.0,
                "timeout_sec": 10.0,
                "retries": 2,
                "tier": "Free Key / BYOK",
                "key_vault_field": "groq_api_key",
                "fallback_id": "gemini",
                "probe_url": "https://api.groq.com/openai/v1/models"
            },
            "openrouter": {
                "name": "OpenRouter Free Pool (:free)",
                "cluster": "LLM Inference",
                "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                "rate_rps": 3.0,
                "timeout_sec": 15.0,
                "retries": 1,
                "tier": "Free Key / BYOK",
                "key_vault_field": "openrouter_api_key",
                "fallback_id": "gemini",
                "probe_url": "https://openrouter.ai/api/v1/models"
            },

            # --- CLUSTER 9: DETECTION ---
            "copyleaks": {
                "name": "CopyLeaks Plagiarism Engine",
                "cluster": "Detection",
                "endpoint": "https://api.copyleaks.com/v3",
                "rate_rps": 1.0,
                "timeout_sec": 10.0,
                "retries": 1,
                "tier": "BYOK / Paid",
                "key_vault_field": "copyleaks_api_key",
                "fallback_id": "roberta_cloud",
                "probe_url": "https://api.copyleaks.com/v3/status"
            },

            # --- CLUSTER 11: VISUALS ---
            "quickchart": {
                "name": "QuickChart 300 DPI Vector Plots",
                "cluster": "Visuals",
                "endpoint": "https://quickchart.io/chart",
                "rate_rps": 10.0,
                "timeout_sec": 6.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "kroki",
                "probe_url": "https://quickchart.io/chart?c={type:'bar',data:{labels:['Q1'],datasets:[{data:[1]}]}}&width=100&height=50"
            },
            "kroki": {
                "name": "Kroki Multi-Diagram Engine",
                "cluster": "Visuals",
                "endpoint": "https://kroki.io",
                "rate_rps": 8.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": "quickchart",
                "probe_url": "https://kroki.io/mermaid/svg/eNpLzs8tyM9LzSvRLcvPL0pNzQEAL_8Hcw=="
            },
            "chemdoodle": {
                "name": "ChemDoodle Reaction Formulas",
                "cluster": "Visuals",
                "endpoint": "https://web.chemdoodle.com/api",
                "rate_rps": 5.0,
                "timeout_sec": 8.0,
                "retries": 2,
                "tier": "Free Public",
                "key_vault_field": None,
                "fallback_id": None,
                "probe_url": "https://web.chemdoodle.com"
            },

            # --- CLUSTER 12: ARCHIVAL ---
            "zenodo": {
                "name": "Zenodo Evidence Archiving",
                "cluster": "Archival",
                "endpoint": "https://zenodo.org/api/deposit/depositions",
                "rate_rps": 2.0,
                "timeout_sec": 10.0,
                "retries": 1,
                "tier": "Free Token / BYOK",
                "key_vault_field": "zenodo_token",
                "fallback_id": None,
                "probe_url": "https://zenodo.org/api/deposit/depositions"
            }
        }

        # Apply persistent overrides and initialize token buckets
        registry = {}
        for api_id, meta in raw.items():
            over = self.overrides.get(api_id, {})
            merged = {
                "id": api_id,
                "name": over.get("name", meta["name"]),
                "cluster": meta["cluster"],
                "endpoint": over.get("endpoint", meta["endpoint"]),
                "rate_rps": float(over.get("rate_rps", meta["rate_rps"])),
                "timeout_sec": float(over.get("timeout_sec", meta["timeout_sec"])),
                "retries": int(over.get("retries", meta["retries"])),
                "enabled": over.get("enabled", True),
                "tier": meta["tier"],
                "key_vault_field": meta["key_vault_field"],
                "custom_key": over.get("custom_key", ""),
                "fallback_id": over.get("fallback_id", meta.get("fallback_id")),
                "probe_url": meta.get("probe_url"),
                "status": "Operational",
                "last_latency_ms": 0.0,
                "last_error": None,
                "error_count": 0,
                "total_requests": 0
            }
            registry[api_id] = merged
            self.limiters[api_id] = AsyncTokenBucket(rate=merged["rate_rps"], capacity=merged["rate_rps"] * 2.0)
        return registry

    def get_api_meta(self, api_id: str) -> Optional[Dict[str, Any]]:
        return self.registry.get(api_id)

    def list_all_apis(self) -> List[Dict[str, Any]]:
        # Sync with BYOK vault in config
        cfg = get_settings()
        vault = cfg.api_vault.model_dump()
        result = []
        for api_id, meta in self.registry.items():
            item = dict(meta)
            field = meta.get("key_vault_field")
            has_vault_key = bool(vault.get(field)) if field else False
            has_custom_key = bool(meta.get("custom_key"))
            item["has_credential"] = has_vault_key or has_custom_key or ("Free Public" in meta["tier"])
            result.append(item)
        return result

    def get_effective_key(self, api_id: str) -> str:
        meta = self.registry.get(api_id, {})
        if meta.get("custom_key"):
            return meta["custom_key"]
        field = meta.get("key_vault_field")
        if field:
            cfg = get_settings()
            return getattr(cfg.api_vault, field, "")
        return ""

    async def acquire_slot(self, api_id: str):
        limiter = self.limiters.get(api_id)
        if limiter:
            await limiter.acquire()

    def update_api_config(self, api_id: str, updates: Dict[str, Any]):
        if api_id not in self.registry:
            return
        meta = self.registry[api_id]
        if "endpoint" in updates:
            meta["endpoint"] = updates["endpoint"]
        if "rate_rps" in updates:
            val = max(0.1, float(updates["rate_rps"]))
            meta["rate_rps"] = val
            self.limiters[api_id] = AsyncTokenBucket(rate=val, capacity=val * 2.0)
        if "timeout_sec" in updates:
            meta["timeout_sec"] = max(1.0, float(updates["timeout_sec"]))
        if "retries" in updates:
            meta["retries"] = max(0, int(updates["retries"]))
        if "enabled" in updates:
            meta["enabled"] = bool(updates["enabled"])
        if "custom_key" in updates:
            meta["custom_key"] = updates["custom_key"].strip()
        if "fallback_id" in updates:
            meta["fallback_id"] = updates["fallback_id"]

        self.overrides[api_id] = {
            "endpoint": meta["endpoint"],
            "rate_rps": meta["rate_rps"],
            "timeout_sec": meta["timeout_sec"],
            "retries": meta["retries"],
            "enabled": meta["enabled"],
            "custom_key": meta["custom_key"],
            "fallback_id": meta["fallback_id"]
        }
        self._save_overrides()

    def reset_api_defaults(self, api_id: Optional[str] = None):
        if api_id and api_id in self.overrides:
            del self.overrides[api_id]
        elif not api_id:
            self.overrides = {}
        self._save_overrides()
        self.registry = self._init_registry()

    def _load_alerts(self) -> List[Dict[str, Any]]:
        if ALERTS_FILE.exists():
            try:
                with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_alerts(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(ALERTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.alerts, f, indent=2)
        except Exception:
            pass

    def add_alert(self, api_id: str, error_type: str, status_code: Optional[int], message: str, recommendation: str, fallback_engaged: Optional[str] = None):
        meta = self.registry.get(api_id, {"name": api_id})
        alert = {
            "id": f"alert_{int(time.time() * 1000)}",
            "api_id": api_id,
            "api_name": meta.get("name", api_id),
            "cluster": meta.get("cluster", "Unknown"),
            "error_type": error_type,
            "status_code": status_code,
            "message": message,
            "recommendation": recommendation,
            "fallback_engaged": fallback_engaged,
            "timestamp": time.strftime("%H:%M:%S")
        }
        self.alerts = self._load_alerts()
        self.alerts.insert(0, alert)
        self.alerts = self.alerts[:20]
        self._save_alerts()

        AgentLogger.log(
            "API_GATEWAY",
            f"⚠️ Intercepted {meta.get('name')}: {error_type} ({status_code or 'Timeout'}). "
            f"{'Cascaded to ' + fallback_engaged if fallback_engaged else 'No fallback.'}",
            "warning"
        )
        return alert

    def dismiss_alert(self, alert_id: str):
        self.alerts = self._load_alerts()
        self.alerts = [a for a in self.alerts if a["id"] != alert_id]
        self._save_alerts()

    async def probe_api(self, api_id: str, test_key: Optional[str] = None, test_endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes an immediate live probe against the specified API,
        measuring round-trip response time, HTTP status, and testing credentials.
        """
        if api_id not in self.registry:
            return {"status": "error", "message": f"Unknown API '{api_id}'"}

        meta = self.registry[api_id]
        endpoint = test_endpoint or meta.get("probe_url") or meta["endpoint"]
        key = test_key if test_key is not None else self.get_effective_key(api_id)

        headers = {"User-Agent": "ScholarForgeOS/2.1 (mailto:researcher@scholarforge.org)"}
        if key:
            if "groq" in api_id or "openrouter" in api_id:
                headers["Authorization"] = f"Bearer {key}"
            elif "materials_project" in api_id:
                headers["X-API-KEY"] = key
            elif "scite" in api_id or "copyleaks" in api_id:
                headers["Authorization"] = f"Bearer {key}"
            elif "zenodo" in api_id:
                headers["Authorization"] = f"Bearer {key}"
            elif "pubmed" in api_id and "api_key=" not in endpoint:
                endpoint = f"{endpoint}&api_key={key}"

        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=meta["timeout_sec"], follow_redirects=True) as client:
                resp = await client.get(endpoint, headers=headers)
                latency = round((time.monotonic() - start_time) * 1000, 1)
                
                meta["last_latency_ms"] = latency
                meta["last_error"] = None
                meta["status"] = f"Active ({latency}ms)"

                is_ok = resp.status_code in (200, 201, 202, 204, 301, 302)
                return {
                    "status": "success" if is_ok else "throttled",
                    "http_status": resp.status_code,
                    "latency_ms": latency,
                    "endpoint_tested": endpoint,
                    "message": f"HTTP {resp.status_code} in {latency}ms",
                    "response_sample": resp.text[:200]
                }
        except httpx.TimeoutException:
            latency = round((time.monotonic() - start_time) * 1000, 1)
            meta["last_error"] = "Connection Timeout"
            meta["status"] = "Timeout"
            return {
                "status": "error",
                "http_status": 408,
                "latency_ms": latency,
                "message": f"Request timed out after {meta['timeout_sec']}s",
                "error_detail": "Server took too long to respond. Increase timeout in API settings."
            }
        except Exception as e:
            latency = round((time.monotonic() - start_time) * 1000, 1)
            meta["last_error"] = str(e)
            meta["status"] = "Error"
            return {
                "status": "error",
                "http_status": 500,
                "latency_ms": latency,
                "message": f"Connection failed: {str(e)[:100]}",
                "error_detail": str(e)
            }

    async def execute_with_circuit_breaker(
        self,
        api_id: str,
        operation: Callable[[str, Dict[str, str]], Any],
        fallback_chain: Optional[List[str]] = None
    ) -> Any:
        """
        Executes a network request function with full circuit-breaker resilience:
        - Rate limiting token bucket check.
        - Timeout enforcement and retries.
        - Automatic fallback cascade if HTTP 429, 401, 403, or 503 occurs.
        - Emits alert to the user with 1-click credential configuration link.
        """
        meta = self.registry.get(api_id)
        if not meta or not meta.get("enabled", True):
            # If primary disabled, immediately cascade to fallback
            if fallback_chain:
                next_api = fallback_chain[0]
                return await self.execute_with_circuit_breaker(next_api, operation, fallback_chain[1:])
            raise RuntimeError(f"API '{api_id}' is disabled and no fallback available.")

        retries = meta.get("retries", 2)
        timeout = meta.get("timeout_sec", 8.0)
        key = self.get_effective_key(api_id)
        
        headers = {"User-Agent": "ScholarForgeOS/2.1 (mailto:researcher@scholarforge.org)"}
        if key:
            if "materials_project" in api_id:
                headers["X-API-KEY"] = key
            elif "groq" in api_id or "openrouter" in api_id or "scite" in api_id:
                headers["Authorization"] = f"Bearer {key}"

        for attempt in range(retries + 1):
            await self.acquire_slot(api_id)
            meta["total_requests"] += 1
            start = time.monotonic()

            try:
                result = await operation(meta["endpoint"], headers)
                meta["last_latency_ms"] = round((time.monotonic() - start) * 1000, 1)
                meta["status"] = f"Active ({meta['last_latency_ms']}ms)"
                meta["error_count"] = 0
                return result
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                meta["last_error"] = f"HTTP {code}"
                meta["error_count"] += 1

                # If rate-limited (429) or unauthenticated (401/403)
                if code == 429:
                    rec = f"Hit rate limit on {meta['name']}. Configure your personal API key or reduce concurrency."
                    fallback = fallback_chain[0] if fallback_chain else meta.get("fallback_id")
                    self.add_alert(api_id, "Rate Limit (HTTP 429)", code, f"{meta['name']} rate limit reached.", rec, fallback)
                    if fallback:
                        return await self.execute_with_circuit_breaker(fallback, operation, fallback_chain[1:] if fallback_chain else None)
                    raise
                elif code in (401, 403):
                    rec = f"{meta['name']} requires credentials. Enter your personal key in Settings -> BYOK Vault."
                    fallback = fallback_chain[0] if fallback_chain else meta.get("fallback_id")
                    self.add_alert(api_id, "Authentication Required", code, f"{meta['name']} requires an API key.", rec, fallback)
                    if fallback:
                        return await self.execute_with_circuit_breaker(fallback, operation, fallback_chain[1:] if fallback_chain else None)
                    raise
                elif attempt == retries:
                    fallback = fallback_chain[0] if fallback_chain else meta.get("fallback_id")
                    if fallback:
                        self.add_alert(api_id, f"HTTP Error {code}", code, f"{meta['name']} failed with HTTP {code}.", "Cascading to backup endpoint.", fallback)
                        return await self.execute_with_circuit_breaker(fallback, operation, fallback_chain[1:] if fallback_chain else None)
                    raise
            except httpx.TimeoutException:
                meta["last_error"] = "Timeout"
                meta["error_count"] += 1
                if attempt == retries:
                    fallback = fallback_chain[0] if fallback_chain else meta.get("fallback_id")
                    rec = f"Request timed out after {timeout}s. Tweak timeout in API Settings."
                    self.add_alert(api_id, "Connection Timeout", 408, f"{meta['name']} timed out.", rec, fallback)
                    if fallback:
                        return await self.execute_with_circuit_breaker(fallback, operation, fallback_chain[1:] if fallback_chain else None)
                    raise
                await asyncio.sleep(0.5)
            except Exception as e:
                meta["last_error"] = str(e)
                meta["error_count"] += 1
                if attempt == retries:
                    fallback = fallback_chain[0] if fallback_chain else meta.get("fallback_id")
                    if fallback:
                        self.add_alert(api_id, "Connection Failure", 500, f"{meta['name']} failed: {str(e)[:60]}", "Cascading to fallback.", fallback)
                        return await self.execute_with_circuit_breaker(fallback, operation, fallback_chain[1:] if fallback_chain else None)
                    raise
                await asyncio.sleep(0.5)

cloud_gateway = CloudApiGateway()
