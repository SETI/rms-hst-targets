##########################################################################################
# cometdb/query_comet_by_elements.py
##########################################################################################

from logging import Logger

from ._utils import comet_dicts
from targets.mpc_tools import element_resid


def query_comet_by_elements(
    elements: dict[str, float], *,
    count: int = 1,
    comets: list[dict] = [],
    fragments: bool = True,
    logger: Logger | None = None
) -> tuple[str, float] | list[tuple[str, float]]:
    """Identify an object in the comet database based on orbital elements.

    Parameters:
        elements: A dictionary containing any or all orbital elements keyed by element
            name, as follows:

            * "A": semimajor axis in AU.
            * "Q": perihelion distance in AU.
            * "I": inclination in degrees.
            * "O": ascending node in degrees.
            * "E": eccentricity.
            * "W": argument of pericenter in degrees.

        count: The maximum number of items to return. If 1, a single tuple (`key`, `rms`)
            is returned; otherwise, a list of `count` tuples is returned.
        comets: List of comet dictionaries to check; if the list is empty, every known
            comet is checked.
        fragments: True to include comet fragments among the matches; False to exclude
            fragments.
        logger: Optional Logger or PdsLogger for messages.

    Returns:
        A tuple (`comet`, `rms`) (if `count` == 1) or a list thereof. Here, `comet` is a
        dictionary of comet parameters and `rms` is the root-mean-square fractional
        discrepancy between the given `elements` and those in the database.
    """

    comet_dict = comet_dicts()[0]
    if not comets:
        comets = list(comet_dict.values())

    resids = []
    for comet in comets:
        if not fragments and comet.get('fragment', ''):
            continue
        rms, element_count = element_resid(elements, comet)
        if element_count >= 3:
            resids.append((rms, comet['key']))

    if not resids:
        logger and logger.warning('No comet found matching the given elements')
        return []

    resids.sort()
    rms, key = resids[0]
    logger and logger.info(f'Comet "{key}" found with orbit residual {rms:.4f}')

    if count == 1:
        return comet_dict[key], rms

    rms_list = ', '.join(['%.4f' % resid[0] for resid in resids[1:count]])
    logger and logger.info(f'Next-best orbit residuals: [{rms_list}]')
    pairs = []
    for resid in resids[:count]:
        rms, key = resid
        pairs.append((comet_dict[key], rms))

    return pairs

##########################################################################################
