##########################################################################################
# aliases: the sets of valid alias and ambiguous keys for a defined target.
##########################################################################################

import re

import anyascii

import roman
from mpc_packing import mpc_pack
from STANDARD_BODIES import STANDARD_BODIES

class TargetType:
    ASTEROID = 'A'
    ASTROPHYSICAL = 'a'
    CALIBRATION_FIELD = 'F'
    CALIBRATOR = 'c'
    CENTAUR = 'H'               # for "Horse"
    COMET = 'C'
    DUST = 'd'
    DWARF_PLANET = 'D'
    EQUIPMENT = 'E'
    LABORATORY_ANALOG = 'L'
    MAGNETIC_FIELD = 'm'
    PLANET = 'P'
    PLANETARY_NEBULA = 'N'
    PLANETARY_SYSTEM = 'p'
    PLASMA_CLOUD = 't'          # for "Torus"
    PLASMA_STREAM = 'W'         # for "Wind"
    RING = 'R'
    SATELLITE = 'S'
    STAR = '*'
    TRANS_NEPTUNIAN_OBJECT = 'T'

    MINOR_PLANET = 'M'

    NAME = {
        'A': 'asteroid',
        'a': 'astrophysical',
        'F': 'calibration_field',
        'c': 'calibrator',
        'H': 'centaur',
        'C': 'comet',
        'd': 'dust',
        'D': 'dwarf_planet',
        'E': 'equipment',
        'L': 'laboratory_analog',
        'm': 'magnetic_field',
        'P': 'planet',
        'N': 'planetary_nebula',
        'p': 'planetary_system',
        't': 'plasma_cloud',
        'W': 'plasma_stream',
        'R': 'ring',
        'S': 'satellite',
        '*': 'star',
        'T': 'trans-neptunian_object',
    }

_KEYWORDS = {
    'ACTIVE'        : TargetType.COMET + TargetType.MINOR_PLANET,
    'ASTEROID'      : TargetType.MINOR_PLANET,
    'BELT'          : TargetType.MINOR_PLANET,
    'BINARY'        : '',
    'CENTAUR'       : TargetType.COMET + TargetType.MINOR_PLANET,
    'CLASSICAL'     : TargetType.MINOR_PLANET,
    'COMET'         : TargetType.COMET,
    'D-TYPE'        : TargetType.MINOR_PLANET,
    'DISK'          : TargetType.MINOR_PLANET,
    'DUST'          : TargetType.DUST,
    'DWARF'         : TargetType.MINOR_PLANET,
    'EXTENDED'      : TargetType.MINOR_PLANET,
    'FRAGMENT'      : TargetType.COMET,
    'INTERSTELLAR'  : TargetType.COMET,
    'KBO'           : TargetType.MINOR_PLANET,
    'MAIN'          : TargetType.MINOR_PLANET,
    'MBC'           : TargetType.MINOR_PLANET + TargetType.COMET,
    'MOON'          : TargetType.SATELLITE,
    'NEO'           : TargetType.MINOR_PLANET,
    'NUCLEUS'       : TargetType.COMET,
    'OBJECT'        : '',
    'PLANET'        : TargetType.PLANET + TargetType.MINOR_PLANET,
    'SATELLITE'     : TargetType.SATELLITE,
    'SCATEXTD'      : TargetType.MINOR_PLANET,
    'SCATNEAR'      : TargetType.MINOR_PLANET,
    'SCATTERED'     : TargetType.MINOR_PLANET,
    'TNO'           : TargetType.MINOR_PLANET,
    'TROJAN'        : TargetType.MINOR_PLANET,
    'TRANSNEPTUNIAN': TargetType.MINOR_PLANET,
}

# Convert standard body list to a dictionary
_STANDARD_BODIES = {info[0].upper():info for info in STANDARD_BODIES}

