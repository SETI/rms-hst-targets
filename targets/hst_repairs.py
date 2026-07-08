##########################################################################################
# hst_repairs.py
##########################################################################################

import re
from collections import deque

from targets.mpc_tools import mpc_unpack, MPC_PACKED_PATTERN
from targets.roman import ROMAN_PATTERN_99 as _ROMAN_99

from targets._TARGNAME_PREFIX_SUFFIX_PATTERNS import (_TARGNAME_PREFIX_PATTERNS,
                                                      _TARGNAME_SUFFIX_PATTERNS)
from targets._TARGET_STRING_REPAIRS import _TARGET_STRING_REPAIRS
from targets._UNDIAGNOSTIC_TARGET_WORDS import _UNDIAGNOSTIC_TARGET_WORDS

_TARGET_REPAIRS = []  # an ordered list of tuples (re.Pattern, substitution string)

for _pattern in _TARGNAME_SUFFIX_PATTERNS:
    # These suffixes can also have a version suffix involving "V" plus digits and a letter
    _regex = re.compile(rf'(.*)-{_pattern}\d*(?:-\d+|-\d?\d?[A-Z]|)$', re.I)
    _TARGET_REPAIRS.append((_regex, r'\1'))

for _pattern in _TARGNAME_PREFIX_PATTERNS:
    _regex = re.compile(rf'{_pattern}-(.*)$', re.I)
    _TARGET_REPAIRS.append((_regex, r'\1'))

for _pattern, _template in _TARGET_STRING_REPAIRS:
    _regex = re.compile(_pattern + '$', re.I)
    _TARGET_REPAIRS.append((_regex, _template))

# These are more complicated patterns to convert a non-standard identification into a
# standard one.

_NUM = r'([1-9]\d*)'
_MPNAME = r"([A-Za-z'`]{2,}(?:[- ]?[A-Z'`]{2,})*)"  # allows for "Purple Mountain"
_MYEAR = r'(1[89]\d\d|20[0-3]\d)'
_MSUFF = r'([A-HJ-Y][A-HJ-Z]\d*)'

# A comet name can include spaces and dashes but always at least two other characters
# surrounding them. Apostrophes count as letters.
_CNAME = r"([A-Za-z'`]{2,}(?:[- ]?[A-Z'`]{2,})*)"
_CYEAR = r'(1[6-9]\d\d|20[0-3]\d)'
_CSUFF = r'([A-HJ-Y][1-9]\d*)'
_CSUFF2 = r'([A-HJ-Y][A-HJ-Z]?[1-9]\d*)'

