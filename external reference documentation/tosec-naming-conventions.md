# ntroduction

The Old School Emulation Center (TOSEC) is a retrocomputing initiative dedicated to the cataloging and preservation of software, firmware and resources for arcade machines, microcomputers, minicomputers and video game consoles. The main goal of the project is to catalog and audit various kinds of software and firmware images for these systems. To support this, the TOSEC Naming Convention (TNC) was created.

The TNC is a set of standardized rules used by TOSEC renamers to provide a consistent, clear and concise naming scheme for cataloging any image from any system. This document serves to cover and describe the entire naming convention and how it should be used.

# Single Image Sets

Most sets are single image sets, so this is the standard used in most of the images cataloged by TOSEC members, the exception to this are the multi-image sets like compilations, etc., which use the same or a very similar scheme for the name of each image within the compilation, with some extra properties to distinguish the various images.

To be TNC complaint a set must follow a well-defined number of rules describing the image. Currently the fields used in TNC are: title, version, demo, date, publisher, system, video, country, language, copyright status, development status, media type, media label, a group of dump info flags (cracked, fixed, hacked…), and finally the more info flag.

The format should look like this example:

• Title version (demo) (date)(publisher)(system)(video)(country)(language)(copyright status)(development status)(media type)(media label)[dump info flags][more info]

 

With dump info flags relative to image modifications being ordered alphabetically first (**cr**acked, **f**ixed, **h**acked, **m**odified, **p**irated, **t**rained, **tr**anslated) followed by the ones related with information about the dump process in the following order: **o**ver dump, **u**nder dump, **v**irus, **b**ad dump, **a**lternate, verified dump [**!**].

So if a set had all dump flags it would look like:

• Title version (demo) (date)(publisher)(system)(video)(country)(language)(copyright)(devstatus)(media type)(media label)[cr][f][h][m][p][t][tr][o][u][v][b][a][!][more info]

 

Although it should be noted that obviously no set can have all flags at the same time because some of them are incompatible with others (e.g. you **cannot** have a set marked as [o] and [u] at the same time etc.)

A final note that all flags used to classify the image are separated either with ( ), or [ ] for dump info flags and more info, also the fields marked with **mandatory** in the next chapters are required for the minimum use of TNC in renaming a file.

All entries marked "**mandatory**" are required for the **minimum** use of TNC in renaming a file, entries contained in parentheses "( )" or square brackets "[ ]" are flags used for classifying the image.

• **Note:** "Title (date)(publisher)" is the bare **minimum** required for a renamed image.

 

 

## Forbidden Characters

Any characters that are disallowed within a file name in most mainstream operating systems cannot be used.

### Forbidden Character Possibilities

