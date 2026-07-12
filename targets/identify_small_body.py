##########################################################################################
# identify_small_body.py
##########################################################################################

from logging import Logger

from targets._DISALLOWED_MINOR_PLANET_NAMES import _DISALLOWED_MINOR_PLANET_NAMES
from targets.hst_repairs import hst_repairs
from targets.identify_comet import comet_identifiers, identify_comet
from targets.identify_minor_planet import identify_minor_planet, minor_planet_identifiers
from targets.targettype import TargetType

__all__ = ['identify_small_body']

_DISALLOWED_UC = {name.upper() for name in _DISALLOWED_MINOR_PLANET_NAMES}


def identify_small_body(
    strings: list[str],
    elements: dict[str, float], *,
    comet_rms: float = 0.1,
    mp_rms: float = 0.08,
    logger: Logger | None = None
) -> tuple[dict | None, float, bool]:
    """Identify a comet or minor planet from name strings and orbital elements.

    Parameters:
        strings: One or more strings that potentially identify a small body, e.g., the
            values of the TARKEY*, TARGNAME, and TARDESCR keywords of an SPT/SHF header.
        elements: A dictionary of orbital elements keyed by element name, as follows:

            * "A": semimajor axis in AU.
            * "Q": perihelion distance in AU.
            * "I": inclination in degrees.
            * "O": ascending node in degrees.
            * "E": eccentricity.
            * "W": argument of pericenter in degrees.

            An empty dictionary if no orbital elements are available.
        comet_rms: Upper limit on the fractional root-mean-square discrepancy between the
            given orbital elements and those of a comet for the match to be accepted.
        mp_rms: Upper limit on the fractional root-mean-square discrepancy between the
            given orbital elements and those of a minor planet for the match to be
            accepted.
        logger: An optional Logger for messages.

    Returns:
        A tuple `(body, rms, valid)`:

        * `body`: A dictionary describing the attributes of the identified comet or minor
          planet; None if no body was identified.
        * `rms`: The fractional root-mean-square discrepancy between the orbital elements
          provided and those of the identified body; zero if no elements were compared.
        * `valid`: True if the identification is believed to be valid, based on the
          strings and the elements.
    """

    logger and logger.info('HST identification strings: ' + str(strings))

    options, types = hst_repairs(strings, logger=logger)
    maybe_minor = bool(set(TargetType.MCODES + TargetType.MINOR_PLANET) & set(types))
    maybe_comet = bool({TargetType.COMET, TargetType.CENTAUR} & set(types))

    # Names reserved for a satellite or comet never identify a minor planet unless the
    # header explicitly marks the target as one.
    mp_options = options
    if not maybe_minor:
        mp_options = [o for o in options if o.upper() not in _DISALLOWED_UC]
        excluded = [o for o in options if o.upper() in _DISALLOWED_UC]
        if excluded:
            logger and logger.info('Excluded from minor planet search: ' + str(excluded))

    _, _, comet_conf = comet_identifiers(options)
    _, _, mp_conf = minor_planet_identifiers(mp_options)

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

##########################################################################################
