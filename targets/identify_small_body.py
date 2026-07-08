##########################################################################################
# identify_small_body.py
##########################################################################################

from logging import Logger

from targets.identify_minor_planet import identify_minor_planet, minor_planet_identifiers
from targets.identify_comet import identify_comet, comet_identifiers
from targets.hst_repairs import hst_repairs


def identify_small_body(
    strings: list[str],
    elements: dict[str, float], *,
    comet_rms: float = 0.1,
    mp_rms: float = 0.08,
    logger: Logger | None = None
) -> tuple[dict | None, float, bool]:

    logger and logger.info('HST identification strings: ' + str(strings))

    options = hst_repairs(strings)
    maybe_minor = ('[M]' in options or '[T]' in options or '[H]' in options
                   or '[A]' in options or ['D'] in options)
    maybe_comet = ('[C]' in options or '[H]' in options)
    options = [o for o in options if o[0] != '[']
    options = list(set(options))  # remove duplicates

    cwords, cunused, comet_conf = comet_identifiers(options)
    mwords, munused, mp_conf = minor_planet_identifiers(options)

    try_comet = maybe_comet or not maybe_minor or comet_conf >= mp_conf
    if try_comet:
        logger and logger.info('Testing comets')
        comet_info = identify_comet(options, elements, confidence=comet_conf,
                                    rms=comet_rms, logger=logger)
        (comet, comet_rms, comet_status) = comet_info
        if comet_status:
            return comet

    logger and logger.info('Testing minor planets')
    minor_planet_info = identify_minor_planet(options, elements, confidence=mp_conf,
                                              rms=mp_rms, logger=logger)
    (minor_planet, mp_rms, mp_status) = minor_planet_info
    if mp_status:
        return minor_planet

    if not try_comet:
        logger and logger.info('Testing comets')
        comet_info = identify_comet(options, elements, confidence=comet_conf,
                                    rms=comet_rms, logger=logger)
        (comet, comet_rms, comet_status) = comet_info
        if comet_status:
            return comet

    return None

##########################################################################################