_TWO_NAME_COMETS = ['La Sagra', 'Van Ness']
du Toit
du Toit–Neujmin–Delporte
du Toit–Hartley
de Vico
de Vico–Swift–NEAT
de Kock-Paraskevopoulos)

73P/Schwassmann–Wachmann 3-AX


_name = r"(?:(?:[^\W\d_]|['`])(?:[^\W\d_]|[-'`])*(?:[^\W\d_]|['`]))"
_name2 = rf'{_name}(?: {_name}|)'
_name3 = rf'{_name}(?: {_name} {_name}| {_name}|)'
_int = r'[1-9]\d*'
_roman = roman.REGEX

_NAME = rf'(?P<name>{_name})'
_NUM = rf'(?P<num>{_int})'
_ROMAN = rf'(?P<roman>{roman.REGEX})'
_PNAME = rf'(?P<pname>{_name})'
_PLETT = rf'(?P<pname>[MJSUNP])'
_PNAMELETT = rf'(?P<pname>[MJSUNP]|{_name})'
_PNUM = rf'(?P<pnum>{_int})'
_SNUM = rf'(?P<snum>{_int})'
_SYEAR = rf'(?P<year>19[7-9]\d|20[0-3]\d)'

_MNAME = rf'(?P<name>{_name2})'
_MNUM = rf'(?P<mnum>{_int})'
_MDESIG = (r'(?P<mdesig>'
           r'(1[89]\d\d|20[0-3]\d|\d\d) ?[A-HJ-Y][A-HJ-Z]([1-9]\d*|)|'
           r'[1-9]\d\d\d ?(P-L|T-[123]))')

_CNAME = r'(?P<name>{_name3})'
_CPREF = r'(?P<cpref>[PCXDAI]|[1-9]\d*[PI])'
_CNP = r'(?P<cpref>[1-9]\d*[PI])'
_CYEAR = r'(?P<cyear>1[6-9]\d\d|20[0-3]\d)'
_CSUFF = r'(?P<csuff>[A-H-J-Y][A-HJ-Z]?[1-9]\d*)'
_CDESIG = rf'(?P<cdesig>{_CYEAR} {_CSUFF})'
_CFRAG = r'(?P<cfrag>[A-Z]\d?)'     # one letter + max one digit
_CNUM = rf'(?P<cnum>[1-9]\d?)'      # max two digits
_NOCNUM = r'(?P<cnum>)'             # comet with name but no number
_CLETT = r'(?P<clett>[a-z]1?)'      # for old-style designations, e.g., 1989d or 1989d1

# These act as "votes"
_S = r'(?P<S>)'
_M = r'(?P<M>)'
_C = r'(?P<C>)'

