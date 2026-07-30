##########################################################################################
# categorize_minor_planet.py
##########################################################################################
"""Refine the target type of a minor planet into asteroid, Centaur, TNO, or dwarf planet.
"""

from targets._utils          import TargetCategorizationFailure
from targets.cometdb         import centaur_lookup
from targets.standard_bodies import STANDARD_BODY_LOOKUP
from targets.targettype      import TargetType

__all__ = ['categorize_minor_planet']

# A body with a semimajor axis at or beyond Neptune's is a trans-Neptunian object.
_TNO_BOUNDARY_AU = 30.1

# A body with perihelion beyond Jupiter's semimajor axis and a semimajor axis inside
# Neptune's is a Centaur (the standard JPL/MPC working definition).
_CENTAUR_PERIHELION_AU = 5.2


def categorize_minor_planet(body, ttypes, *, logger=None):
    """Fill in the `ttype` if the given body is a minor planet.

    Parameters:
        body (dict): The body dictionary, modified in place.
        ttypes (list[str]): The target types suggested by the SPT file.
        logger (Logger, optional): A Logger for messages.

    Raises:
        TargetCategorizationFailure: If the body cannot be categorized.
    """

    if body['ttype'] != TargetType.MINOR_PLANET:
        return

    name = body.get('full_name') or body.get('name') or body.get('desig')  # for messages
    keys = [body.get('full_name'), body.get('desig'), body.get('mnum')]
    keys = [k.upper() for k in keys if k]
    # Don't include ['name'] here because 106 Dione -> ['ttype'] == "S"
    for key in keys:
        if key in STANDARD_BODY_LOOKUP:  # handles all dwarf planets, a few others
            body['ttype'] = STANDARD_BODY_LOOKUP[key]['ttype']
            return

    ttypes = set(ttypes)

    # Categorize based on orbit
    a = body.get('A')
    q = body.get('Q')
    e = body.get('E')
    if e is not None and e < 1.:
        if a is None and q is not None:
            a = q / (1. - e)
        elif q is None and a is not None:
            q = a * (1. - e)

    # Without an orbit...
    if a is None:
        # Check Centaur database
        if 'name' in body:
            keys.append(body['name'].upper())
        for key in keys:
            if key in centaur_lookup():
                logger and logger.debug(f'"{name}" is a Centaur from online database')
                body['ttype'] = TargetType.CENTAUR
                return

        # Check SPT file info
        set1 = ttypes - {TargetType.DWARF_PLANET}
        set2 = ttypes - {TargetType.DWARF_PLANET, TargetType.ASTEROID}
        for test in (set1, set2):
            if test == {TargetType.TRANS_NEPTUNIAN_OBJECT}:
                body['ttype'] = TargetType.TRANS_NEPTUNIAN_OBJECT
                logger and logger.debug(f'"{name}" is a TNO based on SPT file')
                return
            elif test == {TargetType.CENTAUR}:
                body['ttype'] = TargetType.CENTAUR
                logger and logger.debug(f'"{name}" is a Centaur based on SPT file')
                return
            elif test == {TargetType.ASTEROID}:
                body['ttype'] = TargetType.ASTEROID
                logger and logger.debug(f'"{name}" is an asteroid based on SPT file')
                return

        # SPT says it's both a TNO and a Centaur, but not an asteroid. Weird.
        logger and logger.error(f'"{name}" cannot be categorized from SPT file')
        raise TargetCategorizationFailure(f'"{name}" cannot be categorized based on '
                                          'SPT file')

    # Use orbit info
    if a >= _TNO_BOUNDARY_AU:
        body['ttype'] = TargetType.TRANS_NEPTUNIAN_OBJECT
        logger and logger.debug(f'"{name}" is a TNO (a = {a:.2f} AU)')
    elif q is None and a < _CENTAUR_PERIHELION_AU:
        body['ttype'] = TargetType.ASTEROID
        logger and logger.debug(f'"{name}" is an asteroid (a = {a:.2f} AU)')
    elif q is None:
        logger and logger.error(f'"{name}" cannot be categorized')
        raise TargetCategorizationFailure(f'"{name}" cannot be categorized due to '
                                          'missing elements')
    elif q > _CENTAUR_PERIHELION_AU:
        body['ttype'] = TargetType.CENTAUR
        logger and logger.debug(f'"{name}" is a Centaur '
                                f'(a = {a:.2f} AU; q = {q:.2f} AU)')
    else:
        body['ttype'] = TargetType.ASTEROID
        logger and logger.debug(f'"{name}" is an asteroid '
                                f'(a = {a:.2f} AU; q = {q:.2f} AU)')

##########################################################################################
