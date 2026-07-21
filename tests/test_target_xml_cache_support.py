##########################################################################################
# tests/test_target_xml_cache_support.py
##########################################################################################
"""Tests for reading a target context product out of the committed TARGET_XML_CACHE.

These read only the on-disk cache (caches/TARGET_XML_CACHE); no network access.
"""

from targets.target_xml_cache_support import read_target_xml, target_xml_lookup
from targets.targettype import TargetType


def test_target_xml_lookup_loads_and_contains_known_key() -> None:
    lookup = target_xml_lookup()
    assert isinstance(lookup, dict)
    assert 'JUPITER' in lookup


def test_read_target_xml_planet() -> None:
    target = read_target_xml('JUPITER')
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


def test_read_target_xml_astrophysical_types() -> None:
    # Galaxy and Star Cluster context products were previously unresolvable (their type
    # names were missing from TargetType); read_target_xml must now handle them.
    galaxy = read_target_xml('Andromeda')
    assert galaxy is not None
    assert galaxy['ttype'] == TargetType.GALAXY
    assert galaxy['type_name'] == 'Galaxy'

    cluster = read_target_xml('NGC 3532')
    assert cluster is not None
    assert cluster['ttype'] == TargetType.STAR_CLUSTER
    assert cluster['type_name'] == 'Star Cluster'


def test_read_target_xml_derives_ttype_from_type_name() -> None:
    # The "ttype" code is recovered from the XML "type" text via TargetType.LOOKUP.
    assert read_target_xml('1 CERES')['ttype'] == TargetType.DWARF_PLANET
    assert read_target_xml('101955 BENNU')['ttype'] == TargetType.ASTEROID


def test_read_target_xml_satellite_has_multiline_description() -> None:
    target = read_target_xml('IO')
    assert target is not None
    assert target['ttype'] == TargetType.SATELLITE
    assert target['lid_tail'] == 'satellite.jupiter.io'
    # Io's context product carries a non-empty, per-line description.
    assert target['description']
    assert all(isinstance(line, str) and line for line in target['description'])


def test_read_target_xml_key_is_case_insensitive() -> None:
    assert read_target_xml('jupiter') == read_target_xml('JUPITER')


def test_read_target_xml_missing_returns_none() -> None:
    assert read_target_xml('NO SUCH TARGET ZZZZZ') is None

##########################################################################################
