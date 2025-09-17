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
        
        # Find DAT entries across ALL platforms (not just same platform)
        # This allows matching games that exist on different platform naming conventions
        cursor.execute("""
            SELECT de.dat_entry_id, de.release_title, de.base_title, de.platform_id, p.name as platform_name
            FROM dat_entry de
            JOIN platform p ON de.platform_id = p.platform_id
            WHERE de.base_title IS NOT NULL
            AND de.base_title != ''
        """)
        
        dat_entries = cursor.fetchall()
        matches = []
        
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
                    platform_id=dat_row['platform_id'],
                    platform_name=dat_row['platform_name'],
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
        
        print(f"Analyzing {len(atomic_games)} atomic games for potential DAT matches...")
        
        for i, atomic_row in enumerate(atomic_games):
            if i % 100 == 0:  # Progress indicator
                print(f"Processing game {i+1}/{len(atomic_games)}: {atomic_row['canonical_title']}")
            
            matches = self.find_matches_for_atomic_game(atomic_row['atomic_id'], min_confidence)
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
                    
                    print(f"Auto-linked: '{match.atomic_title}' -> '{match.base_title}' ({match.confidence:.3f})")
                    
                except Exception as e:
                    print(f"Error creating link for atomic_id {atomic_id}: {e}")
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
