"""
Universal DAT filename parser for No-Intro, TOSEC, and GoodTools naming conventions.

This module extracts universal metadata concepts from ROM/game names in DAT files,
including base title, region, version, development status, dump status, and languages.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParsedMetadata:
    """Container for parsed metadata from a ROM/game name."""
    base_title: str
    region_normalized: str = ""
    version_info: str = ""
    development_status: str = ""
    dump_status: str = ""
    language_codes: str = ""
    extra_info: str = ""


class DATNameParser:
    """Parser for extracting metadata from ROM/game names in various DAT formats."""
    
    def __init__(self):
        # Centralized region mappings - all convert to No-Intro format
        self.region_mappings = {
            # No-Intro (already correct format)
            'nointro': {
                'USA': 'USA', 'US': 'USA', 'U': 'USA',
                'Europe': 'Europe', 'EUR': 'Europe', 'E': 'Europe', 
                'Japan': 'Japan', 'JPN': 'Japan', 'J': 'Japan',
                'World': 'World', 'W': 'World',
                'Asia': 'Asia',
                'Australia': 'Australia', 'AUS': 'Australia', 'A': 'Australia',
                'Brazil': 'Brazil', 'BRA': 'Brazil', 'B': 'Brazil',
                'Canada': 'Canada', 'CAN': 'Canada', 'C': 'Canada',
                'China': 'China', 'CHN': 'China', 'CH': 'China',
                'France': 'France', 'FRA': 'France', 'F': 'France',
                'Germany': 'Germany', 'GER': 'Germany', 'G': 'Germany',
                'Italy': 'Italy', 'ITA': 'Italy', 'I': 'Italy',
                'Korea': 'Korea', 'KOR': 'Korea', 'K': 'Korea',
                'Netherlands': 'Netherlands', 'NLD': 'Netherlands', 'D': 'Netherlands',
                'Spain': 'Spain', 'ESP': 'Spain', 'S': 'Spain',
                'Sweden': 'Sweden', 'SWE': 'Sweden', 'SW': 'Sweden',
                'Taiwan': 'Taiwan', 'TWN': 'Taiwan', 'TW': 'Taiwan',
                'UK': 'UK', 'GBR': 'UK', 'GB': 'UK'
            },
            
            # TOSEC (ISO 3166-1 alpha-2) → No-Intro
            'tosec': {
                'US': 'USA', 'JP': 'Japan', 'EU': 'Europe', 'GB': 'UK',
                'DE': 'Germany', 'FR': 'France', 'IT': 'Italy', 'ES': 'Spain',
                'NL': 'Netherlands', 'AU': 'Australia', 'BR': 'Brazil', 'CA': 'Canada',
                'CN': 'China', 'KR': 'Korea', 'TW': 'Taiwan', 'AS': 'Asia',
                'RU': 'Russia', 'PL': 'Poland', 'SE': 'Sweden', 'NO': 'Norway',
                'DK': 'Denmark', 'FI': 'Finland', 'PT': 'Portugal', 'GR': 'Greece',
                'HU': 'Hungary', 'CZ': 'Czech Republic', 'SK': 'Slovakia',
                'HR': 'Croatia', 'SI': 'Slovenia', 'BG': 'Bulgaria', 'RO': 'Romania',
                'LT': 'Lithuania', 'LV': 'Latvia', 'EE': 'Estonia', 'LU': 'Luxembourg',
                'MT': 'Malta', 'CY': 'Cyprus', 'IE': 'Ireland', 'IS': 'Iceland',
                'CH': 'Switzerland', 'AT': 'Austria', 'BE': 'Belgium', 'LI': 'Liechtenstein',
                'MC': 'Monaco', 'SM': 'San Marino', 'VA': 'Vatican City', 'AD': 'Andorra',
                'FO': 'Faroe Islands', 'GL': 'Greenland', 'SJ': 'Svalbard and Jan Mayen',
                'AX': 'Åland Islands', 'AL': 'Albania', 'BA': 'Bosnia and Herzegovina',
                'ME': 'Montenegro', 'MK': 'North Macedonia', 'RS': 'Serbia', 'XK': 'Kosovo',
                'MD': 'Moldova', 'UA': 'Ukraine', 'BY': 'Belarus', 'KZ': 'Kazakhstan',
                'KG': 'Kyrgyzstan', 'TJ': 'Tajikistan', 'TM': 'Turkmenistan', 'UZ': 'Uzbekistan',
                'AF': 'Afghanistan', 'PK': 'Pakistan', 'BD': 'Bangladesh', 'BT': 'Bhutan',
                'IN': 'India', 'MV': 'Maldives', 'LK': 'Sri Lanka', 'NP': 'Nepal',
                'MM': 'Myanmar', 'TH': 'Thailand', 'LA': 'Laos', 'KH': 'Cambodia',
                'VN': 'Vietnam', 'MY': 'Malaysia', 'SG': 'Singapore', 'BN': 'Brunei',
                'ID': 'Indonesia', 'TL': 'East Timor', 'PH': 'Philippines', 'MN': 'Mongolia',
                'KP': 'North Korea', 'HK': 'Hong Kong', 'MO': 'Macau'
            },
            
            # GoodTools → No-Intro
            'goodtools': {
                # Official GoodTools codes
                '1': 'Japan', '4': 'USA', 'A': 'Australia', 'B': 'Brazil', 'C': 'China',
                'D': 'Netherlands', 'E': 'Europe', 'F': 'France', 'FC': 'Canada',
                'FN': 'Finland', 'G': 'Germany', 'GR': 'Greece', 'HK': 'Hong Kong',
                'J': 'Japan', 'K': 'Korea', 'NL': 'Netherlands', 'PD': 'Public Domain',
                'S': 'Spain', 'Sw': 'Sweden', 'U': 'USA', 'UK': 'UK', 'Unk': 'Unknown',
                'I': 'Italy', 'Unl': 'Unlicensed',
                
                # Unofficial GoodTools codes (ISO 3166-1 alpha-2)
                'Ar': 'Argentina', 'As': 'Asia', 'Au': 'Australia', 'Br': 'Brazil',
                'Ca': 'Canada', 'Cn': 'China', 'Dk': 'Denmark', 'Eu': 'Europe',
                'Fr': 'France', 'Fi': 'Finland', 'De': 'Germany', 'Gr': 'Greece',
                'It': 'Italy', 'Jp': 'Japan', 'Kr': 'Korea', 'Mx': 'Mexico',
                'Nl': 'Netherlands', 'NZ': 'New Zealand', 'Pt': 'Portugal',
                'Ru': 'Russia', 'Es': 'Spain', 'Se': 'Sweden', 'Tw': 'Taiwan',
                'US': 'USA', 'Wo': 'World'
            }
        }
        
        # Development status keywords
        self.dev_status_keywords = {
            'demo': 'demo',
            'beta': 'beta', 
            'proto': 'proto',
            'prototype': 'proto',
            'alpha': 'alpha',
            'sample': 'sample',
            'preview': 'preview',
            'test': 'test',
            'debug': 'debug'
        }
        
        # Dump status keywords  
        self.dump_status_keywords = {
            'verified': 'verified',
            'good': 'good',
            'bad': 'bad',
            'alternate': 'alternate',
            'overdump': 'overdump',
            'underdump': 'underdump',
            'fixed': 'fixed',
            'hack': 'hack',
            'translated': 'translated',
            'cracked': 'cracked',
            'trained': 'trained',
            'pirate': 'pirate'
        }
        
        # Language code mappings (ISO 639-1)
        self.language_codes = {
            'en': 'en', 'english': 'en',
            'ja': 'ja', 'japanese': 'ja', 'jp': 'ja',
            'fr': 'fr', 'french': 'fr',
            'de': 'de', 'german': 'de',
            'es': 'es', 'spanish': 'es',
            'it': 'it', 'italian': 'it',
            'nl': 'nl', 'dutch': 'nl',
            'pt': 'pt', 'portuguese': 'pt',
            'sv': 'sv', 'swedish': 'sv',
            'no': 'no', 'norwegian': 'no',
            'da': 'da', 'danish': 'da',
            'fi': 'fi', 'finnish': 'fi',
            'zh': 'zh', 'chinese': 'zh',
            'ko': 'ko', 'korean': 'ko',
            'pl': 'pl', 'polish': 'pl'
        }

    def parse_title(self, title: str, dat_format: str = "auto") -> Dict[str, str]:
        """
        Parse a ROM/game title and extract universal metadata.
        
        Args:
            title: The ROM/game name from the DAT file
            dat_format: Format hint ("nointro", "tosec", "goodtools", or "auto")
            
        Returns:
            Dictionary with parsed metadata fields
        """
        if not title:
            return self._empty_result()
            
        # Detect format if auto
        if dat_format == "auto":
            dat_format = self._detect_format(title)
            
        # Parse based on detected/specified format
        if dat_format == "nointro":
            return self._parse_nointro(title)
        elif dat_format == "tosec":
            return self._parse_tosec(title)
        elif dat_format == "goodtools":
            return self._parse_goodtools(title)
        else:
            # Fallback: basic parsing
            return self._parse_generic(title)

    def _detect_format(self, title: str) -> str:
        """Auto-detect the DAT format based on naming patterns."""
        # TOSEC typically uses lots of parentheses with specific patterns
        if re.search(r'\(\d{4}\)', title) and '(' in title:
            # Check for TOSEC-specific patterns
            if any(pattern in title.lower() for pattern in ['disk ', 'side ', 'tape ', 'file ']):
                return "tosec"
                
        # GoodTools uses [brackets] and specific abbreviations
        if '[' in title and ']' in title:
            # Look for GoodTools patterns: [!], [U], [E], [J], [h1], [t1], etc.
            goodtools_patterns = [
                r'\[!\]',           # verified
                r'\[[UEJWuejw]\]',  # regions
                r'\[[abcfhoptx]\d*\]', # status codes with optional numbers
                r'\[USA?\]', r'\[EUR?\]', r'\[JPN?\]'  # full region names
            ]
            if any(re.search(pattern, title) for pattern in goodtools_patterns):
                return "goodtools"
                
        # No-Intro is cleaner, typically (Region) patterns
        if re.search(r'\([A-Za-z, ]+\)(?:\s*\([^)]*\))*$', title):
            return "nointro"
            
        return "generic"

    def _parse_nointro(self, title: str) -> Dict[str, str]:
        """Parse No-Intro format: Game Title (Region) (Language) (Version) (Status)"""
        result = self._empty_result()
        
        # Extract base title (everything before first parenthesis)
        base_match = re.match(r'^([^(]+)', title.strip())
        if base_match:
            result['base_title'] = base_match.group(1).strip()
        else:
            result['base_title'] = title
            
        # Find all parenthetical groups
        paren_groups = re.findall(r'\(([^)]+)\)', title)
        
        # Collect all regions for multi-region handling
        regions_found = []
        
        for group in paren_groups:
            group_lower = group.lower()
            
            # Check for regions (first priority)
            region = self._standardize_region(group, 'nointro')
            if region:
                regions_found.append(region)
                continue
                    
            # Check for languages
            if not result['language_codes']:
                languages = self._extract_languages(group)
                if languages:
                    result['language_codes'] = languages
                    continue
                    
            # Check for version info
            if not result['version_info']:
                version = self._extract_version(group)
                if version:
                    result['version_info'] = version
                    continue
                    
            # Check for development status
            if not result['development_status']:
                dev_status = self._extract_dev_status(group)
                if dev_status:
                    result['development_status'] = dev_status
                    continue
                    
            # Check for dump status
            if not result['dump_status']:
                dump_status = self._extract_dump_status(group)
                if dump_status:
                    result['dump_status'] = dump_status
                    continue
                    
            # Store unrecognized info
            if result['extra_info']:
                result['extra_info'] += f"; {group}"
            else:
                result['extra_info'] = group
        
        # Handle regions: single region or MULTI
        if regions_found:
            if len(regions_found) == 1:
                result['region_normalized'] = regions_found[0]
            else:
                result['region_normalized'] = 'MULTI'
                # Note: Individual regions would be stored in EAV table in actual implementation
                
        return result

    def _parse_tosec(self, title: str) -> Dict[str, str]:
        """Parse TOSEC format: Game Title (Year)(Company)(Country)[more info]"""
        result = self._empty_result()
        
        # TOSEC format: Title (Year)(Publisher)(Country)[Status]
        # Extract just the title part (before year)
        title_match = re.match(r'^([^(]+?)(?:\s*\(\d{4}\).*)?$', title.strip())
        if title_match:
            result['base_title'] = title_match.group(1).strip()
        else:
            # Fallback: take everything before first parenthesis
            base_match = re.match(r'^([^(]+)', title.strip())
            if base_match:
                result['base_title'] = base_match.group(1).strip()
            else:
                result['base_title'] = title
            
        # Extract year (usually first parenthesis with 4 digits)
        year_match = re.search(r'\((\d{4})\)', title)
        if year_match:
            result['extra_info'] = f"Year: {year_match.group(1)}"
            
        # Extract regions/countries - look in all parentheses
        paren_groups = re.findall(r'\(([^)]+)\)', title)
        regions_found = []
        for group in paren_groups:
            if group.isdigit() and len(group) == 4:  # Skip years
                continue
            region = self._standardize_region(group, 'tosec')
            if region:
                regions_found.append(region)
                    
        # Look for dump status in brackets [good], [bad], etc.
        bracket_matches = re.findall(r'\[([^\]]+)\]', title)
        for match in bracket_matches:
            if match == '!':
                result['dump_status'] = 'verified'
            else:
                dump_status = self._extract_dump_status(match)
                if dump_status and not result['dump_status']:
                    result['dump_status'] = dump_status
        
        # Handle regions: single region or MULTI
        if regions_found:
            if len(regions_found) == 1:
                result['region_normalized'] = regions_found[0]
            else:
                result['region_normalized'] = 'MULTI'
                # Note: Individual regions would be stored in EAV table in actual implementation
                
        return result

    def _parse_goodtools(self, title: str) -> Dict[str, str]:
        """Parse GoodTools format: Game Title [!] [region codes] [status]"""
        result = self._empty_result()
        
        # Extract base title (everything before first bracket)
        base_match = re.match(r'^([^\[]+)', title.strip())
        if base_match:
            result['base_title'] = base_match.group(1).strip()
        else:
            result['base_title'] = title
            
        # Find all bracketed groups
        bracket_groups = re.findall(r'\[([^\]]+)\]', title)
        
        # Collect all regions for multi-region handling
        regions_found = []
        
        for group in bracket_groups:
            group_lower = group.lower()
            
            # Check for regions first
            region = self._standardize_region(group, 'goodtools')
            if region:
                regions_found.append(region)
                continue
            # GoodTools status codes
            elif group == '!':
                if not result['dump_status']:
                    result['dump_status'] = 'verified'
            elif group in ['a', 'a1', 'a2']:
                if not result['dump_status']:
                    result['dump_status'] = 'alternate'
            elif group in ['b', 'b1', 'b2']:
                if not result['dump_status']:
                    result['dump_status'] = 'bad'
            elif group == 'c':
                if not result['dump_status']:
                    result['dump_status'] = 'cracked'
            elif group == 'f':
                if not result['dump_status']:
                    result['dump_status'] = 'fixed'
            elif group.startswith('h') and (len(group) == 1 or group[1:].isdigit()):
                if not result['dump_status']:
                    result['dump_status'] = 'hack'
            elif group == 'o':
                if not result['dump_status']:
                    result['dump_status'] = 'overdump'
            elif group == 'p':
                if not result['dump_status']:
                    result['dump_status'] = 'pirate'
            elif group.startswith('t') and (len(group) == 1 or group[1:].isdigit()):
                if not result['dump_status']:
                    result['dump_status'] = 'translated'
            elif group == 'x':
                if not result['dump_status']:
                    result['dump_status'] = 'bad'
            else:
                # Store other info
                if result['extra_info']:
                    result['extra_info'] += f"; {group}"
                else:
                    result['extra_info'] = group
        
        # Handle regions: single region or MULTI
        if regions_found:
            if len(regions_found) == 1:
                result['region_normalized'] = regions_found[0]
            else:
                result['region_normalized'] = 'MULTI'
                # Note: Individual regions would be stored in EAV table in actual implementation
                    
        return result

    def _parse_generic(self, title: str) -> Dict[str, str]:
        """Generic parsing for unknown formats."""
        result = self._empty_result()
        result['base_title'] = title.strip()
        
        # Try to extract any recognizable patterns
        all_groups = re.findall(r'[\(\[]([^\)\]]+)[\)\]]', title)
        
        for group in all_groups:
            # Try region extraction
            if not result['region_normalized']:
                region = self._extract_region(group)
                if region:
                    result['region_normalized'] = region
                    continue
                    
            # Try other extractions...
            if not result['extra_info']:
                result['extra_info'] = group
            else:
                result['extra_info'] += f"; {group}"
                
        return result

    def _standardize_region(self, region_text: str, source_format: str) -> Optional[str]:
        """Convert any region code to standardized No-Intro format."""
        if not region_text:
            return None
            
        region_clean = region_text.strip().upper()
        
        # Check if it's already in No-Intro format
        if region_clean in self.region_mappings['nointro']:
            return self.region_mappings['nointro'][region_clean]
        
        # Convert from source format to No-Intro
        if source_format in self.region_mappings:
            if region_clean in self.region_mappings[source_format]:
                return self.region_mappings[source_format][region_clean]
        
        # Handle multi-region formats
        if ',' in region_clean:
            regions = [r.strip() for r in region_clean.split(',')]
            normalized_regions = []
            for region in regions:
                normalized = self._standardize_region(region, source_format)
                if normalized:
                    normalized_regions.append(normalized)
            if normalized_regions:
                return ', '.join(normalized_regions)
        
        # Partial matching for common variations (only for exact word matches)
        if source_format in self.region_mappings:
            for key, value in self.region_mappings[source_format].items():
                # Only match if the key is a complete word, not a substring
                if f' {key.lower()} ' in f' {region_clean.lower()} ' or region_clean.lower() == key.lower():
                    return value
        
        return None

    def _extract_region(self, text: str) -> Optional[str]:
        """Extract and normalize region from text (legacy method - use _standardize_region instead)."""
        # This method is kept for backward compatibility but should be replaced
        # with _standardize_region calls in the individual parsers
        text_clean = text.strip()
        
        # Direct mapping (legacy)
        if text_clean in self.region_mappings['nointro']:
            return self.region_mappings['nointro'][text_clean]
            
        # Check for multi-region format like "Japan, USA"
        if ',' in text_clean:
            regions = [r.strip() for r in text_clean.split(',')]
            normalized_regions = []
            for region in regions:
                if region in self.region_mappings['nointro']:
                    normalized_regions.append(self.region_mappings['nointro'][region])
            if normalized_regions:
                return ', '.join(normalized_regions)
                
        # Partial matching
        text_lower = text_clean.lower()
        for key, value in self.region_mappings['nointro'].items():
            if key.lower() in text_lower:
                return value
                
        return None

    def _extract_languages(self, text: str) -> Optional[str]:
        """Extract language codes from text."""
        text_lower = text.lower()
        found_languages = []
        
        # Look for comma-separated language codes like "En,Fr,De"
        if ',' in text:
            parts = [p.strip() for p in text.split(',')]
            for part in parts:
                part_lower = part.lower()
                if part_lower in self.language_codes:
                    found_languages.append(self.language_codes[part_lower])
                    
        # Single language check
        if not found_languages and text_lower in self.language_codes:
            found_languages.append(self.language_codes[text_lower])
            
        return ','.join(found_languages) if found_languages else None

    def _extract_version(self, text: str) -> Optional[str]:
        """Extract version information from text."""
        # Common version patterns
        version_patterns = [
            r'v?(\d+\.?\d*)',           # v1.0, v2, 1.02
            r'rev\s*(\d+)',             # Rev 1, Rev A
            r'version\s*(\d+\.?\d*)',   # Version 1.0
            r'\b(\d+\.?\d*)\b',         # Just numbers
        ]
        
        text_lower = text.lower()
        for pattern in version_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1)
                
        return None

    def _extract_dev_status(self, text: str) -> Optional[str]:
        """Extract development status from text."""
        text_lower = text.lower()
        for keyword, status in self.dev_status_keywords.items():
            if keyword in text_lower:
                return status
        return None

    def _extract_dump_status(self, text: str) -> Optional[str]:
        """Extract dump status from text."""
        text_lower = text.lower()
        for keyword, status in self.dump_status_keywords.items():
            if keyword in text_lower:
                return status
        return None

    def _empty_result(self) -> Dict[str, str]:
        """Return empty result dictionary."""
        return {
            'base_title': '',
            'region_normalized': '',
            'version_info': '',
            'development_status': '',
            'dump_status': '',
            'language_codes': '',
            'extra_info': ''
        }


# Example usage and testing
if __name__ == "__main__":
    parser = DATNameParser()
    
    # Test cases
    test_cases = [
        # No-Intro examples
        "Super Mario Bros. (USA)",
        "The Legend of Zelda (USA) (Rev 1)",
        "Final Fantasy (USA) (En,Fr,De)",
        "Pokemon Red (Japan) (Beta)",
        
        # TOSEC examples  
        "Sonic the Hedgehog (1991)(Sega)(US)[!]",
        "Prince of Persia (1989)(Broderbund)(Disk 1 of 2)",
        
        # GoodTools examples
        "Super Mario Bros [!]",
        "Zelda II - The Adventure of Link [U][!]",
        "Metroid [U][h1]",
    ]
    
    for test in test_cases:
        print(f"\nParsing: {test}")
        result = parser.parse_title(test)
        for key, value in result.items():
            if value:
                print(f"  {key}: {value}")