_TARGET_TRANSFORM_PATTERNS = [
    # Rarely, a comet has a second letter in the suffix. We only tolerate this if "COMET"
    # (or "C") is explicit in the target string.
    (rf'COMET[- ]?C?([7-9]\d){_CSUFF2}-{_CNAME}',           r'C/19\1 \2|[C]$\3'),
    (rf'COMET[- ]?C?([0-3]\d){_CSUFF2}-{_CNAME}',           r'C/20\1 \2|[C]$\3'),
    (rf'COMET[- ]?C?{_CYEAR}[- ]?{_CSUFF2}',                r'C/\1 \2|[C]'),
    (rf'COMET[- ]?C?([7-9]\d)[- ]?{_CSUFF2}',               r'C/19\1 \2|[C]'),
    (rf'COMET[- ]?C?([0-3]\d)[- ]?{_CSUFF2}',               r'C/20\1 \2|[C]'),
    (rf'COMET[- ]{_CNAME}[- ]C?/?{_CYEAR} ?{_CSUFF2}',      r'C/\2 \3|[C]$\1'),
    (rf'COMET[- ]{_CNAME}[- ]C?([7-9]\d)-?{_CSUFF2}',       r'C/19\2 \3|[C]$\1'),
    (rf'COMET[- ]{_CNAME}[- ]C?([0-3]\d)-?{_CSUFF2}',       r'C/20\2 \3|[C]$\1'),
    (rf'COMET[- ]{_CNAME}[- ]?(\d)',                        r'\1 \2|[C]'),
    (rf'COMET[- ]([A-Z]{3,}) ([A-Z]{3,}) C?/?{_CYEAR} ?{_CSUFF2}',
                                                            r'C/\3 \4|[C]|$\1-\2'),
    (rf'COMET[- ]{_CNAME}[ -](\d\d[A-Z])[ -](\d\d)({_ROMAN_99})',
                                                            r'\1|19\2|19\3 \4|[C]'),
    (rf'C{_CYEAR}[- ]?{_CSUFF2}-{_CNAME}',                  r'C/\1 \2|[C]$\3'),
    (rf'C{_CYEAR}[- ]?{_CSUFF2}',                           r'C/\1 \2|[C]'),

    # Other comet patterns only allow one letter in the designation code
    (rf'([1-9]\d?\d?P)[- ]?{_CNAME}(\d)',                   r'\1/\2 \3'),
    (rf'([1-9]\d?\d?P)[- ]?{_CNAME}',                       r'\1/\2'),
    (rf'([PCXDAI])-?{_CYEAR}[- ]?{_CSUFF}',                 r'\1/\2 \3'),
    (rf'{_CYEAR}-?{_CSUFF}-{_CNAME}',                       r'P/\1 \2$\3'),
    (rf'(?:C|C1|){_CYEAR}-?{_CSUFF}',                       r'C/\1 \2'),
    (rf'C?{_NUM}P[- ]([A-Z-]*)',                            r'\1P/\2'),
    (rf'([PCXDAI]){_NUM}[-/ ]{_MPNAME}',                    r'\2\1/\3'),
    (rf'{_NUM}([PCXDAI])[-/ ]{_MPNAME}',                    r'\1\2/\3'),
    (rf'{_CYEAR}([a-hj-uwyz]1?)',                           r'\1\2|[C]'), # not roman
    (rf'{_CYEAR}-?({_ROMAN_99})',                           r'\1 \2'),

    (rf'ASTEROID[- ]0*{_NUM}[- ]{_MPNAME}',                 r'(\1) \2|[A]'),
    (rf'ASTEROID[- ]{_MYEAR}[- ]{_MSUFF}',                  r'\1 \2|[A]'),
    (rf'ASTEROID[- ]0*{_NUM}',                              r'(\1)|[A]'),
    (rf'{_NUM}[=-]?\({_MPNAME}\)',                          r'(\1) \2'),
    (rf'{_NUM}-{_MPNAME}',                                  r'(\1) \2'),
    (rf'MP-?{_NUM}-{_MPNAME}',                              r'(\1) \2|[M]'),
    (rf'MP-?{_NUM}',                                        r'(\1)|[M]'),
    (rf'TR-?{_NUM}(\d\d)',                                  r'(\1\2)|[A]'), # 3+ digits
    (rf'TROJAN-?{_NUM}',                                    r'(\1)|[A]'),
    (rf'AST0*{_NUM}{_MPNAME}-?[A-Z]?',                      r'(\1) \2|[A]'),
    (rf'BIN(?:20)?([012]\d){_MSUFF}',                       r'20\1 \2|[M]'),
    (rf'NEO(?:20)?([012]\d){_MSUFF}',                       r'20\1 \2|[A]'),
    (rf'KBO{_MYEAR}{_MSUFF}',                               r'\1 \2|[T]'),
    (rf'KBO{_NUM}(\d\d\d){_MPNAME}',                        r'(\1\2) \3|[T]'),
    (rf'KBO{_NUM}(\d\d\d)',                                 r'(\1\2)|[T]'),
    (rf'[AB]{_NUM}(\d\d\d)',                                r'(\1\2)'),
    (rf'(?:MP|){_MYEAR}[- ]?{_MSUFF}[ABC]?',                r'\1 \2'),
    (rf'(9\d)[- ]?{_MSUFF}',                                r'19\1 \2'),
    (rf'([012]\d)[- ]?{_MSUFF}',                            r'20\1 \2'),
    (rf'[ABY]{_MYEAR}{_MSUFF}',                             r'\1 \2'),
    (r'([1-9]\d{4,})-[A-Z]',                                r'\1'),
    (rf'({MPC_PACKED_PATTERN})',                            mpc_unpack),

    # Transposition of a designation
    (rf'{_MYEAR}([A-HJ-Y])(\d+)([A-HJ-Z])',                 r'\1 \2\4\3'),
]