_PATTERNS = [

    # Satellite patterns
    rf'\(?{_PNUM}\)? {_PNAME} {_ROMAN} \(?{_NAME}\)?{_S}',      # (243) Ida I (Dactyl)
    rf'\(?{_PNUM}\)? {_PNAME} {_ROMAN}{_S}',                    # (243) Ida I
    rf'{_PNAMELETT} {_ROMAN} \(?{_NAME}\)?{_S}',                # Ida I (Dactyl)
    rf'{_PNAMELETT} {_ROMAN}{_S}',                              # Ida I, J V
    rf'{_PLETT}[ -]?{_SNUM} \(?{_NAME}\)?{_S}',                 # J5 Amalthea
    rf'{_PLETT}[ -]?{_SNUM}{_S}',                               # J5
    rf'S/?{_SYEAR} ?{_PLETT} ?{_NUM} \(?{_NAME}\)?{_S}',        # S/2003 J 17 (Herse)
    rf'S/?{_SYEAR} ?{_PLETT} ?{_NUM}{_S}',                      # S/2003 J 17
    rf'S/?{_SYEAR} \({_PNUM}\) {_NUM}{_S}',                     # S/2018 (3548) 1

    # Minor planet patterns
    rf'\(?{_MNUM}\)? {_MDESIG} \({_MNAME}\){_M}',               # (1) 1801 AA (Ceres)
    rf'\(?{_MNUM}\)? {_MDESIG}{_M}',                            # (1) 1801 AA
    rf'{_MDESIG} \(?{_MNAME}\)?{_M}',                           # 1801 AA (Ceres)
    rf'{_MDESIG}{_M}',                                          # 1801 AA
    rf'\(?{_MNUM}\)? {_MNAME}{_M}',                             # (1) Ceres, 1 Ceres
    rf'{_MNUM} \({_MNAME}\){_M}',                               # 1 (Ceres)
    rf'\({_MNUM}\){_M}',                                        # (1)

    # Comet patterns with fragments
    rf'{_CPREF}/{_CDESIG}-{_CFRAG} \({_CNAME} {_CNUM}([- ](?P=cfrag)|)\){_C}',
                                                                # D/1993 F2-P1 (name 9-P1)
    rf'{_CPREF}/{_CDESIG} \({_CNAME} {_CNUM}[- ]{_CFRAG}\){_C}',# D/1993 F2 (name 9-P1)
    rf'{_CPREF}/{_CDESIG} \({_CNAME} {_CFRAG}\){_NOCNUM}{_C}',  # D/1993 F2 (name P1)
    rf'{_CPREF}/{_CDESIG}-{_CFRAG}{_NOCNUM}{_C}',               # D/1993 F2-P1
    rf'{_CNP}[/- ]{_CNAME} {_CNUM}-{_CFRAG}{_C}',               # 10P/Tempel 2-A
    rf'{_CNP}[/- ]{_CNAME} {_CFRAG}{_NOCNUM}{_C}',              # 1P/Halley A
    rf'{_CNP}-{_CFRAG}{_C}',                                    # 10P-A
    rf'{_NAME} {_CNUM}-{_CFRAG}{_C}',                           # Tempel 2-A
    rf'{_NAME} {_CFRAG}{_C}',                                   # Halley A

    # Comet patterns without fragments
    rf'{_CPREF}/{_CDESIG} \({_CNAME}( {_CNUM}|){_C}',           # D/1993 F2 (name 9)
    rf'{_CPREF}/{_CDESIG}{_C}',                                 # D/1993 F2
    rf'{_CNP}/{_CNAME} {_CNUM}{_C}',                            # 10P/Tempel 2
    rf'{_CNP}/{_CNAME}{_NOCNUM}{_C}',                           # 1P/Halley
    rf'{_CNP}{_C}',                                             # 10P
    rf'{_CNAME} {_CNUM}{_C}',                                   # Tempel 2
    rf'C{_CDESIG}{_C}',                                         # C1988 B1
    rf'{_CDESIG}{_C}',                                          # 1988 B1
    rf'{_CYEAR} ?{_ROMAN}{_C}',                                 # 1984 XI
    rf'{_CYEAR}{_CLETT}{_C}',                                   # 1989d

    # Generic
    rf'\({_NAME}\)',                                            # (Ceres)
    rf'{_NAME}',                                                # Ceres
]





for _k, _pattern in enumerate(_PATTERNS):
    _regex = _pattern + r'(?!\S)'  # can't be followed by a character that isn't white
    _PATTERNS[k] = re.compile(_regex)


