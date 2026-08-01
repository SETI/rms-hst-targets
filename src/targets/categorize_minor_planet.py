##########################################################################################
# categorize_minor_planet.py
##########################################################################################
"""Refine the target type of a minor planet into asteroid, Centaur, TNO, or dwarf planet.
"""

import re

from targets._utils          import TargetCategorizationFailure
from targets.cometdb         import centaur_lookup, damocloid_lookup
from targets.standard_bodies import STANDARD_BODY_LOOKUP
from targets.targettype      import TargetType as TT

__all__ = ['categorize_minor_planet']

# A body with a semimajor axis at or beyond Neptune's is a trans-Neptunian object.
_TNO_MIN_SEMIMAJOR_AU = 30.03  # was 30.1

# From MPC, a body with perihelion beyond Jupiter's semimajor axis and a semimajor axis
# inside Neptune's is a Centaur
_CENTAUR_MIN_PERIHELION_AU = 5.2

# From JPL, a body with a semimajor axis between 5.5 and 30.1 AU is a Centaur
_CENTAUR_MIN_SEMIMAJOR_AU = 5.5

_COMET = re.compile(r'[1-9]\d?\d?[PDI](/.*)?')

_WORDS = {TT.CENTAUR: 'Centaur', TT.TNO: 'TNO', TT.ASTEROID: 'asteroid'}


def categorize_minor_planet(body, ttypes, *, logger=None):
    """Fill in the `ttype` if the given body is a minor planet.

    Parameters:
        body (dict): The body dictionary, modified in place.
        ttypes (list[str]): The target types suggested by the SPT file.
        logger (Logger, optional): A Logger for messages.

    Raises:
        TargetCategorizationFailure: If the body cannot be categorized.
    """

    if body['ttype'] != TT.MINOR_PLANET:
        return

    name = body.get('full_name') or body.get('name') or body.get('desig')  # for messages
    keys = [body.get('full_name', '').upper(), body.get('desig'), body.get('mnum')]
    # Don't include ['name'] here because 106 Dione -> ['ttype'] == "S"
    for key in keys:
        if key in STANDARD_BODY_LOOKUP:  # handles all dwarf planets, a few others
            body['ttype'] = STANDARD_BODY_LOOKUP[key]['ttype']
            return

    # Minor planet 2004 PY42 maps to 167P/CINEOS; there may be other examples
    if _COMET.fullmatch(name):  # can't be None
        logger and logger.info(f'"{name}" is a comet based on name')
        body['ttype'] = TT.COMET
        return

    # Check the damocloid database first
    damocloid_keys = [body.get('name', '').upper(), body.get('desig'), body.get('mnum')]
    for key in damocloid_keys:
        if key in damocloid_lookup():
            body['ttype'] = damocloid_lookup()[key]['ttype']
            word = _WORDS[body['ttype']]
            logger and logger.info(f'"{name}" is a {word} based on damocloid database')
            return

    ttypes = set(ttypes)

    # Categorize based on orbit
    centaur_candidate_by_elements = False
    a = body.get('A')
    q = body.get('Q')
    e = body.get('E')
    if e is not None and e < 1.:
        if a is None and q is not None:
            a = q / (1. - e)
        elif q is None and a is not None:
            q = a * (1. - e)

    if a is not None:
        if a >= _TNO_MIN_SEMIMAJOR_AU:
            body['ttype'] = TT.TRANS_NEPTUNIAN_OBJECT
            logger and logger.info(f'"{name}" is a TNO (a = {a:.2f} AU)')
            return
        if a < _CENTAUR_MIN_PERIHELION_AU:
            body['ttype'] = TT.ASTEROID
            logger and logger.info(f'"{name}" is an asteroid (a = {a:.2f} AU)')
            return

        if q is not None:
            test1 = a < _CENTAUR_MIN_SEMIMAJOR_AU   # JPL test
            test2 = q < _CENTAUR_MIN_PERIHELION_AU  # MPC test
            if test1 and test2:
                body['ttype'] = TT.ASTEROID
                logger and logger.info(f'"{name}" is an asteroid '
                                       f'(a = {a:.2f} AU; q = {q:.2f} AU)')
                return
            if not test1 and not test2:
                body['ttype'] = TT.CENTAUR
                logger and logger.info(f'"{name}" is a Centaur '
                                       f'(a = {a:.2f} AU; q = {q:.2f} AU)')
                return

        centaur_candidate_by_elements = True
        if q is None:
            logger and logger.info(f'"{name}" has a = {a:.2f} AU; q unknown')
        else:
            logger and logger.info(f'"{name}" has a = {a:.2f} AU; q = {q:.2f} AU')
        # Orbital elements are ambiguous!

    # Check Centaur database
    if 'name' in body:
        keys.append(body['name'].upper())
    for key in keys:
        if key in centaur_lookup():
            logger and logger.info(f'"{name}" is a Centaur from online database')
            body['ttype'] = TT.CENTAUR
            return
    if centaur_candidate_by_elements:
        logger and logger.info(f'"{name}" is not in the Centaur database')

    # Check SPT file info
    set1 = ttypes - {TT.DWARF_PLANET}
    set2 = ttypes - {TT.DWARF_PLANET, TT.ASTEROID}
    for test in (set1, set2):
        if test == {TT.TRANS_NEPTUNIAN_OBJECT}:
            body['ttype'] = TT.TRANS_NEPTUNIAN_OBJECT
            logger and logger.info(f'"{name}" is a TNO based on SPT file')
            return
        if test == {TT.CENTAUR}:
            body['ttype'] = TT.CENTAUR
            logger and logger.info(f'"{name}" is a Centaur based on SPT file')
            return
        if test == {TT.ASTEROID}:
            body['ttype'] = TT.ASTEROID
            logger and logger.info(f'"{name}" is an asteroid based on SPT file')
            return

    # SPT says it's both a TNO and a Centaur, but not an asteroid. Weird.
    logger and logger.error(f'"{name}" cannot be categorized from SPT file')
    raise TargetCategorizationFailure(f'"{name}" cannot be categorized based on '
                                      'SPT file')

##########################################################################################