for _pattern, _template in _TARGET_TRANSFORM_PATTERNS:
    _regex = re.compile(_pattern + '$', re.I)
    _TARGET_REPAIRS.append((_regex, _template))

# This table takes target types and embeds them into the returned string with newlines
_TARGET_CATEGORIZER_PATTERNS = [
    (r'(MAIN[- ]BELT |JUPITER FAMILY |)COMET',  r'[C]'),
    (r'INTERSTELLAR?',                          r'[C]'),
    (r'MBC',                                    r'[C]'),
    (r'NUCLEUS',                                r'[C]'),
    (r'FRAGMENT(ED|)',                          r'[C]'),

    (r'ACTIVE[- ]ASTEROID',                     r'[A]|[C]'),
    (r'ASTEROID',                               r'[A]'),
    (r'TROJAN',                                 r'[A]'),
    (r'JUPITER CROSSER',                        r'[A]'),
    (r'MAIN[- ]BELT',                           r'[A]'),
    (r'NEAR[- ]EARTH',                          r'[A]'),
    (r'NEO',                                    r'[A]'),

    (r'DWARF[- ]PLANET',                        r'[D]'),
    (r'CENTAUR[RS]?',                           r'[H]'),
    (r'(SMALL|BIG) CENT Q ?. ?\d+',             r'[H]'),
    (r'MINOR[- ]PLANET',                        r'[M]'),
    (r'PLANET',                                 r'[P]'),
    (r'(RINGS?|ARCS?|ANSA\d?)',                 r'[R]'),
    (r'MOON',                                   r'[S]'),
    (r'SATELLITE',                              r'[S]'),
    (r'TORUS',                                  r'[t]'),

    (r'HOT( CANDIDATE|CLASSICAL)',              r'[T]'),
    (r'KBO\d?',                                 r'[T]'),
    (r'TN[OB]',                                 r'[T]'),
    (r'KUIPER[- ]BELT( OBJECT|)',               r'[T]'),
    (r'CLASSICAL (COLD|HOT)( DISK|)',           r'[T]'),
    (r'(COLD |)CLASSICAL( DISK|)',              r'[T]'),
    (r'(COLD|NEAR) DISK',                       r'[T]'),
    (r'\d*[EI]*:\d+[EI]*(\+[\w:]+)?',           r'[T]'),
    (r'SCAT(EXTD|NEAR)',                        r'[T]'),
    (r'(SCATTERED|EXTENDED)( DISK|)',           r'[T]'),
    (r'TRANS[- ]?NEPTUNIAN( OBJECT| BINARY|)',  r'[T]'),
    (r'(SMALL|BIG) SCAT Q ?. ?\d+',             r'[T]'),
]

for _pattern, _template in _TARGET_CATEGORIZER_PATTERNS:
    _regex = re.compile(rf'\(?{_pattern}\)?$', re.I)
    _TARGET_REPAIRS.append((_regex, _template))

for _word in _UNDIAGNOSTIC_TARGET_WORDS:
    _regex = re.compile(rf'{_word}$', re.I)
    _TARGET_REPAIRS.append((_regex, ''))

# Strip possessives
_regex = re.compile(r"([^ ]*[A-Z])'S", re.I)
_TARGET_REPAIRS.append((_regex, r'\1'))

# For debugging and tracking pattern usage
_USAGE = {}
_LAST_INPUT = {}
for _regex, _template in _TARGET_REPAIRS:
    _USAGE[_regex.pattern] = 0
    _LAST_INPUT[_regex.pattern] = ''

##########################################################################################
##########################################################################################

def hst_repairs(
    strings: list[str] | str
) -> list[str]:
    """Given a list of strings defining TARKEY or TARGNAME values, isolate the strings
    that represent target bodies and convert them to their proper form.
    """

    if isinstance(strings, str):
        strings = [strings]

    # Misc. string cleanup...

    # Split at commas, equal, period
    for char in (',', '=', '.', '(', ')'):
        cleaned = []
        for string in strings:
            cleaned += string.split(char)
        strings = cleaned

    strings = [' '.join(s.split()) for s in strings]  # remove duplicated spaces
    strings = [s.strip('- ') for s in strings]
    strings = [s.replace('_', ' ') for s in strings]
    strings = [s for s in strings if s]

    answers = _repair_list(strings, sep=' ')
    answers = _repair_list(answers, sep='-')

    # Vertical bar marks separators
    answers2 = []
    for answer in answers:
        answers2 += answer.split('|')
    return answers2

