##########################################################################################
# tests/test_roman.py
##########################################################################################
"""Unit tests for targets/roman.py: Roman-numeral validation and conversion."""

import re

import pytest

from targets.roman import (
    ROMAN_PATTERN_99,
    ROMAN_PATTERN_999,
    int_to_roman,
    roman_to_int,
    validate_roman,
)

# (roman, integer) pairs exercising units, tens, hundreds, thousands, and every
# subtractive form (IV, IX, XL, XC, CD, CM).
_KNOWN = [
    ('I', 1), ('II', 2), ('III', 3), ('IV', 4), ('V', 5), ('IX', 9),
    ('X', 10), ('XIV', 14), ('XL', 40), ('XLII', 42), ('XC', 90), ('XCIX', 99),
    ('C', 100), ('CD', 400), ('D', 500), ('CM', 900),
    ('M', 1000), ('MCMXCIV', 1994), ('MMXXV', 2025), ('MMMCMXCIX', 3999),
]


@pytest.mark.parametrize(('numeral', 'value'), _KNOWN)
def test_roman_to_int(numeral: str, value: int) -> None:
    assert roman_to_int(numeral) == value


@pytest.mark.parametrize(('numeral', 'value'), _KNOWN)
def test_int_to_roman(numeral: str, value: int) -> None:
    assert int_to_roman(value) == numeral


@pytest.mark.parametrize('numeral', [n for n, _ in _KNOWN])
def test_validate_roman_accepts_valid(numeral: str) -> None:
    assert validate_roman(numeral) is True


@pytest.mark.parametrize('bad', ['', 'IIII', 'VV', 'IL', 'IC', 'XM', 'MMMM', 'ABC', 'iv'])
def test_validate_roman_rejects_invalid(bad: str) -> None:
    assert validate_roman(bad) is False


@pytest.mark.parametrize('bad', ['IIII', 'VX', 'MMMM', 'nope', ''])
def test_roman_to_int_rejects_invalid(bad: str) -> None:
    with pytest.raises(ValueError, match=re.escape(f'not a valid Roman numeral: "{bad}"')):
        roman_to_int(bad)


@pytest.mark.parametrize('num', [0, -1, -100, 4000, 5000])
def test_int_to_roman_out_of_range(num: int) -> None:
    with pytest.raises(ValueError,
                       match=re.escape(f'value outside range 1-3999 for Roman '
                                       f'numerals: {num}')):
        int_to_roman(num)


def test_round_trip_all_values() -> None:
    # Every value in the representable range converts to a numeral and back.
    for n in range(1, 4000):
        numeral = int_to_roman(n)
        assert validate_roman(numeral)
        assert roman_to_int(numeral) == n


def test_patterns_match_expected() -> None:
    # ROMAN_PATTERN_999 spans 1-999 (no thousands); ROMAN_PATTERN_99 spans 1-99
    # (no hundreds). Both are used to match satellite numerals embedded in a name,
    # so they are anchored here to test full-string acceptance/rejection.
    re_999 = re.compile(f'{ROMAN_PATTERN_999}$')
    re_99 = re.compile(f'{ROMAN_PATTERN_99}$')

    assert re_999.match('CMXCIX')       # 999
    assert re_99.match('XCIX')          # 99
    assert not re_99.match('C')         # 100 is out of the 1-99 range
