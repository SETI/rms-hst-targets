##########################################################################################
# targets/comet_identifiers.py
##########################################################################################

import re

from targets import cometdb
from targets.roman import ROMAN_PATTERN_99 as _ROMAN_99


def comet_identifiers(strings, *, logger=None):
    """Identify one or more minor planets by a name or list of alternative names.

    Parameters:
        strings (str or list[str]): One or more strings potentially identifying a comet.
        logger (Logger, optional): Logger to use.

    Returns:
        tuple: `(comet_dicts, used, unused, single)`:

        * `comet_dicts` (list[dict]): Zero or more dictionaries containing the attributes
          of a comet. Multiple values indicate that the strings are either contradictory
          (identifying different comets) or ambiguous.
        * `used` (dict[str] or list[dict[str]]]): A dictionary keyed by each recognized
          string, returning either a comet dictionary or, if ambiguous, a list of comet
          dictionaries.
        * `unused` (list[str]): The list of input strings that were not recognized as
          comet identifiers.
        * `single` (bool): True if a single, unambiguous commet was identified.
    """

    if isinstance(strings, str):
        strings = [strings]

    # Select the properly formatted options
    _formatted, unused, _confidence = _select_comet_identifiers(strings)

    # Interpret each string as a comet name
    comets = {}     # comet key -> comet
    ambigs = {}     # string -> ambiguous list of comets
    used = {}       # string -> any associated list of comets
    for string in strings:
        test = cometdb.query_comet_by_name(string, logger=logger, ambiguous=True)
        if test:
            used[string] = test if isinstance(test, list) else [test]
            if isinstance(test, dict):
                comets[test['key']] = test
            else:
                ambigs[string] = test
        else:
            unused.append(string)

    # If `comets` is empty, return the ambiguous comets as a list
    if not comets:
        ambig_dict = {}
        for ambig_list in ambigs.values():
            for comet in ambig_list:
                ambig_dict[comet['key']] = comet

        if ambig_dict:
            names = [c['name'] for c in ambig_dict.values()]
            logger and logger.info(f'Ambiguous comets: {names}')
        else:
            logger and logger.info('No comets identified')
        if unused:
            logger and logger.info(f'Unused strings: {unused}')

        return list(ambig_dict.values()), used, unused, False

    # If a comet or parent is in an ambiguous list, that list is superfluous

    # Get every comet key and comet parent key
    comet_keys = set(comets.keys())
    parent_keys = {comet.get('parent_key', '') for comet in comets.values()} - {''}
    either_keys = comet_keys | parent_keys

    # Get the list of strings producing an ambiguous result
    ambig_strings = list(ambigs.keys())

    # Remove any entry in the `ambigs` dict if one of its comets is in the `comets` dict
    for ambig_string in ambig_strings:

        # Get the set of keys for these ambiguous comets
        ambig_keys = {comet['key'] for comet in ambigs[ambig_string]}

        # If there's overlap, this entry was used and is no longer ambiguous
        if ambig_keys & either_keys:
            del ambigs[ambig_string]

    # Anything string that remains in the `ambigs` dict was unused
    unused += list(ambigs.keys())

    # If one comet in the remaining list is a parent of the other, remove the parent
    for key in comet_keys:
        if key in parent_keys:
            del comets[key]

    comets = list(comets.values())

    # Log the results
    names = [c['name'] for c in comets]
    if len(comets) == 1:
        logger and logger.info(f'Comet identified: {names[0]!r}')
    else:
        logger and logger.info(f'Multiple comets identified: {names}')
    if unused:
        logger and logger.info(f'Unused strings: {unused}')

    # Return the list of matches
    return comets, used, unused, True


_NUM   = r'(?:[1-9]\d*)'
_YEAR  = r'(?:19\d\d|20\d\d)'
_FRAG  = r'(?:-[A-Z][A-Z]?\d*)'
_DESIG = rf'{_YEAR} [A-HJ-Y][A-HJ-Z]?{_NUM}'
_NAME  = r"(?:[A-Z'`]{2,}(?:[- ]?[A-Z'`]{2,})*)"
_CNUM  = rf'(?: {_NUM})'

# Confidence > 5 means this pattern most likely defines a comet.
# If comet confidence exceeds minor planet confidence, comets will be checked first.
_PATTERNS = [
    (rf'([PCXDAI]/{_DESIG}{_FRAG}?) \(({_NAME}{_CNUM}?{_FRAG}?)\)'  , 9),
    (rf'([PCXDAI]/{_DESIG}{_FRAG}?)'                                , 9),
    (rf'([1-9]\d*[PCXDAI])/({_NAME}{_CNUM}?{_FRAG}?)'               , 9),
    (rf'({_YEAR} {_ROMAN_99})'                                      , 6),
    (rf'({_YEAR}[a-z]\d?)'                                          , 4),
    (rf'({_NAME}{_CNUM}{_FRAG}?)'                                   , 4),
    (rf'({_NAME}{_CNUM}?{_FRAG})'                                   , 4),
    (rf'({_NAME})'                                                  , 1),
]

_REGEXES = [(re.compile(pattern, re.I), conf) for pattern, conf in _PATTERNS]


def _select_comet_identifiers(strings):
    """Recognize one or more strings as possible comet identifiers.

    Parameters:
        strings (str or list[str]): One or more potential identifiers for a comet.

    Returns:
        tuple: `(formatted, unused, confidence)`:

        * `formatted` (set[str]): The subset of input strings in the format of a possible
          comet identifier.
        * `unused` (list[str]): The list of input strings that are not in a recognized
          format of comet identifier.
        * `confidence` (int): A numeric value 0-9 indicating the level of confidence that
          the strings represent a comet.
    """

    if isinstance(strings, str):
        strings = [strings]

    formatted = set()
    confidence = 0
    unused = []
    for string in strings:
        for regex, conf in _REGEXES:
            match = regex.match(string)
            if match:
                formatted |= set(match.groups())
                confidence = max(confidence, conf)
                break
        if not match:
            unused.append(string)

    return formatted, unused, confidence


__all__ = ['comet_identifiers']

##########################################################################################