| **Symbol** | **Description** |
| ---------- | --------------- |
| **/**      | Slash           |
| **\**      | Backslash       |
| **?**      | Question Mark   |
| **:**      | Colon           |
| *****      | Asterisk        |
| **"**      | Quote           |
| **<**      | Less Than       |
| **>**      | Greater Than    |
| **\|**     | Vertical Pipe   |

 

## Title

**Mandatory**

The name of the software. This should match the official publisher's released title if known, or the name on the title screen (there can often be differences between the two and best judgement will need to be exercised).

In cases where the title begins with "The" or "A", it should be moved to the end of the title, and preceded by a comma. This same rule applies if the title is not in English, e.g. "De" for Dutch, "Die" for German, and "Le/La/Les" for French etc.

• "The Legend of TOSEC" would become "Legend of TOSEC, The"

• "A Legend of TOSEC" would become "Legend of TOSEC, A

 

## Version

Version information is considered an extension of the filename. It should be included in all cases where it is known and verified. There are **no parentheses** involved, and the format should (generally) be "**v x.yy** ", with **x** being the major, and **yy** the minor revision. If the program uses a different approach, then this is what should be used, e.g. "Re**v x**", "**vYYYYMMDD** "etc.

### Version Flag Examples

• Legend of TOSEC, The **v1.0**

• Legend of TOSEC, The **v1.03b**

• Legend of TOSEC, The **Rev 1**

• Legend of TOSEC, The **v20000101**

 

 

## Demo

This field is used if a software title is a demonstration, promotional or sample version. This is the **only** case where there should be a space between a closing and the following opening parenthesis.

### Demo Flag Possibilities

| **Demo Flag**      | **Description**                                          |
| ------------------ | -------------------------------------------------------- |
| **demo**           | General demonstration version                            |
| **demo-kiosk**     | Retail demo units and kiosks                             |
| **demo-playable**  | General demonstration version, playable                  |
| **demo-rolling**   | General demonstration version, non-interactive           |
| **demo-slideshow** | General demonstration version, non-interactive slideshow |

### Demo Flag Samples

• Legend of TOSEC, The **(demo)** (1986)(Devstudio)

 

Note the space between "(demo)" and "(1986)"

 

 

## Date

**Mandatory**

The date the software was released. If no exact year is known but the decade can be determined, then use (**199x**) if from the 1990's, (200**x**) if from the 2000's etc. If no information is available, use (**19xx**) or (**20xx**) until a year can be determined.

If more complete date information is known, then this can be shown using the format **YYYY-MM-DD**.

Also note that **19xx-MM** and **19xx-MM-DD** are allowed when only month or month and day are known, this can happen in things like magazines and other monthly publications where year is unknown. Additionally, if the exact day in the month is not known, but the day can be narrowed down to part of the month, then **19xx-MM-Dx** is also acceptable.

### Date Flag Examples

• Legend of TOSEC, The **(19xx)**

• Legend of TOSEC, The **(200x)**

• Legend of TOSEC, The **(1986)**

• Legend of TOSEC, The **(199x)**

• Legend of TOSEC, The **(2001-01)**

• Legend of TOSEC, The **(1986-06-21)**

• Legend of TOSEC, The **(19xx-12)**

• Legend of TOSEC, The **(19xx-12-25)**

• Legend of TOSEC, The **(19xx-12-2x)**

 

 

## Publisher

**Mandatory**

The publisher field contains the company name(s) of the software's publisher(s). If this is unknown or if desired, the developer's company name(s) or programmer's name(s) can also be used.

In cases where none of these are known, a hyphen **(-)** is used. If more than one name is required, separate names with a space hyphen space (" - ")

As a general rule, **do not** include extra company notations such as Ltd, PLC, Inc. unless they are absolutely necessary in the company name.

If individual person names need to be used, these should be entered in the format "Surname, First name" or "Surname, Initials".

Multiple publishers should be in alphabetical order.

### Publisher Flag Examples

• Legend of TOSEC, The (1986)**(Devstudio)**

• Legend of TOSEC, The (1986)**(-)**

• Legend of TOSEC, The (1986)**(Ultrafast Software)**

• Legend of TOSEC, The (1987)**(U.S. Gold)**

• Legend of TOSEC, The (1988)**(Delphine - U.S. Gold)**

• Legend of TOSEC, The (2001)**(Smith, Robert)**

• Legend of TOSEC, The (2001)**(Smith, R.)**

• Legend of TOSEC, The (2001)**(Smith, R. - White, P.S.)**

 

 

## System

This field is reserved for collections that require multiple system support, such as Amiga, which could require (**A500**), (**A1000**) etc., to address compatibility issues.

### System Flag Possibilities

| **System Flag**            | **Description**       |
| -------------------------- | --------------------- |
| **+2**                     | Sinclair ZX Spectrum  |
| **+2a**                    | Sinclair ZX Spectrum  |
| **+3**                     | Sinclair ZX Spectrum  |
| **130XE**                  | Atari 8-bit           |
| **A1000**                  | Commodore Amiga       |
| **A1200**                  | Commodore Amiga       |
| **A1200-A4000**            | Commodore Amiga       |
| **A2000**                  | Commodore Amiga       |
| **A2000-A3000**            | Commodore Amiga       |
| **A2024**                  | Commodore Amiga       |
| **A2500-A3000UX**          | Commodore Amiga       |
| **A3000**                  | Commodore Amiga       |
| **A4000**                  | Commodore Amiga       |
| **A4000T**                 | Commodore Amiga       |
| **A500**                   | Commodore Amiga       |
| **A500+**                  | Commodore Amiga       |
| **A500-A1000-A2000**       | Commodore Amiga       |
| **A500-A1000-A2000-CDTV**  | Commodore Amiga       |
| **A500-A1200**             | Commodore Amiga       |
| **A500-A1200-A2000-A4000** | Commodore Amiga       |
| **A500-A2000**             | Commodore Amiga       |
| **A500-A600-A2000**        | Commodore Amiga       |
| **A570**                   | Commodore Amiga       |
| **A600**                   | Commodore Amiga       |
| **A600HD**                 | Commodore Amiga       |
| **AGA**                    | Commodore Amiga       |
| **AGA-CD32**               | Commodore Amiga       |
| **Aladdin Deck Enhancer**  | Nintendo NES          |
| **CD32**                   | Commodore Amiga       |
| **CDTV**                   | Commodore Amiga       |
| **Computrainer**           | Nintendo NES          |
| **Doctor PC Jr.**          | Nintendo NES          |
| **ECS**                    | Commodore Amiga       |
| **ECS-AGA**                | Commodore Amiga       |
| **Executive**              | Osborne 1 & Executive |
| **Mega ST**                | Atari ST              |
| **Mega-STE**               | Atari ST              |
| **OCS**                    | Commodore Amiga       |
| **OCS-AGA**                | Commodore Amiga       |
| **ORCH80**                 | ???                   |
| **Osbourne 1**             | Osborne 1 & Executive |
| **PIANO90**                | ???                   |
| **PlayChoice-10**          | Nintendo NES          |
| **Plus4**                  | ???                   |
| **Primo-A**                | Microkey Primo        |
| **Primo-A64**              | Microkey Primo        |
| **Primo-B**                | Microkey Primo        |
| **Primo-B64**              | Microkey Primo        |
| **Pro-Primo**              | Microkey Primo        |
| **ST**                     | Atari ST              |
| **STE**                    | Atari ST              |
| **STE-Falcon**             | ???                   |
| **TT**                     | Atari ST              |
| **TURBO-R GT**             | MSX                   |
| **TURBO-R ST**             | MSX                   |
| **VS DualSystem**          | Nintendo NES          |
| **VS UniSystem**           | Nintendo NES          |

### System Flag Examples

• Legend of TOSEC, The (1986)(Devstudio)**(A500)**

 

 

## Video

The video field is only used in cases where the images cannot be classified by countries or languages, but for example only the **PAL** or **NTSC** video formats they were released in.

### Video Flag Possibilities

| **Video Flag** | **Description** |
| -------------- | --------------- |
| **CGA**        | ?               |
| **EGA**        | ?               |
| **HGC**        | ?               |
| **MCGA**       | ?               |
| **MDA**        | ?               |
| **NTSC**       | ?               |
| **NTSC-PAL**   | ?               |
| **PAL**        | ?               |
| **PAL-60**     | ?               |
| **PAL-NTSC**   | ?               |
| **SVGA**       | ?               |
| **VGA**        | ?               |
| **XGA**        | ?               |

### Video Flag Examples

• Legend of TOSEC, The (1986)(Devstudio)**(PAL)**

• Legend of TOSEC, The (1986)(Devstudio)**(NTSC)**

 

 

## Country

This field is used to classify the country or region of origin. The codes used are defined by the international ISO 3166-1 alpha-2 standard where possible.

### Country/Region Flag Possibilities

| **Country/Region Flag** | **Description**        |
| ----------------------- | ---------------------- |
| **AE**                  | United Arab Emirates   |
| **AL**                  | Albania                |
| **AS**                  | Asia                   |
| **AT**                  | Austria                |
| **AU**                  | Australia              |
| **BA**                  | Bosnia and Herzegovina |
| **BE**                  | Belgium                |
| **BG**                  | Bulgaria               |
| **BR**                  | Brazil                 |
| **CA**                  | Canada                 |
| **CH**                  | Switzerland            |
| **CL**                  | Chile                  |
| **CN**                  | China                  |
| **CS**                  | Serbia and Montenegro  |
| **CY**                  | Cyprus                 |
| **CZ**                  | Czech Republic         |
| **DE**                  | Germany                |
| **DK**                  | Denmark                |
| **EE**                  | Estonia                |
| **EG**                  | Egypt                  |
| **ES**                  | Spain                  |
| **EU**                  | Europe                 |
| **FI**                  | Finland                |
| **FR**                  | France                 |
| **GB**                  | United Kingdom         |
| **GR**                  | Greece                 |
| **HK**                  | Hong Kong              |
| **HR**                  | Croatia                |
| **HU**                  | Hungary                |
| **ID**                  | Indonesia              |
| **IE**                  | Ireland                |
| **IL**                  | Israel                 |
| **IN**                  | India                  |
| **IR**                  | Iran                   |
| **IS**                  | Iceland                |
| **IT**                  | Italy                  |
| **JO**                  | Jordan                 |
| **JP**                  | Japan                  |
| **KR**                  | South Korea            |
| **LT**                  | Lithuania              |
| **LU**                  | Luxembourg             |
| **LV**                  | Latvia                 |
| **MN**                  | Mongolia               |
| **MX**                  | Mexico                 |
| **MY**                  | Malaysia               |
| **NL**                  | Netherlands            |
| **NO**                  | Norway                 |
| **NP**                  | Nepal                  |
| **NZ**                  | New Zealand            |
| **OM**                  | Oman                   |
| **PE**                  | Peru                   |
| **PH**                  | Philippines            |
| **PL**                  | Poland                 |
| **PT**                  | Portugal               |
| **QA**                  | Qatar                  |
| **RO**                  | Romania                |
| **RU**                  | Russia                 |
| **SE**                  | Sweden                 |
| **SG**                  | Singapore              |
| **SI**                  | Slovenia               |
| **SK**                  | Slovakia               |
| **TH**                  | Thailand               |
| **TR**                  | Turkey                 |
| **TW**                  | Taiwan                 |
| **US**                  | United States          |
| **VN**                  | Vietnam                |
| **YU**                  | Yugoslavia             |
| **ZA**                  | South Africa           |

In the case of two countries being required, both are given, alphabetised and separated by a hyphen:

For example: (DE-GB) - Released in Germany and the United Kingdom

For example: (DE-FR) - Released in France and Germany

For example: (EU-US) - Released in Europe and the US

 

### Country Flag Examples

• Legend of TOSEC, The (1986)(Devstudio)**(US)**

• Legend of TOSEC, The (1986)(Devstudio)**(JP)**

• Legend of TOSEC, The (1986)(Devstudio)**(DE)**

• Legend of TOSEC, The (1986)(Devstudio)**(DE-FR)**

 

 

## Language

The language used in the software. The codes used are defined by the international ISO 639-1 standard.

Language flags usage has to obey a few basic rules for reasons of enforced simplicity:

English is seen as the **default** language, in other words when no language or country flag is used it is taken that the software is in English or is language neutral.

On the other hand if a country flag is used, we assume that the software language is the official country language, so there is no need to use "(JP)(ja) ", "(DE)(de)" or "(PT)(pt)" only the country code. Conversely, software released in Japan but using English language should be "(JP)(en)" for example.

###  

### Language Flag Examples

• Legend of TOSEC, The (1986)(Devstudio) ***-\*** *set uses English language or is language neutral..*

• Legend of TOSEC, The (1986)(Devstudio)(pt) ***-\*** *set is in Portuguese.*

• Legend of TOSEC, The (1986)(Devstudio)(JP) ***-\*** *set released in Japan and in Japanese.*

• Legend of TOSEC, The (1986)(Devstudio)(JP)(en) ***-\*** *set released in Japan and in English.*

 

In the case of two languages being required, both are given, separated by a hyphen:

For example: (**en-fr**) Contains English and French versions

For example: (**es -pt**) Contains Spanish and Portuguese versions

For example: (**de-fr**) Contains Deutsch and French versions

 

When two languages are used they should be alphabetically ordered.

 

In cases of more than two languages or countries being required, (**Mx**) is used to represent multiple languages, where **x** is the number of languages:

 

For example: (**M3**) for 3 languages, so "Legend of TOSEC, The (1986)(Devstudio)(**M3**)"

For example: (**M4**) for 4 languages, so "Legend of TOSEC, The (1986)(Devstudio)(**M4**)"

 

### Language Flag Possibilities

| **Language Flag** | **Description** |
| ----------------- | --------------- |
| **ar**            | Arabic          |
| **bg**            | Bulgarian       |
| **bs**            | Bosnian         |
| **cs**            | Czech           |
| **cy**            | Welsh           |
| **da**            | Danish          |
| **de**            | German          |
| **el**            | Greek           |
| **en**            | English         |
| **eo**            | Esperanto       |
| **es**            | Spanish         |
| **et**            | Estonian        |
| **fa**            | Persian         |
| **fi**            | Finnish         |
| **fr**            | French          |
| **ga**            | Irish           |
| **gu**            | Gujarati        |
| **he**            | Hebrew          |
| **hi**            | Hindi           |
| **hr**            | Croatian        |
| **hu**            | Hungarian       |
| **is**            | Icelandic       |
| **it**            | Italian         |
| **ja**            | Japanese        |
| **ko**            | Korean          |
| **lt**            | Lithuanian      |
| **lv**            | Latvian         |
| **ms**            | Malay           |
| **nl**            | Dutch           |
| **no**            | Norwegian       |
| **pl**            | Polish          |
| **pt**            | Portuguese      |
| **ro**            | Romanian        |
| **ru**            | Russian         |
| **sk**            | Slovakian       |
| **sl**            | Slovenian       |
| **sq**            | Albanian        |
| **sr**            | Serbian         |
| **sv**            | Swedish         |
| **th**            | Thai            |
| **tr**            | Turkish         |
| **ur**            | Urdu            |
| **vi**            | Vietnamese      |
| **yi**            | Yiddish         |
| **zh**            | Chinese         |

 

### Further Language Flag Examples

• Legend of TOSEC, The (1986)(Devstudio)**(de)**

• Legend of TOSEC, The (1986)(Devstudio)**(pt)**

• Legend of TOSEC, The (1986)(Devstudio)**(de-fr)**

 

 

## Copyright Status

This field is used to denote the copyright status of software if applicable. If the software has been realised to the Public Domain by the copyright holder or if it is Freeware or Shareware for example, this is the place to note it.

If a Shareware title is registered, -R is appended to the field. This can also be used for Cardware and Giftware titles.

###  

### Copyright Status Flag Possibilities

| **Copyright Flag** | **Description**      |
| ------------------ | -------------------- |
| **CW**             | Cardware             |
| **CW-R**           | Cardware-Registered  |
| **FW**             | Freeware             |
| **GW**             | Giftware             |
| **GW-R**           | Giftware-Registered  |
| **LW**             | Licenceware          |
| **PD**             | Public Domain        |
| **SW**             | Shareware            |
| **SW-R**           | Shareware-Registered |

 

### Copyright Status Flag Examples

• Legend of TOSEC, The (1986)(Devstudio)**(PD)**

• Legend of TOSEC, The (1986)(Devstudio)(FR)**(SW)**

 

 

## Development Status

This field is for marking alpha, beta, preview, prototype or pre-release versions of software titles.

### Development Status Flag Possibilities

| **Development Flag** | **Description**                    |
| -------------------- | ---------------------------------- |
| **alpha**            | Early test build                   |
| **beta**             | Later, feature complete test build |
| **preview**          | Near complete build                |
| **pre-release**      | Near complete build                |
| **proto**            | Unreleased, prototype software     |

### Development Status Flag Examples

• Legend of TOSEC, The (1986)(Devstudio)(US)**(beta)**

• Legend of TOSEC, The (1986)(Devstudio)(US)**(proto)**

 

Media Type

This field is used if the software spans more than one optical, diskette, tape or file. Note that apart from the normal possibilities (Disk, Disc, Tape …), "**Side x of y**" is also allowed.

### Media Type Possibilities

| **Media Types** | **Description**           |
| --------------- | ------------------------- |
| **Disc**        | Optical disc based media  |
| **Disk**        | Magnetic disk based media |
| **File**        | Individual files          |
| **Part**        | Individual parts          |
| **Side**        | Side of media             |
| **Tape**        | Magnetic tape based media |

For example, where there are 9 or less disks, the format of "(**Disk x of y**)" is used, if there are 10 or more disks then (**Disk xx of yy**) should be used, there can also be the case where more than one volume is grouped in a single image, so something like (**Part 1-2 of 3**) is also allowed.

### Media Flag Examples

• Legend of TOSEC, The (1986)(Devstudio)(US)**(File 1 of 2)**

• Legend of TOSEC, The (1986)(Devstudio)(US)**(File 2 of 2)**

• Legend of TOSEC, The (1986)(Devstudio)(US)**(Disc 1 of 6)**

• Legend of TOSEC, The (1986)(Devstudio)(US)**(Disk 06 of 13)**

• Legend of TOSEC, The (1986)(Devstudio)(US)**(Side A)**

• Legend of TOSEC, The (1986)(Devstudio)(US)**(Side B)**

• Legend of TOSEC, The (1986)(Devstudio)(US)**(Tape 2 of 2 Side B)**

• Legend of TOSEC, The (1986)(Devstudio)(US)**(Side 1 of 2)**

• Legend of TOSEC, The (1986)(Devstudio)(US)**(Part 1-2 of 3)**

 

 

## Media Label

If the disk label is required, this field should contain it. This field is **always** the **last** flag using **( ) brackets**, just before any existent [ ] flags.

This is mainly used when a "**Save Disk**", "**Program Disk**", "**Scenery Disk**" etc. might be requested by the software when running. For example (Disk 2 of 2) is not useful by itself when the program asks you to "**Insert Character Disk**".

### Media Label Flag Examples

• Legend of TOSEC, The (1986)(Devstudio)(Disk 3 of 3)**(Character Disk)**

• Legend of TOSEC, The (1986)(Devstudio)(US)(Disk 1 of 2)**(Program)**

• Legend of TOSEC, The (1986)(Devstudio)(US)(Disk 2 of 2)**(Data)**

• Legend of TOSEC, The (1986)(Devstudio)(US)(Disk 2 of 2)**(Disk B)**

• Legend of TOSEC, The (1986)(Devstudio)(US)**(Bonus Disc)**

 

 

##  

## Dump Info Flags

This is the 'alphabet soup' used to describe the nature, quality and condition of the particular image of the software (not the software as a whole). This is where **images** that are **b**ad, **a**lternates, **cr**acks, **h**acks, **t**rainers, **f**ixes, **tr**anslations, etc. are noted.

**Note:** These flags use square brackets [ ]

As noted at the start of **Single Image Sets** chapter, the order of those flags is important and should be kept correct. The order should always be:

•[cr][f][h][m][p][t][tr][o][u][v][b][a][!]

 

Please note that whenever a "group" is used in a dump flag, the alteration could also be done by single persons. Renamers should be aware that taking the group they're in (if known) is preferable.

### Cracked - [cr]

The original software has been deliberately hacked/altered to remove some form of copy protection.

The variants are:

**[cr]** - Cracked

**[cr Cracker]** - Cracked by Cracker (group or person)

### Fixed - [f]

The original software has been deliberately hacked/altered in some way to 'improve' or fix the image to work in a non-standard way, e.g. 'fixing' a software that is supposed to run in PAL to run on a NTSC system.

The variants are:

**[f]** - Fixed

**[f Fix]** - Fix/amendment added

**[f Fixer]** - Fixed by Fixer (group or person)

**[f Fix Fixer]** - Fix added by Fixer (group or person)

 

In cases where there is more than one Fix or Fixer, they can be separated like the group names in other dump flags, for example, [f Fix1 group1 - Fix2 group2] - fix1 was made by group1 and fix2 was made by group2.

 

Some examples of fixes:

**NTSC** = Fixed for NTSC

**copier** = Fixed for game copiers

**Note:** Renamers must try to use fix descriptions already used before, e.g. if "copier" is already in use then there is no need to use "copier" in one set and "game copier" in another (if they represent the same thing).

###  

### Hacked - [h]

The original software has been deliberately hacked/altered in some way, such as adding an intro or changing in game sprites or text.

The variants are:

**[h]** - Hacked

**[h Hack]** – Description of hack

**[h Hacker]** – Hacked by (group or person)

**[h Hack Hacker]** – Description of hack, followed by hacker (group or person)

 

**Note:** Renamers must try to use hack descriptions already used before, e.g. if "intro" is already in use then there is no need to use "intro" in one set and "scene intro" in another (if they represent the same thing).

###  

### Modified - [m]

The original software has been hacked/altered in some way (but not deliberately), e.g. if you dumped an original UNTOUCHED floppy disk (say it is a game for some microcomputer), the image would also be original/clean. If the floppy disk had been played/loaded (BUT NOT WRITE PROTECTED), then the disk might have an additional file saved back to it such as a saved game, or saved high score table. If you then re-dumped it, the image would no longer be original/clean, and a [m] flag would be appropriate.

The variants are:

**[m]** - Modified (general hack)

**[m Modification]** - Modification added

**Note:** Renamers must try to use modified descriptions already used before, e.g. if "high score" is already in use then there is no need to use "high score" in one set and "hiscore" in another (if they represent the same thing).

### Pirated - [p]

The software is not legally licensed or violates some international IP.

The variants are:

**[p]** - Pirate version

**[p Pirate]** - Pirate version by Pirate (group or person)

### Trained - [t]

The original software has been deliberately hacked/altered to add cheats and/or a cheat menu.

The variants are:

**[t]** - Trained

**[t Trainer]** - Trained by trainer (group or person)

**[t +x]** - x denotes number of trainers added

**[t +x Trainer]** - Trained and x number of trainers added by trainer (group or person)

### Translated - [tr]

The original software has been deliberately hacked/altered to translate into a different language than originally published/released.

If it is a **partial translation**, not fully complete, "**-partial**" should be appended to the language code. Also note that the **language codes** used in this flag are the same used in **language flag**.

Some of the variants are:

**[tr]** - Translation

**[tr language]** - Translated to Language

**[tr language-partial]** - Translated to Language (partial translation)

**[tr language Translator]** - Translated to Language by Translator (group or person)

**[tr language1-language2]** - Translated to both Language1 and Language2.

**[tr language1-partial-language2-partial Translator]** - Partially translated to both Language1 and language2 by Translator (group or person).

**Note:** Translator name is not allowed if language isn't identified too ([tr Translator] **not** allowed).

###  

### Over Dump - [o]

The image is damaged (duplicated data or too much data).

The variants are:

**[o]** - Over Dump (too much data dumped)

###  

### Under Dump - [u]

The image is damaged (missing data).

The variants are:

**[u]** - Under Dump (not enough data dumped)

### Virus - [v]

The image is damaged from the infection of a virus.

The variants are:

**[v]** - Virus (infected)

**[v Virus]** - Infected with virus

**[v Virus Version]** - Infected with virus of version

**Note:** Renamers should try to always using the same virus names, for example don't use "VirusXPTO1", "virusxpto1" and "Virus XPTO1" with different images for the same virus.

### Bad Dump - [b]

The image is damaged. This is a general 'damaged/bad' flag, to be used when the type of damage does not fit into any of the other 'damaged' categories. It is likely this image will not work properly, or not at all.

The variants are:

**[b]** - Bad dump (incorrect data dumped)

**[b Descriptor]** - Bad dump (including reason)

 

Some examples of descriptors:

**corrupt file** = Image contains a corrupt file

**read-write** = Image has a read/write error

**Note:** Renamers must try to use bad dump descriptions already used before, e.g. if "read-write" is already in use then there is no need to use "read-write" in one set and "read-write errors"" in another (if they represent the same thing).

### Alternate - [a]

An alternate ORIGINAL version of another ORIGINAL image, e.g. if a game was released, then re-released later with a small change (and the revision/version number is not known).

 

The variants are:

**[a]** - Alternate version

**[a Descriptor]** - Alternate (including reason)

 

Some examples of descriptors:

**no title screen** = Game has no title screen, the non [a] image does

**readme** = Only a readme file is different from a non [a] image

### Known Verified Dump - [!]

Image has had multiply person/multi dump verification to confirm it is a 100% repeatable and correct dump. This is currently only used in the TOSEC-ISO branch.

The variants are:

**[!]** - Verified good dump

### Dump Flags Samples

• Legend of TOSEC, The (1986)(Devstudio)(US)**[a]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[b]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[f]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[f NTSC]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[u]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[tr fr]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[tr de-partial someguy]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[h Fairlight]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[m save game]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[o]**

 

In case where multiple images exist that need the same dump info flags, the flag is numbered as follows:

• Legend of TOSEC, The (1986)(Devstudio)(US)**[a]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[a2]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[a3]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[a4]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[b]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[b2]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[b3]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr2]**

 

There is **no [n1]**, so for example you will need to have a **[b]** for a **[b2]** to exist. When dealing with flags that can contain more information, be sure to **not add numbers if it is not necessary** to remain unique. If, for example, the cracking group can be used to distinguish between different files, use that instead:

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr PDX]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr TRSi]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr2]**

 

**Instead of:**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr2 PDX]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr3 TRSi]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr4]**

 

A dump info flag can only be used once (except in the case of compilations). So, if something was hacked by PDX, then hacked again by TRSi, **do not** use:

• Legend of TOSEC, The (1986)(Devstudio)(US)**[h PDX][h TRSi]**

 

Instead, use one of the following, depending on how the program was altered.

• Legend of TOSEC, The (1986)(Devstudio)(US)**[cr PDX][h TRSi]**

• Legend of TOSEC, The (1986)(Devstudio)(US)**[h PDX - TRSi]**

 

**Note:** When **various** groups or person names are used in the same flag, they must be separated using space-hyphen-space, e.g. " **-** "**.**

 

## More Info

This field contains any miscellaneous information about the image that is not covered by any of the prior flag fields.

**Note:** These flags use square brackets [ ], and should always be the last flag.

**Note:** It is possible for a file to have more than one [more info] flags, although commas can be used to separate items also. When adding an alternate name, prefix the name with 'aka'.

Examples include, but are not limited to:

• [aka House of TOSEC]

• [Req TRS-DOS]

• [source code]

 

Full filenames could look like:

• Legend of TOSEC, The (1986)(Devstudio)**[data disk]**

• Legend of TOSEC, The (1986)(Devstudio)**[Req Super-BASIC][docs]**

 

**
**

# Multi Image Sets

The multi-image sets generally represent compilations and other kind of sets that have more than one software image, as the single sets format doesn't work when you want to describe and catalog a set with two different programs.

The idea is to use the standard TNC single image sets format for each of the images and group them together with " & ".

The format for multi-program images is as follows:

• Title1 (year)(publisher)[flags] **&** Title2 (year)(publisher)[flags] **&** Title3 (year)(publisher)[flags]

 

Representing a set made of 3 images (Title1, Title2 and Title3) and all the corresponding flags grouped together using " & ".

 

## Some Multi Image Sets Samples

• Amidar (19xx)(Devstudio) **&** Amigos (1987)(Mr. Tosec)

• Amidar (19xx)(Devstudio) **&** Amigos (1987)(Mr. Tosec)[a][more info]

• Amidar (19xx)(Devstudio)(preview) **&** Amigos (1987)(Mr. Tosec)(PD)[cr]

• Amidar (19xx)(Devstudio)[h] **&** Amigos (demo) (1987)(Mr. Tosec)[tr fr]

## Global Flags

Using the above scheme for multi-image sets may turn into a problem, large compilations or images with lots of flags or big names will end up having an enormous length, possibly hitting the maximum length for a filename (255 chars). A partial solution to these problems are the global flags.

In cases where there are identical multi-program images, use a hyphen as a separator after the last title entry in the image, followed by any dump info flags specific to the entire image.

• Amidar (19xx)(Devstudio)**[a]** **&** Amigos (1987)(Mr. Tosec)**[a]**

Could be expressed like:

• Amidar (19xx)(Devstudio) **&** Amigos (1987)(Mr. Tosec)**-[a]**

 

If needed renamers can compress even more flags relative to all images and not only the dump info flags, please note that you should try to have at least **year** and **publisher** flags represented **separately** for each image.

• Amidar (19xx)(Devstudio)**(PD)(Disk 1 of 2)[a] &** Amigos (1987)(Mr. Tosec)**(PD)(Disk 1 of 2)[a]**

Could be expressed like:

• Amidar (19xx)(Devstudio) **&** Amigos (1987)(Mr. Tosec)**-(PD)(Disk 1 of 2)[a]**

 

If for any reason using this you can't came up with a small enough length and are forced to compress it a bit more, you can also put the year and publisher after the hyphen if they apply for both, please note that this is should only be used as a last resort since it will generate some weird file names that are difficult to parse, the hyphen "-" will appear between **title** (+ version) and **year** flag, using " **&** " to separate only titles, versions and possibly demo flags.

• Paradroid 90 **(19xx)(-)[h]** **&** F.O.F.T. **(19xx)(-)[h]** **&** Black Lamp **(19xx)(-)[h]** **&** QED v2.05 **(19xx)(-)[h]**

Could be expressed like:

• Paradroid 90 **&** F.O.F.T. **&** Black Lamp **&** QED v2.05**-(19xx)(-)[h]**

 

Please note that this is **not recommended and strongly discouraged**. It is only used once or twice till now in all **TOSEC** sets, the use of this scheme makes it impossible to easily parse each image title name since **&** usage is generally allowed in other flags (like title), there is no way to know if for example "Tom **&** Jerry **&** Other" are three separate titles (Tom/Jerry/Other) or only two (Tom **&** Jerry/Other, etc.).