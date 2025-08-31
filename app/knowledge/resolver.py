"""Entity resolver for RHCP knowledge base.

This module provides functions to resolve user input spans (including typos,
variants, and diacritics) to canonical entities from the knowledge base.
"""

import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Literal
import yaml  # type: ignore

from app.infra.logging import get_logger

logger = get_logger(__name__)

# Type aliases
EntityType = Literal["member", "album", "song"]
CanonicalEntity = Dict[str, Any]
ResolutionResult = Optional[CanonicalEntity]

class KnowledgeResolver:
    """Resolves user spans to canonical entities from the knowledge base."""
    
    def __init__(self, knowledge_dir: str = "data/knowledge"):
        """Initialize the resolver with knowledge base data.
        
        Args:
            knowledge_dir: Path to knowledge base directory
        """
        self.knowledge_dir = Path(knowledge_dir)
        self.members: List[CanonicalEntity] = []
        self.albums: List[CanonicalEntity] = []
        self.songs: List[CanonicalEntity] = []
        self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> None:
        """Load all knowledge base files."""
        try:
            # Load members
            members_path = self.knowledge_dir / "members.yml"
            if members_path.exists():
                with open(members_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.members = data.get('members', [])
                    logger.info(f"Loaded {len(self.members)} members from knowledge base")
            
            # Load albums
            albums_path = self.knowledge_dir / "albums.yml"
            if albums_path.exists():
                with open(albums_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.albums = data.get('albums', [])
                    logger.info(f"Loaded {len(self.albums)} albums from knowledge base")
            
            # Load songs
            songs_path = self.knowledge_dir / "songs.yml"
            if songs_path.exists():
                with open(songs_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.songs = data.get('songs', [])
                    logger.info(f"Loaded {len(self.songs)} songs from knowledge base")
                    
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            # Initialize with empty lists to prevent crashes
            self.members = []
            self.albums = []
            self.songs = []
    
    def _normalize_span(self, span: str | None) -> str:
        """Normalize a span for comparison.
        
        Args:
            span: Raw span text
            
        Returns:
            Normalized span (lowercase, no diacritics, trimmed)
        """
        if not span:
            return ""
        
        # Convert to lowercase
        normalized = span.lower().strip()
        
        # Remove diacritics (e.g., Björk -> Bjork)
        normalized = unicodedata.normalize('NFD', normalized)
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common punctuation that might interfere with matching
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized
    
    def _calculate_similarity(self, span: str, target: str) -> float:
        """Calculate similarity between span and target (0.0 to 1.0)."""
        if not span or not target:
            return 0.0
        
        # Normalize both spans for comparison
        span_norm = self._normalize_span(span)
        target_norm = self._normalize_span(target)
        
        if span_norm == target_norm:
            return 1.0
        
        # Check if span is contained in target or vice versa
        if span_norm in target_norm or target_norm in span_norm:
            return 0.8
        
        # Check for common typo patterns first (higher priority)
        # Transposed characters (e.g., "teh" -> "the")
        if len(span_norm) == len(target_norm) and len(span_norm) >= 3:
            for i in range(len(span_norm) - 1):
                # Swap adjacent characters
                swapped = span_norm[:i] + span_norm[i+1] + span_norm[i] + span_norm[i+2:]
                if swapped == target_norm:
                    return 0.6
        
        # Check for phonetic similarities (basic)
        # Common sound-alike patterns
        phonetic_patterns = [
            ('f', 'ph'), ('c', 'k'), ('s', 'z'), ('x', 'ks'),
            ('qu', 'kw'), ('tion', 'shun'), ('sion', 'zhun')
        ]
        
        span_phonetic = span_norm
        target_phonetic = target_norm
        
        for pattern1, pattern2 in phonetic_patterns:
            span_phonetic = span_phonetic.replace(pattern1, pattern2)
            target_phonetic = target_phonetic.replace(pattern1, pattern2)
        
        if span_phonetic == target_phonetic:
            return 0.6
        
        # Check for common typos (single character differences)
        if len(span_norm) == len(target_norm):
            diff_count = sum(1 for a, b in zip(span_norm, target_norm) if a != b)
            if diff_count == 1:
                return 0.7
            elif diff_count == 2:
                return 0.5
        
        # Check for length differences (insertions/deletions)
        if abs(len(span_norm) - len(target_norm)) == 1:
            # Check if one is a substring of the other
            if span_norm in target_norm or target_norm in span_norm:
                return 0.6
            
            # Check for single character insertion/deletion (e.g., "fruciante" vs "frusciante")
            shorter = span_norm if len(span_norm) < len(target_norm) else target_norm
            longer = target_norm if len(span_norm) < len(target_norm) else span_norm
            
            # Try removing one character at a time from the longer string
            for i in range(len(longer)):
                candidate = longer[:i] + longer[i+1:]
                if candidate == shorter:
                    return 0.7
        
        return 0.0
    
    def resolve_member(self, span: str) -> ResolutionResult:
        """Resolve a span to a canonical member.
        
        Args:
            span: User input span (e.g., "fruciante", "john")
            
        Returns:
            Canonical member entity or None if not found
        """
        normalized_span = self._normalize_span(span)
        
        # First try exact matches with canonical names
        for member in self.members:
            if self._normalize_span(member['canonical']) == normalized_span:
                logger.debug(f"Exact match for member: {span} -> {member['name']}")
                return member
        
        # Then try aliases
        for member in self.members:
            aliases = member.get('aliases', [])
            for alias in aliases:
                if self._normalize_span(alias) == normalized_span:
                    logger.debug(f"Alias match for member: {span} -> {member['name']}")
                    return member
        
        # Finally try fuzzy matching
        best_match = None
        best_score = 0.0
        
        for member in self.members:
            # Check canonical name
            score = self._calculate_similarity(normalized_span, self._normalize_span(member['canonical']))
            if score > best_score:
                best_score = score
                best_match = member
            
            # Check aliases
            aliases = member.get('aliases', [])
            for alias in aliases:
                score = self._calculate_similarity(normalized_span, self._normalize_span(alias))
                if score > best_score:
                    best_score = score
                    best_match = member
        
        # Only return if similarity is high enough and we have a match
        if best_match is not None and best_score >= 0.6:
            logger.debug(f"Fuzzy match for member: {span} -> {best_match['name']} (score: {best_score})")
            return best_match
        
        logger.debug(f"No match found for member: {span}")
        return None
    
    def resolve_album(self, span: str) -> ResolutionResult:
        """Resolve a span to a canonical album.
        
        Args:
            span: User input span (e.g., "californication", "bssm")
            
        Returns:
            Canonical album entity or None if not found
        """
        normalized_span = self._normalize_span(span)
        
        # First try exact matches with canonical names
        for album in self.albums:
            if self._normalize_span(album['canonical']) == normalized_span:
                logger.debug(f"Exact match for album: {span} -> {album['title']}")
                return album
        
        # Then try aliases
        for album in self.albums:
            aliases = album.get('aliases', [])
            for alias in aliases:
                if self._normalize_span(alias) == normalized_span:
                    logger.debug(f"Alias match for album: {span} -> {album['title']}")
                    return album
        
        # Finally try fuzzy matching
        best_match = None
        best_score = 0.0
        
        for album in self.albums:
            # Check canonical name
            score = self._calculate_similarity(normalized_span, self._normalize_span(album['canonical']))
            if score > best_score:
                best_score = score
                best_match = album
            
            # Check aliases
            aliases = album.get('aliases', [])
            for alias in aliases:
                score = self._calculate_similarity(normalized_span, self._normalize_span(alias))
                if score > best_score:
                    best_score = score
                    best_match = album
        
        # Only return if similarity is high enough and we have a match
        if best_match is not None and best_score >= 0.6:
            logger.debug(f"Fuzzy match for album: {span} -> {best_match['title']} (score: {best_score})")
            return best_match
        
        logger.debug(f"No match found for album: {span}")
        return None
    
    def resolve_song(self, span: str) -> ResolutionResult:
        """Resolve a span to a canonical song.
        
        Args:
            span: User input span (e.g., "under the bridge", "utb")
            
        Returns:
            Canonical song entity or None if not found
        """
        normalized_span = self._normalize_span(span)
        
        # First try exact matches with canonical names
        for song in self.songs:
            if self._normalize_span(song['canonical']) == normalized_span:
                logger.debug(f"Exact match for song: {span} -> {song['title']}")
                return song
        
        # Then try aliases
        for song in self.songs:
            aliases = song.get('aliases', [])
            for alias in aliases:
                if self._normalize_span(alias) == normalized_span:
                    logger.debug(f"Alias match for song: {span} -> {song['title']}")
                    return song
        
        # Finally try fuzzy matching
        best_match = None
        best_score = 0.0
        
        for song in self.songs:
            # Check canonical name
            score = self._calculate_similarity(normalized_span, self._normalize_span(song['canonical']))
            if score > best_score:
                best_score = score
                best_match = song
            
            # Check aliases
            aliases = song.get('aliases', [])
            for alias in aliases:
                score = self._calculate_similarity(normalized_span, self._normalize_span(alias))
                if score > best_score:
                    best_score = score
                    best_match = song
        
        # Only return if similarity is high enough and we have a match
        if best_match is not None and best_score >= 0.6:
            logger.debug(f"Fuzzy match for song: {span} -> {best_match['title']} (score: {best_score})")
            return best_match
        
        logger.debug(f"No match found for song: {span}")
        return None
    
    def resolve_entity(self, span: str, entity_type: Optional[EntityType] = None) -> ResolutionResult:
        """Resolve a span to a canonical entity of any type.
        
        Args:
            span: User input span
            entity_type: Optional entity type to restrict search
            
        Returns:
            Canonical entity or None if not found
        """
        if entity_type == "member":
            return self.resolve_member(span)
        elif entity_type == "album":
            return self.resolve_album(span)
        elif entity_type == "song":
            return self.resolve_song(span)
        else:
            # Try all types and return the best match
            member_result = self.resolve_member(span)
            album_result = self.resolve_album(span)
            song_result = self.resolve_song(span)
            
            # Return the first non-None result, prioritizing members
            if member_result:
                return member_result
            elif album_result:
                return album_result
            elif song_result:
                return song_result
            
            return None

# Global resolver instance
_knowledge_resolver: Optional[KnowledgeResolver] = None

def get_knowledge_resolver() -> KnowledgeResolver:
    """Get the global knowledge resolver instance."""
    global _knowledge_resolver
    if _knowledge_resolver is None:
        _knowledge_resolver = KnowledgeResolver()
    return _knowledge_resolver

def resolve_member(span: str) -> ResolutionResult:
    """Resolve a span to a canonical member."""
    return get_knowledge_resolver().resolve_member(span)

def resolve_album(span: str) -> ResolutionResult:
    """Resolve a span to a canonical album."""
    return get_knowledge_resolver().resolve_album(span)

def resolve_song(span: str) -> ResolutionResult:
    """Resolve a span to a canonical song."""
    return get_knowledge_resolver().resolve_song(span)

def resolve_entity(span: str, entity_type: Optional[EntityType] = None) -> ResolutionResult:
    """Resolve a span to a canonical entity of any type."""
    return get_knowledge_resolver().resolve_entity(span, entity_type)
