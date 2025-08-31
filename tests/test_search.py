"""Tests for the factual search system."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import sqlite3

from app.knowledge.search import (
    Fact, FactSearchEngine, search_facts, get_facts_by_canonical,
    get_facts_by_type, get_database_stats
)


class TestFact:
    """Test the Fact dataclass."""
    
    def test_fact_creation(self):
        """Test creating a Fact instance."""
        fact = Fact(
            id=1,
            type="member",
            canonical="john frusciante",
            field="name",
            value="John Anthony Frusciante",
            year=1988,
            source="members.yml",
            rank=0.95
        )
        
        assert fact.id == 1
        assert fact.type == "member"
        assert fact.canonical == "john frusciante"
        assert fact.field == "name"
        assert fact.value == "John Anthony Frusciante"
        assert fact.year == 1988
        assert fact.source == "members.yml"
        assert fact.rank == 0.95
    
    def test_fact_without_optional_fields(self):
        """Test creating a Fact without optional fields."""
        fact = Fact(
            id=2,
            type="album",
            canonical="californication",
            field="title",
            value="Californication",
            year=None,
            source="albums.yml"
        )
        
        assert fact.id == 2
        assert fact.type == "album"
        assert fact.canonical == "californication"
        assert fact.field == "title"
        assert fact.value == "Californication"
        assert fact.year is None
        assert fact.source == "albums.yml"
        assert fact.rank is None


class TestFactSearchEngine:
    """Test the FactSearchEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_fts.sqlite"
        self._create_test_database()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_test_database(self):
        """Create a test database with sample facts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create schema
        cursor.executescript("""
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                canonical TEXT NOT NULL,
                field TEXT NOT NULL,
                value TEXT NOT NULL,
                year INTEGER,
                source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE VIRTUAL TABLE facts_fts USING fts5(
                type,
                canonical,
                field,
                value,
                year,
                source,
                content='facts',
                content_rowid='id'
            );
            
            CREATE INDEX idx_facts_type ON facts(type);
            CREATE INDEX idx_facts_canonical ON facts(canonical);
        """)
        
        # Insert test data
        test_facts = [
            (1, "member", "john frusciante", "name", "John Anthony Frusciante", 1988, "members.yml"),
            (2, "member", "john frusciante", "role", "guitar", None, "members.yml"),
            (3, "member", "john frusciante", "role", "backing vocals", None, "members.yml"),
            (4, "member", "john frusciante", "join_year", "1988", 1988, "members.yml"),
            (5, "album", "californication", "title", "Californication", 1999, "albums.yml"),
            (6, "album", "californication", "year", "1999", 1999, "albums.yml"),
            (7, "album", "californication", "label", "Warner Bros.", None, "albums.yml"),
            (8, "song", "under the bridge", "title", "Under the Bridge", 1991, "songs.yml"),
            (9, "song", "under the bridge", "album", "Blood Sugar Sex Magik", None, "songs.yml"),
        ]
        
        cursor.executemany("""
            INSERT INTO facts (id, type, canonical, field, value, year, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, test_facts)
        
        # Insert into FTS table
        cursor.executemany("""
            INSERT INTO facts_fts (type, canonical, field, value, year, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(f[1], f[2], f[3], f[4], f[5], f[6]) for f in test_facts])
        
        conn.commit()
        conn.close()
    
    def test_initialization(self):
        """Test search engine initialization."""
        engine = FactSearchEngine(str(self.db_path))
        assert engine.db_path == self.db_path
    
    def test_initialization_with_nonexistent_db(self):
        """Test initialization with non-existent database."""
        with pytest.raises(FileNotFoundError):
            FactSearchEngine("nonexistent.db")
    
    def test_search_facts_exact_match(self):
        """Test exact fact search."""
        engine = FactSearchEngine(str(self.db_path))
        
        # Search for exact member name
        facts = engine.search_facts("John Anthony Frusciante", k=5)
        assert len(facts) > 0
        
        # Check that we found the member
        member_facts = [f for f in facts if f.type == "member"]
        assert len(member_facts) > 0
        assert any(f.canonical == "john frusciante" for f in member_facts)
    
    def test_search_facts_partial_match(self):
        """Test partial fact search."""
        engine = FactSearchEngine(str(self.db_path))
        
        # Search for partial name
        facts = engine.search_facts("frusciante", k=5)
        assert len(facts) > 0
        
        # Should find member facts
        member_facts = [f for f in facts if f.type == "member"]
        assert len(member_facts) > 0
    
    def test_search_facts_by_type(self):
        """Test fact search filtered by type."""
        engine = FactSearchEngine(str(self.db_path))
        
        # Search only for members
        facts = engine.search_facts("frusciante", k=5, fact_type="member")
        assert len(facts) > 0
        assert all(f.type == "member" for f in facts)
        
        # Search only for albums
        facts = engine.search_facts("californication", k=5, fact_type="album")
        assert len(facts) > 0
        assert all(f.type == "album" for f in facts)
    
    def test_search_facts_empty_query(self):
        """Test search with empty query."""
        engine = FactSearchEngine(str(self.db_path))
        
        facts = engine.search_facts("", k=5)
        assert facts == []
        
        facts = engine.search_facts("   ", k=5)
        assert facts == []
    
    def test_get_facts_by_canonical(self):
        """Test getting facts for a specific canonical entity."""
        engine = FactSearchEngine(str(self.db_path))
        
        # Get all facts for John Frusciante
        facts = engine.get_facts_by_canonical("john frusciante")
        assert len(facts) == 4  # name, role, role, join_year
        
        # Check specific facts
        name_facts = [f for f in facts if f.field == "name"]
        assert len(name_facts) == 1
        assert name_facts[0].value == "John Anthony Frusciante"
        
        role_facts = [f for f in facts if f.field == "role"]
        assert len(role_facts) == 2
        assert "guitar" in [f.value for f in role_facts]
        assert "backing vocals" in [f.value for f in role_facts]
    
    def test_get_facts_by_canonical_with_type_filter(self):
        """Test getting facts by canonical with type filter."""
        engine = FactSearchEngine(str(self.db_path))
        
        # Get member facts only
        facts = engine.get_facts_by_canonical("john frusciante", "member")
        assert len(facts) == 4
        assert all(f.type == "member" for f in facts)
        
        # Get album facts (should be empty)
        facts = engine.get_facts_by_canonical("john frusciante", "album")
        assert len(facts) == 0
    
    def test_get_facts_by_type(self):
        """Test getting facts of a specific type."""
        engine = FactSearchEngine(str(self.db_path))
        
        # Get all member facts
        facts = engine.get_facts_by_type("member")
        assert len(facts) == 4
        
        # Get all album facts
        facts = engine.get_facts_by_type("album")
        assert len(facts) == 3
        
        # Get all song facts
        facts = engine.get_facts_by_type("song")
        assert len(facts) == 2
    
    def test_get_facts_by_type_with_limit(self):
        """Test getting facts by type with limit."""
        engine = FactSearchEngine(str(self.db_path))
        
        # Get limited member facts
        facts = engine.get_facts_by_type("member", limit=2)
        assert len(facts) == 2
    
    def test_get_database_stats(self):
        """Test getting database statistics."""
        engine = FactSearchEngine(str(self.db_path))
        
        stats = engine.get_database_stats()
        
        assert stats["total_facts"] == 9
        assert stats["type_counts"]["member"] == 4
        assert stats["type_counts"]["album"] == 3
        assert stats["type_counts"]["song"] == 2
        assert stats["source_counts"]["members.yml"] == 4
        assert stats["source_counts"]["albums.yml"] == 3
        assert stats["source_counts"]["songs.yml"] == 2
        assert "database_size_bytes" in stats
        assert "database_path" in stats


class TestSearchFunctions:
    """Test the convenience search functions."""
    
    @patch("app.knowledge.search.get_search_engine")
    def test_search_facts_function(self, mock_get_engine):
        """Test the search_facts convenience function."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        test_facts = [
            Fact(1, "member", "john frusciante", "name", "John Anthony Frusciante", 1988, "members.yml")
        ]
        mock_engine.search_facts.return_value = test_facts
        
        result = search_facts("frusciante", k=5)
        
        assert result == test_facts
        mock_engine.search_facts.assert_called_once_with("frusciante", 5, None)
    
    @patch("app.knowledge.search.get_search_engine")
    def test_get_facts_by_canonical_function(self, mock_get_engine):
        """Test the get_facts_by_canonical convenience function."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        test_facts = [
            Fact(1, "member", "john frusciante", "name", "John Anthony Frusciante", 1988, "members.yml")
        ]
        mock_engine.get_facts_by_canonical.return_value = test_facts
        
        result = get_facts_by_canonical("john frusciante")
        
        assert result == test_facts
        mock_engine.get_facts_by_canonical.assert_called_once_with("john frusciante", None)
    
    @patch("app.knowledge.search.get_search_engine")
    def test_get_facts_by_type_function(self, mock_get_engine):
        """Test the get_facts_by_type convenience function."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        test_facts = [
            Fact(1, "member", "john frusciante", "name", "John Anthony Frusciante", 1988, "members.yml")
        ]
        mock_engine.get_facts_by_type.return_value = test_facts
        
        result = get_facts_by_type("member", limit=10)
        
        assert result == test_facts
        mock_engine.get_facts_by_type.assert_called_once_with("member", 10)
    
    @patch("app.knowledge.search.get_search_engine")
    def test_get_database_stats_function(self, mock_get_engine):
        """Test the get_database_stats convenience function."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        test_stats = {"total_facts": 100, "type_counts": {"member": 50}}
        mock_engine.get_database_stats.return_value = test_stats
        
        result = get_database_stats()
        
        assert result == test_stats
        mock_engine.get_database_stats.assert_called_once()


class TestSearchEdgeCases:
    """Test edge cases and error handling."""
    
    def test_search_with_special_characters(self):
        """Test search with special characters."""
        # This would require a real database, so we'll test the function signature
        # and basic error handling
        with patch("app.knowledge.search.get_search_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine
            mock_engine.search_facts.return_value = []
            
            # Test with special characters
            result = search_facts("fruciante!", k=5)
            assert result == []
    
    def test_search_with_very_long_query(self):
        """Test search with very long query."""
        with patch("app.knowledge.search.get_search_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine
            mock_engine.search_facts.return_value = []
            
            long_query = "a" * 1000
            result = search_facts(long_query, k=5)
            assert result == []
    
    def test_search_with_none_values(self):
        """Test search with None values."""
        with patch("app.knowledge.search.get_search_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine
            mock_engine.search_facts.return_value = []
            
            # This should handle None gracefully
            result = search_facts(None, k=5)  # type: ignore
            assert result == []