def recognize(string: str, *,
              logger: Logger | None = None
) -> tuple[str, dict[str, str], list[tuple[str, str]]]:
    """Recognize a given string as a planetary target.

    Parameters:
        string: String to interpret.
        logger: Optional Logger for messages.

    Returns:
        Three quantities: (`votes`, `matchdict`, `rejects`)

        * `votes`: Concatenated string of target types recognized: "P" for planet; "S" for
          satellite; "D" for dwarf planet; "T" for trans-neptunian object'; "A" for
          asteroid; "C" for comet; "*" for star.
        * `matchdict`: Dictionary of target information.
        * `rejects`: List of contradicted keyword/value pairs.
    """

    string = string.replace(',', ' ').replace('(', ' (').replace(')', ') ').strip()
    words = string.split()

    matches = []
    votes = []
    rejects = []
    while words:

        # Check for a leading keyword
        uword = words[0].upper()
        if uword in _KEYWORDS:
            votes.append(_KEYWORDS[uword])
            words = words[1:]
            continue

        # Attempt to match a known pattern
        string = ' '.join(words)
        ustring = string.upper()
        dstring = string.replace('-', ' ')
        strings = [string, ustring, dstring, dstring.upper()]
        for k, string in enumerate(strings):
            if string in strings[:k]:
                continue
            for pattern in _PATTERNS:
                match = pattern.match(string)
                if match:
                    matches.append(match.groupdict())
                    string = string[match.end():].lstrip()
                    words = string.split()
                    break
            if match:
                break

        # Check for a standard body
        if not match:
            if uword in _STANDARD_BODIES:
                name, num, _, target_type, pname, aliases = _STANDARD_BODIES[uword]
                votes.append(target_type)
                matches.append({'name': name, 'num': num, 'pname': pname})
                words = words[1:]

    # Merge the votes and dictionaries; identify rejects
    matchdict = {}
    rejects = []
    for match in matches:
        for key, value in match.items():
            if len(key) == 1:
                votes.append(key)

            if key in matchdict:
                if value != matchdict[key]:
                    logger and logger.warn(f'target field "{value}" ignored')
                    rejects.append((key, value))
            else:
                matchdict[key] = value

    return (''.join(votes), matchdict, rejects)




    votes = []
    matches = []
    for key in keys:
        while True:
            substrings = _substrings(key)
            for string in substrings:
                ustring = string.upper()
                if ustring in _KEYWORDS:
                    votes.append(_KEYWORDS[ustring])
                    continue

                for pattern, vote, replacement in _TRANSLATOR:
                    match_found = False
                    for test in (string, ustring):
                        match = pattern.match(test)
                        if match:
                            match_found = True
                            votes.append(vote)
                            if isinstance(replacement, str):
                                answer = match.expand(replacement)
                            else:
                                answer = replacement(test)
                            matches.append(answer)
                            break

                    if match_found:
                        break

            votes = ''.join(votes)
            return votes, matches



# key, list of extra names
ABBREVIATIONS = {'D/1993 F2': ['SL9', 'SL-9'],
                 '67P': ['CG', 'Chury'],
                 '29P': ['SW1', 'SW-1'],
                 '31P': ['SW2', 'SW-2'],
                 '73P': ['SW3', 'SW-3']}





for test, cat, answer in TESTS:
    for regex, category, replacement in CATEGORIZER:
        match = regex.match(test)
        if match:
            break
    assert match, f'No match for "{test}"'
    expanded = match.expand(replacement)
    assert answer == expanded, f'Replacement failed, "{test}" -> "{expanded}"'
    assert cat == category, f'Category mismatch, "{test}" -> "{category}"'

# Regular expressions
NAME         = r"([A-Z`'][A-Z `'\.\|!-]*[A-Z])"
NNN          = r'([1-9]\d*)'
NAMENUM      = NAME[:-1] + '|' + NNN[1:]

YY19_XXNNN   = r'([7-9]\d)[ -]?([A-Z]{2}\d*)[A-D]?'
YY20_XXNNN   = r'([0-2]\d)[ -]?([A-Z]{2}\d*)[A-D]?'
YY_YY_XXNNN  = r'(19|20)(\d\d)[ -]?([A-Z]{2}\d*)[A-D]?'
YYYY         = r'(1\d{3})'

NAME_N       = NAME + r'[ _-]?(\d)'
NUMP         = r'(\d+[PCXDAI])'
YY_YY_XX     = r'(19|20)(\d\d)[ _-]?([A-Z]\w\d*)'
YY_YY_XX_F   = YY_YY_XX + r'(|-[A-G])'
P_YY_YY_XX   = r'([PCXDAI])[ /_-]?' + YY_YY_XX
P_YY_YY_XX_F = P_YY_YY_XX + r'(|-[A-G])'

