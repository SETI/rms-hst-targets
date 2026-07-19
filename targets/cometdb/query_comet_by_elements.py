##########################################################################################
# cometdb/query_comet_by_elements.py
##########################################################################################

from logging import Logger

from targets.mpc_tools import element_resid

from ._utils import comet_dict


def query_comet_by_elements(elements, *, count=1, comets=None, fragments=True,
                            logger=None):
    """Identify an object in the comet database based on orbital elements.

    Parameters:
        elements dict[str, float]: A dictionary containing any or all orbital elements
            keyed by element name, as follows:

            * "A": semimajor axis in AU.
            * "Q": perihelion distance in AU.
            * "I": inclination in degrees.
            * "O": ascending node in degrees.
            * "E": eccentricity.
            * "W": argument of pericenter in degrees.

        count (int, optional): The maximum number of items to return. If 1, a single tuple
            `(key, rms)` is returned; otherwise, a list of up to `count` tuples is
            returned.
        comets (list[dict], optional): List of comet dictionaries to check; if the list
            is empty, every known comet is checked.
        fragments (bool, optional): True to include comet fragments among the matches;
            False to exclude fragments.
        logger (PdsLogger, optional): PdsLogger for messages.

    Returns:
        tuple or list[tuple]: A tuple (`body`, `rms`) if `count` == 1; otherwise a list
        of up to `count` of these tuples.

            * `body` (dict): Dictionary of body parameters.
            * `rms` (float): The root-mean-square fractional discrepancy between the given
              `elements` and those in the database.
    """

    comets_by_key = comet_dict()
    if not comets:
        comets = list(comets_by_key.values())

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
        return comets_by_key[key], rms

    rms_list = ', '.join([f'{resid[0]:.4f}' for resid in resids[1:count]])
    logger and logger.info(f'Next-best orbit residuals: [{rms_list}]')
    pairs = []
    for resid in resids[:count]:
        rms, key = resid
        pairs.append((comets_by_key[key], rms))

    return pairs


__all__ = ['query_comet_by_elements']

##########################################################################################
