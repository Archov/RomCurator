#!/usr/bin/env python3
"""
Enhanced DAT name parser with comprehensive dump status support.

This parser extracts metadata from ROM filenames following No-Intro, TOSEC, GoodTools,
and Redump naming conventions. The format must be explicitly specified by the calling
code - no auto-detection is performed.

Supported formats:
- nointro: No-Intro naming conventions
- tosec: TOSEC naming conventions  
- goodtools: GoodTools naming conventions
- redump: Redump naming conventions (uses No-Intro rules)
"""

import re
from typing import Dict, Optional, List

class DATNameParser:
    """Parser for extracting metadata from DAT filenames."""
    
    def __init__(self):
        # Region mappings for standardization to No-Intro format
        self.region_mappings = {
            'nointro': {
                # No-Intro regions (already standardized)
                'USA': 'USA', 'United States': 'USA', 'US': 'USA',
                'Europe': 'Europe', 'EU': 'Europe', 'European': 'Europe',
                'Japan': 'Japan', 'JP': 'Japan', 'Japanese': 'Japan',
                'Australia': 'Australia', 'AU': 'Australia', 'AUS': 'Australia',
                'Brazil': 'Brazil', 'BR': 'Brazil', 'Brasil': 'Brazil',
                'Canada': 'Canada', 'CA': 'Canada', 'CAN': 'Canada',
                'China': 'China', 'CN': 'China', 'CHN': 'China',
                'France': 'France', 'FR': 'France', 'FRA': 'France',
                'Germany': 'Germany', 'DE': 'Germany', 'DEU': 'Germany',
                'Italy': 'Italy', 'IT': 'Italy', 'ITA': 'Italy',
                'Spain': 'Spain', 'ES': 'Spain', 'ESP': 'Spain',
                'Korea': 'Korea', 'KR': 'Korea', 'KOR': 'Korea',
                'Netherlands': 'Netherlands', 'NL': 'Netherlands', 'NLD': 'Netherlands',
                'Sweden': 'Sweden', 'SE': 'Sweden', 'SWE': 'Sweden',
                'Hong Kong': 'Hong Kong', 'HK': 'Hong Kong', 'HKG': 'Hong Kong',
                'Taiwan': 'Taiwan', 'TW': 'Taiwan', 'TWN': 'Taiwan',
                'Asia': 'Asia', 'AS': 'Asia',
                'World': 'World', 'WD': 'World',
                'Unlicensed': 'Unlicensed'
            },
            'tosec': {
                # TOSEC ISO codes -> No-Intro
                'US': 'USA', 'JP': 'Japan', 'DE': 'Germany', 'FR': 'France',
                'GB': 'UK', 'IT': 'Italy', 'ES': 'Spain', 'NL': 'Netherlands',
                'SE': 'Sweden', 'AU': 'Australia', 'CA': 'Canada', 'BR': 'Brazil',
                'CN': 'China', 'KR': 'Korea', 'HK': 'Hong Kong', 'TW': 'Taiwan',
                'EU': 'Europe', 'AS': 'Asia', 'RU': 'Russia', 'PL': 'Poland',
                'CZ': 'Czech Republic', 'HU': 'Hungary', 'FI': 'Finland',
                'NO': 'Norway', 'DK': 'Denmark', 'AT': 'Austria', 'CH': 'Switzerland',
                'BE': 'Belgium', 'PT': 'Portugal', 'GR': 'Greece', 'IE': 'Ireland',
                'NZ': 'New Zealand', 'ZA': 'South Africa', 'MX': 'Mexico',
                'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia', 'PE': 'Peru',
                'VE': 'Venezuela', 'UY': 'Uruguay', 'PY': 'Paraguay', 'BO': 'Bolivia',
                'EC': 'Ecuador', 'GY': 'Guyana', 'SR': 'Suriname', 'GF': 'French Guiana',
                'IN': 'India', 'ID': 'Indonesia', 'MY': 'Malaysia', 'SG': 'Singapore',
                'TH': 'Thailand', 'PH': 'Philippines', 'VN': 'Vietnam', 'MM': 'Myanmar',
                'KH': 'Cambodia', 'LA': 'Laos', 'BN': 'Brunei', 'TL': 'East Timor',
                'BD': 'Bangladesh', 'LK': 'Sri Lanka', 'MV': 'Maldives', 'NP': 'Nepal',
                'BT': 'Bhutan', 'AF': 'Afghanistan', 'PK': 'Pakistan', 'IR': 'Iran',
                'IQ': 'Iraq', 'SY': 'Syria', 'LB': 'Lebanon', 'JO': 'Jordan',
                'IL': 'Israel', 'PS': 'Palestine', 'SA': 'Saudi Arabia', 'AE': 'UAE',
                'QA': 'Qatar', 'BH': 'Bahrain', 'KW': 'Kuwait', 'OM': 'Oman',
                'YE': 'Yemen', 'EG': 'Egypt', 'LY': 'Libya', 'TN': 'Tunisia',
                'DZ': 'Algeria', 'MA': 'Morocco', 'SD': 'Sudan', 'SS': 'South Sudan',
                'ET': 'Ethiopia', 'ER': 'Eritrea', 'DJ': 'Djibouti', 'SO': 'Somalia',
                'KE': 'Kenya', 'UG': 'Uganda', 'TZ': 'Tanzania', 'RW': 'Rwanda',
                'BI': 'Burundi', 'MW': 'Malawi', 'ZM': 'Zambia', 'ZW': 'Zimbabwe',
                'BW': 'Botswana', 'NA': 'Namibia', 'SZ': 'Swaziland', 'LS': 'Lesotho',
                'MG': 'Madagascar', 'MU': 'Mauritius', 'SC': 'Seychelles', 'KM': 'Comoros',
                'YT': 'Mayotte', 'RE': 'Reunion', 'MZ': 'Mozambique', 'AO': 'Angola',
                'CD': 'Congo', 'CG': 'Congo', 'CF': 'Central African Republic',
                'TD': 'Chad', 'CM': 'Cameroon', 'GQ': 'Equatorial Guinea', 'GA': 'Gabon',
                'ST': 'Sao Tome and Principe', 'GH': 'Ghana', 'TG': 'Togo', 'BJ': 'Benin',
                'NE': 'Niger', 'NG': 'Nigeria', 'BF': 'Burkina Faso', 'ML': 'Mali',
                'SN': 'Senegal', 'GM': 'Gambia', 'GN': 'Guinea', 'GW': 'Guinea-Bissau',
                'SL': 'Sierra Leone', 'LR': 'Liberia', 'CI': 'Ivory Coast', 'GH': 'Ghana',
                'TG': 'Togo', 'BJ': 'Benin', 'NE': 'Niger', 'NG': 'Nigeria',
                'BF': 'Burkina Faso', 'ML': 'Mali', 'SN': 'Senegal', 'GM': 'Gambia',
                'GN': 'Guinea', 'GW': 'Guinea-Bissau', 'SL': 'Sierra Leone',
                'LR': 'Liberia', 'CI': 'Ivory Coast'
            },
            'goodtools': {
                # GoodTools codes -> No-Intro
                'U': 'USA', 'E': 'Europe', 'J': 'Japan', 'A': 'Australia',
                'B': 'Brazil', 'C': 'Canada', 'D': 'Germany', 'F': 'France',
                'G': 'Germany', 'H': 'Hong Kong', 'I': 'Italy', 'K': 'Korea',
                'L': 'Netherlands', 'N': 'Netherlands', 'P': 'Portugal',
                'Q': 'Qatar', 'R': 'Russia', 'S': 'Spain', 'T': 'Taiwan',
                'V': 'Venezuela', 'W': 'World', 'X': 'Unknown', 'Y': 'Yugoslavia',
                'Z': 'Zimbabwe', 'Unl': 'Unlicensed'
            }
        }
        
        # Development status keywords
        self.dev_status_keywords = {
            'alpha': 'alpha',
            'beta': 'beta', 
            'demo': 'demo',
            'kiosk': 'kiosk',
            'proto': 'proto',
            'prototype': 'proto',
            'preview': 'preview',
            'prerelease': 'prerelease',
            'sample': 'sample'
        }
        
        # Comprehensive dump status keywords covering all three formats
        self.dump_status_keywords = {
            # Verification status
            'verified': 'verified',
            'good': 'verified',
            '!': 'verified',
            
            # Quality issues
            'bad': 'bad',
            'b': 'bad',
            'overdump': 'overdump',
            'o': 'overdump',
            'underdump': 'underdump', 
            'u': 'underdump',
            'virus': 'virus',
            'v': 'virus',
            
            # Modifications
            'fixed': 'fixed',
            'f': 'fixed',
            'hack': 'hack',
            'h': 'hack',
            'hacked': 'hack',
            'modified': 'modified',
            'm': 'modified',
            'cracked': 'cracked',
            'cr': 'cracked',
            'trained': 'trained',
            't': 'trained',
            'translated': 'translated',
            'tr': 'translated',
            'oldtranslation': 'old_translation',
            't-': 'old_translation',
            'newtranslation': 'new_translation', 
            't+': 'new_translation',
            
            # Licensing
            'pirate': 'pirate',
            'p': 'pirate',
            'pirated': 'pirate',
            'unlicensed': 'unlicensed',
            'unl': 'unlicensed',
            
            # Versions
            'alternate': 'alternate',
            'a': 'alternate',
            'alt': 'alternate',
            'pending': 'pending',
            '!p': 'pending'
        }
        
        # Language code mappings (ISO 639-1)
        self.language_codes = {
            'en': 'en', 'english': 'en',
            'ja': 'ja', 'japanese': 'ja', 'jp': 'ja',
            'fr': 'fr', 'french': 'fr',
            'de': 'de', 'german': 'de', 'deutsch': 'de',
            'es': 'es', 'spanish': 'es', 'espanol': 'es',
            'it': 'it', 'italian': 'it', 'italiano': 'it',
            'pt': 'pt', 'portuguese': 'pt', 'portugues': 'pt',
            'ru': 'ru', 'russian': 'ru', 'russkiy': 'ru',
            'ko': 'ko', 'korean': 'ko', 'hangul': 'ko',
            'zh': 'zh', 'chinese': 'zh', 'zhongwen': 'zh',
            'nl': 'nl', 'dutch': 'nl', 'nederlands': 'nl',
            'sv': 'sv', 'swedish': 'sv', 'svenska': 'sv',
            'no': 'no', 'norwegian': 'no', 'norsk': 'no',
            'da': 'da', 'danish': 'da', 'dansk': 'da',
            'fi': 'fi', 'finnish': 'fi', 'suomi': 'fi',
            'pl': 'pl', 'polish': 'pl', 'polski': 'pl',
            'cs': 'cs', 'czech': 'cs', 'cesky': 'cs',
            'hu': 'hu', 'hungarian': 'hu', 'magyar': 'hu',
            'ro': 'ro', 'romanian': 'ro', 'romana': 'ro',
            'bg': 'bg', 'bulgarian': 'bg', 'bulgarski': 'bg',
            'hr': 'hr', 'croatian': 'hr', 'hrvatski': 'hr',
            'sk': 'sk', 'slovak': 'sk', 'slovensky': 'sk',
            'sl': 'sl', 'slovenian': 'sl', 'slovenski': 'sl',
            'et': 'et', 'estonian': 'et', 'eesti': 'et',
            'lv': 'lv', 'latvian': 'lv', 'latviesu': 'lv',
            'lt': 'lt', 'lithuanian': 'lt', 'lietuviu': 'lt',
            'el': 'el', 'greek': 'el', 'ellinika': 'el',
            'tr': 'tr', 'turkish': 'tr', 'turkce': 'tr',
            'ar': 'ar', 'arabic': 'ar', 'arabiyya': 'ar',
            'he': 'he', 'hebrew': 'he', 'ivrit': 'he',
            'hi': 'hi', 'hindi': 'hi', 'hindustani': 'hi',
            'th': 'th', 'thai': 'th', 'thai': 'th',
            'vi': 'vi', 'vietnamese': 'vi', 'tieng viet': 'vi',
            'id': 'id', 'indonesian': 'id', 'bahasa indonesia': 'id',
            'ms': 'ms', 'malay': 'ms', 'bahasa melayu': 'ms',
            'tl': 'tl', 'tagalog': 'tl', 'filipino': 'tl'
        }

    def parse_title(self, title: str, format_type: str) -> Dict[str, str]:
        """Parse a ROM title and extract metadata using the specified format rules."""
        if format_type == "nointro":
            return self._parse_nointro(title)
        elif format_type == "tosec":
            return self._parse_tosec(title)
        elif format_type == "goodtools":
            return self._parse_goodtools(title)
        elif format_type == "redump":
            # Redump uses No-Intro naming conventions
            return self._parse_nointro(title)
        else:
            # Fallback to generic parsing for unknown formats
            return self._parse_generic(title)

    def _detect_format(self, title: str) -> str:
        """Auto-detect the naming convention format."""
        # Check for TOSEC format (square brackets with dump flags)
        if re.search(r'\[[a-z!]+\]', title):
            return "tosec"
        
        # Check for GoodTools format (specific patterns)
        if re.search(r'\[[a-z!]+\]|\([A-Z]{1,3}\)', title):
            return "goodtools"
            
        # Check for No-Intro format (parentheses with regions)
        if re.search(r'\([A-Za-z\s,]+\)', title):
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
            
            # Check for dump status first (before regions)
            if not result['dump_status']:
                dump_status = self._extract_dump_status(group)
                if dump_status:
                    result['dump_status'] = dump_status
                    continue
                    
            # Check for development status
            if not result['development_status']:
                dev_status = self._extract_dev_status(group)
                if dev_status:
                    result['development_status'] = dev_status
                    continue
                    
            # Check for version info
            if not result['version_info']:
                version = self._extract_version(group)
                if version:
                    result['version_info'] = version
                    continue
                    
            # Check for languages
            if not result['language_codes']:
                languages = self._extract_languages(group)
                if languages:
                    result['language_codes'] = languages
                    continue
            
            # Check for regions (last priority)
            # Handle comma-separated regions in No-Intro format
            if ',' in group:
                # Split by comma and check each part for regions
                sub_regions = [part.strip() for part in group.split(',')]
                found_any_regions = False
                for sub_region in sub_regions:
                    region = self._standardize_region(sub_region, 'nointro')
                    if region:
                        regions_found.append(region)
                        found_any_regions = True
                if found_any_regions:
                    continue
            else:
                # Single region check
                region = self._standardize_region(group, 'nointro')
                if region:
                    regions_found.append(region)
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
                result['regions_list'] = regions_found  # Store individual regions for EAV storage
                
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
        
        # Find all parenthetical groups
        paren_groups = re.findall(r'\(([^)]+)\)', title)
        
        # Collect all regions for multi-region handling
        regions_found = []
        
        for group in paren_groups:
            # Check for regions (ISO country codes)
            region = self._standardize_region(group, 'tosec')
            if region:
                regions_found.append(region)
                continue
                
            # Check for languages
            if not result['language_codes']:
                languages = self._extract_languages(group)
                if languages:
                    result['language_codes'] = languages
                    continue
                    
            # Check for development status
            if not result['development_status']:
                dev_status = self._extract_dev_status(group)
                if dev_status:
                    result['development_status'] = dev_status
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
                result['regions_list'] = regions_found
                
        # Parse TOSEC dump flags in square brackets
        dump_flags = re.findall(r'\[([^\]]+)\]', title)
        for flag_group in dump_flags:
            # Split by space to handle multiple flags
            flags = flag_group.split()
            for flag in flags:
                # Check for verified dump
                if flag == '!':
                    if not result['dump_status']:
                        result['dump_status'] = 'verified'
                else:
                    dump_status = self._extract_dump_status(flag)
                    if dump_status and not result['dump_status']:
                        result['dump_status'] = dump_status
        
        return result

    def _parse_goodtools(self, title: str) -> Dict[str, str]:
        """Parse GoodTools format: Game Title (Country) [Flags]"""
        result = self._empty_result()
        
        # Extract base title (everything before first parenthesis or bracket)
        base_match = re.match(r'^([^(\[]+)', title.strip())
        if base_match:
            result['base_title'] = base_match.group(1).strip()
        else:
            result['base_title'] = title
            
        # Find all parenthetical groups
        paren_groups = re.findall(r'\(([^)]+)\)', title)
        
        # Collect all regions for multi-region handling
        regions_found = []
        
        for group in paren_groups:
            # Check for regions (GoodTools country codes)
            region = self._standardize_region(group, 'goodtools')
            if region:
                regions_found.append(region)
                continue
                
            # Check for languages
            if not result['language_codes']:
                languages = self._extract_languages(group)
                if languages:
                    result['language_codes'] = languages
                    continue
                    
            # Check for development status
            if not result['development_status']:
                dev_status = self._extract_dev_status(group)
                if dev_status:
                    result['development_status'] = dev_status
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
                result['regions_list'] = regions_found
                
        # Parse GoodTools dump flags in square brackets
        dump_flags = re.findall(r'\[([^\]]+)\]', title)
        for flag_group in dump_flags:
            # Split by space to handle multiple flags
            flags = flag_group.split()
            for flag in flags:
                # Check for verified dump
                if flag == '!':
                    if not result['dump_status']:
                        result['dump_status'] = 'verified'
                elif flag == '!p':
                    if not result['dump_status']:
                        result['dump_status'] = 'pending'
                else:
                    dump_status = self._extract_dump_status(flag)
                    if dump_status and not result['dump_status']:
                        result['dump_status'] = dump_status
        
        return result

    def _parse_generic(self, title: str) -> Dict[str, str]:
        """Parse generic format (fallback)."""
        result = self._empty_result()
        result['base_title'] = title
        return result

    def _standardize_region(self, region_text: str, source_format: str) -> Optional[str]:
        """Convert any region code to standardized No-Intro format."""
        if not region_text:
            return None
            
        region_clean = region_text.strip()
        
        # First check if it's already in No-Intro format (case-insensitive)
        if source_format in self.region_mappings:
            mapping = self.region_mappings[source_format]
            for key, value in mapping.items():
                if key.upper() == region_clean.upper():
                    return value
        
        # Check No-Intro format as fallback (case-insensitive)
        nointro_mapping = self.region_mappings['nointro']
        for key, value in nointro_mapping.items():
            if key.upper() == region_clean.upper():
                return value
            
        # Handle multi-region formats
        if ',' in region_clean:
            # This will be handled by the calling function
            return None
            
        # More precise partial matching - only match if the input is a significant part of the key
        # or if the key is a significant part of the input (avoid single character matches)
        for key, value in nointro_mapping.items():
            key_upper = key.upper()
            region_upper = region_clean.upper()
            
            # Only match if either:
            # 1. The input is at least 3 characters and is contained in the key
            # 2. The key is at least 3 characters and is contained in the input
            # 3. The input is exactly 2 characters and matches the key exactly
            if (len(region_upper) >= 3 and region_upper in key_upper) or                (len(key_upper) >= 3 and key_upper in region_upper) or                (len(region_upper) == 2 and region_upper == key_upper):
                return value
                
        return None

    def _extract_languages(self, text: str) -> Optional[str]:
        """Extract language codes from text."""
        text_lower = text.lower().strip()
        languages = []
        
        # Only exact matches - no partial matching
        for code, standard_code in self.language_codes.items():
            if code == text_lower:
                if standard_code not in languages:
                    languages.append(standard_code)
        
        return ','.join(languages) if languages else None

    def _extract_version(self, text: str) -> Optional[str]:
        """Extract version information from text."""
        # Look for version patterns: v1.0, Rev 1, Rev A, v20000101, etc.
        # Preserve the full version string including prefix
        version_patterns = [
            r'(v\d+\.?\d*)',  # v1.0, v1, v20000101
            r'(rev\s*\d+)',   # Rev 1, Rev2
            r'(rev\s*[a-z])',  # Rev A, Rev B
            r'(version\s*\d+\.?\d*)',  # Version 1.0
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Return the full matched string (including prefix)
                return match.group(1).strip()
        
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
        text_lower = text.lower().strip()
        
        # Only check for known dump status patterns, not generic single characters
        dump_status_patterns = {
            # Multi-character patterns (exact matches)
            'unl': 'unlicensed',
            'unlicensed': 'unlicensed',
            'pirate': 'pirate',
            'pirated': 'pirate',
            'cracked': 'cracked',
            'fixed': 'fixed',
            'hack': 'hack',
            'hacked': 'hack',
            'modified': 'modified',
            'trained': 'trained',
            'translated': 'translated',
            'alternate': 'alternate',
            'bad': 'bad',
            'overdump': 'overdump',
            'underdump': 'underdump',
            'virus': 'virus',
            'verified': 'verified',
            'good': 'verified',
            'oldtranslation': 'old_translation',
            'newtranslation': 'new_translation',
            'pending': 'pending',
            
            # Single character patterns (only when they appear as standalone flags)
            '!': 'verified',
            'a': 'alternate',
            'b': 'bad', 
            'cr': 'cracked',  # TOSEC cracked
            'f': 'fixed',
            'h': 'hack',
            'm': 'modified',
            'o': 'overdump',
            'p': 'pirate',
            't': 'trained',
            'tr': 'translated',  # TOSEC translated
            'u': 'underdump',
            'v': 'virus'
        }
        
        # Check for exact matches first (multi-character)
        for pattern, status in dump_status_patterns.items():
            if len(pattern) > 1 and pattern == text_lower:
                return status
        
        # Check for single character matches only if the text is exactly that character
        # and it's a known dump status flag (not part of version info like "Rev A")
        for pattern, status in dump_status_patterns.items():
            if len(pattern) == 1 and pattern == text_lower:
                # Additional check: make sure it's not part of version info
                if not re.match(r'^rev\s+[a-z0-9]+$', text_lower) and                    not re.match(r'^v\d+', text_lower) and                    not re.match(r'^version\s+\d+', text_lower):
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
