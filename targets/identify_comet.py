##########################################################################################
# identify_comet.py
##########################################################################################

import re
from logging import Logger

from targets import cometdb
from targets import mpc_tools
from targets.roman import ROMAN_PATTERN_99 as _ROMAN_99

_NUM = r'(?:[1-9]\d*)'
_YEAR = r'(?:19\d\d|20\d\d)'

_FRAG = r'(?:-[A-Z][A-Z]?\d*)'
_DESIG = rf'{_YEAR} [A-HJ-Y][A-HJ-Z]?{_NUM}'
_NAME = r"(?:[A-Z'`]{2,}(?:[- ]?[A-Z'`]{2,})*)"
_CNUM = rf'(?: {_NUM})'

# Confidence > 5 means this pattern almost surely defines a comet
# If comet confidence exceeds minor planet confidence, comets will be checked first
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


def identify_comet(
    strings: list[str],
    elements: dict[str, float], *,
    confidence: int,
    rms: float = 0.1,
    logger: Logger | None = None
) -> tuple[dict | None, float, bool]:

    has_elements = ('A' in elements or 'Q' in elements)

    # Query by strings
    comets, used, unused, status = _identify_comets_by_strings(strings)

    # For an empty list of comets, query by elements alone
    if not comets:
        logger and logger.info('No comet identifiers recognized')
        logger and logger.info('Unknown comet identifiers: ' + str(unused))

        if not has_elements:
            logger and logger.error('No orbital elements available')
            return (None, 0., False)

        results = cometdb.query_comet_by_elements(elements, count=5, fragments=True,
                                                  logger=logger)
        if not results:
            logger and logger.error('No comet found by orbital elements')
            return (None, 0., False)

        best_comet, best_rms = results[0]
        if best_rms > rms:
            logger and logger.error(f'Orbit residual exceeds threshold of {rms}')
            return (None, 0., False)
        if len(results) > 1 and best_rms > results[1][1] / 2:
            logger and logger.error('Orbital element test failed; multiple comets have '
                                    'similar residuals')
            return (best_comet, best_rms, False)

        logger and logger.info('Comet selected by orbital elements: '
                               + best_comet['full_name'])
        return (best_comet, best_rms, True)

    # For a single comet, check elements and report
    if len(comets) == 1:
        comet = comets[0]
        logger and logger.info('Comet identified: ' + comet['full_name'])
        logger and logger.info('Recognized identifiers: ' + str(list(used.keys())))
        if unused:
            logger and logger.info('Unknown identifiers: ' + str(unused))

        if has_elements:
            rms_test, _ = mpc_tools.element_resid(elements, comet)
            if rms_test > rms:
                if confidence > 5:
                    logger and logger.error(f'Orbit residual {rms_test:.4f} '
                                            f'exceeds threshold of {rms}')
                    valid = True
                else:
                    logger and logger.error(f'Orbit residual {rms_test:.4f} '
                                            f'exceeds threshold of {rms}')
                    valid = False
            else:
                logger and logger.info(f'Orbit residual: {rms_test:.4f}')
                valid = True
            return (comet, rms_test, valid)
        else:
            if confidence > 5:
                logger and logger.info('No orbital elements available for cross-check')
            else:
                logger and logger.warning('No orbital elements available for cross-check')
            return (comet, 0., True)

    # For multiple comets, select the one with the closest elements
    if len(comets) > 5:
        logger and logger.info(f'Ambiguous comet name: {len(comets)} candidates')
    else:
        names = [c['full_name'] for c in comets]
        logger and logger.info(f'Ambiguous comet name: {names}')

    if not has_elements:
        logger and logger.error('No orbital elements available to resolve ambiguity')
        return (None, 0., False)

    fragments = any(comet.get('fragment', '') for comet in comets)
    results = cometdb.query_comet_by_elements(elements, count=5, comets=comets,
                                              fragments=fragments, logger=logger)

    # Move strings that didn't map to the best orbit out of the `used` dict
    best_comet, best_rms = results[0]
    used_strings = list(used.keys())
    for string in used_strings:
        keys = {comet['key'] for comet in used[string]}
        if best_comet['key'] not in keys:
            unused.append(string)
            del used[string]

    logger and logger.info('Recognized identifiers: ' + str(list(used.keys())))
    if unused:
        logger and logger.info('Unused identifiers: ' + str(unused))

    if best_rms >= rms:
        if confidence > 5:
            logger and logger.warning(f'Orbit residual {best_rms:.4f} '
                                      f'exceeds threshold of {rms}')
            valid = True
        else:
            logger and logger.error(f'Orbit residual {best_rms:.4f} '
                                    f'exceeds threshold of {rms}')
            valid = False
    else:
        logger and logger.info(f'Orbit residual: {best_rms:.4f}')
        valid = True

    return (best_comet, best_rms, valid)


def _identify_comets_by_strings(
    strings: list[str]
) -> tuple[list[dict], dict[str, dict | list], list[str], bool]:

    # Select the properly formatted options
    formatted, unused, confidence = comet_identifiers(strings)

    # Interpret each string as a comet name
    comets = {}     # comet key -> comet
    ambigs = {}     # string -> ambiguous list of comets
    used = {}       # string -> any associated list of comets
    for string in strings:
        test = cometdb.query_comet_by_name(string)
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

    # Return the list of matches
    return list(comets.values()), used, unused, True


def comet_identifiers(
    strings: list[str]
) -> tuple[list[str], list[str], int]:

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

##########################################################################################
