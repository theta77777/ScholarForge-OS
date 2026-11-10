import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DB_PATH = CONFIG_DIR / "cache.db"

def init_db(db_path: Path = DB_PATH) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. DOI & Metadata Cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doi_cache (
                doi TEXT PRIMARY KEY,
                title TEXT,
                authors TEXT,
                year INTEGER,
                journal TEXT,
                abstract TEXT,
                is_open_access INTEGER,
                oa_url TEXT,
                scihub_available INTEGER,
                raw_json TEXT,
                created_at REAL
            )
        """)
        
        # 2. Search Query Cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                database TEXT,
                result_count INTEGER,
                results_json TEXT,
                created_at REAL
            )
        """)
        
        # 3. PRISMA 2020 Deterministic Tracker
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prisma_records (
                project_slug TEXT PRIMARY KEY,
                total_identified INTEGER DEFAULT 0,
                duplicates_removed INTEGER DEFAULT 0,
                records_screened INTEGER DEFAULT 0,
                records_excluded INTEGER DEFAULT 0,
                reports_sought INTEGER DEFAULT 0,
                reports_not_retrieved INTEGER DEFAULT 0,
                reports_assessed INTEGER DEFAULT 0,
                reports_excluded_with_reasons TEXT,
                studies_included INTEGER DEFAULT 0,
                updated_at REAL
            )
        """)
        
        # 4. Decision Log (Human vs CodeIV)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_slug TEXT,
                step TEXT,
                decision_maker TEXT, -- 'human' or 'codeiv'
                decision_details TEXT,
                confidence REAL,
                timestamp REAL
            )
        """)
        
        conn.commit()

class DatabaseManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)
        
    def get_doi_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        clean_doi = doi.strip().lower()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT raw_json FROM doi_cache WHERE doi = ?", (clean_doi,))
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return None
        return None

    def cache_doi_metadata(self, doi: str, title: str, authors: str, year: Optional[int], 
                           journal: str, abstract: str, is_oa: bool, oa_url: str, 
                           scihub_avail: bool, raw_data: Dict[str, Any]) -> None:
        clean_doi = doi.strip().lower()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO doi_cache 
                (doi, title, authors, year, journal, abstract, is_open_access, oa_url, scihub_available, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (clean_doi, title, authors, year, journal, abstract, 1 if is_oa else 0, oa_url, 1 if scihub_avail else 0, json.dumps(raw_data), time.time()))
            conn.commit()

    def log_decision(self, project_slug: str, step: str, decision_maker: str, details: Dict[str, Any], confidence: float = 1.0) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO decision_log (project_slug, step, decision_maker, decision_details, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (project_slug, step, decision_maker, json.dumps(details), confidence, time.time()))
            conn.commit()

    def get_prisma_stats(self, project_slug: str) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prisma_records WHERE project_slug = ?", (project_slug,))
            row = cursor.fetchone()
            if not row:
                return {
                    "total_identified": 0,
                    "duplicates_removed": 0,
                    "records_screened": 0,
                    "records_excluded": 0,
                    "reports_sought": 0,
                    "reports_not_retrieved": 0,
                    "reports_assessed": 0,
                    "reports_excluded_with_reasons": {},
                    "studies_included": 0
                }
            return {
                "total_identified": row[1],
                "duplicates_removed": row[2],
                "records_screened": row[3],
                "records_excluded": row[4],
                "reports_sought": row[5],
                "reports_not_retrieved": row[6],
                "reports_assessed": row[7],
                "reports_excluded_with_reasons": json.loads(row[8] or "{}"),
                "studies_included": row[9]
            }

    def update_prisma_stats(self, project_slug: str, stats: Dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO prisma_records
                (project_slug, total_identified, duplicates_removed, records_screened, records_excluded,
                 reports_sought, reports_not_retrieved, reports_assessed, reports_excluded_with_reasons,
                 studies_included, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_slug,
                stats.get("total_identified", 0),
                stats.get("duplicates_removed", 0),
                stats.get("records_screened", 0),
                stats.get("records_excluded", 0),
                stats.get("reports_sought", 0),
                stats.get("reports_not_retrieved", 0),
                stats.get("reports_assessed", 0),
                json.dumps(stats.get("reports_excluded_with_reasons", {})),
                stats.get("studies_included", 0),
                time.time()
            ))
            conn.commit()

