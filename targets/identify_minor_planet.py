##########################################################################################
# identify_minor_planet.py
##########################################################################################

import re

from targets import mpc_tools


def identify_minor_planet(strings, elements=None, *, rms=0.1, confidence=0, logger=None):
    """Try to identify a minor planet based on a list of possible name strings and
    optional orbital elements.

    Parameters:
        strings (str or list[str]): One or more strings that potentially identify a minor
            planet.
        elements (dict, optional): A dictionary of orbital elements keyed by element name,
            as follows:

            * "A": semimajor axis in AU.
            * "Q": perihelion distance in AU.
            * "I": inclination in degrees.
            * "O": ascending node in degrees.
            * "E": eccentricity.
            * "W": argument of pericenter in degrees.

            Any other items in the dictionary are ignored.
        rms (float, optional): Upper limit on the root-mean-square fractional difference
             in orbital elements that represents a match.
        confidence (int, optional): A value 0-9 indicating the level of confidence that
            this item is a minor planet. A value > 5 indicates that this is _probably_ a
            minor planet; this affects how discrepancies are reported and logged.
        logger (Logger, optional): Logger to use.

    Returns:
        tuple: `(body_dict, rms, valid)`:

        * `body_dict` (dict[str] or None): A dictionary containing the attributes of a
          minor planet if one was identified; None otherwise.
        * `rms` (float): The fractional root-mean-square residual of the orbital elements
          if a body was identified; zero otherwise.
        * `valid` (bool): True if a minor planet was matched and the RMS threshold was
          met.
    """

    if not strings:
        strings = []
    elif isinstance(strings, str):
        strings = [strings]

    elements = elements or {}
    has_elements = ('A' in elements or 'Q' in elements)

    # Query by strings
    bodies, used, unused, _status = _identify_minor_planet_by_strings(strings)

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
        msg = f'Orbit residual {best_rms:.4f} exceeds threshold of {rms}'
        if confidence > 5:
            logger and logger.warning(msg)
            valid = True
        else:
            logger and logger.error(msg)
            valid = False
    else:
        logger and logger.info(f'Orbit residual: {best_rms:.4f}')
        valid = True

    return (best_body, best_rms, valid)


def _identify_minor_planet_by_strings(strings):
    """Identify one or more minor planets by a name or list of alternative names.

    Parameters:
        strings (str or list[str]): One or more strings potentially identifying a minor
            planet.

    Returns:
        tuple: `(mpc_dicts, used, unused, single)`:

        * mpc_dicts (list[dict]): One or more identified minor planets.
        * used (dict[str, dict]): The list of strings that were recognized as identifiers.
        * unused (list[str]): The list of string that were not recognized as identifiers.
        * single (bool): True if a single, unambiguous body was identified.
    """

    # Separate the formatted and un-formatted strings
    formatted, unused, _confidence = _minor_planet_identifiers(strings)

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


def _minor_planet_identifiers(strings):
    """Interpret one or more strings as minor planet identifiers.

    Parameters:
        strings (str or list[str]): One or more potential identifiers for a minor planet.

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


__all__ = ['identify_minor_planet']

##########################################################################################
