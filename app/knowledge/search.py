"""Factual retrieval system using SQLite FTS.

This module provides search capabilities for the RHCP knowledge base
to reduce hallucination in responses by backing answers with searchable facts.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.infra.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Fact:
    """A single factual piece of information."""
    id: int
    type: str  # 'member', 'album', 'song'
    canonical: str  # Canonical name/title
    field: str  # Field name (e.g., 'name', 'title', 'year', 'role')
    value: str  # Field value
    year: Optional[int]  # Year (if applicable)
    source: str  # Source file
    rank: Optional[float] = None  # FTS rank score


class FactSearchEngine:
    """Search engine for factual information using SQLite FTS."""
    
    def __init__(self, db_path: str = "data/rhcp_fts.sqlite"):
        """Initialize the search engine.
        
        Args:
            db_path: Path to the SQLite FTS database
        """
        self.db_path = Path(db_path)
        self._validate_database()
    
    def _validate_database(self) -> None:
        """Validate that the database exists and has the expected schema."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"FTS database not found: {self.db_path}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if facts table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='facts'")
                if not cursor.fetchone():
                    raise ValueError("Database missing 'facts' table")
                
                # Check if FTS table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='facts_fts'")
                if not cursor.fetchone():
                    raise ValueError("Database missing 'facts_fts' table")
                
                # Check fact count
                cursor.execute("SELECT COUNT(*) FROM facts")
                count = cursor.fetchone()[0]
                if count == 0:
                    raise ValueError("Database has no facts")
                
                logger.info(f"FTS database validated: {count} facts available")
                
        except Exception as e:
            logger.error(f"Database validation failed: {e}")
            raise
    
    def search_facts(self, query: str, k: int = 5, fact_type: Optional[str] = None) -> List[Fact]:
        """Search for facts using full-text search.
        
        Args:
            query: Search query string
            k: Maximum number of results to return
            fact_type: Optional filter by fact type ('member', 'album', 'song')
            
        Returns:
            List of matching facts, ordered by relevance
        """
        if not query or not query.strip():
            return []
        
        query = query.strip()
        logger.debug(f"Searching for: '{query}' (k={k}, type={fact_type})")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build the search query - use simpler approach without rank function for now
                if fact_type:
                    # Filter by type and search in all text fields
                    sql = """
                    SELECT 
                        f.id, f.type, f.canonical, f.field, f.value, f.year, f.source,
                        NULL as rank
                    FROM facts_fts
                    JOIN facts f ON f.id = facts_fts.rowid
                    WHERE facts_fts.type = ? AND facts_fts MATCH ?
                    LIMIT ?
                    """
                    cursor.execute(sql, (fact_type, query, k))
                else:
                    # Search across all types
                    sql = """
                    SELECT 
                        f.id, f.type, f.canonical, f.field, f.value, f.year, f.source,
                        NULL as rank
                    FROM facts_fts
                    JOIN facts f ON f.id = facts_fts.rowid
                    WHERE facts_fts MATCH ?
                    LIMIT ?
                    """
                    cursor.execute(sql, (query, k))
                
                results = []
                for row in cursor.fetchall():
                    fact = Fact(
                        id=row[0],
                        type=row[1],
                        canonical=row[2],
                        field=row[3],
                        value=row[4],
                        year=row[5],
                        source=row[6],
                        rank=row[7]
                    )
                    results.append(fact)
                
                logger.debug(f"Found {len(results)} facts for query '{query}'")
                return results
                
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
    
    def get_facts_by_canonical(self, canonical: str, fact_type: Optional[str] = None) -> List[Fact]:
        """Get all facts for a specific canonical entity.
        
        Args:
            canonical: Canonical name/title to search for
            fact_type: Optional filter by fact type
            
        Returns:
            List of facts for the canonical entity
        """
        logger.debug(f"Getting facts for canonical: '{canonical}' (type={fact_type})")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if fact_type:
                    sql = """
                    SELECT id, type, canonical, field, value, year, source, NULL as rank
                    FROM facts
                    WHERE canonical = ? AND type = ?
                    ORDER BY field, value
                    """
                    cursor.execute(sql, (canonical, fact_type))
                else:
                    sql = """
                    SELECT id, type, canonical, field, value, year, source, NULL as rank
                    FROM facts
                    WHERE canonical = ?
                    ORDER BY field, value
                    """
                    cursor.execute(sql, (canonical,))
                
                results = []
                for row in cursor.fetchall():
                    fact = Fact(
                        id=row[0],
                        type=row[1],
                        canonical=row[2],
                        field=row[3],
                        value=row[4],
                        year=row[5],
                        source=row[6],
                        rank=row[7]
                    )
                    results.append(fact)
                
                logger.debug(f"Found {len(results)} facts for canonical '{canonical}'")
                return results
                
        except Exception as e:
            logger.error(f"Failed to get facts for canonical '{canonical}': {e}")
            return []
    
    def get_facts_by_type(self, fact_type: str, limit: int = 100) -> List[Fact]:
        """Get facts of a specific type.
        
        Args:
            fact_type: Type of facts to retrieve ('member', 'album', 'song')
            limit: Maximum number of facts to return
            
        Returns:
            List of facts of the specified type
        """
        logger.debug(f"Getting {fact_type} facts (limit={limit})")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                sql = """
                SELECT id, type, canonical, field, value, year, source, NULL as rank
                FROM facts
                WHERE type = ?
                ORDER BY canonical, field
                LIMIT ?
                """
                cursor.execute(sql, (fact_type, limit))
                
                results = []
                for row in cursor.fetchall():
                    fact = Fact(
                        id=row[0],
                        type=row[1],
                        canonical=row[2],
                        field=row[3],
                        value=row[4],
                        year=row[5],
                        source=row[6],
                        rank=row[7]
                    )
                    results.append(fact)
                
                logger.debug(f"Found {len(results)} {fact_type} facts")
                return results
                
        except Exception as e:
            logger.error(f"Failed to get {fact_type} facts: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total facts
                cursor.execute("SELECT COUNT(*) FROM facts")
                total_facts = cursor.fetchone()[0]
                
                # Facts by type
                cursor.execute("SELECT type, COUNT(*) FROM facts GROUP BY type")
                type_counts = dict(cursor.fetchall())
                
                # Facts by source
                cursor.execute("SELECT source, COUNT(*) FROM facts GROUP BY source")
                source_counts = dict(cursor.fetchall())
                
                # Database size
                db_size = self.db_path.stat().st_size
                
                return {
                    'total_facts': total_facts,
                    'type_counts': type_counts,
                    'source_counts': source_counts,
                    'database_size_bytes': db_size,
                    'database_path': str(self.db_path)
                }
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


# Global search engine instance
_search_engine: Optional[FactSearchEngine] = None


def get_search_engine() -> FactSearchEngine:
    """Get the global search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = FactSearchEngine()
    return _search_engine


def search_facts(query: str, k: int = 5, fact_type: Optional[str] = None) -> List[Fact]:
    """Search for facts using the global search engine.
    
    Args:
        query: Search query string
        k: Maximum number of results to return
        fact_type: Optional filter by fact type
        
    Returns:
        List of matching facts
    """
    return get_search_engine().search_facts(query, k, fact_type)


def get_facts_by_canonical(canonical: str, fact_type: Optional[str] = None) -> List[Fact]:
    """Get facts for a canonical entity using the global search engine.
    
    Args:
        canonical: Canonical name/title
        fact_type: Optional filter by fact type
        
    Returns:
        List of facts for the canonical entity
    """
    return get_search_engine().get_facts_by_canonical(canonical, fact_type)


def get_facts_by_type(fact_type: str, limit: int = 100) -> List[Fact]:
    """Get facts of a specific type using the global search engine.
    
    Args:
        fact_type: Type of facts to retrieve
        limit: Maximum number of facts to return
        
    Returns:
        List of facts of the specified type
    """
    return get_search_engine().get_facts_by_type(fact_type, limit)


def get_database_stats() -> Dict[str, Any]:
    """Get database statistics using the global search engine.
    
    Returns:
        Dictionary with database statistics
    """
    return get_search_engine().get_database_stats()

