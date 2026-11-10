import asyncio
import hashlib
import os
import re
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List
import httpx
from bs4 import BeautifulSoup

from ..core.rate_limiter import rate_limiter
from ..core.database import DatabaseManager
from ..core.agent_logs import AgentLogger, TaskProgressTracker

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

class LiteratureDownloader:
    """
    High-Capacity Concurrent Literature Acquisition & Ingestion Engine:
    Exhaustively acquires full-text scientific PDFs across multiple redundant channels:
    1. Direct Metadata PDF URLs (arXiv, Europe PMC, DOAJ, Unpaywall)
    2. Publisher DOI Landing Page Meta-Tag Scraper (<meta name="citation_pdf_url">)
    3. Active Sci-Hub Multi-Mirror Pool (with embed & iframe stream resolution)
    4. Unpaywall REST API & Europe PMC / PubMed Central direct resolvers
    5. bioRxiv / medRxiv / arXiv preprint direct servers
    6. Structured Web Article extraction
    
    Papers that cannot be automatically acquired are systematically recorded in:
    02_sources/subscription_manual_verification_list.csv with full metadata,
    direct publisher links, Sci-Hub links, and suggested filenames for 1-click manual upload.
    """

    SCIHUB_MIRRORS = [
        "https://sci-hub.ren",
        "https://sci-hub.wf",
        "https://sci-hub.do",
        "https://www.sci-hub.ren",
        "https://sci-hub.se",
        "https://sci-hub.ru"
    ]

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.sources_dir = self.workspace_path / "02_sources" / "originals"
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self.db = DatabaseManager()

    @staticmethod
    def _is_valid_pdf_stream(data: bytes) -> bool:
        """Verifies magic bytes: must contain %PDF- in the first 1024 bytes."""
        if not data or len(data) < 100:
            return False
        # Strip leading whitespace or byte order marks
        header = data[:1024]
        return b"%PDF-" in header

    def _compute_sha256(self, filepath: Path) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def fetch_meta_citation_pdf(self, doi: str) -> Optional[str]:
        """
        Scrapes publisher DOI landing page for standard citation PDF meta tags.
        Works across Nature, Springer, Wiley, ScienceDirect, MDPI, Frontiers, PLOS, IEEE, Oxford, etc.
        """
        clean_doi = doi.strip()
        doi_url = f"https://doi.org/{clean_doi}"
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
                resp = await client.get(doi_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Search for standard academic citation PDF meta tags
                    meta_pdf = (
                        soup.find("meta", {"name": re.compile(r"^(?:citation_pdf_url|bepress_citation_pdf_url|wl_pdf_url)$", re.I)}) or
                        soup.find("link", {"rel": re.compile(r"alternate", re.I), "type": "application/pdf"})
                    )
                    if meta_pdf:
                        href = meta_pdf.get("content") or meta_pdf.get("href")
                        if href and href.startswith("http"):
                            return href
                        elif href and href.startswith("//"):
                            return f"https:{href}"
                        elif href:
                            return urllib.parse.urljoin(str(resp.url), href)
        except Exception:
            pass
        return None

    async def fetch_open_access_pdf_url(self, doi: str) -> Optional[str]:
        """Queries Unpaywall and Europe PMC for lawful Open Access PDF links."""
        clean_doi = doi.strip()
        
        # 1. Europe PMC direct search
        try:
            epmc_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{clean_doi}&format=json"
            async with httpx.AsyncClient(timeout=6.0, headers=BROWSER_HEADERS) as client:
                resp = await client.get(epmc_url)
                if resp.status_code == 200:
                    results = resp.json().get("resultList", {}).get("result", [])
                    if results and results[0].get("hasPDF") == "Y":
                        pmcid = results[0].get("pmcid")
                        if pmcid:
                            return f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
        except Exception:
            pass

        # 2. Unpaywall API
        try:
            unpaywall_url = f"https://api.unpaywall.org/v2/{clean_doi}?email=scholarforge@gmail.com"
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
                resp = await client.get(unpaywall_url)
                if resp.status_code == 200:
                    data = resp.json()
                    best_oa = data.get("best_oa_location")
                    if best_oa and best_oa.get("url_for_pdf"):
                        return best_oa["url_for_pdf"]
        except Exception:
            pass

        return None

    async def download_from_scihub(self, doi: str) -> Optional[bytes]:
        """
        Attempts download from active, working Sci-Hub mirrors concurrently.
        Races mirrors with asyncio.as_completed for maximum speed (returns in 2-4 seconds).
        Resolves direct PDF streams, embedded iframes, embed tags, and onclick download buttons.
        """
        clean_doi = doi.strip()
        working_mirrors = ["https://sci-hub.ren", "https://sci-hub.wf", "https://sci-hub.do"]

        async def try_mirror(mirror: str) -> Optional[bytes]:
            try:
                target_url = f"{mirror}/{clean_doi}"
                async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
                    resp = await client.get(target_url)
                    if resp.status_code == 200:
                        content_type = resp.headers.get("Content-Type", "").lower()
                        if "application/pdf" in content_type and self._is_valid_pdf_stream(resp.content):
                            AgentLogger.log("SCIHUB", f"Direct PDF stream acquired from {mirror}", "success")
                            return resp.content

                        soup = BeautifulSoup(resp.text, "html.parser")
                        pdf_element = (
                            soup.find("embed", {"type": "application/pdf"}) or 
                            soup.find("iframe", {"id": "pdf"}) or
                            soup.find("iframe", {"src": re.compile(r"\.pdf", re.I)}) or
                            soup.find("button", {"onclick": re.compile(r"location\.href", re.I)})
                        )
                        if pdf_element:
                            pdf_src = pdf_element.get("src") or pdf_element.get("onclick")
                            if pdf_src and "location.href" in pdf_src:
                                match = re.search(r"'(https?://[^']+)'", pdf_src)
                                if match:
                                    pdf_src = match.group(1)
                            if pdf_src:
                                if pdf_src.startswith("//"):
                                    pdf_src = "https:" + pdf_src
                                elif not pdf_src.startswith("http"):
                                    pdf_src = f"{mirror}/{pdf_src.lstrip('/')}"
                                stream_resp = await client.get(pdf_src, timeout=8.0, headers=BROWSER_HEADERS)
                                if stream_resp.status_code == 200 and self._is_valid_pdf_stream(stream_resp.content):
                                    AgentLogger.log("SCIHUB", f"Resolved embedded PDF stream from {mirror}", "success")
                                    return stream_resp.content
            except Exception:
                pass
            return None

        # Check working mirrors concurrently and return first valid stream
        tasks = [asyncio.create_task(try_mirror(m)) for m in working_mirrors]
        for fut in asyncio.as_completed(tasks):
            try:
                res = await fut
                if res:
                    # Cancel remaining tasks
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    return res
            except Exception:
                continue

        return None

    async def acquire_paper(self, catalog_id: str, title: str, author_year: str, 
                            doi: str, year: Optional[int], pdf_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Comprehensive multi-strategy literature acquisition pipeline.
        Saves verified PDF as {catalog_id}_{author_year}.pdf in 02_sources/originals/.
        """
        safe_filename = f"{catalog_id}_{re.sub(r'[^a-zA-Z0-9_-]', '', author_year)}.pdf"
        target_path = self.sources_dir / safe_filename

        # Strategy 0: Local verified cache
        if target_path.exists() and target_path.stat().st_size > 1000:
            sha256 = self._compute_sha256(target_path)
            return {
                "catalog_id": catalog_id,
                "status": "cached",
                "filename": safe_filename,
                "filepath": str(target_path),
                "sha256": sha256,
                "access_level": "full_text"
            }

        pdf_bytes = None
        source_channel = "none"

        # Strategy 1: Direct PDF URL from metadata (arXiv, OpenAlex, Europe PMC)
        if pdf_url and pdf_url.startswith("http"):
            try:
                async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
                    resp = await client.get(pdf_url)
                    if resp.status_code == 200 and self._is_valid_pdf_stream(resp.content):
                        pdf_bytes = resp.content
                        source_channel = "direct_metadata_url"
                        AgentLogger.log("DOWNLOAD", f"[{catalog_id}] Acquired direct PDF from metadata ({len(pdf_bytes):,} bytes)", "success")
            except Exception:
                pass

        # Strategy 2: Dedicated arXiv Direct Resolver
        if not pdf_bytes and ("arxiv" in doi.lower() or "arxiv" in (pdf_url or "").lower()):
            arxiv_id = ""
            m = re.search(r'arXiv\.([0-9]+\.[0-9]+[v0-9]*)', doi, re.I)
            if not m and pdf_url:
                m = re.search(r'([0-9]+\.[0-9]+[v0-9]*)', pdf_url)
            if m:
                arxiv_id = m.group(1)
                direct_arxiv_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                try:
                    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
                        resp = await client.get(direct_arxiv_url)
                        if resp.status_code == 200 and self._is_valid_pdf_stream(resp.content):
                            pdf_bytes = resp.content
                            source_channel = "arxiv_direct"
                            AgentLogger.log("DOWNLOAD", f"[{catalog_id}] Acquired arXiv preprint ({len(pdf_bytes):,} bytes)", "success")
                except Exception:
                    pass

        # Strategy 3: Dedicated bioRxiv / medRxiv Resolver
        if not pdf_bytes and doi.startswith("10.1101/"):
            biorxiv_pdf = f"https://www.biorxiv.org/content/{doi}.full.pdf"
            try:
                async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
                    resp = await client.get(biorxiv_pdf)
                    if resp.status_code == 200 and self._is_valid_pdf_stream(resp.content):
                        pdf_bytes = resp.content
                        source_channel = "biorxiv_direct"
                        AgentLogger.log("DOWNLOAD", f"[{catalog_id}] Acquired bioRxiv full-text PDF ({len(pdf_bytes):,} bytes)", "success")
            except Exception:
                pass

        # Strategy 4: Publisher DOI Landing Page Meta Citation Scraper
        if not pdf_bytes and doi:
            meta_pdf_url = await self.fetch_meta_citation_pdf(doi)
            if meta_pdf_url:
                try:
                    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
                        resp = await client.get(meta_pdf_url)
                        if resp.status_code == 200 and self._is_valid_pdf_stream(resp.content):
                            pdf_bytes = resp.content
                            source_channel = "publisher_meta_pdf"
                            AgentLogger.log("DOWNLOAD", f"[{catalog_id}] Acquired publisher open-access PDF ({len(pdf_bytes):,} bytes)", "success")
                except Exception:
                    pass

        # Strategy 5: Open Access via Unpaywall & Europe PMC
        if not pdf_bytes and doi:
            oa_url = await self.fetch_open_access_pdf_url(doi)
            if oa_url:
                try:
                    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
                        resp = await client.get(oa_url)
                        if resp.status_code == 200 and self._is_valid_pdf_stream(resp.content):
                            pdf_bytes = resp.content
                            source_channel = "unpaywall_europepmc"
                            AgentLogger.log("DOWNLOAD", f"[{catalog_id}] Acquired Unpaywall/EuropePMC PDF ({len(pdf_bytes):,} bytes)", "success")
                except Exception:
                    pass

        # Strategy 6: Sci-Hub Multi-Mirror Pool (Unrestricted by Year)
        if not pdf_bytes and doi:
            pdf_bytes = await self.download_from_scihub(doi)
            if pdf_bytes:
                source_channel = "scihub_mirror"

        # Successful Write
        if pdf_bytes and self._is_valid_pdf_stream(pdf_bytes):
            with open(target_path, "wb") as f:
                f.write(pdf_bytes)
            sha256 = self._compute_sha256(target_path)
            AgentLogger.log("STORAGE", f"Saved verified PDF: 02_sources/originals/{safe_filename} ({len(pdf_bytes):,} bytes)", "success")
            return {
                "catalog_id": catalog_id,
                "status": "downloaded",
                "filename": safe_filename,
                "channel": source_channel,
                "filepath": str(target_path),
                "sha256": sha256,
                "file_size_bytes": len(pdf_bytes),
                "access_level": "full_text"
            }

        # Failed: Mark as Institutional Subscription Required
        AgentLogger.log("SUBSCRIPTION", f"[{catalog_id}] Subscription required for DOI {doi}. Recorded in manual verification list.", "info")
        return {
            "catalog_id": catalog_id,
            "status": "subscription_required",
            "filename": safe_filename,
            "doi": doi,
            "publisher_link": f"https://doi.org/{doi}" if doi else "#",
            "scihub_link": f"https://sci-hub.ren/{doi}" if doi else "#",
            "suggested_filename": safe_filename,
            "access_level": "abstract_only"
        }

    async def acquire_web_article(self, catalog_id: str, title: str, author_year: str, url: str) -> Dict[str, Any]:
        """Downloads full text of a web article or wiki page and saves to 02_sources/originals/ as clean text."""
        safe_filename = f"{catalog_id}_{re.sub(r'[^a-zA-Z0-9_-]', '', author_year)}.txt"
        target_path = self.sources_dir / safe_filename
        
        if target_path.exists() and target_path.stat().st_size > 100:
            sha256 = self._compute_sha256(target_path)
            return {
                "catalog_id": catalog_id,
                "status": "cached",
                "filename": safe_filename,
                "filepath": str(target_path),
                "sha256": sha256,
                "access_level": "full_text"
            }

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for s in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        s.decompose()
                    
                    article_el = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r'content|body|post')) or soup.body
                    text_content = ""
                    if article_el:
                        paragraphs = [p.get_text().strip() for p in article_el.find_all(["p", "h1", "h2", "h3", "li"]) if len(p.get_text().strip()) > 20]
                        text_content = "\n\n".join(paragraphs)
                    if not text_content:
                        text_content = soup.get_text(separator="\n", strip=True)

                    full_doc = f"# {title}\nSource URL: {url}\n\n{text_content[:30000]}"
                    target_path.write_text(full_doc, encoding="utf-8")
                    sha256 = self._compute_sha256(target_path)
                    AgentLogger.log("STORAGE", f"Saved web article: {safe_filename} ({len(full_doc):,} chars)", "success")
                    return {
                        "catalog_id": catalog_id,
                        "status": "downloaded",
                        "filename": safe_filename,
                        "channel": "web_scrape",
                        "filepath": str(target_path),
                        "sha256": sha256,
                        "file_size_bytes": len(full_doc.encode('utf-8')),
                        "access_level": "full_text"
                    }
        except Exception as e:
            AgentLogger.log("DOWNLOAD", f"Web article fetch note for {url}: {e}", "warning")

        return {
            "catalog_id": catalog_id,
            "status": "subscription_required",
            "title": title,
            "filename": safe_filename,
            "doi": "",
            "publisher_link": url,
            "scihub_link": "#",
            "suggested_filename": safe_filename,
            "access_level": "abstract_only"
        }

    async def acquire_selected_sources(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Uncapped Concurrent Mass Downloader:
        Politely parallelizes acquisition across 15 concurrent workers.
        Saves all full texts to 02_sources/originals/.
        Exports all missing / paywalled papers to 02_sources/subscription_manual_verification_list.csv
        with full metadata and direct links.
        """
        AgentLogger.log("DOWNLOAD", f"Launching Uncapped Concurrent Mass Downloader for {len(candidates)} selected items...", "info")
        sem = asyncio.Semaphore(15)
        downloaded = []
        subscription_required = []

        total = len(candidates)
        completed_count = 0
        TaskProgressTracker.set_progress("Acquisition", 5, f"Launching mass acquisition for {total} selected sources...", step=2)

        async def worker(c: Dict[str, Any]):
            nonlocal completed_count
            async with sem:
                cid = c.get("catalog_id", "C000")
                key = c.get("citation_key", "source")
                title = c.get("title", "")
                doi = c.get("doi", "").strip()
                year = c.get("year")
                pdf_url = c.get("pdf_url")
                landing_url = c.get("landing_url")
                item_type = c.get("type", "academic_paper")
                journal = c.get("journal", "Academic Publication")
                authors = c.get("authors", "Unknown Authors")

                if item_type == "web_article" and landing_url:
                    res = await self.acquire_web_article(cid, title, key, landing_url)
                else:
                    res = await self.acquire_paper(cid, title, key, doi, year, pdf_url)

                res["title"] = title
                res["authors"] = authors
                res["journal"] = journal
                res["year"] = year
                res["doi"] = doi
                res["publisher_link"] = landing_url or (f"https://doi.org/{doi}" if doi else "#")
                res["scihub_link"] = f"https://sci-hub.ren/{doi}" if doi else "#"

                if res.get("status") in ["downloaded", "cached"]:
                    downloaded.append(res)
                else:
                    subscription_required.append(res)

                completed_count += 1
                pct = int(5 + (completed_count / max(1, total)) * 90)
                TaskProgressTracker.set_progress(
                    "Acquisition",
                    pct,
                    f"Acquired {len(downloaded)} / {total} files ({completed_count}/{total} checked) - {title[:38]}...",
                    step=2
                )

        await asyncio.gather(*(worker(c) for c in candidates), return_exceptions=True)

        # Write subscription manual verification CSV and JSON
        import csv
        import json
        sub_csv = self.workspace_path / "02_sources" / "subscription_manual_verification_list.csv"
        sub_json = self.workspace_path / "02_sources" / "subscription_manual_verification_list.json"
        
        fieldnames = ["catalog_id", "title", "authors", "journal", "year", "doi", "publisher_link", "scihub_link", "suggested_filename", "status", "access_level"]
        with open(sub_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            w.writeheader()
            for item in subscription_required:
                w.writerow(item)

        with open(sub_json, "w", encoding="utf-8") as f:
            json.dump(subscription_required, f, indent=2)

        TaskProgressTracker.set_progress(
            "Acquisition",
            100,
            f"Acquisition complete: {len(downloaded)} local files saved in 02_sources/originals/, {len(subscription_required)} in manual list.",
            step=2
        )
        AgentLogger.log("DOWNLOAD", f"Acquisition Complete: {len(downloaded)} stored in 02_sources/originals/, {len(subscription_required)} recorded in subscription manual verification list.", "success")
        
        return {
            "total_requested": len(candidates),
            "acquired_count": len(downloaded),
            "subscription_count": len(subscription_required),
            "missing_count": len(subscription_required),
            "downloaded": downloaded,
            "subscription_manual_list": subscription_required,
            "missing_paywalled": subscription_required,
            "storage_path": str(self.sources_dir)
        }
