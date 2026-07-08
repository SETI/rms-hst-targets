##########################################################################################
# mpc/mpc_packing.py
##########################################################################################
"""Conversion functions between packed and unpacked MPC provisional designations.

See https://minorplanetcenter.net/mpcops/documentation/provisional-designation-definition

Examples::
    Unpacked     -> Packed

    "1995 XA"    -> "J95X00A"
    "1995 XL1"   -> "J95X01L"
    "1995 FB13"  -> "J95F13B"
    "1998 SQ108" -> "J98SA8Q"
    "1998 SV127" -> "J98SC7V"
    "1998 SS162" -> "J98SG2S"
    "2099 AZ193" -> "K99AJ3Z"
    "2008 AA360" -> "K08Aa0A"
    "2007 TA418" -> "K07Tf8A"
    "A904 OA"    -> "J04O00A"

    # For the Palomar-Leiden Survey:
    "2040 P-L" -> "PLS2040"
    "3138 T-1" -> "T1S3138"
    "1010 T-2" -> "T2S1010"
    "4101 T-3" -> "T3S4101"

    # Extended packed provisional designations:
    "2025 DA620"    -> "_PD0000"
    "2026 DY620"    -> "_QD000N"
    "2027 DZ6190"   -> "_RD0aEM"
    "2028 EA339749" -> "_SEZZZZ"
    "2029 FL591673" -> "_TFzzzz"

Attributes:
    MPC_UNPACKED_PATTERN (str): Regular expression that matches any provisional
        designation.
    MPC_PACKED_PATTERN (str): Regular expression that matches a packed provisional
        designation.
    MPC_EXTENDED_PATTERN (str): Regular expression that matches an extended packed
        designation.
"""

import re

_BASE62_CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
_BASE62_VALS = {c: k for k, c in enumerate(_BASE62_CHARS)}

_CENTURY_CHARS = {'18': 'I', '19': 'J', '20': 'K'}
_CENTURY_DIGITS = {c: k for k, c in _CENTURY_CHARS.items()}

_PALOMAR_UNPACKED = {'P-L', 'T-1', 'T-2', 'T-3'}
_PALOMAR_PACKED = {'PL', 'T1', 'T2', 'T3'}

_LETTERS = 'ABCDEFGHJKLMNOPQRSTUVWXYZ'  # skipping "I"
_LETTER_LOOKUP = {c: i for i, c in enumerate(_LETTERS)}


def mpc_pack(unpacked: str) -> str:
    """Convert an unpacked name to a packed name.

    Raises:
        ValueError: If `unpacked` is not a valid provisional designation.
    """

    if not mpc_is_valid_unpacked(unpacked):
        raise ValueError(f'invalid unpacked name: "{unpacked}"')

    # Handle Palomar-Leiden Survey values
    if unpacked[-3:] in _PALOMAR_UNPACKED:
        parts = [unpacked[-3], unpacked[-1], 'S', unpacked[:4]]
        return ''.join(parts)

    # Replace leading "A" with "1" for pre-1925 discovery notation
    parts = [_CENTURY_CHARS[unpacked[:2].replace('A', '1')], unpacked[2:4], unpacked[5]]
    match len(unpacked):
        case 7:
            parts += ['00']
        case 8:
            parts += ['0', unpacked[7]]
        case 9:
            parts += [unpacked[7:]]
        case _:
            indx = int(unpacked[7:-1])
            if indx < 62:
                parts += [_BASE62_CHARS[indx], unpacked[9]]
            else:
                return _mpc_pack_extended(unpacked)

    parts += [unpacked[6]]
    return ''.join(parts)


def _mpc_pack_extended(unpacked: str) -> str:

    year = int(unpacked[:4]) - 2000
    parts = ['_', _BASE62_CHARS[year], unpacked[5]]
    indx = 25 * int(unpacked[7:]) + _LETTER_LOOKUP[unpacked[6]] - 15500
    parts += [_to_base62(indx).rjust(4, '0')]
    return ''.join(parts)


def mpc_unpack(packed: str) -> str:
    """Convert a packed name to a unpacked name.

    Raises:
        ValueError: If `packed` is not a valid packed provisional designation (extended or
            otherwise).
    """

    if not mpc_is_valid_packed(packed, extended=True):
        raise ValueError(f'invalid packed name: "{packed}"')

    # Handle for Palomar-Leiden Survey values
    if packed[:2] in _PALOMAR_PACKED:
        parts = [packed[3:7], ' ', packed[0], '-', packed[1]]
        return ''.join(parts)

    if packed[0] == '_':
        return _mpc_unpack_extended(packed)

    # Years before 1925 use "A" in place of first digit
    year = _CENTURY_DIGITS[packed[0]] + packed[1:3]
    if year < '1925':
        year = 'A' + year[1:]

    parts = [year, ' ', packed[3], packed[6]]
    if packed[4] == '0':
        if packed[5] != '0':
            parts += [packed[5]]
    else:
        parts += [str(_BASE62_VALS[packed[4]]), packed[5]]

    return ''.join(parts)


def _mpc_unpack_extended(packed: str) -> str:

    parts = ['20', str(_BASE62_VALS[packed[1]]), ' ', packed[2]]
    (number, iletter) = divmod(_from_base62(packed[3:]) + 15500, 25)
    parts += [_LETTERS[iletter]]
    if number:
        parts += [str(number)]
    return ''.join(parts)


# Year uses "A" for 1800-1925, is valid through 2099
_MPYEAR = r'(?:A8\d\d|A9(?:[01]\d|2[0-4])|19(?:2[5-9]|[3-9]\d)|20\d\d)'
MPC_UNPACKED_PATTERN = rf'(?:{_MPYEAR} [A-HJ-Y][A-HJ-Z]\d*|\d{4} (?:P-L|T-[123]))'
MPC_PACKED_PATTERN = (r'(?:[IJK]\d\d[A-HJ-Y][0-9A-Za-z]\d[A-HJ-Z]'
                      r'|(?:PL|T[123])S[1-9]\d{3})')
MPC_EXTENDED_PATTERN = '_[P-Z][A-HJ-Y][0-9A-Za-z]{4}'

_UNPACKED = re.compile(MPC_UNPACKED_PATTERN + '$')
_PACKED = re.compile(MPC_PACKED_PATTERN + '$')
_EXTENDED = re.compile(MPC_EXTENDED_PATTERN + '$')


def mpc_is_valid_unpacked(name: str) -> bool:
    """True if the given string is a valid unpacked provisional name for a minor planet.
    """

    return bool(_UNPACKED.match(name))


def mpc_is_valid_packed(name: str, *, extended: bool = False) -> bool:
    """True if the given string is a valid packed provisional name for a minor planet.

    Parameters:
        name: Name to test for validity.
        extended: True to allow extended packed names.

    Returns:
        True if the name is valid.
    """

    if _PACKED.match(name):
        return True
    if extended and _EXTENDED.match(name):
        return True
    return False


def _to_base62(n: int) -> str:
    if n == 0:
        return '0'

    chars = []
    while n:
        chars.append(_BASE62_CHARS[n % 62])
        n //= 62
    return ''.join(chars[::-1])


def _from_base62(string: str) -> int:
    result = 0
    for char in string:
        result = result * 62 + _BASE62_VALS[char]
    return result

##########################################################################################
