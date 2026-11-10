from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List, Dict, Any
from ..services.search_engine import FederatedSearchEngine
from ..services.literature_downloader import LiteratureDownloader
from ..core.config import get_settings

router = APIRouter(prefix="/api/search", tags=["Search & Acquisition"])

class SearchRequest(BaseModel):
    query: str
    limit_per_database: int = 15
    workspace_path: Optional[str] = None

class DownloadRequest(BaseModel):
    catalog_id: str
    title: str
    author_year: str
    doi: str
    year: Optional[int] = None
    workspace_path: Optional[str] = None

@router.post("")
async def execute_federated_search(req: SearchRequest):
    """
    Executes federated search across PubMed, Crossref, and OpenAlex.
    Deduplicates candidates and assigns permanent C001, C002 IDs.
    """
    workspace = Path(req.workspace_path) if req.workspace_path else Path(get_settings().workspace_dir)
    engine = FederatedSearchEngine(workspace)
    
    candidates = await engine.search_all(req.query, req.limit_per_database)
    return {
        "status": "success",
        "query": req.query,
        "count": len(candidates),
        "candidates": candidates
    }

@router.post("/download")
async def download_candidate_paper(req: DownloadRequest):
    """
    1-Click Automated Download:
    - Tier 1: Free Open Access (Unpaywall, PMC, arXiv)
    - Tier 2: Pre-2021 Paywalled Papers via Sci-Hub Mirrors (%PDF- validation)
    - Tier 3: Subscription-needed fallback
    """
    workspace = Path(req.workspace_path) if req.workspace_path else Path(get_settings().workspace_dir)
    downloader = LiteratureDownloader(workspace)
    
    result = await downloader.acquire_paper(
        catalog_id=req.catalog_id,
        title=req.title,
        author_year=req.author_year,
        doi=req.doi,
        year=req.year
    )
    return result

