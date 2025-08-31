#!/usr/bin/env python3
"""
Build SQLite FTS database from RHCP knowledge base.

This script ingests data from YAML files and creates a searchable facts database
with full-text search capabilities to reduce hallucination in responses.
"""

import os
import sqlite3
import yaml  # type: ignore
from pathlib import Path
from typing import List, Dict, Any
import argparse
import sys

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infra.logging import get_logger

logger = get_logger(__name__)

# Database schema
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,           -- 'member', 'album', 'song'
    canonical TEXT NOT NULL,      -- Canonical name/title
    field TEXT NOT NULL,          -- Field name (e.g., 'name', 'title', 'year', 'role')
    value TEXT NOT NULL,          -- Field value
    year INTEGER,                 -- Year (if applicable)
    source TEXT NOT NULL,         -- Source file
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create FTS virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    type,
    canonical,
    field,
    value,
    year,
    source,
    content='facts',
    content_rowid='id'
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(type);
CREATE INDEX IF NOT EXISTS idx_facts_canonical ON facts(canonical);
CREATE INDEX IF NOT EXISTS idx_facts_field ON facts(field);
CREATE INDEX IF NOT EXISTS idx_facts_year ON facts(year);

-- Create triggers to keep FTS table in sync
CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(type, canonical, field, value, year, source) 
    VALUES (new.type, new.canonical, new.field, new.value, new.year, new.source);
END;

CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, type, canonical, field, value, year, source) 
    VALUES('delete', old.type, old.canonical, old.field, old.value, old.year, old.source);
END;

CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, type, canonical, field, value, year, source) 
    VALUES('delete', old.type, old.canonical, old.field, old.value, old.year, old.source);
    INSERT INTO facts_fts(type, canonical, field, value, year, source) 
    VALUES (new.type, new.canonical, new.field, new.value, new.year, new.source);
END;
"""


def load_yaml_data(file_path: Path) -> Dict[str, Any]:
    """Load data from a YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        logger.info(f"Loaded {file_path.name}")
        return data if data else {}
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return {}