SEP   = r'[ _-]?'
SEP1  = r'[ _-]?\(?'
SSEP1 = r'[ /_-]?\(?'
SEP2  = r'\)?'

ROMAN = r'((?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))'   # Roman numeral < 100
YYYY_ROMAN = r'(1\d{3})[ -]?' + ROMAN
YY19_ROMAN = r'([7-9]\d)[ -]?' + ROMAN

YYYYx = r'(1\d{3}[A-Za-z]1?)'
YY19x = r'([7-9]\d[A-Za-z]1?)'



# https://minorplanetcenter.net/mpcops/documentation/provisional-designation-definition
# Note that some very old formats are not supported:
# Year + letter: 1913 a
# Year + Greek letter: 1914 gamma
# Year + SIGMA + letter: 1915 SIGMA r, 1916 SIGMA ci
# SIGMA + number: SIGMA 27

# _MPNAME: Matches a name including diacritics, apostrophes and internal dashes; no
# digits or spaces. Note that "[^\W\d_]" only matches letters but they can have
# diacritics. Dashes cannot appear at the beginning or end.
_MPNAME = r"(?:[^\W\d_]|['`])(?:[^\W\d_]|[-'`])*(?:[^\W\d_]|['`])"

# _MPYEAR: Matches any year 1800-2099, but uses "A" as first character for 1800-1925.
_MPYEAR = r'(?:A8\d\d|A9(?:[01]\d|2[0-4])|19(?:2[5-9]|[3-9]\d)|20\d\d)'

# "(11372) 1998 QP41" -> ("11372", "1998 QP41", "QP41")
_MP_NUMBERED_PROVISIONAL = re.compile(rf'\((\d+)\) ({_MPYEAR} ([A-HJ-Y][A-HJ-Z]\d*))$')

# "1998 QP41" -> ("", "1998 QP41", "QP41")
_MP_UNNUMBERED_PROVISIONAL = re.compile(rf'()({_MPYEAR} ([A-HJ-Y][A-HJ-Z]\d*))$')

# "(15649) 6317 P-L" -> ("15649", "2040 P-L", "")
_MP_NUMBERED_SURVEY = re.compile(r'\((\d+)\) (\d\d\d\d (?:P-L|T-[123]))()$')

# "2040 P-L" -> ("", "2040 P-L", "")
_MP_UNNUMBERED_SURVEY = re.compile(r'()(\d\d\d\d (?:P-L|T-[123]))()$')

# "(10664) Phemios" -> ("10664", "Phemios", "")
# "10664 Phemios" -> ("10664", "Phemios", "")
# Note that _MP_UNNUMBERED_SURVEY has to be checked _before_ _MP_NUMBERED_NAMED!
_MP_NUMBERED_NAMED = re.compile(rf'\(?(\d+)\)? ({_MPNAME})()$')

# _CPROV: Captures any provisional designation of a four-digit year through 2099 plus one
# or two letters and one or more digits
_CPROV = rf'(?P<prov>(?:1\d\d\d|20\d\d) [A-HJ-Y][A-HJ-Z]?\d*)'

# _CPREF: Captures optional digits plus one of "PCXDAI".
_CPREF = r'(?P<pref>[PCXDAI]|\d+[PI])'

# _CFRAG: Captures a fragment ID
_CFRAG = r'[- ]?(?P<frag>[A-Z]\d*|)'

# _CNAME: Captures names including diacritics, apostrophes, internal dashes and spaces; no
# spaces; digits. Dashes and spaces cannot appear at the beginning or end. At least two
# characters.
_CNAME = r"(?P<name>(?:[^\W\d_]|')(?:[^\W\d_]|[-' ])*(?:[^\W\d_]|'))"

