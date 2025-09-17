## Preamble

This convention was created to improve the consistency and quality of all NoIntro Dat releases. To be recognized as an Official No-Intro Dat, it must meet all requirements as described here.

Dats that are not converted will be dropped from the project until they meet the requirements of this convention.

## Naming convention

### General

General naming rules are described here.

#### Characters

Only 7 Bit ASCII (Low ASCII) characters are allowed for titles. Accents, Umlauts, High ASCII, Double byte characters are converted to the best comparable Low ASCII characters. Also several characters that are invalid on some file systems are not allowed.

The following Low ASCII characters are allowed:
a-z A-Z 0-9 SPACE $ ! # % ' ( ) + , - . ; = @ [ ] ^ _ { } ~

In addition to the various control characters, the following Low ASCII characters are NOT allowed:
\ / : * ? " < > | `

Discretion is advised for the adoption of special characters in artistic titles (ex. leet speech). In that case they should be converted to their real meaning.

In addition, a filename is not allowed to start or end with a SPACE or DOT character.

#### Priority

Titles should be primary named after the publisher’s released title (box title). Sometimes the screen title can be more relevant or complete than the box title. In that case the title may be named after the screen title or a mix of the two. If box and screen titles are totally different, the box title is preferred. Common sense is highly advised!

Only one title is used even if the game contains multiple titles or is released with different titles in multiple regions. In that case the priority is in this order: US English title, Europe English title, Japanese title and rest.

#### Capitalization

Generally all common names, adjectives and verbs should be uppercased. Articles and link words should be lowercased except when first word.

*Examples: Adventure of the Hero, Riding in a Car, Travel from Earth to the Moon, From Earth..., Into the Darkness...*

The official title written by the publisher or developer can be used as a reference including related titles from other media (movie titles). Some titles also have an unusual capitalization on purpose. In that case, capitalization should be left as intended.

*Example 1: RoboCop (= Roboter + Cop)
*Example 2: Sonic The Hedgehog is all uppercase: "The" is his middle name, not an article.

However titles that are entirely capitalized should be highly avoided except if the title is an acronym!

#### Ordering

If the first word is a common article then it will be moved to the end of the main title and separated with a comma. This includes non English common articles too.

*Example 1: The Legend of Zelda -> Legend of Zelda, The
*Example 2: A Man Born in Hell -> Man Born in Hell, A

#### Subtitles

Subtitles and pretitles are always separated from the main title by a hyphen " - ". Titles that use a different separation style (ex. colon or "~ Subtitle ~") will be converted to a hyphen style.

If the first word of a subtitle is a common article it will NOT be moved to the end.

*Example 1: Castlevania II - Belmont's Revenge
*Example 2: Double Dragon - The Ultimate Team
Example 3: Legend of Zelda, The - A Link to the Past

#### Punctuation

Single and multiple dots should always be included as part of the title. In abbreviated words such as "vs", "Dr", "Mr", etc the dot should be included (or not) as it appears on the title.

#### Trademark Reminders

Trademark reminders such as "Disney’s" are not included in the title usually. They are only included if they are relevant or part of the title (ex. "Disney Sports"). Also generally original artists or authors are not removed from titles (ex. "Mary Shelley’s Dracula, "Archer McLean’s Dropzone).

### Japanese Romanization