def extract_member_facts(member_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract atomic facts from member data."""
    facts = []
    member_name = member_data.get('name', '')
    canonical = member_data.get('canonical', '')
    
    # Basic member facts
    facts.append({
        'type': 'member',
        'canonical': canonical,
        'field': 'name',
        'value': member_name,
        'year': None,
        'source': 'members.yml'
    })
    
    # Aliases
    aliases = member_data.get('aliases', [])
    for alias in aliases:
        facts.append({
            'type': 'member',
            'canonical': canonical,
            'field': 'alias',
            'value': alias,
            'year': None,
            'source': 'members.yml'
        })
    
    # Roles
    roles = member_data.get('roles', [])
    for role in roles:
        facts.append({
            'type': 'member',
            'canonical': canonical,
            'field': 'role',
            'value': role,
            'year': None,
            'source': 'members.yml'
        })
    
    # Join year
    join_year = member_data.get('join_year')
    if join_year:
        facts.append({
            'type': 'member',
            'canonical': canonical,
            'field': 'join_year',
            'value': str(join_year),
            'year': join_year,
            'source': 'members.yml'
        })
    
    # Leave years
    leave_years = member_data.get('leave_years', [])
    for year in leave_years:
        facts.append({
            'type': 'member',
            'canonical': canonical,
            'field': 'leave_year',
            'value': str(year),
            'year': year,
            'source': 'members.yml'
        })
    
    # Notes
    notes = member_data.get('notes', '')
    if notes:
        facts.append({
            'type': 'member',
            'canonical': canonical,
            'field': 'notes',
            'value': notes,
            'year': None,
            'source': 'members.yml'
        })
    
    # Active status
    active = member_data.get('active', None)
    if active is not None:
        facts.append({
            'type': 'member',
            'canonical': canonical,
            'field': 'active',
            'value': str(active),
            'year': None,
            'source': 'members.yml'
        })
    
    return facts


def extract_album_facts(album_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract atomic facts from album data."""
    facts = []
    album_title = album_data.get('title', '')
    canonical = album_data.get('canonical', '')
    
    # Basic album facts
    facts.append({
        'type': 'album',
        'canonical': canonical,
        'field': 'title',
        'value': album_title,
        'year': None,
        'source': 'albums.yml'
    })
    
    # Aliases
    aliases = album_data.get('aliases', [])
    for alias in aliases:
        facts.append({
            'type': 'album',
            'canonical': canonical,
            'field': 'alias',
            'value': alias,
            'year': None,
            'source': 'albums.yml'
        })
    
    # Year
    year = album_data.get('year')
    if year:
        facts.append({
            'type': 'album',
            'canonical': canonical,
            'field': 'year',
            'value': str(year),
            'year': year,
            'source': 'albums.yml'
        })
    
    # Label
    label = album_data.get('label', '')
    if label:
        facts.append({
            'type': 'album',
            'canonical': canonical,
            'field': 'label',
            'value': label,
            'year': None,
            'source': 'albums.yml'
        })
    
    # Lineup hint
    lineup_hint = album_data.get('lineup_hint', '')
    if lineup_hint:
        facts.append({
            'type': 'album',
            'canonical': canonical,
            'field': 'lineup_hint',
            'value': lineup_hint,
            'year': None,
            'source': 'albums.yml'
        })
    
    # Notes
    notes = album_data.get('notes', '')
    if notes:
        facts.append({
            'type': 'album',
            'canonical': canonical,
            'field': 'notes',
            'value': notes,
            'year': None,
            'source': 'albums.yml'
        })
    
    # Track count
    tracks = album_data.get('tracks')
    if tracks:
        facts.append({
            'type': 'album',
            'canonical': canonical,
            'field': 'tracks',
            'value': str(tracks),
            'year': None,
            'source': 'albums.yml'
        })
    
    return facts


def extract_song_facts(song_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract atomic facts from song data."""
    facts = []
    song_title = song_data.get('title', '')
    canonical = song_data.get('canonical', '')
    
    # Basic song facts
    facts.append({
        'type': 'song',
        'canonical': canonical,
        'field': 'title',
        'value': song_title,
        'year': None,
        'source': 'songs.yml'
    })
    
    # Aliases
    aliases = song_data.get('aliases', [])
    for alias in aliases:
        facts.append({
            'type': 'song',
            'canonical': canonical,
            'field': 'alias',
            'value': alias,
            'year': None,
            'source': 'songs.yml'
        })
    
    # Year
    year = song_data.get('year')
    if year:
        facts.append({
            'type': 'song',
            'canonical': canonical,
            'field': 'year',
            'value': str(year),
            'year': year,
            'source': 'songs.yml'
        })
    
    # Album
    album = song_data.get('album', '')
    if album:
        facts.append({
            'type': 'song',
            'canonical': canonical,
            'field': 'album',
            'value': album,
            'year': None,
            'source': 'songs.yml'
        })
    
    # Track number
    track_no = song_data.get('track_no')
    if track_no:
        facts.append({
            'type': 'song',
            'canonical': canonical,
            'field': 'track_no',
            'value': str(track_no),
            'year': None,
            'source': 'songs.yml'
        })
    
    # Notes
    notes = song_data.get('notes', '')
    if notes:
        facts.append({
            'type': 'song',
            'canonical': canonical,
            'field': 'notes',
            'value': notes,
            'year': None,
            'source': 'songs.yml'
        })
    
    # Writers
    writers = song_data.get('writers', [])
    for writer in writers:
        facts.append({
            'type': 'song',
            'canonical': canonical,
            'field': 'writer',
            'value': writer,
            'year': None,
            'source': 'songs.yml'
        })
    
    return facts


def build_database(db_path: Path, knowledge_dir: Path) -> None:
    """Build the FTS database from knowledge files."""
    logger.info(f"Building FTS database at {db_path}")
    
    # Remove existing database
    if db_path.exists():
        db_path.unlink()
        logger.info("Removed existing database")
    
    # Create database and schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create schema
        cursor.executescript(SCHEMA_SQL)
        logger.info("Created database schema")
        
        # Load knowledge data
        members_path = knowledge_dir / "members.yml"
        albums_path = knowledge_dir / "albums.yml"
        songs_path = knowledge_dir / "songs.yml"
        
        all_facts = []
        
        # Process members
        if members_path.exists():
            members_data = load_yaml_data(members_path)
            for member in members_data.get('members', []):
                all_facts.extend(extract_member_facts(member))
        
        # Process albums
        if albums_path.exists():
            albums_data = load_yaml_data(albums_path)
            for album in albums_data.get('albums', []):
                all_facts.extend(extract_album_facts(album))
        
        # Process songs
        if songs_path.exists():
            songs_data = load_yaml_data(songs_path)
            for song in songs_data.get('songs', []):
                all_facts.extend(extract_song_facts(song))
        
        # Insert facts
        insert_sql = """
        INSERT INTO facts (type, canonical, field, value, year, source)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        cursor.executemany(insert_sql, [
            (fact['type'], fact['canonical'], fact['field'], 
             fact['value'], fact['year'], fact['source'])
            for fact in all_facts
        ])
        
        # Commit and optimize
        conn.commit()
        
        # Optimize FTS table
        cursor.execute("INSERT INTO facts_fts(facts_fts) VALUES('optimize')")
        conn.commit()
        
        logger.info(f"Inserted {len(all_facts)} facts into database")
        
        # Show some statistics
        cursor.execute("SELECT COUNT(*) FROM facts")
        total_facts = cursor.fetchone()[0]
        
        cursor.execute("SELECT type, COUNT(*) FROM facts GROUP BY type")
        type_counts = cursor.fetchall()
        
        logger.info(f"Database statistics:")
        logger.info(f"  Total facts: {total_facts}")
        for fact_type, count in type_counts:
            logger.info(f"  {fact_type}: {count} facts")
        
    except Exception as e:
        logger.error(f"Failed to build database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build RHCP FTS database")
    parser.add_argument(
        "--db-path", 
        default="data/rhcp_fts.sqlite",
        help="Path to output SQLite database (default: data/rhcp_fts.sqlite)"
    )
    parser.add_argument(
        "--knowledge-dir",
        default="data/knowledge",
        help="Path to knowledge directory (default: data/knowledge)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Convert to Path objects
    db_path = Path(args.db_path)
    knowledge_dir = Path(args.knowledge_dir)
    
    # Ensure output directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        build_database(db_path, knowledge_dir)
        logger.info("✅ FTS database built successfully!")
        logger.info(f"Database location: {db_path.absolute()}")
    except Exception as e:
        logger.error(f"❌ Failed to build FTS database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