# _CFRAG: Captures an optional comet number following the discoverer name
_CNUM = r' ?(?P<num>\d*)'

# (prefix, designation, fragment, name, number)
# "1P/1682 Q1" -> ("1P", "1682 Q1", "", "", "")
# "227P/2004 EW38" -> ("227P", "2004 EW38", "", "", "")
# "C/1995 O1" -> ("C", "1995 O1", "", "", "")
# "D/1993 F2-P1" -> ("D", "1995 O1", "P1", "", "")
_COMET_PROVISIONAL = re.compile(rf'{_CPREF}/{_CPROV}[- ]?{_CFRAG}(?P<name>)(?P<num>)$')

# (prefix, provisional, fragment, name, number)
# "1P/1682 Q1 (Halley)" -> ("1P", "1682 Q1", "", "Halley", "")
# "227P/2004 EW38 (Catalina-LINEAR)" -> ("227P", "2004 EW38", "", "Catalina-LINEAR", "")
# "C/2007 E2 (Lovejoy)" -> ("C", "2007 E2", "", "Lovejoy", "")
# "1I/2017 U1 (ʻOumuamua)" -> ("1I", "2017 U1", "", "ʻOumuamua", "")
# "1I/2017 U1 ('Oumuamua)" -> ("1I", "2017 U1", "", "'Oumuamua", "")
# "D/1993 F2 (Shoemaker-Levy 9)" -> ("D", "1995 O1", "", "Shoemaker-Levy", "9")
# "D/1993 F2-A (Shoemaker-Levy 9-A)" -> ("D", "1995 O1", "A", "Shoemaker-Levy", "9")
# "D/1993 F2-P1 (Shoemaker-Levy 9-P1)" -> ("D", "1995 O1", "P1", "Shoemaker-Levy", "9")
# "C/2025 N1 (ATLAS)" -> ("C", "2025 N1", "", "ATLAS", "")
_COMET_FULL = re.compile(rf'{_CPREF}/{_CPROV}{_CFRAG} ?\(?{_CNAME}{_CNUM}[- ]?\3\)?$')

# (prefix, name, number, fragment, provisional)
# Example: "29P/Schwassmann-Wachmann 1" -> ("29P", "Schwassmann-Wachmann", "1", "", "")
# Example: "3I/ATLAS" -> ("3I", "ATLAS", "", "", "")
_COMET_NAMED = re.compile(rf'(?P<pref>\d+[PI])/{_CNAME}{_CNUM}{_CFRAG}(?P<prov>)$')

# "(243) Ida I (Dactyl)" -> ("243", "Ida", "I", Dactyl)
# "(243) Ida I Dactyl" -> ("243", "Ida", "I", Dactyl)
# "(243) Ida I" -> ("243", "Ida", "I", "")
# "Jupiter XXVII (Praxidike)" -> ("", "Jupiter", "XXVII", "Praxidike")
_SAT_FULL = re.compile(rf'\(?(\d+)\)? ?({_MPNAME}) {roman.REGEX} ?\(?({_MPNAME}|)\)?$')

# "S/1981 S 13" -> ("1981", "S", "13")
# "S/2018 (3548) 1" -> ("2018", "(3548)", "1")
_SAT_PROVISIONAL = re.compile(r'S/((?:19|20)\d\d) ?([VMJSUNP]|\(\d+\)) (\d+)$')


