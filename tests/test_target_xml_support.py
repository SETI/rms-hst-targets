##########################################################################################
# tests/test_target_xml_support.py
##########################################################################################
"""Tests for targets.target_xml_support: filling in the PDS-context fields (title, LID,
parent, alt_titles, description) of a target dictionary produced by the identification
code.
"""

import copy
import pathlib
from typing import Any

import pytest

from targets import target_xml_cache_support
from targets.standard_bodies import STANDARD_BODY_DICT
from targets.target_xml_support import _complete_target, _lid_tail, get_target_xml_path
from targets.targettype import TargetType

# An existing context product with two aliases (AliasA, AliasB) and a "none" description.
_EXISTING_XML = """<?xml version='1.0' encoding='UTF-8'?>
<Product_Context xmlns="http://pds.nasa.gov/pds4/pds/v1">
  <Identification_Area>
    <logical_identifier>urn:nasa:pds:context:target:asteroid.9999_testbody</logical_identifier>
    <version_id>1.1</version_id>
    <title>9999 Testbody</title>
    <information_model_version>1.22.0.0</information_model_version>
    <product_class>Product_Context</product_class>
    <Alias_List>
      <Alias><alternate_title>AliasA</alternate_title></Alias>
      <Alias><alternate_title>AliasB</alternate_title></Alias>
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


def _body(key: str) -> dict[str, Any]:
    """A private, deep copy of one standard-body dictionary, safe to modify."""

    return copy.deepcopy(STANDARD_BODY_DICT[key])


def _install_existing_product(tmp_path: pathlib.Path,
                              monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """Set up a monkeypatched committed cache holding _EXISTING_XML; return its path."""

    primary = tmp_path / 'primary'
    primary.mkdir()
    (primary / 'asteroid.9999_testbody_1.1.xml').write_text(_EXISTING_XML)
    monkeypatch.setattr(target_xml_cache_support, '_TARGET_XML_CACHE', primary)
    monkeypatch.setattr(target_xml_cache_support, '_TARGET_XML_LOOKUP', None)
    target_xml_cache_support._update_target_cache(offline=True, warn_on_duplicates=False)
    return primary


def _asteroid_body(alt_titles: list[str]) -> dict[str, Any]:
    return {'lid': 'urn:nasa:pds:context:target:asteroid.9999_testbody',
            'lid_tail': 'asteroid.9999_testbody', 'title': '9999 Testbody',
            'alt_titles': alt_titles, 'ttype': TargetType.ASTEROID, 'description': 'none'}


def test_get_target_xml_path_updates_when_body_adds_an_alias(
        tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: a body whose aliases are a superset of the file's (a new alias to add,
    # none removed) must route to update_target_xml_dict and return the new path. The old
    # routing keyed on old_alts - new_alts, so it returned None and dropped the alias.
    _install_existing_product(tmp_path, monkeypatch)
    overlay = tmp_path / 'overlay'
    body = _asteroid_body(['AliasA', 'AliasB', 'AliasC'])    # AliasC is new
    with target_xml_cache_support.use_local_xml_dir(overlay):
        path = get_target_xml_path(body)
        assert path == overlay / 'asteroid.9999_testbody_1.2_local.xml'
        parsed = target_xml_cache_support._read_target_xml_dict(path)
        assert 'AliasC' in parsed['alt_titles']


def test_get_target_xml_path_no_op_when_nothing_to_add(
        tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Nothing to add (the body's aliases are already present, even when the file has extras
    # the body lacks): the existing file is returned unchanged -- no pointless new version.
    primary = _install_existing_product(tmp_path, monkeypatch)
    existing = primary / 'asteroid.9999_testbody_1.1.xml'
    overlay = tmp_path / 'overlay'
    with target_xml_cache_support.use_local_xml_dir(overlay):
        assert get_target_xml_path(_asteroid_body(['AliasA', 'AliasB'])) == existing
        assert get_target_xml_path(_asteroid_body(['AliasA'])) == existing


def test_complete_target_planet() -> None:
    # A planet is not parent-prefixed: its system ("planet_system") must never appear in
    # the LID of anything but a planetary_system target.
    target = _complete_target(_body('Uranus'))
    assert target['type_name'] == 'Planet'
    assert target['title'] == 'Uranus'
    assert target['lid_tail'] == 'planet.uranus'
    assert target['lid'] == 'urn:nasa:pds:context:target:planet.uranus'
    assert '_system' not in target['lid_tail']
    assert target['parent']['name'] == 'Uranus System'   # set, but not used in the LID
    assert 'NAIF ID 799' in target['alt_titles']
    assert isinstance(target['description'], str)
    assert target['description']


def test_complete_target_satellite() -> None:
    target = _complete_target(_body('Io'))
    assert target['type_name'] == 'Satellite'
    assert target['ttype'] == TargetType.SATELLITE
    assert target['lid_tail'] == 'satellite.jupiter.io'
    assert target['parent']['name'] == 'Jupiter'
    assert 'NAIF ID 501' in target['alt_titles']


def test_complete_target_ring() -> None:
    target = _complete_target(_body('Saturn Rings'))
    assert target['type_name'] == 'Ring'
    assert target['lid_tail'] == 'ring.saturn.saturn_rings'
    assert target['parent']['name'] == 'Saturn'
    assert target['description'].startswith('Ring of: Saturn;')


def test_complete_target_trans_neptunian_object() -> None:
    # _complete_target fills the PDS fields of an already-categorized minor planet; the
    # identification core categorizes minor planets, _complete_target no longer does. A TNO
    # has no parent and description "none".
    tno = {'name': '', 'full_name': '1999 XY99', 'desig': '1999 XY99',
           'aliases': [], 'mnum': '', 'ttype': TargetType.TRANS_NEPTUNIAN_OBJECT,
           'parent_key': ''}
    target = _complete_target(tno)
    assert target['type_name'] == 'Trans-Neptunian Object'
    assert target['title'] == '1999 XY99'
    assert target['lid_tail'] == 'trans-neptunian_object.1999_xy99'
    assert target['parent'] is None
    assert target['description'] == 'none'


def test_complete_target_alt_titles_from_number_and_naif() -> None:
    asteroid = {'name': 'Fake', 'full_name': '99999 Fake', 'aliases': ['Alias A'],
                'mnum': '99999', 'naif_id': 2099999, 'ttype': TargetType.ASTEROID,
                'parent_key': ''}
    target = _complete_target(asteroid)
    assert target['alt_titles'] == ['Alias A', 'Minor Planet 99999', 'NAIF ID 2099999']
    assert target['lid_tail'] == 'asteroid.99999_fake'


def test_complete_target_respects_existing_description() -> None:
    body = _body('Io')
    body['description'] = 'preset'
    assert _complete_target(body)['description'] == 'preset'


def test_lid_tail_comet_variants() -> None:
    # A numbered comet: "1P/Halley" -> slash to space to underscore, with the type prefix.
    assert _lid_tail({'full_name': '1P/Halley', 'ttype': TargetType.COMET}) \
        == 'comet.1p_halley'
    # A provisional comet: the slash after the leading letter is dropped.
    assert _lid_tail({'full_name': 'C/2007 N3', 'ttype': TargetType.COMET}) \
        == 'comet.c2007_n3'


def test_lid_tail_provisional_satellite() -> None:
    # "S/2003 J 5" -> slashes and spaces stripped, prefixed by the parent planet.
    target = {'full_name': 'S/2003 J 5', 'ttype': TargetType.SATELLITE,
              'parent': {'full_name': 'Jupiter'}}
    assert _lid_tail(target) == 'satellite.jupiter.s2003j5'

##########################################################################################
