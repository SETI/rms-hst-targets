##########################################################################################
# tests/test_target_xml_cache_support.py
##########################################################################################
"""Tests for reading a target context product out of the committed TARGET_XML_CACHE.

These read only the on-disk cache (caches/TARGET_XML_CACHE); no network access.
"""

import pathlib
import shutil

import pytest

from targets import target_xml_cache_support
from targets.target_xml_cache_support import target_xml_dict, target_xml_lookup
from targets.targettype import TargetType

_LOCAL_XML = (
    '<?xml version="1.0"?>\n'
    '<Product_Context><Identification_Area>'
    '<logical_identifier>urn:nasa:pds:context:target:asteroid.9999_testbody'
    '</logical_identifier><version_id>1.0</version_id>'
    '<title>9999 Testbody</title></Identification_Area>'
    '<Target><name>9999 Testbody</name><alternate_title>Testbody</alternate_title>'
    '<type>Asteroid</type><description>none</description></Target>'
    '</Product_Context>'
)


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


def test_local_overlay_isolates_writes_from_committed_cache(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Point the "committed" cache at a tiny primary (a couple of real Engineering Node
    # files) so the rebuild is fast and hermetic, then build its $LOOKUP.pickle offline.
    real_cache = target_xml_cache_support._TARGET_XML_CACHE
    primary = tmp_path / 'primary'
    overlay = tmp_path / 'overlay'
    primary.mkdir()
    for pattern in ('planet.jupiter_*.xml', 'satellite.jupiter.io_*.xml'):
        for src in real_cache.glob(pattern):
            shutil.copy(src, primary / src.name)

    monkeypatch.setattr(target_xml_cache_support, '_TARGET_XML_CACHE', primary)
    monkeypatch.setattr(target_xml_cache_support, '_TARGET_XML_LOOKUP', None)
    target_xml_cache_support._update_target_cache(offline=True, warn_on_duplicates=False)

    committed_pickle = primary / '$LOOKUP.pickle'
    committed_before = committed_pickle.read_bytes()
    assert target_xml_cache_support.target_xml_path('JUPITER').parent == primary

    with target_xml_cache_support.use_local_xml_dir(overlay):
        (overlay / 'asteroid.9999_testbody_1.0_local.xml').write_text(_LOCAL_XML)
        target_xml_cache_support._update_target_cache(offline=True, warn_on_duplicates=False)

        # The merged lookup lives in the overlay; the committed pickle is untouched.
        assert (overlay / '$LOOKUP.pickle').exists()
        assert committed_pickle.read_bytes() == committed_before

        # Reads span both dirs: the EN body from the primary, the local body from overlay.
        assert target_xml_cache_support.target_xml_path('JUPITER').parent == primary
        assert target_xml_cache_support.target_xml_path('TESTBODY').parent == overlay
        assert target_xml_dict('9999')['ttype'] == TargetType.ASTEROID

    # Leaving the context disables the overlay; the local body is no longer visible.
    assert target_xml_cache_support._LOCAL_XML_DIR is None
    assert target_xml_cache_support.target_xml_path('TESTBODY') is None
    assert target_xml_cache_support.target_xml_path('JUPITER').parent == primary


##########################################################################################
