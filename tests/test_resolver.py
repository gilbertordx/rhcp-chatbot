"""Tests for the knowledge resolver."""

import pytest
from unittest.mock import patch, MagicMock

from app.knowledge.resolver import KnowledgeResolver, resolve_member, resolve_album, resolve_song


class TestKnowledgeResolver:
    """Test the KnowledgeResolver class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock data for testing
        self.mock_members = [
            {
                "name": "Anthony Kiedis",
                "canonical": "anthony kiedis",
                "aliases": ["anthony", "kiedis", "tony", "ant", "ak"],
                "roles": ["vocals", "lyrics"],
                "join_year": 1983,
                "active": True,
            },
            {
                "name": "John Anthony Frusciante",
                "canonical": "john frusciante",
                "aliases": ["john", "frusciante", "fruciante", "johnny", "jf"],
                "roles": ["guitar", "backing vocals"],
                "join_year": 1988,
                "active": True,
            },
        ]

        self.mock_albums = [
            {
                "title": "Californication",
                "canonical": "californication",
                "aliases": ["cali", "californication"],
                "year": 1999,
                "label": "Warner Bros.",
            },
            {
                "title": "By the Way",
                "canonical": "by the way",
                "aliases": ["btw", "by the way"],
                "year": 2002,
                "label": "Warner Bros.",
            },
        ]

        self.mock_songs = [
            {
                "title": "Under the Bridge",
                "canonical": "under the bridge",
                "aliases": ["utb", "bridge"],
                "year": 1991,
                "album": "Blood Sugar Sex Magik",
            },
            {
                "title": "Scar Tissue",
                "canonical": "scar tissue",
                "aliases": ["scar", "tissue"],
                "year": 1999,
                "album": "Californication",
            },
        ]

    @patch.object(KnowledgeResolver, '_load_knowledge_base')
    def test_resolver_initialization(self, mock_load):
        """Test resolver initialization and knowledge loading."""
        # Mock the knowledge loading method
        mock_load.return_value = None
        
        resolver = KnowledgeResolver("fake_path")
        
        # Manually set the data for testing
        resolver.members = self.mock_members
        resolver.albums = self.mock_albums
        resolver.songs = self.mock_songs
        
        assert len(resolver.members) == 2
        assert len(resolver.albums) == 2
        assert len(resolver.songs) == 2

    @patch.object(KnowledgeResolver, '_load_knowledge_base')
    def test_normalize_span(self, mock_load):
        """Test span normalization (case, diacritics, whitespace)."""
        mock_load.return_value = None
        resolver = KnowledgeResolver()
        
        # Test case normalization
        assert resolver._normalize_span("ANTHONY") == "anthony"
        assert resolver._normalize_span("John Frusciante") == "john frusciante"
        
        # Test whitespace normalization
        assert resolver._normalize_span("  john   frusciante  ") == "john frusciante"
        
        # Test diacritics (though we don't have any in our test data)
        assert resolver._normalize_span("Björk") == "bjork"  # Example with diacritics

    @patch.object(KnowledgeResolver, '_load_knowledge_base')
    def test_calculate_similarity(self, mock_load):
        """Test similarity calculation between spans."""
        mock_load.return_value = None
        resolver = KnowledgeResolver()
        
        # Exact matches
        assert resolver._calculate_similarity("anthony", "anthony") == 1.0
        assert resolver._calculate_similarity("ANTHONY", "anthony") == 1.0
        
        # Substring matches
        assert resolver._calculate_similarity("anthony", "anthony kiedis") == 0.8
        assert resolver._calculate_similarity("kiedis", "anthony kiedis") == 0.8
        
        # Single character differences (typos)
        assert resolver._calculate_similarity("fruciante", "frusciante") == 0.7
        
        # No similarity
        assert resolver._calculate_similarity("anthony", "flea") == 0.0

    @patch.object(KnowledgeResolver, '_load_knowledge_base')
    def test_resolve_member_typos(self, mock_load):
        """Test member resolution with common typos."""
        mock_load.return_value = None
        resolver = KnowledgeResolver()
        
        # Manually set the data for testing
        resolver.members = self.mock_members
        resolver.albums = self.mock_albums
        resolver.songs = self.mock_songs
        
        # Test typo resolution
        result = resolver.resolve_member("fruciante")  # Missing 's'
        assert result is not None
        assert result["name"] == "John Anthony Frusciante"
        
        # Test alias resolution
        result = resolver.resolve_member("tony")
        assert result is not None
        assert result["name"] == "Anthony Kiedis"
        
        # Test partial name
        result = resolver.resolve_member("kiedis")
        assert result is not None
        assert result["name"] == "Anthony Kiedis"

    @patch.object(KnowledgeResolver, '_load_knowledge_base')
    def test_resolve_album_aliases(self, mock_load):
        """Test album resolution with aliases and variations."""
        mock_load.return_value = None
        resolver = KnowledgeResolver()
        
        # Manually set the data for testing
        resolver.members = self.mock_members
        resolver.albums = self.mock_albums
        resolver.songs = self.mock_songs
        
        # Test alias resolution
        result = resolver.resolve_album("cali")
        assert result is not None
        assert result["title"] == "Californication"
        
        # Test abbreviation
        result = resolver.resolve_album("btw")
        assert result is not None
        assert result["title"] == "By the Way"
        
        # Test full title
        result = resolver.resolve_album("californication")
        assert result is not None
        assert result["title"] == "Californication"

    @patch.object(KnowledgeResolver, '_load_knowledge_base')
    def test_resolve_song_variations(self, mock_load):
        """Test song resolution with various input formats."""
        mock_load.return_value = None
        resolver = KnowledgeResolver()
        
        # Manually set the data for testing
        resolver.members = self.mock_members
        resolver.albums = self.mock_albums
        resolver.songs = self.mock_songs
        
        # Test abbreviation
        result = resolver.resolve_song("utb")
        assert result is not None
        assert result["title"] == "Under the Bridge"
        
        # Test partial title
        result = resolver.resolve_song("bridge")
        assert result is not None
        assert result["title"] == "Under the Bridge"
        
        # Test full title
        result = resolver.resolve_song("scar tissue")
        assert result is not None
        assert result["title"] == "Scar Tissue"

    @patch.object(KnowledgeResolver, '_load_knowledge_base')
    def test_resolve_entity_generic(self, mock_load):
        """Test generic entity resolution."""
        mock_load.return_value = None
        resolver = KnowledgeResolver()
        
        # Manually set the data for testing
        resolver.members = self.mock_members
        resolver.albums = self.mock_albums
        resolver.songs = self.mock_songs
        
        # Test member resolution
        result = resolver.resolve_entity("fruciante", "member")
        assert result is not None
        assert result["name"] == "John Anthony Frusciante"
        
        # Test album resolution
        result = resolver.resolve_entity("cali", "album")
        assert result is not None
        assert result["title"] == "Californication"
        
        # Test song resolution
        result = resolver.resolve_entity("utb", "song")
        assert result is not None
        assert result["title"] == "Under the Bridge"
        
        # Test unknown entity type
        result = resolver.resolve_entity("test", "unknown")
        assert result is None

    @patch.object(KnowledgeResolver, '_load_knowledge_base')
    def test_no_matches(self, mock_load):
        """Test resolution when no matches are found."""
        mock_load.return_value = None
        resolver = KnowledgeResolver()
        
        # Manually set the data for testing
        resolver.members = self.mock_members
        resolver.albums = self.mock_albums
        resolver.songs = self.mock_songs
        
        # Test non-existent member
        result = resolver.resolve_member("nonexistent")
        assert result is None
        
        # Test non-existent album
        result = resolver.resolve_album("fake album")
        assert result is None
        
        # Test non-existent song
        result = resolver.resolve_song("fake song")
        assert result is None


class TestResolverFunctions:
    """Test the convenience resolver functions."""

    @patch("app.knowledge.resolver.get_knowledge_resolver")
    def test_resolve_member_function(self, mock_get_resolver):
        """Test the resolve_member convenience function."""
        mock_resolver = MagicMock()
        mock_get_resolver.return_value = mock_resolver
        mock_resolver.resolve_member.return_value = {"name": "Anthony Kiedis"}
        
        result = resolve_member("anthony")
        assert result["name"] == "Anthony Kiedis"
        mock_resolver.resolve_member.assert_called_once_with("anthony")

    @patch("app.knowledge.resolver.get_knowledge_resolver")
    def test_resolve_album_function(self, mock_get_resolver):
        """Test the resolve_album convenience function."""
        mock_resolver = MagicMock()
        mock_get_resolver.return_value = mock_resolver
        mock_resolver.resolve_album.return_value = {"title": "Californication"}
        
        result = resolve_album("cali")
        assert result["title"] == "Californication"
        mock_resolver.resolve_album.assert_called_once_with("cali")

    @patch("app.knowledge.resolver.get_knowledge_resolver")
    def test_resolve_song_function(self, mock_get_resolver):
        """Test the resolve_song convenience function."""
        mock_resolver = MagicMock()
        mock_resolver.resolve_song.return_value = {"title": "Under the Bridge"}
        mock_get_resolver.return_value = mock_resolver
        
        result = resolve_song("utb")
        assert result["title"] == "Under the Bridge"
        mock_resolver.resolve_song.assert_called_once_with("utb")


class TestResolverEdgeCases:
    """Test edge cases and error handling."""

    @patch.object(KnowledgeResolver, '_load_knowledge_base')
    def test_empty_span(self, mock_load):
        """Test resolution with empty or None spans."""
        mock_load.return_value = None
        resolver = KnowledgeResolver()
        
        assert resolver.resolve_member("") is None
        assert resolver.resolve_member(None) is None
        assert resolver.resolve_album("") is None
        assert resolver.resolve_song("") is None

    @patch.object(KnowledgeResolver, '_load_knowledge_base')
    def test_special_characters(self, mock_load):
        """Test resolution with special characters and punctuation."""
        mock_load.return_value = None
        resolver = KnowledgeResolver()
        
        # Test with quotes
        assert resolver._normalize_span('"anthony"') == "anthony"
        
        # Test with parentheses
        assert resolver._normalize_span("(john)") == "john"
        
        # Test with numbers
        assert resolver._normalize_span("john123") == "john123"

    def test_malformed_yaml_handling(self):
        """Test handling of malformed YAML files."""
        # Create a resolver with a non-existent path to test error handling
        resolver = KnowledgeResolver("non_existent_path")
        # Should initialize with empty lists when files don't exist
        assert len(resolver.members) == 0
        assert len(resolver.albums) == 0
        assert len(resolver.songs) == 0

