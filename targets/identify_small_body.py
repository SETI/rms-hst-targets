##########################################################################################
# identify_small_body.py
##########################################################################################

from targets._DISALLOWED_MINOR_PLANET_NAMES import _DISALLOWED_MINOR_PLANET_NAMES
from targets.hst_repairs import hst_repairs
from targets.identify_comet import _comet_identifiers, identify_comet
from targets.identify_minor_planet import _minor_planet_identifiers, identify_minor_planet
from targets.targettype import TargetType

_DISALLOWED_UC = {name.upper() for name in _DISALLOWED_MINOR_PLANET_NAMES}


def identify_small_body(strings, elements, *, comet_rms=0.1, mp_rms=0.08, logger=None):
    """Identify a comet or minor planet from name strings and orbital elements.

    Parameters:
        strings (str or list[str]): One or more strings that potentially identify a small
            body, e.g., the values of the TARKEY*, TARGNAME, and TARDESCR keywords of an
            SPT/SHF header.
        elements (dict[str], optional): A dictionary of orbital elements keyed by element
            name, as follows:

            * "A": semimajor axis in AU.
            * "Q": perihelion distance in AU.
            * "I": inclination in degrees.
            * "O": ascending node in degrees.
            * "E": eccentricity.
            * "W": argument of pericenter in degrees.

            Any other items in the dictionary are ignored.
        comet_rms (float): Upper limit on the fractional root-mean-square discrepancy
            between the given orbital elements and those of a comet for the match to be
            accepted.
        mp_rms (float): Upper limit on the fractional root-mean-square discrepancy between
            the given orbital elements and those of a minor planet for the match to be
            accepted.
        logger: An optional Logger for messages.

    Returns:
        tuple: `(body_dict, rms, valid)`:

        * `body_dict` (dict[str] or None): A dictionary containing the attributes of a
          minor planet or comet if one was identified; None otherwise.
        * `rms` (float): The fractional root-mean-square residual of the orbital elements
          if a body was identified; zero otherwise.
        * `valid` (bool): True if a minor planet was matched and the RMS threshold was
          met.
    """

    if not strings:
        strings = []
    elif isinstance(strings, str):
        strings = [strings]

    logger and logger.info('HST identification strings: ' + str(strings))

    options, ttypes = hst_repairs(strings, logger=logger)
    maybe_minor = bool(set(TargetType.MCODES + TargetType.MINOR_PLANET) & set(ttypes))
    maybe_comet = bool({TargetType.COMET, TargetType.CENTAUR} & set(ttypes))

    # Names reserved for a satellite or comet never identify a minor planet unless the
    # header explicitly marks the target as one.
    mp_options = options
    if not maybe_minor:
        mp_options = [o for o in options if o.upper() not in _DISALLOWED_UC]
        excluded = [o for o in options if o.upper() in _DISALLOWED_UC]
        if excluded:
            logger and logger.info('Excluded from minor planet search: ' + str(excluded))

    _, _, comet_conf = _comet_identifiers(options)
    _, _, mp_conf = _minor_planet_identifiers(mp_options)

    try_comet = maybe_comet or not maybe_minor or comet_conf >= mp_conf
    if try_comet:
        logger and logger.info('Testing comets')
        comet, rms, status = identify_comet(options, elements, confidence=comet_conf,
                                            rms=comet_rms, logger=logger)
        if status:
            return (comet, rms, True)

    logger and logger.info('Testing minor planets')
    body, rms, status = identify_minor_planet(mp_options, elements, confidence=mp_conf,
                                              rms=mp_rms, logger=logger)
    if status:
        return (body, rms, True)

    if not try_comet:
        logger and logger.info('Testing comets')
        comet, rms, status = identify_comet(options, elements, confidence=comet_conf,
                                            rms=comet_rms, logger=logger)
        if status:
            return (comet, rms, True)

    return (None, 0., False)


__all__ = ['identify_small_body']

##########################################################################################
