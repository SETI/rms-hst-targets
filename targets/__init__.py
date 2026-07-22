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

from targets.cometdb import (centaur_dict, centaur_lookup, comet_dict, comet_lookup,  # noqa: I001
                             query_centaur_by_name, query_comet_by_elements,
                             query_comet_by_name, repair_comet)
from targets.comet_identifiers import comet_identifiers
from targets.hst_repairs import hst_repairs
from targets.identify_standard_body import identify_standard_body
from targets.identify_targets import identify_target_dicts, identify_targets
from targets.minor_planet_identifiers import minor_planet_identifiers
from targets.targettype import TargetType
from targets._utils import TargetIdentificationFailure, categorize_minor_planet

try:
    from targets.orbital_radec import RaDec, asteroid_radec, comet_radec, rotate_elements_to_j2000
except ImportError:
    _HAS_ORBITAL_RADEC = False
else:
    _HAS_ORBITAL_RADEC = True

__all__ = [
    'TargetIdentificationFailure',
    'TargetType',
    'categorize_minor_planet',
    'centaur_dict',
    'centaur_lookup',
    'comet_dict',
    'comet_lookup',
    'comet_identifiers',
    'hst_repairs',
    'identify_standard_body',
    'identify_target_dicts',
    'identify_targets',
    'minor_planet_identifiers',
    'query_centaur_by_name',
    'query_comet_by_elements',
    'query_comet_by_name',
    'repair_comet',
]

if _HAS_ORBITAL_RADEC:
    __all__ += ['RaDec', 'asteroid_radec', 'comet_radec', 'rotate_elements_to_j2000']

##########################################################################################