Japanese characters are transcribed to roman characters according to a ASCII-compatible form of the [Hepburn convention](https://en.wikipedia.org/wiki/Hepburn_romanization#Hepburn_romanization_charts).

The following pattern is generally followed:

- When を is used as a particle, it is written o.
- When へ is used as a particle, it is written e.
- Long vowels are transcribed as in [Wapuro romaji](https://en.wikipedia.org/wiki/Wāpuro_rōmaji)
- Loan words are spelled in their original language (e.g. "Pocket Monsters" not "Poketto Monsutaa")
- Suffixes (-san, -tachi, -dan) are usually hyphenated unless a common word (e.g. tomodachi)
- Capitalization rules apply (lowercase for particles and suffixes) with the following exceptions:
  - Particles are lowercased even if they are the final word in the title or before a hyphen (e.g. "Higanbana no Saku Yoru ni"). This includes words like から and より.

Examples:

- "Looney Tunes - Bugs Bunny to Yukai na Nakama-tachi"
- "Ninku Dai-2-dan - Ninku Sensou Hen"

### Chinese Romanization

TO DO

#### Korean Romanization

TO DO

## Filename format

### Overview

The following elements can be part of a ROM title. They are also appended in this order.

[BIOS flag] Title (Region) (Languages) (Version) (Devstatus) (Additional) (Special) (License) [Status]

The only mandatory elements are Title and Region. All other elements are optional.

### Name

**Form HTML name:** archive_name
**Custom XML name:** name
**Mandatory**: Yes
**Default**: [blank]

The title of the game. See also chapter 2.

### Name Alt

**Form HTML name:** archive_name_alt
**Custom XML name:** namealt
**Mandatory**: No
**Default**: [blank]

Same as Name, but for UTF-8 filesystems, so no need to romanise (you can use Russian cyrillic, Japanese kanji etc).

### Region

**Form HTML name:** archive_region
**Custom XML name:** region
**Mandatory**: Yes
**Default**: [blank]

This flag is the region of the game. It is put in parentheses. Full country names are used.

The flag represents the primary region. Secondary regions are omitted (ex. USA and Canada are often the same; Canada will be omitted).

Single region codes (not exhaustive):
\- (Australia) *Don’t use with Europe*
\- (Brazil)
\- (Canada) *Don’t use with USA*
\- (China)
\- (France)
\- (Germany)
\- (Hong Kong)
\- (Italy)
\- (Japan)
\- (Korea)
\- (Netherlands)
\- (Spain)
\- (Sweden)
\- (USA) *Includes Canada*

If a game is released in all 3 major territories (Japan, USA, Europe) the flag (World) will be used. If a game is only released in 2 major territories, then be both will be listed and separated by a comma and a space.

If a game is released in 2 or more European countries the flag (Europe) will be used. The flag (Asia) will be only used if the target regions are multiple Asian countries and the game is different from the Japanese release.

Multi region codes:
\- (World)
\- (Europe) *Includes Australia*
\- (Asia)
\- (Japan, USA)
\- (Japan, Europe)
\- (USA, Europe)

This is basically used as a summary of regions specified in the sources' Region fields

### Language(s)

**Form HTML name:** archive_languages
**Custom XML name:** languages
**Mandatory**: Not in filename, but yes, in DAT-o-MATIC/XML
**Default**: [blank]

This flag lists the languages of a game. It is put in parentheses. ISO 639-1 codes are used.
http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes

The flag is only added if more than one language is available in the game.

First letter of each language code is always uppercased, second letter is always lowercased. All codes are separated by comma without space.

Language variations are merged and not listed twice (ex. US English, UK English).

List of codes:
En English
Ja Japanese
Fr French
De German
Es Spanish
It Italian
Nl Dutch
Pt Portuguese
Sv Swedish
No Norwegian
Da Danish
Fi Finish
Zh Chinese
Ko Korean
Pl Polish

This order is to be respected.

*Example: Super Metroid (Japan, USA) (En,Ja)*

### Version

**Form HTML name:** archive_version
**Custom XML name:** version
**Mandatory**: No
**Default**: [blank]

This flag shows the version (vX.XX) or revision (Rev X) of the game. It is put in parentheses. Revision is used instead of version when applicable. Numbers and/or letters can be used depending on the system or program approach.

The flag is only added if the version/revision is greater than the initial release. Source is usually ROM header or cartridge stamps.

### Development and/or Commercial Status

**Form HTML name:** archive_version
**Custom XML name:** archive_devstatus
**Mandatory**: No
**Default**: [blank]

Those flags are added to games that are not classical commercial releases. It is applicable for (but not limited to) unfinished games, promotional games, prize games, limited editions.

Examples:

- The flag (Beta) is added to games that are unfinished but have a final release.
- The flag (Proto) is added to unreleased games.
- The flag (Sample) is added to internal-use or press samples.

If more than one (Beta) is available an incremented number will be added (Beta 1), (Beta 2), etc. If determinable the oldest Beta gets the lowest number. Same with Protos and Samples. Although if there is build date information available, instead of doing this, the build date should be written in the "Additional" field in YYYY-MM-DD format.

### Additional

**Form HTML name:** archive_additional
**Custom XML name:** additional
**Mandatory**: No
**Default**: [blank]

This flag will be only added if it is required to differentiate between multiple releases. It is put in parentheses. Additional information can be added here (ex. Rumble Version, Doritos Promo)

### Special1

**Form HTML name:** archive_special1
**Custom XML name:** special1
**Mandatory**: No
**Default**: [blank]

These flags will be added to games that are noteworthy different from the usual other games. It is put in parentheses.

Example: (ST), (MB), (NP), etc

### Special2

**Form HTML name:** archive_special2
**Custom XML name:** special1
**Mandatory**: No
**Default**: [blank] [to do]

### Licensed

**Form HTML name:** archive_licensed
**Custom XML name:** licensed
**Mandatory**: No in filename and XML, yes in DoM
**Default**: 1

Boolean in DoM/XML. The flag (Unl) will be added if a game is unlicensed.

### Status

The flag [b] will be added to dumps that are bad and/or hacked. This is automatically added based on the source/file entries.

### BIOS flag

**Form HTML name:** archive_bios
**Custom XML name:** bios
**Mandatory**: No
**Default**: 0 Boolean.

### Dat format

TO DO

| Code | Language name |           Native Name            | Common Flag |
| :--: | :-----------: | :------------------------------: | :---------: |
|  En  |    English    |             English              |    🇬🇧🇺🇸     |
|  Ja  |   Japanese    |  日本語 (にほんご／にっぽんご)   |     🇯🇵      |
|  Fr  |    French     |             Français             |     🇫🇷      |
|  De  |    German     |             Deutsch              |     🇩🇪      |
|  Es  |    Spanish    |             Español              |     🇪🇸      |
|  It  |    Italian    |             Italiano             |     🇮🇹      |
|  Nl  |     Dutch     |            Nederlands            |     🇳🇱      |
|  Pt  |  Portuguese   |            Português             |     🇵🇹      |
|  Sv  |    Swedish    |             Swenska              |     🇸🇪      |
|  No  |   Norwegian   |              Norsk               |     🇳🇴      |
|  Da  |    Danish     |              Dansk               |     🇩🇰      |
|  Fi  |    Finish     |           Suomen Kieli           |     🇫🇮      |
|  Zh  |    Chinese    |         中文, 汉汉, 漢語         |     🇨🇳      |
|  Ko  |    Korean     | 한한한 (韓國語); 한한한 (朝鮮語) |     🇰🇷      |
|  Pl  |    Polish     |              Polski              |     🇵🇱      |

## Non-name-affecting archive fields

### Show lang

**Form HTML name:** archive_showlang
**Custom XML name:** showlang
Integer. Default is "auto" ("2") , other option is "always" ("[unknown]").

### Pirate

**Form HTML name:** archive_pirate
**Custom XML name:** [unknown]
Boolean. Default is 0.

### Adult

**Form HTML name:** archive_adult
**Custom XML name:** [unknown]
Boolean. Default is 0.

### nodump

**Form HTML name:** archive_nodump
**Custom XML name:** nodump
Boolean. Default is 0. If the ROM is undumped or not.

### Physical

**Form HTML name:** archive_physical
**Custom XML name:** physical
Boolean. Default is 1 for most dats. If the ROM is physical or digital.

### Public

**Form HTML name:** archive_public
**Custom XML name:** public
Boolean. Default is 1. If the archive is public or not. Unrelated to the private dats - this is basically just a way to get ride of an old/garbage entry without deleting it (since restoring from selection is not straightforward at the moment).

### DAT

**Form HTML name:** archive_dat
**Custom XML name:** dat
Boolean. Default is 1. If the archive appears in the datfile or not. Same usage as "Public".

### Release

**Form HTML name:** archive_complete
**Custom XML name:** [unknown]
Boolean. Default is 1 (apparently?). 1 is "Fulltitle" and 0 is "Proto/Beta/Demo/...". Basically a way to make the "Devstatus" field machine readable, for use in dat filtering.

### P/Clone

**Form HTML name:** archive_clone
**Custom XML name:** clone
Optional, but you should fill it out


String. Set to "P" if this archive is the parent, or put the archive number of the parent if this archive is a clone. [to do]

### Reg. Parent

**Form HTML name:** archive_regparent
**Custom XML name:** regionalparent
Optional, but you should fill it out


String. [to do]

### MergeOf

**Form HTML name:** archive_mergeof
**Custom XML name:** mergeof
Optional


String. New field, something todo with MAME-like merging.

### GameID

**Form HTML name:** archive_gameid
**Custom XML name:** gameid
Optional


String. Used by some datters, but probably should be deprecated for source digitalserial and file serial (despite the fact it was created after those).

### Description

**Form HTML name:** archive_gameid
**Custom XML name:** archive_description
Optional


String. Deprecated [to do].