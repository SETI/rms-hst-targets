##########################################################################################
# targets/__init__.pyi
#
# Typed public interface for the ``targets`` package. The implementation modules under
# ``targets/`` are intentionally left un-annotated (mypy excludes that tree); this stub
# supplies the types for anything imported as ``from targets import ...``. Names whose
# source is already annotated are re-exported with their real types; the un-annotated
# ``identify_*`` entry points are typed explicitly below.
#
# The ``orbital_radec`` helpers (RaDec, asteroid_radec, comet_radec,
# rotate_elements_to_j2000) are only present at runtime when the optional ``palpy``
# package is installed.
##########################################################################################

from logging import Logger

from targets.categorize_minor_planet import minor_planet_ttype as minor_planet_ttype
from targets.cometdb import centaur_dicts as centaur_dicts
from targets.cometdb import comet_dicts as comet_dicts
from targets.cometdb import query_centaur_by_name as query_centaur_by_name
from targets.cometdb import query_comet_by_elements as query_comet_by_elements
from targets.cometdb import query_comet_by_name as query_comet_by_name
from targets.cometdb import repair_comet as repair_comet
from targets.hst_repairs import hst_repairs as hst_repairs
from targets.identify_target import TargetIdentificationError as TargetIdentificationError
from targets.identify_target import identify_target as identify_target
from targets.orbital_radec import RaDec as RaDec
from targets.orbital_radec import asteroid_radec as asteroid_radec
from targets.orbital_radec import comet_radec as comet_radec
from targets.orbital_radec import rotate_elements_to_j2000 as rotate_elements_to_j2000
from targets.targettype import TargetType as TargetType

__all__ = [
    'RaDec',
    'TargetIdentificationError',
    'TargetType',
    'asteroid_radec',
    'centaur_dicts',
    'comet_dicts',
    'comet_radec',
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
    'rotate_elements_to_j2000',
]

def identify_small_body(
    strings: str | list[str] | None,
    elements: dict[str, float],
    *,
    comet_rms: float = ...,
    mp_rms: float = ...,
    logger: Logger | None = ...,
) -> tuple[dict | None, float, bool]: ...
def identify_comet(
    strings: str | list[str] | None,
    elements: dict[str, float] | None = ...,
    *,
    rms: float = ...,
    confidence: int = ...,
    logger: Logger | None = ...,
) -> tuple[dict | None, float, bool]: ...
def identify_minor_planet(
    strings: str | list[str] | None,
    elements: dict[str, float] | None = ...,
    *,
    rms: float = ...,
    confidence: int = ...,
    logger: Logger | None = ...,
) -> tuple[dict | None, float, bool]: ...

##########################################################################################
