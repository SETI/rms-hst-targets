##########################################################################################
# identify_minor_planet.py
##########################################################################################

import re
from logging import Logger

from targets import mpc_tools

_NUM = r'(?:[1-9]\d*)'
_YEAR = r'(?:19\d\d|20\d\d)'

_NAME = r"(?:[A-Z']{2,}(?:[- ]?[A-Z']{2,})*)"
_DESIG = rf'(?:{_YEAR} [A-HJ-Y][A-HJ-Z]{_NUM}?)'

# Confidence > 5 means this pattern almost surely defines a minor planet
# If minor planet confidence exceeds comet confidence, comets will be checked second
_PATTERNS = [
    (rf'({_DESIG})'                 , 7),
    (rf'\(?({_NUM})\)? ({_NAME})'   , 9),
    (rf'({_NUM}) \(({_NAME})\)'     , 9),
    (rf'\(({_NUM})\) ({_DESIG})'    , 9),
    (rf'\(({_NUM})\)'               , 8),
    (rf'({_NUM})'                   , 1),
    (rf'\(?({_NAME})\)?'            , 2),
]

_REGEXES = [(re.compile(pattern, re.I), conf) for pattern, conf in _PATTERNS]


def identify_minor_planet(
    strings: list[str],
    elements: dict[str, float], *,
    confidence: int,
    rms: float = 0.05,
    logger: Logger | None = None
) -> tuple[dict | None, float, bool]:

    has_elements = ('A' in elements or 'Q' in elements)

    # Query by strings
    bodies, used, unused, status = _identify_minor_planets_by_strings(strings)

    # For an empty list of bodies, query by elements alone
    if not bodies:
        logger and logger.info('No minor planet identifiers recognized')
        if unused:
            logger and logger.info('Unknown minor planet identifiers: ' + str(unused))

        if not has_elements:
            logger and logger.error('No orbital elements available')
            return (None, 0., False)

        results = mpc_tools.mpc_query_by_elements(elements, count=5, logger=logger)
        if not results:
            logger and logger.error('No minor planet found by orbital elements')
            return (None, 0., False)

        best_body, best_rms = results[0]
        if best_rms > rms:
            logger and logger.error(f'Orbit residual exceeds threshold of {rms}')
            return (None, 0., False)
        if len(results) > 1 and best_rms > results[1][1] / 2:
            logger and logger.error('Orbital element test failed; multiple bodies have '
                                    'similar residuals')
            return (best_body, best_rms, False)

        logger and logger.warning('Low-confidence candidate selected by orbital elements '
                                  + best_body['full_name'])
        return (best_body, best_rms, True)

    # For a single body, check elements and report
    if len(bodies) == 1:
        body = bodies[0]
        logger and logger.info('Minor planet identified: ' + body['full_name'])
        logger and logger.info('Recognized identifiers: ' + str(list(used.keys())))
        if unused:
            logger and logger.info('Unknown identifiers: ' + str(unused))

        if has_elements:
            rms_test, _ = mpc_tools.element_resid(elements, body)
            if rms_test >= rms:
                if confidence > 5:
                    logger and logger.warning(f'Orbit residual {rms_test:.4f} '
                                              f'exceeds threshold of {rms}')
                    valid = True
                else:
                    logger and logger.error(f'Orbit residual {rms_test:.4f} '
                                            f'exceeds threshold of {rms}')
                    valid = False
            else:
                logger and logger.info(f'Orbit residual: {rms_test:.4f}')
                valid = True
            return (body, rms_test, valid)
        else:
            if confidence > 5:
                logger and logger.info('No orbital elements available for cross-check')
            else:
                logger and logger.warning('No orbital elements available for cross-check')
            return (body, 0., True)

    # For multiple bodies, select the one with the closest elements
    names = [b['full_name'] for b in bodies]
    logger and logger.info('Ambiguous minor planet: ' + str(names))

    if not has_elements:
        logger and logger.error('No orbital elements available to resolve ambiguity')
        return (None, 0., False)

    results = mpc_tools.mpc_query_by_elements(elements, count=5, bodies=bodies,
                                              logger=logger)

    # Move strings that didn't map to the best orbit out of the `used` dict
    best_body, best_rms = results[0]
    used_strings = list(used.keys())
    for string in used_strings:
        if best_body != used[string]:
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

    return (best_body, best_rms, valid)


def _identify_minor_planets_by_strings(
    strings: list[str]
) -> tuple[list[dict], dict[str, dict], list[str], bool]:

    # Separate the formatted and un-formatted strings
    formatted, unused, confidence = minor_planet_identifiers(strings)

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

            # Otherwise, see if is the same as one already in the list
            # If yes, merge the content
            same = False
            for mpc_dict in mpc_dicts:
                same |= _same_minor_planet(mpc_dict, new_dict)

            # Otherwise, add this body dict to the list
            if not same:
                mpc_dicts.append(new_dict)

            used[string] = new_dict

        except RuntimeError:
            unused.append(string)

    return mpc_dicts, used, unused, len(mpc_dicts) == 1


def _same_minor_planet(dict1, dict2):
    """True if these dicts describe the same minor planet; also merge content into first.
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


def minor_planet_identifiers(
    strings: list[str]
) -> tuple[list[str], list[str], int]:

    formatted = set()
    unused = []
    confidence = 0
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
