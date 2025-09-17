"""
Intelligent matching engine for linking atomic games with DAT entries.

This module implements the core logic for automatically matching imported game metadata
(from sources like MobyGames) with DAT entries (from No-Intro, TOSEC, etc.).
"""

import sqlite3
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

import logging

logger = logging.getLogger(__name__)


@dataclass
class MatchCandidate:
    """Represents a potential match between an atomic game and DAT entry."""
    atomic_id: int
    atomic_title: str
    dat_entry_id: int
    dat_title: str
    base_title: str
    platform_id: int
    platform_name: str
    confidence: float
    match_reasons: List[str]


class GameMatcher:
    """Main class for matching atomic games with DAT entries."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        logger.debug("GameMatcher initialized for database %s", db_path)
        
        # Title normalization patterns
        self.normalization_patterns = [
            # Remove common subtitle separators
            (r'\s*[:;-]\s*', ' '),
            # Remove "The" prefix
            (r'^The\s+', ''),
            # Normalize Roman numerals
            (r'\bII\b', '2'),
            (r'\bIII\b', '3'),
            (r'\bIV\b', '4'),
            (r'\bV\b', '5'),
            (r'\bVI\b', '6'),
            (r'\bVII\b', '7'),
            (r'\bVIII\b', '8'),
            # Remove common words that cause mismatches
            (r'\s+(?:Edition|Version|Release|Remaster|HD|Complete|Special|Limited|Directors?)\b', ''),
            # Normalize spacing
            (r'\s+', ' '),
        ]
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
    
    def normalize_title(self, title: str) -> str:
        """Normalize a title for better matching."""
        normalized = title.strip()
        
        # Apply normalization patterns
        for pattern, replacement in self.normalization_patterns:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Convert to lowercase and strip extra whitespace
        return normalized.lower().strip()
    
    def calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles using multiple methods."""
        # Normalize both titles
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)
        
        # Exact match gets highest score
        if norm1 == norm2:
            return 1.0
        
        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost score for substring matches
        if norm1 in norm2 or norm2 in norm1:
            similarity = max(similarity, 0.8)
        
        # Boost score for word-order independent matches
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        word_overlap = len(words1 & words2) / max(len(words1), len(words2), 1)
        similarity = max(similarity, word_overlap * 0.9)
        
        return similarity
    
    def find_matches_for_atomic_game(self, atomic_id: int, min_confidence: float = 0.7) -> List[MatchCandidate]:
        """Find potential DAT entry matches for a specific atomic game."""
        cursor = self.conn.cursor()
        
        # Get the atomic game details
        cursor.execute("""
            SELECT canonical_title FROM atomic_game_unit WHERE atomic_id = ?
        """, (atomic_id,))
        atomic_row = cursor.fetchone()
        if not atomic_row:
            return []
        
        atomic_title = atomic_row['canonical_title']
        logger.debug("Evaluating atomic game %s (%s)", atomic_title, atomic_id)
        
        # Get all platforms this atomic game has releases for
        cursor.execute("""
            SELECT DISTINCT gr.platform_id, p.name as platform_name
            FROM game_release gr
            JOIN platform p ON gr.platform_id = p.platform_id
            WHERE gr.atomic_id = ?
        """, (atomic_id,))
        platforms = cursor.fetchall()
        logger.debug("Atomic %s (%s) has %d release platforms", atomic_title, atomic_id, len(platforms))
        
        matches = []
        
        for platform_row in platforms:
            platform_id = platform_row['platform_id']
            platform_name = platform_row['platform_name']
            
            # Find DAT entries for this platform AND linked platforms
            # First get the platform and any linked platforms
            linked_platform_ids = self.get_linked_platform_ids(platform_id)
            if not linked_platform_ids:
                logger.debug("No platform links for atomic %s (%s) on platform %s (%s); skipping", atomic_title, atomic_id, platform_name, platform_id)
                continue
            logger.debug("Atomic %s (%s) platform %s (%s) -> %d linked DAT platforms", atomic_title, atomic_id, platform_name, platform_id, len(linked_platform_ids))

            # Find DAT entries for this platform and linked platforms
            placeholders = ','.join(['?' for _ in linked_platform_ids])
            cursor.execute(f"""
                SELECT de.dat_entry_id, de.release_title, de.base_title, de.platform_id, p.name as platform_name
                FROM dat_entry de
                JOIN platform p ON de.platform_id = p.platform_id
                WHERE de.platform_id IN ({placeholders})
                AND de.base_title IS NOT NULL
                AND de.base_title != ''
            """, linked_platform_ids)
            
            dat_entries = cursor.fetchall()
            logger.debug("Atomic %s (%s) platform %s produced %d DAT candidates", atomic_title, atomic_id, platform_name, len(dat_entries))
            if not dat_entries:
                continue
            
            for dat_row in dat_entries:
                # Calculate similarity between atomic title and DAT base title
                base_similarity = self.calculate_similarity(atomic_title, dat_row['base_title'])
                
                # Also check similarity with full release title
                full_similarity = self.calculate_similarity(atomic_title, dat_row['release_title'])
                
                # Use the higher similarity score
                confidence = max(base_similarity, full_similarity)
                
                if confidence >= min_confidence:
                    # Determine match reasons
                    reasons = []
                    if base_similarity >= min_confidence:
                        reasons.append(f"Base title match ({base_similarity:.2f})")
                    if full_similarity >= min_confidence:
                        reasons.append(f"Full title match ({full_similarity:.2f})")
                    
                    match = MatchCandidate(
                        atomic_id=atomic_id,
                        atomic_title=atomic_title,
                        dat_entry_id=dat_row['dat_entry_id'],
                        dat_title=dat_row['release_title'],
                        base_title=dat_row['base_title'],
                        platform_id=platform_id,  # Use original platform, not DAT platform
                        platform_name=platform_name,
                        confidence=confidence,
                        match_reasons=reasons
                    )
                    matches.append(match)
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches
    
    def find_all_potential_matches(self, min_confidence: float = 0.7) -> Dict[int, List[MatchCandidate]]:
        """Find all potential matches between atomic games and DAT entries."""
        cursor = self.conn.cursor()
        
        # Get all atomic games that don't have existing DAT links
        cursor.execute("""
            SELECT DISTINCT agu.atomic_id, agu.canonical_title
            FROM atomic_game_unit agu
            LEFT JOIN dat_atomic_link dal ON agu.atomic_id = dal.atomic_id
            WHERE dal.atomic_id IS NULL
            ORDER BY agu.canonical_title
        """)
        
        atomic_games = cursor.fetchall()
        all_matches = {}
        
        logger.debug("Analyzing %d atomic games for potential DAT matches (min_confidence=%.2f)", len(atomic_games), min_confidence)
        
        for i, atomic_row in enumerate(atomic_games):
            if i % 100 == 0:  # Progress indicator
                logger.debug("Processing game %d/%d: %s", i + 1, len(atomic_games), atomic_row['canonical_title'])
            
            matches = self.find_matches_for_atomic_game(atomic_row['atomic_id'], min_confidence)
            logger.debug("Atomic %s (%s) produced %d match candidates", atomic_row['canonical_title'], atomic_row['atomic_id'], len(matches))
            if matches:
                all_matches[atomic_row['atomic_id']] = matches
        
        return all_matches
    
    def create_automatic_links(self, high_confidence_threshold: float = 0.95) -> Dict[str, int]:
        """Automatically create links for high-confidence matches."""
        cursor = self.conn.cursor()
        stats = {'created': 0, 'skipped': 0, 'errors': 0}
        
        # Find high-confidence matches
        all_matches = self.find_all_potential_matches()
        
        for atomic_id, matches in all_matches.items():
            # Only auto-link if there's exactly one high-confidence match
            high_conf_matches = [m for m in matches if m.confidence >= high_confidence_threshold]
            
            if len(high_conf_matches) == 1:
                match = high_conf_matches[0]
                
                try:
                    # Check if link already exists
                    cursor.execute("""
                        SELECT link_id FROM dat_atomic_link 
                        WHERE atomic_id = ? AND dat_entry_id = ?
                    """, (atomic_id, match.dat_entry_id))
                    
                    if cursor.fetchone():
                        stats['skipped'] += 1
                        continue
                    
                    # Create the link
                    cursor.execute("""
                        INSERT INTO dat_atomic_link (atomic_id, dat_entry_id, confidence, match_type)
                        VALUES (?, ?, ?, 'automatic')
                    """, (atomic_id, match.dat_entry_id, match.confidence))
                    
                    self.conn.commit()
                    stats['created'] += 1
                    
                    logger.info("Auto-linked: %s -> %s (confidence=%.3f)", match.atomic_title, match.base_title, match.confidence)
                    
                except Exception as e:
                    logger.exception("Error creating link for atomic_id %s", atomic_id)
                    stats['errors'] += 1
                    self.conn.rollback()
        
        return stats
    
    def get_unmatched_atomic_games(self) -> List[Dict]:
        """Get atomic games that don't have any DAT links."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT agu.atomic_id, agu.canonical_title, 
                   COUNT(gr.release_id) as release_count,
                   GROUP_CONCAT(DISTINCT p.name) as platforms
            FROM atomic_game_unit agu
            LEFT JOIN dat_atomic_link dal ON agu.atomic_id = dal.atomic_id
            LEFT JOIN game_release gr ON agu.atomic_id = gr.atomic_id
            LEFT JOIN platform p ON gr.platform_id = p.platform_id
            WHERE dal.atomic_id IS NULL
            GROUP BY agu.atomic_id, agu.canonical_title
            ORDER BY agu.canonical_title
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_manual_curation_queue(self, min_confidence: float = 0.5, max_confidence: float = 0.95) -> List[Dict]:
        """Get potential matches that need manual curation."""
        all_matches = self.find_all_potential_matches(min_confidence)
        
        curation_queue = []
        
        for atomic_id, matches in all_matches.items():
            # Filter matches in the manual curation range
            manual_matches = [m for m in matches if min_confidence <= m.confidence < max_confidence]
            
            if manual_matches:
                curation_queue.append({
                    'atomic_id': atomic_id,
                    'atomic_title': manual_matches[0].atomic_title,
                    'match_count': len(manual_matches),
                    'best_match': manual_matches[0],
                    'all_matches': manual_matches[:5]  # Limit to top 5 for display
                })
        
        return curation_queue


    def get_linked_platform_ids(self, platform_id: int) -> List[int]:
        """Return DAT platform IDs linked to the given platform via mappings."""
        cursor = self.conn.cursor()

        linked_ids = set()

        # Direct mappings from the canonical platform to DAT platforms
        cursor.execute("""
            SELECT DISTINCT dat_platform_id
            FROM platform_links
            WHERE atomic_platform_id = ?
        """, (platform_id,))
        linked_ids.update(row['dat_platform_id'] for row in cursor.fetchall() if row['dat_platform_id'] is not None)

        # If this platform appears as a DAT alias, follow it back to the canonical platforms
        cursor.execute("""
            SELECT DISTINCT atomic_platform_id
            FROM platform_links
            WHERE dat_platform_id = ?
        """, (platform_id,))
        reverse_atomic_ids = [row['atomic_platform_id'] for row in cursor.fetchall() if row['atomic_platform_id'] is not None]

        if reverse_atomic_ids:
            placeholders = ','.join('?' for _ in reverse_atomic_ids)
            cursor.execute(f"""
                SELECT DISTINCT dat_platform_id
                FROM platform_links
                WHERE atomic_platform_id IN ({placeholders})
            """, reverse_atomic_ids)
            linked_ids.update(row['dat_platform_id'] for row in cursor.fetchall() if row['dat_platform_id'] is not None)

        # Only return DAT platform IDs that are explicitly linked
        if not linked_ids:
            logger.debug("Platform %s has no DAT platform links", platform_id)
            return []

        linked_list = sorted(linked_ids)
        logger.debug("Platform %s resolves to DAT platforms %s", platform_id, linked_list)
        return linked_list

    def create_platform_link(self, atomic_platform_id: int, dat_platform_id: int, confidence: float = 1.0) -> bool:
        """Create a link between atomic and DAT platforms."""
        if atomic_platform_id == dat_platform_id:
            return True  # Same platform, no link needed
            
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO platform_links 
                (atomic_platform_id, dat_platform_id, confidence)
                VALUES (?, ?, ?)
            """, (atomic_platform_id, dat_platform_id, confidence))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error creating platform link: {e}")
            return False

    def auto_link_platforms(self) -> Dict[str, int]:
        """Automatically link platforms based on name similarity."""
        cursor = self.conn.cursor()
        
        # Get all platforms
        cursor.execute("SELECT platform_id, name FROM platform ORDER BY name")
        platforms = cursor.fetchall()
        
        stats = {'linked': 0, 'skipped': 0, 'errors': 0}
        
        # Platform name mappings for common variations
        platform_mappings = {
            'NES': ['Nintendo Entertainment System', 'Nintendo Famicom & Entertainment System'],
            'SNES': ['Super Nintendo Entertainment System', 'Super Famicom'],
            'Genesis': ['Sega Genesis', 'Mega Drive'],
            'Game Boy': ['Nintendo Game Boy'],
            'Game Boy Color': ['Nintendo Game Boy Color'],
            'Game Boy Advance': ['Nintendo Game Boy Advance'],
            'Nintendo 64': ['Nintendo 64'],
            'PlayStation': ['Sony PlayStation'],
            'PlayStation 2': ['Sony PlayStation 2'],
            'PlayStation 3': ['Sony PlayStation 3'],
            'Xbox': ['Microsoft Xbox'],
            'Xbox 360': ['Microsoft Xbox 360'],
            'Arcade': ['Arcade'],
            'DOS': ['MS-DOS', 'PC DOS'],
            'Windows': ['Microsoft Windows'],
            'Mac': ['Apple Macintosh', 'macOS'],
            'Linux': ['GNU/Linux']
        }
        
        for atomic_platform in platforms:
            atomic_id = atomic_platform['platform_id']
            atomic_name = atomic_platform['name']
            
            # Check if we have a mapping for this platform
            if atomic_name in platform_mappings:
                target_names = platform_mappings[atomic_name]
                
                for target_name in target_names:
                    # Find DAT platform with this name
                    cursor.execute("""
                        SELECT platform_id FROM platform WHERE name = ?
                    """, (target_name,))
                    dat_platform = cursor.fetchone()
                    
                    if dat_platform:
                        if self.create_platform_link(atomic_id, dat_platform['platform_id']):
                            stats['linked'] += 1
                            print(f"Linked: {atomic_name} -> {target_name}")
                        else:
                            stats['errors'] += 1
                    else:
                        stats['skipped'] += 1
                        print(f"No DAT platform found for: {target_name}")
        
        return stats


