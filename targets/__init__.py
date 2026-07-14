##########################################################################################
# __init__.py
##########################################################################################
"""Top-level package re-exporting the primary identification API.

``from targets import *`` pulls in the high-level identification functions along with the
comet-database queries and the ``TargetType`` enum. The astrometry helpers in
``orbital_radec`` depend on ``palpy`` (an optional C-built package); they are imported
only when ``palpy`` is available, so ``import targets`` still works without it.
Lower-level helpers (``mpc_tools``, ``roman``, ``remote_listdir``) remain importable from
their own modules.
"""

from targets.categorize_minor_planet import minor_planet_ttype  # noqa: I001
from targets.cometdb import (centaur_dicts, comet_dicts, query_centaur_by_name,
                             query_comet_by_elements, query_comet_by_name, repair_comet)
from targets.hst_repairs import hst_repairs
from targets.identify_comet import identify_comet
from targets.identify_minor_planet import identify_minor_planet
from targets.identify_small_body import identify_small_body
from targets.identify_target import TargetIdentificationError, identify_target
from targets.targettype import TargetType

try:
    from targets.orbital_radec import RaDec, asteroid_radec, comet_radec, rotate_elements_to_j2000
except ImportError:
    _HAS_ORBITAL_RADEC = False
else:
    _HAS_ORBITAL_RADEC = True

__all__ = [
    'TargetIdentificationError',
    'TargetType',
    'centaur_dicts',
    'comet_dicts',
    'hst_repairs',
    'identify_comet',
    'identify_minor_planet',
    'identify_small_body',
    'identify_target',
    'minor_planet_ttype',
    'query_centaur_by_name',
    'query_comet_by_elements',
    'query_comet_by_name',
    'repair_comet',
]

if _HAS_ORBITAL_RADEC:
    __all__ += ['RaDec', 'asteroid_radec', 'comet_radec', 'rotate_elements_to_j2000']

##########################################################################################
