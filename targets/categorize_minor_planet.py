##########################################################################################
# categorize_minor_planet.py
##########################################################################################
"""Assign the correct TargetType to a minor planet.

The MPC does not distinguish among asteroids, Centaurs, trans-Neptunian objects, and
dwarf planets, so body dictionaries returned by `mpc_tools.mpc_query_by_name` and
`mpc_tools.mpc_query_by_elements` carry the generic code TargetType.MINOR_PLANET ("M").
This module determines the specific category from the most reliable sources available:
the IAU dwarf planet list, the Centaur database, and the body's own orbital elements.

To use::

    from targets.categorize_minor_planet import minor_planet_ttype

"""

from logging import Logger

from targets import cometdb
from targets.standard_bodies import STANDARD_BODY_DICT
from targets.targettype import TargetType

__all__ = ['minor_planet_ttype']

# A body with a semimajor axis at or beyond Neptune's is a trans-Neptunian object.
_TNO_BOUNDARY_AU = 30.1

# A body with perihelion beyond Jupiter's semimajor axis and a semimajor axis inside
# Neptune's is a Centaur (the standard JPL/MPC working definition).
_CENTAUR_PERIHELION_AU = 5.2

# The IAU dwarf planets, drawn from the standard body list.
_DWARF_PLANET_MNUMS = {str(body['mnum']) for body in STANDARD_BODY_DICT.values()
                       if body['ttype'] == TargetType.DWARF_PLANET and 'mnum' in body}
_DWARF_PLANET_NAMES = {body['name'].upper() for body in STANDARD_BODY_DICT.values()
                       if body['ttype'] == TargetType.DWARF_PLANET}


def minor_planet_ttype(
    body: dict, *,
    hints: str = '',
    logger: Logger | None = None
) -> str:
    """Determine the TargetType code for a minor planet.

    Parameters:
        body: A dictionary of minor planet parameters as returned by
            `mpc_tools.mpc_body_dict`, containing at least one of "name", "mnum", or
            "desig", and optionally the orbital elements "A", "Q", and "E".
        hints: An optional string of single-letter TargetType codes derived from the
            words of the HST target description (see `hst_repairs`). These are used only
            as a tiebreaker when no orbital elements are available; a contradiction with
            the category derived here is reported as a warning, because HST headers
            sometimes mislabel their targets.
        logger: An optional Logger for messages.

    Returns:
        One of TargetType.ASTEROID ("A"), TargetType.CENTAUR ("H"),
        TargetType.DWARF_PLANET ("D"), or TargetType.TRANS_NEPTUNIAN_OBJECT ("T").
    """

    name = body.get('name', '')
    mnum = str(body.get('mnum', '') or '')
    desig = body.get('desig', '')
    label = body.get('full_name', '') or name or desig or mnum

    ttype = ''

    # 1. The IAU dwarf planets are a fixed list
    if (mnum and mnum in _DWARF_PLANET_MNUMS) or name.upper() in _DWARF_PLANET_NAMES:
        logger and logger.info(f'"{label}" is a dwarf planet')
        ttype = TargetType.DWARF_PLANET

    # 2. Anything in the Centaur database is a Centaur
    if not ttype:
        for key in (name, mnum, desig):
            if key and cometdb.query_centaur_by_name(key):
                logger and logger.info(f'"{label}" is in the Centaur database')
                ttype = TargetType.CENTAUR
                break

    # 3. Otherwise, categorize by the orbital elements
    if not ttype:
        a = body.get('A')
        q = body.get('Q')
        e = body.get('E')
        if a is None and None not in (q, e) and e < 1.:
            a = q / (1. - e)
        if q is None and None not in (a, e):
            q = a * (1. - e)

        if a is not None:
            if a >= _TNO_BOUNDARY_AU:
                logger and logger.info(f'"{label}" is a trans-Neptunian object '
                                       f'(a = {a:.2f} AU)')
                ttype = TargetType.TRANS_NEPTUNIAN_OBJECT
            elif q is not None and q > _CENTAUR_PERIHELION_AU:
                logger and logger.info(f'"{label}" is a Centaur '
                                       f'(q = {q:.2f} AU, a = {a:.2f} AU)')
                ttype = TargetType.CENTAUR
            else:
                logger and logger.info(f'"{label}" is an asteroid (a = {a:.2f} AU)')
                ttype = TargetType.ASTEROID

    hint_codes = []
    for letter in hints:
        if letter in TargetType.MCODES and letter not in hint_codes:
            hint_codes.append(letter)

    # 4. Without elements, fall back on the target description
    if not ttype:
        if hint_codes:
            ttype = hint_codes[0]
            logger and logger.info(f'"{label}" categorized as '
                                   f'{TargetType.NAME[ttype]} by the target description')
        else:
            logger and logger.warning(f'No basis to categorize "{label}"; '
                                      'defaulting to asteroid')
            ttype = TargetType.ASTEROID
    elif hint_codes and ttype not in hint_codes:
        names = [TargetType.NAME[code] for code in hint_codes]
        logger and logger.warning(f'"{label}" is categorized as {TargetType.NAME[ttype]} '
                                  f'but the target description says {names}')

    return ttype

##########################################################################################
