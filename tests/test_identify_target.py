##########################################################################################
# tests/test_identify_target.py
##########################################################################################

import logging
import sys
from types import ModuleType
from typing import Any, cast

import pytest
from astropy.io import fits
from categorize_minor_planet import minor_planet_ttype
from identify_small_body import identify_small_body
from identify_target import (
    TargetIdentificationError,
    _collect_strings,
    _norm_date,
    _normalize_body,
    _parse_mt_lv,
    _resolve_std,
    identify_target,
)
from mpc_tools.mpc_query_by_name import _mpc_date_to_str, mpc_query_by_name
from SPT_TESTS import SPT_TESTS

_SPT = dict(SPT_TESTS)


def _header(filename: str) -> dict[str, Any]:
    """A private copy of one SPT_TESTS header, safe to modify."""

    return dict(_SPT[filename])


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any attempt to reach the network; tests run entirely from the committed
    caches in caches/MPC_CACHE and caches/COMET_CACHE.
    """

    def _blocked(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError('network access attempted during test')

    monkeypatch.setattr('requests.get', _blocked)
    monkeypatch.setattr('requests.Session.request', _blocked)


##########################################################################################
# Standard bodies
##########################################################################################

def test_planet_std() -> None:
    # MT_LV1 "STD = URANUS", TARGNAME "URANUS-CENTER"
    bodies = identify_target(_header('1083/v0zf0101t_shf.fits'))
    assert len(bodies) == 1
    body = bodies[0]
    assert body['name'] == 'Uranus'
    assert body['ttype'] == 'P'
    assert body['ttype_name'] == 'planet'
    assert body['lid_suffix'] == 'planet.uranus'
    assert body['naif_id'] == 799


def test_satellite_and_parent() -> None:
    # MT_LV1 "STD = JUPITER", MT_LV2 "STD = IO": the satellite observed comes first,
    # the tracked planet second
    bodies = identify_target(_header('1206/z1cw0101t_shf.fits'))
    assert [b['name'] for b in bodies] == ['Io', 'Jupiter']
    assert [b['ttype'] for b in bodies] == ['S', 'P']
    assert bodies[0]['naif_id'] == 501
    assert bodies[0]['parent_key'] == 'Jupiter'


def test_satellite_from_tardescr_alone() -> None:
    # Io must be found even when TARDESCR is the only keyword naming it
    header = _header('1206/z1cw0101t_shf.fits')
    del header['TARKEY1']
    del header['TARGNAME']
    assert header['TARDESCR'] == 'SOLAR SYSTEM;SATELLITE IO'
    bodies = identify_target(header)
    assert [b['name'] for b in bodies] == ['Io', 'Jupiter']


def test_offset_pointing() -> None:
    # TARGNAME "...-BACKGROUND" with TARKEY "OFFSET JUPITER": only Jupiter is relevant
    bodies = identify_target(_header('1080/y0zz0301t_shf.fits'))
    assert [b['name'] for b in bodies] == ['Jupiter']


def test_astropy_header_input() -> None:
    header = fits.Header()
    for key, value in _SPT['1083/v0zf0101t_shf.fits'].items():
        header[key] = value
    bodies = identify_target(header)
    assert [b['name'] for b in bodies] == ['Uranus']


##########################################################################################
# STD fields naming small bodies
##########################################################################################

def test_std_ceres_is_dwarf_planet() -> None:
    # MT_LV1 "STD = 1 (CERES)"
    bodies = identify_target(_header('1268/x0xa0101t_shf.fits'))
    assert len(bodies) == 1
    assert bodies[0]['name'] == 'Ceres'
    assert bodies[0]['ttype'] == 'D'
    assert bodies[0]['lid_suffix'] == 'dwarf_planet.ceres'


def test_std_number_is_centaur() -> None:
    # MT_LV1 "STD=2060" identifies Chiron by minor planet number
    bodies = identify_target(_header('3769/w1a70201t_shf.fits'))
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '2060 Chiron'
    assert bodies[0]['ttype'] == 'H'


def test_std_metis_is_the_asteroid() -> None:
    # MT_LV1 "STD = 9(METIS)": the asteroid 9 Metis, not the satellite of Jupiter
    bodies = identify_target(_header('4521/w1k10r01t_shf.fits'))
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '9 Metis'
    assert bodies[0]['ttype'] == 'A'


def test_std_wrong_number_right_name() -> None:
    # MT_LV1 "STD = 1 (VESTA)": the name is right, the number is not
    bodies = identify_target(_header('5175/x2it0101t_shf.fits'))
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '4 Vesta'
    assert bodies[0]['ttype'] == 'A'


def test_std_comet() -> None:
    # MT_LV1 "STD = HARTLEY-2,ACQ = 0.25" names a comet
    bodies = identify_target(_header('2481/y0rib201t_shf.fits'))
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '103P/Hartley 2'
    assert bodies[0]['ttype'] == 'C'


def test_resolve_std_tokens() -> None:
    body, name, number = _resolve_std('JUPITER', None)
    assert body is not None
    assert body['name'] == 'Jupiter'

    body, name, number = _resolve_std('1 (CERES)', None)
    assert body is not None
    assert body['name'] == 'Ceres'

    body, name, number = _resolve_std('9(METIS)', None)
    assert body is None
    assert (name, number) == ('METIS', '9')

    body, name, number = _resolve_std('2060', None)
    assert body is None
    assert (name, number) == ('2060', '2060')

    body, name, number = _resolve_std('HARTLEY-2', None)
    assert body is None
    assert (name, number) == ('HARTLEY-2', '')


##########################################################################################
# Comets
##########################################################################################

def test_comet_by_name_b1950_elements() -> None:
    # TARGNAME "COMET-FAYE-1984XI" with B1950 elements in MT_LV1
    pytest.importorskip('palpy')    # for the B1950 -> J2000 element rotation
    bodies = identify_target(_header('2231/w0sb0101t_shf.fits'))
    assert len(bodies) == 1
    body = bodies[0]
    assert body['full_name'] == '4P/Faye'
    assert body['ttype'] == 'C'
    assert body['lid_suffix'] == 'comet.4p_faye'
    assert body['Q'] is not None       # orbital elements ride along


def test_comet_fragment() -> None:
    bodies = identify_target(_header('10625/j9fr01010_spt.fits'))
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '73P/Schwassmann-Wachmann 3-C'
    assert bodies[0]['fragment'] == 'C'
    assert bodies[0]['ttype'] == 'C'


def test_comet_incompatible_elements_raises() -> None:
    pytest.importorskip('palpy')
    header = _header('2231/w0sb0101t_shf.fits')
    assert 'Q = 1.5933855' in header['MT_LV1_1']
    header['MT_LV1_1'] = header['MT_LV1_1'].replace('Q = 1.5933855', 'Q = 4.78')
    with pytest.raises(TargetIdentificationError,
                       match='incompatible with the header orbital elements'):
        identify_target(header)


def test_comet_by_elements_alone() -> None:
    # An unrecognizable name with Faye's orbital elements identifies Faye from the
    # comet database
    pytest.importorskip('palpy')
    header = _header('2231/w0sb0101t_shf.fits')
    header['TARGNAME'] = 'ZZZZZ'
    del header['TARKEY1']
    del header['TARDESCR']
    bodies = identify_target(header)
    assert bodies[0]['full_name'] == '4P/Faye'


def test_comet_rescued_by_elements_and_name() -> None:
    # Program 2442: the TARGNAME resolves to the wrong comet (an old designation
    # shared with 97P), but the elements plus the name "SHOEMAKER-LEVY" identify
    # C/1991 T2
    bodies = identify_target(_header('2442/w0yy0201t_shf.fits'))
    assert bodies[0]['full_name'] == 'C/1991 T2 (Shoemaker-Levy)'


##########################################################################################
# Minor planets
##########################################################################################

def test_asteroid_named_pholus_is_centaur(caplog: pytest.LogCaptureFixture) -> None:
    # TARGNAME "1992AD", header says ASTEROID; the body is the Centaur 5145 Pholus and
    # its sky position confirms the identification
    pytest.importorskip('palpy')
    logger = logging.getLogger('test_pholus')
    with caplog.at_level(logging.INFO, logger='test_pholus'):
        bodies = identify_target(_header('2432/w0xh0101t_shf.fits'), logger=logger)
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '5145 Pholus'
    assert bodies[0]['ttype'] == 'H'
    assert bodies[0]['ttype_name'] == 'centaur'
    assert 'Sky position confirmed' in caplog.text


def test_tno() -> None:
    bodies = identify_target(_header('9110/o6e939010_spt.fits'))
    assert bodies[0]['full_name'] == '66652 Borasisi'
    assert bodies[0]['ttype'] == 'T'
    assert bodies[0]['ttype_name'] == 'trans-neptunian_object'


def test_dwarf_planet_via_override() -> None:
    # TARG_ID 10545_22 has a TARKEY2 override replacing "KBO-Santa" with "HAUMEA"
    header = _header('10545/j9fs20011_spt.fits')
    assert header['TARG_ID'] == '10545_22'
    bodies = identify_target(header)
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '136108 Haumea'
    assert bodies[0]['ttype'] == 'D'


def test_arrokoth() -> None:
    bodies = identify_target(_header('14053/ict101efq_spt.fits'))
    assert bodies[0]['full_name'] == '486958 Arrokoth'
    assert bodies[0]['ttype'] == 'T'


def test_asteroid_position_winnow(monkeypatch: pytest.MonkeyPatch) -> None:
    # An unrecognizable name whose elements are ambiguous between two TNOs: the sky
    # position selects the right one
    pytest.importorskip('palpy')
    header = _header('9110/o6e939010_spt.fits')
    header['TARGNAME'] = 'ZZZZZ'
    for key in list(header):
        if key.startswith(('TARKEY', 'TARDESC')):
            del header[key]

    borasisi = mpc_query_by_name('1999 RZ253')
    arrokoth = mpc_query_by_name('2014 MU69')
    assert borasisi is not None
    assert arrokoth is not None
    canned = [(borasisi, 0.02), (arrokoth, 0.03)]   # too similar to pick by elements
    monkeypatch.setattr('targets.mpc_tools.mpc_query_by_elements',
                        lambda *args, **kwargs: canned)

    bodies = identify_target(header)
    assert bodies[0]['full_name'] == '66652 Borasisi'


def test_asteroid_position_winnow_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    # Same setup, but RA_TARG points nowhere near either candidate
    pytest.importorskip('palpy')
    header = _header('9110/o6e939010_spt.fits')
    header['TARGNAME'] = 'ZZZZZ'
    for key in list(header):
        if key.startswith(('TARKEY', 'TARDESC')):
            del header[key]
    header['RA_TARG'] = (float(header['RA_TARG']) + 90.) % 360.

    borasisi = mpc_query_by_name('1999 RZ253')
    arrokoth = mpc_query_by_name('2014 MU69')
    assert borasisi is not None
    assert arrokoth is not None
    canned = [(borasisi, 0.02), (arrokoth, 0.03)]
    monkeypatch.setattr('targets.mpc_tools.mpc_query_by_elements',
                        lambda *args, **kwargs: canned)

    with pytest.raises(TargetIdentificationError, match='No target identified'):
        identify_target(header)


def test_asteroid_position_incompatible_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # A body identified by name whose sky position contradicts RA_TARG/DEC_TARG raises
    # when no better candidate exists
    pytest.importorskip('palpy')
    header = _header('9110/o6e939010_spt.fits')      # TARGNAME "1999RZ253"
    header['RA_TARG'] = (float(header['RA_TARG']) + 90.) % 360.

    def _no_candidates(*args: Any, **kwargs: Any) -> list[tuple[dict[str, Any], float]]:
        return []

    monkeypatch.setattr('targets.mpc_tools.mpc_query_by_elements', _no_candidates)
    with pytest.raises(TargetIdentificationError, match='beyond the tolerance'):
        identify_target(header)


def test_palpy_unavailable_degrades(monkeypatch: pytest.MonkeyPatch) -> None:
    # Without palpy the sky position check is skipped and the element match decides
    monkeypatch.setitem(sys.modules, 'targets.orbital_radec',
                        cast(ModuleType, None))
    bodies = identify_target(_header('2432/w0xh0101t_shf.fits'))
    assert bodies[0]['full_name'] == '5145 Pholus'


def test_disallowed_minor_planet_name() -> None:
    # "IO" must never resolve to the minor planet 85 Io
    body, _, valid = identify_small_body(['IO'], {})
    assert body is None
    assert not valid


##########################################################################################
# Sentinels and failures
##########################################################################################

def test_tno_survey_sentinel() -> None:
    # TARG_ID 12535_3 is flagged TNO_SURVEY: no identifiable target, no exception
    bodies = identify_target(_header('12535/ibr001faq_spt.fits'))
    assert bodies == []


def test_wildcard_override() -> None:
    # TARG_ID "13633_*" flags every target of program 13633 as TNO_SURVEY
    header = {'TARG_ID': '13633_5', 'TARGNAME': 'ANY'}
    assert identify_target(header) == []


def test_unidentifiable_raises() -> None:
    header = {'TARG_ID': '9999_1', 'TARGNAME': 'XYZZYQ'}
    with pytest.raises(TargetIdentificationError,
                       match='No target identified for TARGNAME "XYZZYQ"'):
        identify_target(header)


##########################################################################################
# Header parsing
##########################################################################################

def test_parse_mt_lv_std() -> None:
    header = _header('1206/z1cw0101t_shf.fits')
    assert _parse_mt_lv(header, 'MT_LV1') == ('STD', 'JUPITER')
    assert _parse_mt_lv(header, 'MT_LV2') == ('STD', 'IO')


def test_parse_mt_lv_value_split_mid_number() -> None:
    # The Chaos entry splits "O = 119.3837" across MT_LV1_1/MT_LV1_2 and
    # "EQUINOX = J2000" across MT_LV1_2/MT_LV1_3
    kind, elements = _parse_mt_lv(_header('2432/w0xh0101t_shf.fits'), 'MT_LV1')
    assert kind == 'ASTEROID'
    assert elements is not None
    assert not isinstance(elements, str)
    assert elements['A'] == 20.464038
    assert elements['O'] == 119.3837
    assert elements['M'] == 2.9208644
    assert elements['EPOCH'] == '27-JUN-1992:00:00:00'
    assert elements['EQUINOX'] == 'J2000'


def test_parse_mt_lv_stray_commas() -> None:
    # The 7239 Pholus entry has a leading comma and a comma inside the M value
    # ("M=2,3.618253" means M=23.618253)
    kind, elements = _parse_mt_lv(_header('7239/n4je09010_spt.fits'), 'MT_LV1')
    assert kind == 'ASTEROID'
    assert elements is not None
    assert not isinstance(elements, str)
    assert elements['M'] == 23.618253
    assert elements['A'] == 20.23369318
    assert elements['W'] == 354.569235


def test_parse_mt_lv_b1950_comet() -> None:
    kind, elements = _parse_mt_lv(_header('2231/w0sb0101t_shf.fits'), 'MT_LV1')
    assert kind == 'COMET'
    assert elements is not None
    assert not isinstance(elements, str)
    assert elements['Q'] == 1.5933855
    assert elements['T'] == '16-NOV-1991:04:38:54'
    assert elements['EPOCH'] == '31-OCT-1991:00:00:00'
    assert elements['EQUINOX'] == 'B1950'


def test_parse_mt_lv_other_kinds() -> None:
    assert _parse_mt_lv({'MT_LV1_1': 'FILE='}, 'MT_LV1') == ('FILE', None)
    assert _parse_mt_lv({'MT_LV2_1': 'TYPE=POS_ANGLE, RAD = 0.001'},
                        'MT_LV2') == ('OFFSET', None)
    assert _parse_mt_lv({}, 'MT_LV1') == (None, None)
    assert _parse_mt_lv({'MT_LV1_1': '   '}, 'MT_LV1') == (None, None)


def test_collect_strings_skips_category() -> None:
    header = {'TARGNAME': 'IO-IN', 'TARKEY1': 'SATELLITE IO', 'TARGCAT': 'SOLAR SYSTEM',
              'TARDESCR': 'SOLAR SYSTEM;SATELLITE IO'}
    assert _collect_strings(header) == ['SATELLITE IO', 'IO-IN', 'SATELLITE IO']


def test_norm_date() -> None:
    assert _norm_date('16-NOV-1991:04:38:54') == '16-NOV-1991:04:38:54'
    assert _norm_date('31-Oct-91') == '31-OCT-1991:00:00:00'
    assert _norm_date('5-JAN-05') == '05-JAN-2005:00:00:00'
    assert _norm_date('27-JUN-1992.') == '27-JUN-1992:00:00:00'


def test_mpc_date_to_str() -> None:
    assert _mpc_date_to_str('2019-04-27.0') == '27-APR-2019:00:00:00'
    assert _mpc_date_to_str('1991-08-26.19791') == '26-AUG-1991:04:44:59'


##########################################################################################
# Categorization
##########################################################################################

def test_minor_planet_ttype_by_elements() -> None:
    assert minor_planet_ttype({'name': 'Fake', 'A': 45., 'E': 0.1}) == 'T'
    assert minor_planet_ttype({'name': 'Fake', 'A': 15., 'E': 0.2}) == 'H'
    assert minor_planet_ttype({'name': 'Fake', 'A': 2.7, 'E': 0.1}) == 'A'
    assert minor_planet_ttype({'name': 'Fake', 'Q': 40., 'E': 0.1}) == 'T'


def test_minor_planet_ttype_dwarf_planet() -> None:
    assert minor_planet_ttype({'name': 'Pluto', 'mnum': '134340'}) == 'D'
    assert minor_planet_ttype({'name': '', 'mnum': '1'}) == 'D'


def test_minor_planet_ttype_hints() -> None:
    # Without elements, the target description decides; with elements it only warns
    assert minor_planet_ttype({'name': 'Fake'}, hints='T') == 'T'
    assert minor_planet_ttype({'name': 'Fake'}, hints='') == 'A'
    assert minor_planet_ttype({'name': 'Fake', 'A': 45., 'E': 0.1}, hints='A') == 'T'


def test_normalize_body_minimal() -> None:
    body = _normalize_body({'name': '', 'desig': '1999 XY99', 'alt_desigs': [],
                            'mnum': '', 'ttype': 'M', 'A': 45., 'E': 0.1}, '', None)
    assert body['full_name'] == '1999 XY99'
    assert body['ttype'] == 'T'
    assert body['naif_id'] is None
    assert body['aliases'] == ['1999 XY99']
    assert body['parent_key'] == ''
    assert body['lid_suffix'] == 'trans-neptunian_object.1999_xy99'

##########################################################################################
