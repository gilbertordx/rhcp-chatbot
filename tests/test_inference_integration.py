"""Integration tests for inference pipeline with knowledge resolver."""

import pytest
from unittest.mock import patch, MagicMock

from app.core.inference import canonicalize_entities
from app.schemas import Entity


class TestInferenceResolverIntegration:
    """Test integration between inference pipeline and knowledge resolver."""

    @patch("app.core.inference.get_knowledge_resolver")
    def test_canonicalize_entities_member_resolution(self, mock_get_resolver):
        """Test that canonicalize_entities properly uses the knowledge resolver for members."""
        # Mock the resolver
        mock_resolver = MagicMock()
        mock_get_resolver.return_value = mock_resolver
        
        # Mock resolver responses
        mock_resolver.resolve_member.return_value = {
            "name": "John Anthony Frusciante",
            "canonical": "john frusciante",
            "aliases": ["john", "frusciante", "fruciante"],
            "roles": ["guitar", "backing vocals"],
            "join_year": 1988,
            "active": True,
        }
        mock_resolver.resolve_album.return_value = None
        mock_resolver.resolve_song.return_value = None
        
        # Test raw entities input
        raw_entities = [
            {
                "type": "member",
                "value": {"text": "fruciante"},
                "confidence": 0.8,
            }
        ]
        
        # Call canonicalize_entities
        canonical_entities = canonicalize_entities(raw_entities)
        
        # Verify the result
        assert len(canonical_entities) == 1
        assert canonical_entities[0].type == "member"
        assert canonical_entities[0].value["name"] == "John Anthony Frusciante"
        assert canonical_entities[0].confidence == 0.8
        
        # Verify resolver was called correctly
        mock_resolver.resolve_member.assert_called_once_with("fruciante")

    @patch("app.core.inference.get_knowledge_resolver")
    def test_canonicalize_entities_album_resolution(self, mock_get_resolver):
        """Test that canonicalize_entities properly uses the knowledge resolver for albums."""
        # Mock the resolver
        mock_resolver = MagicMock()
        mock_get_resolver.return_value = mock_resolver
        
        # Mock resolver responses
        mock_resolver.resolve_member.return_value = None
        mock_resolver.resolve_album.return_value = {
            "title": "Blood Sugar Sex Magik",
            "canonical": "blood sugar sex magik",
            "aliases": ["bssm", "blood sugar"],
            "year": 1991,
            "label": "Warner Bros.",
        }
        mock_resolver.resolve_song.return_value = None
        
        # Test raw entities input
        raw_entities = [
            {
                "type": "album",
                "value": {"text": "bssm"},
                "confidence": 0.9,
            }
        ]
        
        # Call canonicalize_entities
        canonical_entities = canonicalize_entities(raw_entities)
        
        # Verify the result
        assert len(canonical_entities) == 1
        assert canonical_entities[0].type == "album"
        assert canonical_entities[0].value["title"] == "Blood Sugar Sex Magik"
        assert canonical_entities[0].confidence == 0.9
        
        # Verify resolver was called correctly
        mock_resolver.resolve_album.assert_called_once_with("bssm")

    @patch("app.core.inference.get_knowledge_resolver")
    def test_canonicalize_entities_song_resolution(self, mock_get_resolver):
        """Test that canonicalize_entities properly uses the knowledge resolver for songs."""
        # Mock the resolver
        mock_resolver = MagicMock()
        mock_get_resolver.return_value = mock_resolver
        
        # Mock resolver responses
        mock_resolver.resolve_member.return_value = None
        mock_resolver.resolve_album.return_value = None
        mock_resolver.resolve_song.return_value = {
            "title": "Under the Bridge",
            "canonical": "under the bridge",
            "aliases": ["utb", "bridge"],
            "year": 1991,
            "album": "Blood Sugar Sex Magik",
        }
        
        # Test raw entities input
        raw_entities = [
            {
                "type": "song",
                "value": {"text": "utb"},
                "confidence": 0.7,
            }
        ]
        
        # Call canonicalize_entities
        canonical_entities = canonicalize_entities(raw_entities)
        
        # Verify the result
        assert len(canonical_entities) == 1
        assert canonical_entities[0].type == "song"
        assert canonical_entities[0].value["title"] == "Under the Bridge"
        assert canonical_entities[0].confidence == 0.7
        
        # Verify resolver was called correctly
        mock_resolver.resolve_song.assert_called_once_with("utb")

    @patch("app.core.inference.get_knowledge_resolver")
    def test_canonicalize_entities_fallback_when_no_resolution(self, mock_get_resolver):
        """Test that canonicalize_entities falls back to original value when no resolution found."""
        # Mock the resolver
        mock_resolver = MagicMock()
        mock_get_resolver.return_value = mock_resolver
        
        # Mock resolver responses - all return None
        mock_resolver.resolve_member.return_value = None
        mock_resolver.resolve_album.return_value = None
        mock_resolver.resolve_song.return_value = None
        
        # Test raw entities input
        raw_entities = [
            {
                "type": "member",
                "value": {"text": "unknown_member"},
                "confidence": 0.5,
            }
        ]
        
        # Call canonicalize_entities
        canonical_entities = canonicalize_entities(raw_entities)
        
        # Verify the result falls back to original value
        assert len(canonical_entities) == 1
        assert canonical_entities[0].type == "member"
        assert canonical_entities[0].value == {"text": "unknown_member"}
        assert canonical_entities[0].confidence == 0.5
        
        # Verify resolver was called
        mock_resolver.resolve_member.assert_called_once_with("unknown_member")

    @patch("app.core.inference.get_knowledge_resolver")
    def test_canonicalize_entities_mixed_types(self, mock_get_resolver):
        """Test that canonicalize_entities handles multiple entity types correctly."""
        # Mock the resolver
        mock_resolver = MagicMock()
        mock_get_resolver.return_value = mock_resolver
        
        # Mock resolver responses
        mock_resolver.resolve_member.return_value = {
            "name": "Anthony Kiedis",
            "canonical": "anthony kiedis",
            "aliases": ["anthony", "kiedis"],
        }
        mock_resolver.resolve_album.return_value = {
            "title": "Californication",
            "canonical": "californication",
            "aliases": ["cali"],
        }
        mock_resolver.resolve_song.return_value = None
        
        # Test raw entities input with mixed types
        raw_entities = [
            {
                "type": "member",
                "value": {"text": "anthony"},
                "confidence": 0.8,
            },
            {
                "type": "album",
                "value": {"text": "cali"},
                "confidence": 0.9,
            },
            {
                "type": "song",
                "value": {"text": "unknown_song"},
                "confidence": 0.6,
            },
        ]
        
        # Call canonicalize_entities
        canonical_entities = canonicalize_entities(raw_entities)
        
        # Verify the results
        assert len(canonical_entities) == 3
        
        # Check member resolution
        assert canonical_entities[0].type == "member"
        assert canonical_entities[0].value["name"] == "Anthony Kiedis"
        
        # Check album resolution
        assert canonical_entities[1].type == "album"
        assert canonical_entities[1].value["title"] == "Californication"
        
        # Check song fallback
        assert canonical_entities[2].type == "song"
        assert canonical_entities[2].value == {"text": "unknown_song"}
        
        # Verify resolver calls
        mock_resolver.resolve_member.assert_called_with("anthony")
        mock_resolver.resolve_album.assert_called_with("cali")
        mock_resolver.resolve_song.assert_called_with("unknown_song")
