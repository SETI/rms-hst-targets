##########################################################################################
# tests/test_target_xml_cache_support.py
##########################################################################################
"""Tests for reading a target context product out of the committed TARGET_XML_CACHE.

These read only the on-disk cache (caches/TARGET_XML_CACHE); no network access.
"""

import inspect
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

# A realistically-formatted existing context product (Alias_List, Modification_History, and
# a "none" Target description), for exercising update_target_xml_dict.
_EXISTING_XML = """<?xml version='1.0' encoding='UTF-8'?>
<Product_Context xmlns="http://pds.nasa.gov/pds4/pds/v1">
  <Identification_Area>
    <logical_identifier>urn:nasa:pds:context:target:asteroid.9999_testbody</logical_identifier>
    <version_id>1.1</version_id>
    <title>9999 Testbody</title>
    <information_model_version>1.22.0.0</information_model_version>
    <product_class>Product_Context</product_class>
    <Alias_List>
      <Alias>
        <alternate_title>Testbody</alternate_title>
      </Alias>
    </Alias_List>
    <Modification_History>
      <Modification_Detail>
        <modification_date>2025-04-24</modification_date>
        <version_id>1.1</version_id>
        <description>Updated schema version.</description>
      </Modification_Detail>
    </Modification_History>
  </Identification_Area>
  <Target>
    <name>9999 Testbody</name>
    <type>Asteroid</type>
    <description>none</description>
  </Target>
</Product_Context>
"""


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


def test_overlay_dir_is_hardwired_to_caches() -> None:
    # The overlay is hard-wired to caches/TARGET_XML_OVERLAY and is the default target of
    # use_local_xml_dir(). (Checked without entering the context, so no directory is made.)
    assert (
        target_xml_cache_support._TARGET_XML_CACHE.parent / 'TARGET_XML_OVERLAY'
        == target_xml_cache_support._TARGET_XML_OVERLAY
    )
    default = (
        inspect.signature(target_xml_cache_support.use_local_xml_dir).parameters['path'].default
    )
    assert default == target_xml_cache_support._TARGET_XML_OVERLAY


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


def test_new_target_xml_dict_generates_valid_label(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Regression: the PdsTemplate refers to the body as `target`, so new_target_xml_dict
    # must nest the dict under that key; otherwise it raises NameError and writes a broken
    # label. The generated "_local" label must be well-formed and read back cleanly.
    primary = tmp_path / 'primary'
    overlay = tmp_path / 'overlay'
    primary.mkdir()
    monkeypatch.setattr(target_xml_cache_support, '_TARGET_XML_CACHE', primary)
    monkeypatch.setattr(target_xml_cache_support, '_TARGET_XML_LOOKUP', None)

    body = {
        'lid': 'urn:nasa:pds:context:target:comet.c9999_test',
        'lid_tail': 'comet.c9999_test',
        'title': 'C/9999 Test',
        'alt_titles': ['Test', 'NAIF ID 1009999'],
        'type_name': 'Comet',
        'ttype': TargetType.COMET,
        'description': [],  # a list of strings; empty means "none"
    }
    with target_xml_cache_support.use_local_xml_dir(overlay):
        path = target_xml_cache_support.new_target_xml_dict(body)
        assert path == overlay / 'comet.c9999_test_1.0_local.xml'
        assert path.exists()

        parsed = target_xml_cache_support._read_target_xml_dict(path)
        assert parsed['lid'] == body['lid']
        assert parsed['title'] == body['title']
        assert parsed['alt_titles'] == body['alt_titles']
        assert parsed['type_name'] == 'Comet'
        assert parsed['ttype'] == TargetType.COMET
        # A "none" description renders as the bare sentinel, not a wrapped "none".
        assert '<description>none</description>' in path.read_text()
        assert parsed['description'] == []


def test_update_target_xml_dict_produces_valid_label(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Regression: adding an alias to an existing product must produce well-formed XML.
    # Previously the modification note injected literal <alternate_title>/<description>
    # markup, and a "none" description was iterated character-by-character.
    primary = tmp_path / 'primary'
    overlay = tmp_path / 'overlay'
    primary.mkdir()
    (primary / 'asteroid.9999_testbody_1.1.xml').write_text(_EXISTING_XML)
    monkeypatch.setattr(target_xml_cache_support, '_TARGET_XML_CACHE', primary)
    monkeypatch.setattr(target_xml_cache_support, '_TARGET_XML_LOOKUP', None)
    target_xml_cache_support._update_target_cache(offline=True, warn_on_duplicates=False)

    body = {
        'lid': 'urn:nasa:pds:context:target:asteroid.9999_testbody',
        'lid_tail': 'asteroid.9999_testbody',
        'title': '9999 Testbody',
        'alt_titles': ['Testbody', '2001 XY99'],  # "2001 XY99" is a genuinely new alias
        'type_name': 'Asteroid',
        'ttype': TargetType.ASTEROID,
        'description': [],
    }
    with target_xml_cache_support.use_local_xml_dir(overlay):
        path = target_xml_cache_support.update_target_xml_dict(body)
        assert path == overlay / 'asteroid.9999_testbody_1.2_local.xml'

        parsed = target_xml_cache_support._read_target_xml_dict(path)  # parses => valid XML
        assert parsed['version_id'] == '1.2'
        assert '2001 XY99' in parsed['alt_titles']
        assert parsed['description'] == []  # Target description stays "none"

        raw = path.read_text()
        assert "<description>RMS Node's HST pipeline added alternate_title.</description>" in raw
        assert '<alternate_title>2001 XY99</alternate_title>' in raw


##########################################################################################
