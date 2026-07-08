##########################################################################################
# roman.py
##########################################################################################
"""roman.py: Support for Roman numerals."""

import re

ROMAN_PATTERN = (r'(?=[MDCLXVI])M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})'
                 r'(?:IX|IV|V?I{0,3})')
ROMAN_PATTERN_999 = (r'(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})')
ROMAN_PATTERN_99 = (r'(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})')

_ROMAN_RE = re.compile(rf'({ROMAN_PATTERN})$')
_ROMAN_MAP = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
_ROMAN_PAIRS = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
                (100,  'C'), (90,  'XC'), (50,  'L'), (40,  'XL'),
                (10,   'X'), (9,   'IX'), (5,   'V'), (4,   'IV'), (1, 'I')]


def validate_roman(s: str) -> bool:
    """True if the given string represents a valid Roman numeral."""

    return bool(_ROMAN_RE.match(s))


def roman_to_int(s: str) -> int:
    """Convert a Roman numeral string to its integer value.

    Raises:
        ValueError: If the string does not represent a valid Roman numeral.
    """

    if not validate_roman(s):
        raise ValueError(f'not a valid Roman numeral: "{s}"')

    # Iterate through the string up to the second-to-last character
    total = 0
    for i in range(len(s) - 1):
        if _ROMAN_MAP[s[i]] < _ROMAN_MAP[s[i+1]]:
            total -= _ROMAN_MAP[s[i]]
        else:
            total += _ROMAN_MAP[s[i]]

    # Add the value of the last character, which is always added
    total += _ROMAN_MAP[s[-1]]
    return total


def int_to_roman(num: int) -> str:
    """Convert an integer to a Roman numeral string.

    Raises:
        ValueError: If the number cannot be represented as a Roman numeral.
    """

    if num < 1 or num >= 4000:
        raise ValueError(f'value outside range 1-3999 for Roman numerals: {num}')

    result = ''
    for value, numeral in _ROMAN_PAIRS:
        while num >= value:
            result += numeral
            num -= value

    return result

##########################################################################################
