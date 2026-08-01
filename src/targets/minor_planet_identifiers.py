##########################################################################################
# targets/minor_planet_identifiers.py
##########################################################################################

import re

from targets import mpc_tools

# A bare 1-3 digit number, optionally parenthesized.
_BARE_NUMBER_REGEX = re.compile(r'\(?\d{1,3}\)?$')


def minor_planet_identifiers(strings, *, logger=None):
    """Identify one or more minor planets by a name or list of alternative names.

    Parameters:
        strings (str or list[str]): One or more strings potentially identifying a minor
            planet.

    Returns:
        tuple: `(mp_dicts, used, unused, single)`:

        * mp_dicts (list[dict]): Dictionaries of zero or more identified minor planets.
        * used (dict[str, dict]): The list of strings that were recognized as identifiers.
        * unused (list[str]): The list of string that were not recognized as identifiers.
        * single (bool): True if a single, unambiguous body was identified.
    """

    # Separate the formatted and un-formatted strings
    formatted, unused, _confidence = _select_minor_planet_identifiers(strings)

    # A bare 1-3 digit number is a weak identifier: in HST target strings it is often a
    # field/aperture index or a mistaken minor-planet number (e.g. the "1" in the STD
    # field "1 (VESTA)", where the body is really 4 Vesta). When the strings also provide
    # a name or full designation, trust that and drop the bare short numbers; keep them
    # only when nothing else identifies the body (e.g. TARGNAME "624" for 624 Hektor).
    if any(not _BARE_NUMBER_REGEX.match(s) for s in formatted):
        dropped = {s for s in formatted if _BARE_NUMBER_REGEX.match(s)}
        if dropped:
            formatted = formatted - dropped

    used = {}  # string -> mpc result as a dict
    mpc_dicts = []

    # For each formatted string...
    for string in formatted:
        try:
            # Look up the formatted string
            new_dict = mpc_tools.mpc_query_by_name(string)

            # If not found, this string is unused
            if not new_dict:
                unused.append(string)
                continue

            # Otherwise, see if it is the same as one already in the list; if yes, merge
            same = False
            for mpc_dict in mpc_dicts:
                same |= _same_minor_planet(mpc_dict, new_dict)

            # Otherwise, add this body dict to the list
            if not same:
                mpc_dicts.append(new_dict)

            used[string] = new_dict

        except RuntimeError:
            unused.append(string)

    # Now that we have candidates, check again using full strings against body lookups.
    # A string matching none of the long patterns still has to be tested, because those
    # patterns all require a number; a bare name or bare number identifies the body just as
    # well, and reporting it as unused would contradict the body we just identified from it.
    formatted, unmatched, _confidence = _select_minor_planet_identifiers(strings,
                                                                         longmatch=True)

    used = {}  # string -> mpc result as a dict
    unused = []
    for string in list(formatted) + unmatched:
        found = False
        for mpc_dict in mpc_dicts:
            if string in mpc_dict['lookups']:
                used[string] = mpc_dict
                found = True
        if not found and string not in unused:
            unused.append(string)

    # Log the result
    if len(mpc_dicts) == 1:
        name = mpc_dicts[0]["full_name"]
        logger and logger.info(f'Minor planet identified: "{name}"')
    elif len(mpc_dicts) > 1:
        names = [m['full_name'] for m in mpc_dicts]
        logger and logger.info(f'Multiple minor planets identified: {names}')
    if unused:
        logger and logger.info(f'Unused minor planet strings: {unused}')

    return (mpc_dicts, used, unused, len(mpc_dicts) == 1)


def _same_minor_planet(dict1, dict2):
    """True if these dicts describe the same minor planet; also merge content into the
    first.
    """

    desigs1 = ({dict1['desig']} | set(dict1['alt_desigs'])) -  {''}
    desigs2 = ({dict2['desig']} | set(dict2['alt_desigs'])) -  {''}

    aliases1 = ({dict1['mnum'], dict1['name']} | desigs1) -  {''}
    aliases2 = ({dict2['mnum'], dict2['name']} | desigs2) -  {''}

    # If no designations are in common, the bodies are different
    if not (aliases1 & aliases2):
        return False

    # Otherwise, merge content
    dict1['mnum'] = dict1['mnum'] or dict2['mnum']
    dict1['name'] = dict1['name'] or dict2['name']

    desigs = list(desigs1 | desigs2)
    if desigs:
        desigs.sort()
        dict1['desig'] = desigs[0]
        dict1['alt_desigs'] = desigs[1:]

    return True


_NUM   = r'(?:[1-9]\d*)'
_YEAR  = r'(?:19\d\d|20\d\d)'
_NAME  = r"(?:[A-Z']{2,}(?:[- ]?[A-Z']{2,})*)"
_DESIG = rf'(?:{_YEAR} [A-HJ-Y][A-HJ-Z]{_NUM}?)'

# Confidence > 5 means this pattern most likely defines a minor planet.
# If minor planet confidence exceeds comet confidence, comets will be checked second.
_SHORT_PATTERNS = [
    (rf'({_DESIG})'                 , 7),
    (rf'\(?({_NUM})\)? ({_NAME})'   , 9),
    (rf'({_NUM}) \(({_NAME})\)'     , 9),
    (rf'\(({_NUM})\) ({_DESIG})'    , 9),
    (rf'\(({_NUM})\)'               , 8),
    (rf'({_NUM})'                   , 1),
    (rf'\(?({_NAME})\)?'            , 2),
]

# Same as above but number + name and number + designation remain together
_LONG_PATTERNS = [
    (rf'(\(?{_NUM}\)? {_NAME})'     , 9),
    (rf'({_NUM} \({_NAME}\))'       , 9),
    (rf'(\({_NUM}\) {_DESIG})'      , 9),
    (rf'(\({_NUM}\))'               , 8),
]

# Negative lookahead ensures that the next character, if any, is not a letter or digit
_SHORT_REGEXES = [(re.compile(pattern + r'(?![A-Z0-9])(.*)', re.I), conf)
                  for pattern, conf in _SHORT_PATTERNS]
_LONG_REGEXES = [(re.compile(pattern + r'(?![A-Z0-9])(.*)', re.I), conf)
                 for pattern, conf in _LONG_PATTERNS]


def _select_minor_planet_identifiers(strings, longmatch=False):
    """Interpret one or more strings as minor planet identifiers.

    Parameters:
        strings (str or list[str]): One or more potential identifiers for a minor planet.
        longmatch (bool, optional): True to keep number+name and number+designation
            together

    Returns:
        tuple: `(formatted, unused, confidence)`:

        * formatted (set[str]): The subset of input strings in the format of a possible
          minor planet identifier.
        * unused (list[str]): The list of input strings that are not in a recognized
          format of minor planet identifier.
        * confidence (int): A numeric value 0-9 indicating the level of confidence that
          the strings represent a minor planet.
    """

    if isinstance(strings, str):
        strings = [strings]

    regexes = _LONG_REGEXES if longmatch else _SHORT_REGEXES

    formatted = set()
    unused = []
    confidence = 0
    for string in strings:
        for regex, conf in regexes:
            match = regex.match(string)
            if match:
                matches = match.groups()
                formatted |= set(matches[:-1])
                tail = matches[-1].strip()
                if tail:
                    unused.append(tail)
                confidence = max(confidence, conf)
                break
        if not match:
            unused.append(string)

    return formatted, unused, confidence


__all__ = ['minor_planet_identifiers']

##########################################################################################