def target_aliases(categories, ):

    lid_tail = lid.rsplit(':')[-1]
    category = lid_tail.split('.')[0]

    keys = {title, lid, lid_tail} | alts

    new_keys = keys.copy()
    alt_keys = set()
    if category in {'asteroid', 'centaur', 'comet', 'dwarf_planet',
                    'trans-neptunian_object'}:
        for key in keys:
            for regex in (_MP_NUMBERED_PROVISIONAL, _MP_UNNUMBERED_PROVISIONAL,
                          _MP_NUMBERED_SURVEY, _MP_UNNUMBERED_SURVEY, _MP_NUMBERED_NAMED):
                match = regex.match(key)
                if match:
                    (number, name, partial) = match.groups()
                    if number:
                        new_keys.add(int(number))
                        if name:
                            new_keys.add(f'({number}) {name}')
                            if not name[0].isdigit():
                                new_keys.add(f'{number} {name}')

                    if name in DUPLICATED_NAMES:
                        alt_keys.add(name)
                    else:
                        new_keys.add(name)

                    if partial:
                        alt_keys.add(partial)

    if category in {'centaur', 'comet'}:
        for key in keys:
            for regex in (_COMET_PROVISIONAL, _COMET_FULL, _COMET_NAMED):
                match = regex.match(key)
                if match:
                    (pref, prov, name, num, frag) = match.groups('pref', 'prov', 'name',
                                                                 'num', 'frag')
                    if name:
                        if num in {'', '1'}:
                            names = [name, f'{name} 1']
                        else:
                            names = [f'{name} {num}']
                    else:
                        names = []

                    if frag:
                        frag = '-' + frag

                    new_keys |= {f'{pref}/{name}{frag}' for name in names}
                    if len(pref) > 1:
                        new_keys.add(f'{pref}{frag}')
                    if prov:
                        new_keys.add(f'{pref}/{prov}{frag}')
                        for name in names:
                            new_keys |= {f'{pref}/{prov}{frag} ({name}{frag})',
                                         f'{pref}/{prov}{frag} ({name})',
                                         f'{pref}/{prov} ({name}{frag})',
                                         f'{pref}/{name}{frag} ({prov}{frag})',
                                         f'{pref}/{name}{frag} ({prov})',
                                         f'{pref}/{name} ({prov}{frag})'}
                    if name:
                        new_keys |= {names[-1], 'Comet ' + names[-1]}  # name plus number
                        alt_keys |= {name, 'Comet ' + name}

    if category == 'satellite':
        for key in keys:
            match = _SAT_FULL.match(key)
            if match:
                (p_number, p_name, numeral, name) = match.groups()
                new_keys |= {f'{p_name} {numeral}'}
                if name:
                    new_keys |= {f'{p_name} {numeral} ({name})', name}
                if p_number:
                    new_keys |= {f'({p_number}) {p_name} {numeral}',
                                 f'{p_number} {p_name} {numeral}',
                                 f'({p_number}) {numeral}'}
                    if name:
                        new_keys |= {f'({p_number}) {p_name} {roman} ({name})',
                                     f'{p_number} {p_name} {roman} ({name})',
                                     f'({p_number}) {numeral} ({name})'}
                if p_name in {'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune'}:
                    new_keys |= {f'{p_name[0]} {numeral}',
                                 f'{p_name[0]}{numeral}',
                                 f'{p_name[0]}{roman.to_int(numeral)}'}

            match = _SAT_PROVISIONAL.match(key)
            if match:
                (year, primary, roman) = match.groups()
                new_keys |= {f'S/{year} {primary} {numeral}'}
                alt_keys |= {f'S{year} {primary} {numeral}',
                             f'{year} {primary} {numeral}'}
                if len(primmary) == 1:
                    indx = roman.to_int(numeral)
                    alt_keys |= {f'S/{year} {primary}{numeral}',
                                 f'S/{year} {primary} {indx}',
                                 f'S/{year} {primary}{indx}'}

    for key in keys | alt_keys:
        alpha = anyascii.anyascii(key).replace('`', "'")
        new_alts = {key, unidecode(key).replace('`', "'")}
        new_alts |= {k.lower() for k in new_alts}
        new_alts |= {k.replace('(', '').replace(')', '') for k in new_alts}

    alt_keys |= new_alts
    alt_keys -= keys

    return (keys, alt_keys)

##########################################################################################
