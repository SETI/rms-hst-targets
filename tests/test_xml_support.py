##########################################################################################
# tests/test_xml_support.py
##########################################################################################
"""Tests for targets.xml_support: filling in the PDS-context fields (title, LID, parent,
alt_titles, description) of a target dictionary produced by the identification code.
"""

import copy
from typing import Any

from targets.standard_bodies import STANDARD_BODY_DICT
from targets.targettype import TargetType
from targets.xml_support import _complete_target, _lid_tail


def _body(key: str) -> dict[str, Any]:
    """A private, deep copy of one standard-body dictionary, safe to modify."""

    return copy.deepcopy(STANDARD_BODY_DICT[key])


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


def test_complete_target_minor_planet_categorized_by_elements() -> None:
    # ttype 'M' with a TNO-scale orbit is categorized to 'T'; no parent, description "none".
    minor_planet = {'name': '', 'full_name': '1999 XY99', 'desig': '1999 XY99',
                    'aliases': [], 'mnum': '', 'ttype': TargetType.MINOR_PLANET,
                    'A': 45., 'E': 0.1, 'parent_key': ''}
    target = _complete_target(minor_planet)
    assert target['ttype'] == TargetType.TRANS_NEPTUNIAN_OBJECT
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
