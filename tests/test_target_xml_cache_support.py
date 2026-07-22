##########################################################################################
# tests/test_target_xml_cache_support.py
##########################################################################################
"""Tests for reading a target context product out of the committed TARGET_XML_CACHE.

These read only the on-disk cache (caches/TARGET_XML_CACHE); no network access.
"""

from targets.target_xml_cache_support import target_xml_dict, target_xml_lookup
from targets.targettype import TargetType


def test_target_xml_lookup_loads_and_contains_known_key() -> None:
    lookup = target_xml_lookup()
    assert isinstance(lookup, dict)
    assert 'JUPITER' in lookup


def test_target_xml_dict_planet() -> None:
    target = target_xml_dict('JUPITER')
    assert target is not None
    assert target['lid'] == 'urn:nasa:pds:context:target:planet.jupiter'
    assert target['lid_tail'] == 'planet.jupiter'
    assert target['title'] == 'Jupiter'
    assert target['type_name'] == 'Planet'
    assert target['ttype'] == TargetType.PLANET
    assert isinstance(target['version_id'], str)
    assert target['version_id']
    assert isinstance(target['alt_titles'], list)
    assert isinstance(target['description'], list)
    assert target['xml_path'].exists()
    assert 'jupiter' in target['xml_path'].name


def test_target_xml_dict_astrophysical_types() -> None:
    # Galaxy and Star Cluster context products were previously unresolvable (their type
    # names were missing from TargetType); target_xml_dict must now handle them.
    galaxy = target_xml_dict('Andromeda')
    assert galaxy is not None
    assert galaxy['ttype'] == TargetType.GALAXY
    assert galaxy['type_name'] == 'Galaxy'

    cluster = target_xml_dict('NGC 3532')
    assert cluster is not None
    assert cluster['ttype'] == TargetType.STAR_CLUSTER
    assert cluster['type_name'] == 'Star Cluster'


def test_target_xml_dict_derives_ttype_from_type_name() -> None:
    # The "ttype" code is recovered from the XML "type" text via TargetType.LOOKUP.
    assert target_xml_dict('1 CERES')['ttype'] == TargetType.DWARF_PLANET
    assert target_xml_dict('101955 BENNU')['ttype'] == TargetType.ASTEROID


def test_target_xml_dict_satellite_has_multiline_description() -> None:
    target = target_xml_dict('IO')
    assert target is not None
    assert target['ttype'] == TargetType.SATELLITE
    assert target['lid_tail'] == 'satellite.jupiter.io'
    # Io's context product carries a non-empty, per-line description.
    assert target['description']
    assert all(isinstance(line, str) and line for line in target['description'])


def test_target_xml_dict_key_is_case_insensitive() -> None:
    assert target_xml_dict('jupiter') == target_xml_dict('JUPITER')


def test_target_xml_dict_missing_returns_none() -> None:
    assert target_xml_dict('NO SUCH TARGET ZZZZZ') is None

##########################################################################################