def _repair_list(
    strings: list[str],
    sep: str = ' '
) -> list[str]:
    """Return a list of repaired strings based on a list of string inputs.

    Separator `sep` can be " " or "-".
    """

    answers = []
    for string in strings:
        answers += _repair_string(string, sep=sep)
    return answers

def _repair_string(
    string: str,
    sep: str = ' '
) -> list[str]:
    """Return a list of repaired strings based on a single string input.

    Separator `sep` can be " " or "-".
    """

    def repair1(target):
        prev_target = ''
        while prev_target != target:
            prev_target = target
            for regex, template in _TARGET_REPAIRS:
                match = regex.match(target)
                if match:
                    _USAGE[regex.pattern] += 1
                    _LAST_INPUT[regex.pattern] = target
                    if isinstance(template, str):
                        target = match.expand(template)
                        if target != prev_target:
                            break
                    else:
                        return template(target)  # used by mpc_tools.unpack

        return target.strip()

    BAR = '|'  # indicates DO NOT append to the last string in the answers list
    answers = [BAR]
    strings = deque([string])
    while strings:
        string = strings.popleft()
        if not string:
            continue
        if string == BAR:
            answers.append(BAR)
            continue

        # Try to repair the entire string at once
        repaired = repair1(string)

        # Re-process anything after "$"
        if '$' in repaired:
            parts = repaired.partition('$')
            answers.append(parts[0])
            answers.append(BAR)
            strings.appendleft(parts[-1].lstrip('- '))
            continue

        # For any other change, just append
        if repaired != string:
            answers.append(repaired)
            continue

        # Split the string up into words
        words = string.split(sep)
        nwords = len(words)

        # If there's only one word, just append it because we know it doesn't repair
        if nwords == 1:
            if answers[-1] == BAR:
                answers[-1] = string
            else:  # connect it to the trailing string of the answer if it's not barred
                answers[-1] += sep + string
            continue

        # See if we can make progress by stripping TRAILING words one by one
        for k in range(nwords-1, 0, -1):
            test = sep.join(words[:k])
            repaired = repair1(test)
            if repaired != test:
                break

        # If a translation was found at the FRONT of the string...
        if repaired != test:
            if '$' in repaired:
                answer, _, remainder = repaired.partition('$')
                string = (remainder + sep + sep.join(words[k:])).strip('- ')
            else:
                answer = repaired
                string = sep.join(words[k:])

            answers.append(answer)
            answers.append(BAR)
            strings.appendleft(string)
            continue

        # See if we can make progress by stripping LEADING words one by one
        for k in range(1, nwords):
            test = sep.join(words[k:])
            repaired = repair1(test)
            if repaired != test:
                break

        # If a translation was found at the END of the string...
        if repaired != test:
            if '$' in repaired:
                answer, _, remainder = repaired.partition('$')
                answers.append(answer)
                answers.append(BAR)
                strings.appendleft(repaired[3:].lstrip('- '))
                strings.appendleft(BAR)  # don't let remainder merge with leading words
            else:
                answer = repaired

            answers.append(repaired)
            answers.append(BAR)
            strings.appendleft(sep.join(words[:k]))
            continue

        # No repair found, so transfer the first word and try again
        if answers[-1] == BAR:
            answers[-1] = words[0]
        else:  # connect it to the trailing string of the answer if it's not barred
            answers[-1] += sep + words[0]

        strings.appendleft(sep.join(words[1:]))

    # Remove anything extraneous
    answers = [a for a in answers if a and a != BAR]
    return answers


# For interactive testing...
if False:
    from targets.tests.SPT_TESTS import SPT_TESTS

    for filename, spt in SPT_TESTS:
        strings = []
        for k in range(1, 7):
            key = 'TARKEY' + str(k)
            if key not in spt:
                break
            strings.append(spt[key])
        strings.append(spt['TARGNAME'])
        answer = hst_repairs(strings)
        print(repr(filename), '---', answer)

##########################################################################################