# Database schema updates needed for linking
def create_dat_atomic_link_table(db_path: str):
    """Create the table for linking atomic games to DAT entries."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dat_atomic_link (
            link_id INTEGER PRIMARY KEY,
            atomic_id INTEGER NOT NULL REFERENCES atomic_game_unit(atomic_id),
            dat_entry_id INTEGER NOT NULL REFERENCES dat_entry(dat_entry_id),
            confidence REAL NOT NULL,
            match_type TEXT NOT NULL DEFAULT 'manual',  -- 'automatic' or 'manual'
            created_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(atomic_id, dat_entry_id)
        )
    """)
    
    # Add indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dat_atomic_link_atomic ON dat_atomic_link(atomic_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dat_atomic_link_dat ON dat_atomic_link(dat_entry_id)")
    
    conn.commit()
    conn.close()
    print("Created dat_atomic_link table and indexes")


# Command-line interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Game matching engine for DAT and metadata linking")
    parser.add_argument('--db_path', required=True, help="Path to the SQLite database")
    parser.add_argument('--action', choices=['create_table', 'auto_link', 'show_unmatched', 'show_curation'], 
                        required=True, help="Action to perform")
    parser.add_argument('--min_confidence', type=float, default=0.7, help="Minimum confidence for matches")
    parser.add_argument('--auto_threshold', type=float, default=0.95, help="Threshold for automatic linking")
    
    args = parser.parse_args()
    
    if args.action == 'create_table':
        create_dat_atomic_link_table(args.db_path)
    
    elif args.action == 'auto_link':
        matcher = GameMatcher(args.db_path)
        try:
            stats = matcher.create_automatic_links(args.auto_threshold)
            print(f"\nAutomatic linking results:")
            print(f"  Created: {stats['created']} links")
            print(f"  Skipped: {stats['skipped']} (already existed)")
            print(f"  Errors: {stats['errors']}")
        finally:
            matcher.close()
    
    elif args.action == 'show_unmatched':
        matcher = GameMatcher(args.db_path)
        try:
            unmatched = matcher.get_unmatched_atomic_games()
            print(f"\nFound {len(unmatched)} unmatched atomic games:")
            for game in unmatched[:20]:  # Show first 20
                print(f"  {game['canonical_title']} ({game['release_count']} releases on {game['platforms']})")
        finally:
            matcher.close()
    
    elif args.action == 'show_curation':
        matcher = GameMatcher(args.db_path)
        try:
            queue = matcher.get_manual_curation_queue()
            print(f"\nFound {len(queue)} games needing manual curation:")
            for item in queue[:10]:  # Show first 10
                best = item['best_match']
                print(f"\n  Atomic: {item['atomic_title']}")
                print(f"  Best match: {best.base_title} ({best.confidence:.3f}) on {best.platform_name}")
                print(f"  {item['match_count']} total potential matches")
        finally:
            matcher.close()
