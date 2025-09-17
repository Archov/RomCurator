"""
Validation and testing tools for the DAT-metadata matching system.

This module provides tools to validate the accuracy of matches and test
the matching engine with known good/bad cases.
"""

import sqlite3
import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'seeders'))
from matching_engine import GameMatcher
from dat_parser import DATNameParser


@dataclass
class ValidationResult:
    """Results of a validation test."""
    test_name: str
    passed: bool
    expected: str
    actual: str
    details: str


class MatchingValidator:
    """Validator for the matching system."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.matcher = GameMatcher(db_path)
        self.parser = DATNameParser()
    
    def close(self):
        """Close database connections."""
        if self.matcher:
            self.matcher.close()
    
    def validate_dat_parser(self) -> List[ValidationResult]:
        """Validate the DAT parser with known test cases."""
        test_cases = [
            # No-Intro test cases
            {
                'title': 'Super Mario Bros. 3 (USA) (Rev 1)',
                'format': 'no-intro',
                'expected': {
                    'base_title': 'Super Mario Bros. 3',
                    'region_normalized': 'USA',
                    'version_info': 'Rev 1',
                    'dump_status': 'unknown'
                }
            },
            {
                'title': 'Final Fantasy VI (Japan) (v1.1)',
                'format': 'no-intro',
                'expected': {
                    'base_title': 'Final Fantasy VI',
                    'region_normalized': 'JPN',
                    'version_info': 'v1.1',
                    'dump_status': 'unknown'
                }
            },
            {
                'title': 'Legend of Zelda, The (USA) [!]',
                'format': 'no-intro',
                'expected': {
                    'base_title': 'Legend of Zelda, The',
                    'region_normalized': 'USA',
                    'dump_status': 'verified'
                }
            },
            # TOSEC test cases
            {
                'title': 'Sonic the Hedgehog (1991)(Sega)(US)[!]',
                'format': 'tosec',
                'expected': {
                    'base_title': 'Sonic the Hedgehog',
                    'region_normalized': 'USA',
                    'dump_status': 'verified'
                }
            },
            {
                'title': 'Super Mario Bros. (1985)(Nintendo)(EU)[cr Razor 1911]',
                'format': 'tosec', 
                'expected': {
                    'base_title': 'Super Mario Bros.',
                    'region_normalized': 'EUR',
                    'dump_status': 'cracked'
                }
            },
            # GoodTools test cases
            {
                'title': 'Metroid (U) [!]',
                'format': 'goodtools',
                'expected': {
                    'base_title': 'Metroid',
                    'region_normalized': 'USA',
                    'dump_status': 'verified'
                }
            },
            {
                'title': 'Castlevania (E) [b1]',
                'format': 'goodtools',
                'expected': {
                    'base_title': 'Castlevania',
                    'region_normalized': 'EUR',
                    'dump_status': 'bad'
                }
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            title = test_case['title']
            format_type = test_case['format']
            expected = test_case['expected']
            
            # Parse the title
            parsed = self.parser.parse_title(title, format_type)
            
            # Check each expected field
            for field, expected_value in expected.items():
                actual_value = parsed.get(field, '')
                
                passed = actual_value == expected_value
                
                result = ValidationResult(
                    test_name=f"DAT Parser - {title} - {field}",
                    passed=passed,
                    expected=expected_value,
                    actual=actual_value,
                    details=f"Title: {title}, Format: {format_type}"
                )
                results.append(result)
        
        return results
    
    def validate_title_normalization(self) -> List[ValidationResult]:
        """Validate title normalization logic."""
        test_cases = [
            # These should match after normalization
            ('Final Fantasy III', 'Final Fantasy 3', True),
            ('Street Fighter II', 'Street Fighter 2', True),
            ('The Legend of Zelda', 'Legend of Zelda', True),
            ('Game: Subtitle', 'Game - Subtitle', True),
            ('Game HD Edition', 'Game', True),
            ('Super Mario Bros.', 'Super Mario Bros', True),
            
            # These should not match
            ('Final Fantasy VI', 'Final Fantasy VII', False),
            ('Super Mario Bros.', 'Super Mario World', False),
            ('Sonic 1', 'Sonic 2', False),
        ]
        
        results = []
        
        for title1, title2, should_match in test_cases:
            norm1 = self.matcher.normalize_title(title1)
            norm2 = self.matcher.normalize_title(title2)
            
            similarity = self.matcher.calculate_similarity(title1, title2)
            actually_matches = similarity >= 0.8  # Use matching threshold
            
            passed = actually_matches == should_match
            
            result = ValidationResult(
                test_name=f"Title Normalization - '{title1}' vs '{title2}'",
                passed=passed,
                expected=f"Should match: {should_match}",
                actual=f"Similarity: {similarity:.3f}, Matches: {actually_matches}",
                details=f"Normalized: '{norm1}' vs '{norm2}'"
            )
            results.append(result)
        
        return results
    
    def validate_database_integrity(self) -> List[ValidationResult]:
        """Validate database integrity and structure."""
        results = []
        cursor = self.matcher.conn.cursor()
        
        # Check if required tables exist
        required_tables = [
            'atomic_game_unit', 'dat_entry', 'dat_atomic_link',
            'platform', 'game_release'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        for table in required_tables:
            passed = table in existing_tables
            
            result = ValidationResult(
                test_name=f"Database - Table {table} exists",
                passed=passed,
                expected="Table exists",
                actual="Exists" if passed else "Missing",
                details=f"Required for matching system"
            )
            results.append(result)
        
        # Check for orphaned records
        if 'dat_atomic_link' in existing_tables:
            cursor.execute("""
                SELECT COUNT(*) FROM dat_atomic_link dal
                LEFT JOIN atomic_game_unit agu ON dal.atomic_id = agu.atomic_id
                WHERE agu.atomic_id IS NULL
            """)
            orphaned_atomic = cursor.fetchone()[0]
            
            result = ValidationResult(
                test_name="Database - No orphaned atomic links",
                passed=orphaned_atomic == 0,
                expected="0 orphaned links",
                actual=f"{orphaned_atomic} orphaned links",
                details="Links pointing to non-existent atomic games"
            )
            results.append(result)
            
            cursor.execute("""
                SELECT COUNT(*) FROM dat_atomic_link dal
                LEFT JOIN dat_entry de ON dal.dat_entry_id = de.dat_entry_id
                WHERE dal.dat_entry_id IS NOT NULL AND de.dat_entry_id IS NULL
            """)
            orphaned_dat = cursor.fetchone()[0]
            
            result = ValidationResult(
                test_name="Database - No orphaned DAT links",
                passed=orphaned_dat == 0,
                expected="0 orphaned links",
                actual=f"{orphaned_dat} orphaned links", 
                details="Links pointing to non-existent DAT entries"
            )
            results.append(result)
        
        return results
    
    def generate_matching_report(self) -> Dict:
        """Generate a comprehensive report on matching status."""
        cursor = self.matcher.conn.cursor()
        
        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM atomic_game_unit")
        total_atomic = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM dat_entry")
        total_dat = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT atomic_id) FROM dat_atomic_link WHERE dat_entry_id IS NOT NULL")
        linked_atomic = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT atomic_id) FROM dat_atomic_link WHERE match_type = 'automatic'")
        auto_linked = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT atomic_id) FROM dat_atomic_link WHERE match_type = 'manual'")
        manual_linked = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT atomic_id) FROM dat_atomic_link WHERE match_type = 'no_match'")
        no_match = cursor.fetchone()[0]
        
        # Platform breakdown
        cursor.execute("""
            SELECT p.name, COUNT(DISTINCT agu.atomic_id) as total,
                   COUNT(DISTINCT dal.atomic_id) as linked
            FROM platform p
            LEFT JOIN game_release gr ON p.platform_id = gr.platform_id
            LEFT JOIN atomic_game_unit agu ON gr.atomic_id = agu.atomic_id
            LEFT JOIN dat_atomic_link dal ON agu.atomic_id = dal.atomic_id AND dal.dat_entry_id IS NOT NULL
            GROUP BY p.platform_id, p.name
            ORDER BY total DESC
        """)
        platform_stats = cursor.fetchall()
        
        # Confidence distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN confidence >= 0.95 THEN '95%+'
                    WHEN confidence >= 0.90 THEN '90-95%'
                    WHEN confidence >= 0.80 THEN '80-90%'
                    WHEN confidence >= 0.70 THEN '70-80%'
                    ELSE '<70%'
                END as confidence_range,
                COUNT(*) as count
            FROM dat_atomic_link
            WHERE dat_entry_id IS NOT NULL
            GROUP BY confidence_range
            ORDER BY MIN(confidence) DESC
        """)
        confidence_stats = cursor.fetchall()
        
        report = {
            'summary': {
                'total_atomic_games': total_atomic,
                'total_dat_entries': total_dat,
                'linked_games': linked_atomic,
                'unlinked_games': total_atomic - linked_atomic - no_match,
                'auto_linked': auto_linked,
                'manual_linked': manual_linked,
                'marked_no_match': no_match,
                'linking_percentage': (linked_atomic / total_atomic * 100) if total_atomic > 0 else 0
            },
            'platform_breakdown': [
                {
                    'platform': row[0],
                    'total_games': row[1],
                    'linked_games': row[2] or 0,
                    'link_percentage': (row[2] / row[1] * 100) if row[1] > 0 else 0
                }
                for row in platform_stats
            ],
            'confidence_distribution': [
                {'range': row[0], 'count': row[1]}
                for row in confidence_stats
            ]
        }
        
        return report
    
    def export_validation_results(self, results: List[ValidationResult], output_file: Path):
        """Export validation results to a file."""
        if output_file.suffix.lower() == '.json':
            # Export as JSON
            results_data = [asdict(result) for result in results]
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2)
        
        elif output_file.suffix.lower() == '.csv':
            # Export as CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['test_name', 'passed', 'expected', 'actual', 'details'])
                writer.writeheader()
                for result in results:
                    writer.writerow(asdict(result))
        
        else:
            # Export as text
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("Validation Results\n")
                f.write("=" * 50 + "\n\n")
                
                passed_count = sum(1 for r in results if r.passed)
                total_count = len(results)
                
                f.write(f"Summary: {passed_count}/{total_count} tests passed ({passed_count/total_count*100:.1f}%)\n\n")
                
                for result in results:
                    status = "PASS" if result.passed else "FAIL"
                    f.write(f"[{status}] {result.test_name}\n")
                    if not result.passed:
                        f.write(f"  Expected: {result.expected}\n")
                        f.write(f"  Actual: {result.actual}\n")
                        f.write(f"  Details: {result.details}\n")
                    f.write("\n")
    
    def run_full_validation(self) -> List[ValidationResult]:
        """Run all validation tests."""
        print("Running DAT parser validation...")
        parser_results = self.validate_dat_parser()
        
        print("Running title normalization validation...")
        normalization_results = self.validate_title_normalization()
        
        print("Running database integrity validation...")
        db_results = self.validate_database_integrity()
        
        all_results = parser_results + normalization_results + db_results
        
        # Print summary
        passed = sum(1 for r in all_results if r.passed)
        total = len(all_results)
        
        print(f"\nValidation Summary: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        # Show failed tests
        failed_tests = [r for r in all_results if not r.passed]
        if failed_tests:
            print(f"\nFailed tests:")
            for test in failed_tests:
                print(f"  - {test.test_name}")
                print(f"    Expected: {test.expected}")
                print(f"    Actual: {test.actual}")
        
        return all_results


def main():
    """Command-line interface for validation tools."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validation tools for DAT-metadata matching")
    parser.add_argument('--db_path', required=True, help="Path to the SQLite database")
    parser.add_argument('--action', choices=['validate', 'report'], default='validate',
                        help="Action to perform")
    parser.add_argument('--output', help="Output file for results (optional)")
    
    args = parser.parse_args()
    
    validator = MatchingValidator(args.db_path)
    
    try:
        if args.action == 'validate':
            results = validator.run_full_validation()
            
            if args.output:
                output_path = Path(args.output)
                validator.export_validation_results(results, output_path)
                print(f"Results exported to {output_path}")
        
        elif args.action == 'report':
            report = validator.generate_matching_report()
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2)
                print(f"Report exported to {args.output}")
            else:
                print("\nMatching Report")
                print("=" * 50)
                summary = report['summary']
                print(f"Total atomic games: {summary['total_atomic_games']}")
                print(f"Total DAT entries: {summary['total_dat_entries']}")
                print(f"Linked games: {summary['linked_games']} ({summary['linking_percentage']:.1f}%)")
                print(f"Unlinked games: {summary['unlinked_games']}")
                print(f"Auto-linked: {summary['auto_linked']}")
                print(f"Manual-linked: {summary['manual_linked']}")
                print(f"Marked no match: {summary['marked_no_match']}")
    
    finally:
        validator.close()


if __name__ == '__main__':
    main()
