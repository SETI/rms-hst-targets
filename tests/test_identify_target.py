##########################################################################################
# tests/test_identify_target.py
##########################################################################################

import logging
import sys
from types import ModuleType
from typing import Any, cast

import pytest
from astropy.io import fits
from identify_target import (
    _collect_strings,
    _norm_date,
    _normalize_body,
    _parse_mt_lv,
    _resolve_std,
)
from mpc_tools.mpc_query_by_name import _mpc_date_to_str, mpc_query_by_name
from SPT_TESTS import SPT_TESTS

from targets import (
    TargetIdentificationError,
    identify_comet,
    identify_minor_planet,
    identify_small_body,
    identify_target,
    minor_planet_ttype,
)

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


def test_element_typo_fixed_by_override() -> None:
    # Program 6841 header had Q=.05320503 (10x too small); the override repairs it
    bodies = identify_target(_header('6841/u33k0201t_shm.fits'))
    assert bodies[0]['full_name'] == '45P/Honda-Mrkos-Pajdusakova'


def test_sl9_precollision_override() -> None:
    # TARGNAME "SL-COL" (ephemeris from file): the override names D/1993 F2 directly
    bodies = identify_target(_header('5590/u2640101t_shm.fits'))
    assert bodies[0]['full_name'] == 'D/1993 F2 (Shoemaker-Levy 9)'


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


def test_inconsistent_ra_targ_skips_position_check(
        caplog: pytest.LogCaptureFixture) -> None:
    # When RA_TARG/DEC_TARG does not track the header's own ephemeris, the pointing is
    # not at the body and the sky-position check must be skipped, not failed
    pytest.importorskip('palpy')
    header = _header('9110/o6e939010_spt.fits')      # TARGNAME "1999RZ253"
    header['RA_TARG'] = (float(header['RA_TARG']) + 90.) % 360.

    logger = logging.getLogger('test_skip')
    with caplog.at_level(logging.INFO, logger='test_skip'):
        bodies = identify_target(header, logger=logger)
    assert bodies[0]['full_name'] == '66652 Borasisi'
    assert 'position check skipped' in caplog.text


def test_pholus_pointing_not_at_body() -> None:
    # Program 7239: RA_TARG is ~68 degrees from where both the header orbit and the
    # catalog put Pholus; the body is still identified from the name and elements
    pytest.importorskip('palpy')
    bodies = identify_target(_header('7239/n4je09010_spt.fits'))
    assert bodies[0]['full_name'] == '5145 Pholus'


def test_asteroid_position_incompatible_raises() -> None:
    # Program 11113 target 14 ("05UX100") carries orbital elements that are not
    # 2005 UX100's: with the SPT_REPAIRS override suppressed, the position check must
    # reject the name match (the offline network ban keeps the replacement search empty)
    pytest.importorskip('palpy')
    header = _header('11113/u9yz1401m_shm.fits')
    header['TARG_ID'] = '11113_999'                  # suppress the TARGNAME repair
    with pytest.raises(TargetIdentificationError, match='beyond the tolerance'):
        identify_target(header)


def test_mislabeled_targname_fixed_by_override() -> None:
    # The same entry with its override identifies the body actually observed
    pytest.importorskip('palpy')
    bodies = identify_target(_header('11113/u9yz1401m_shm.fits'))
    assert bodies[0]['full_name'] == '(308634) 2005 XU100'


def test_revised_orbit_accepted(caplog: pytest.LogCaptureFixture) -> None:
    # (19308) 1996 TO66: the catalog orbit was revised after the observation, so the
    # propagated position misses RA_TARG, but the elements still match; accept
    pytest.importorskip('palpy')
    logger = logging.getLogger('test_revised')
    with caplog.at_level(logging.INFO, logger='test_revised'):
        bodies = identify_target(_header('8258/o5lk05g2q_spt.fits'), logger=logger)
    assert bodies[0]['full_name'] == '(19308) 1996 TO66'
    assert bodies[0]['ttype'] == 'T'
    assert 'revised after the observation' in caplog.text


def test_comet_rescued_from_wrong_name() -> None:
    # TARGNAME "KUSHIDA" resolves to 144P/Kushida, but the elements identify
    # 147P/Kushida-Muramatsu, whose name also matches
    bodies = identify_target(_header('8699/u65z7a01r_shm.fits'))
    assert bodies[0]['full_name'] == '147P/Kushida-Muramatsu'

    bodies = identify_target(_header('8699/u65z7i01r_shm.fits'))
    assert bodies[0]['full_name'] == 'C/1999 T1 (McNaught-Hartley)'


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
# Input normalization
##########################################################################################

def test_identify_small_body_accepts_a_bare_string() -> None:
    # A lone string is normalized to a single-element list, matching the list form.
    assert identify_small_body('IO', {}) == identify_small_body(['IO'], {})


@pytest.mark.parametrize('strings', [[], None])
def test_identify_small_body_handles_missing_identifiers(strings: Any) -> None:
    # Empty or None identifiers yield no body rather than raising.
    assert identify_small_body(strings, {}) == (None, 0., False)


@pytest.mark.parametrize('strings', ['', [], None])
def test_identify_comet_handles_missing_identifiers(strings: Any) -> None:
    # `elements` defaults to None and empty identifiers yield no comet.
    assert identify_comet(strings) == (None, 0., False)


@pytest.mark.parametrize('strings', ['', [], None])
def test_identify_minor_planet_handles_missing_identifiers(strings: Any) -> None:
    # `elements` defaults to None and empty identifiers yield no minor planet.
    assert identify_minor_planet(strings) == (None, 0., False)


##########################################################################################
# Sentinels and failures
##########################################################################################

def test_tno_survey_sentinel() -> None:
    # TARG_ID 12535_3 is flagged TNO_SURVEY: a placeholder body named for the program
    bodies = identify_target(_header('12535/ibr001faq_spt.fits'))
    assert len(bodies) == 1
    assert bodies[0]['name'] == 'Survey HST-12535'
    assert bodies[0]['full_name'] == 'Survey HST-12535'
    assert bodies[0]['desig'] == ''
    assert bodies[0]['ttype'] == 'T'
    assert bodies[0]['ttype_name'] == 'trans-neptunian_object'
    assert bodies[0]['lid_suffix'] == 'trans-neptunian_object.survey_hst-12535'

    # The program ID is zero-padded to five digits
    bodies = identify_target(_header('6497/o45001010_spt.fits'))    # Kuiper field
    assert len(bodies) == 1
    assert bodies[0]['name'] == 'Survey HST-06497'


def test_no_target_sentinels() -> None:
    # Anti-solar pointings, slew tests, and parallel fields have no identifiable target
    assert identify_target(_header('1431/w0aqxp01t_shf.fits')) == []   # ANTISUN
    assert identify_target(_header('3069/v0e10101t_shf.fits')) == []   # ASLAG
    assert identify_target(_header('8800/u69va201r_shm.fits')) == []   # SLEW-11
    assert identify_target(_header('12537/ibu5110e1_spt.fits')) == []  # parallel


def test_nicknamed_targets_resolved_by_override() -> None:
    # Survey-internal and pre-announcement names mapped to real designations
    pytest.importorskip('palpy')
    bodies = identify_target(_header('9110/o6e945010_spt.fits'))    # "MINIXENA"
    assert bodies[0]['full_name'] == '55565 Aya'

    bodies = identify_target(_header('9678/j8i701011_spt.fits'))    # "OBJECTX"
    assert bodies[0]['full_name'] == 'Quaoar'
    assert bodies[0]['ttype'] == 'T'

    bodies = identify_target(_header('16183/iedk15ifq_spt.fits'))   # "P959EB2C"
    assert bodies[0]['full_name'] == '2020 KD54'

    bodies = identify_target(_header('14498/id3t01n9q_spt.fits'))   # "P2010-V-C-OFFSET"
    assert bodies[0]['full_name'] == '332P/Ikeya-Murakami-C'


def test_undesignated_tno_sentinel() -> None:
    # Survey candidates that never received an MPC designation
    bodies = identify_target(_header('16183/iedk11dbq_spt.fits'))   # "P72X4B2"
    assert len(bodies) == 1
    assert bodies[0]['name'] == 'Unknown HST-16183'
    assert bodies[0]['full_name'] == 'Unknown HST-16183'
    assert bodies[0]['desig'] == ''
    assert bodies[0]['ttype'] == 'T'
    assert bodies[0]['lid_suffix'] == 'trans-neptunian_object.unknown_hst-16183'

    bodies = identify_target(_header('12887/ibzx01g4q_spt.fits'))   # "VNH0034"
    assert len(bodies) == 1
    assert bodies[0]['name'] == 'Unknown HST-12887'


def test_internal_calibration_targnames() -> None:
    # Lamp/calibration exposures (COS "WAVE", FOS "TALED") are not sky targets
    assert identify_target(_header('17780/lfee01fgq_spt.fits')) == []
    assert identify_target(_header('2569/y11e0c03t_shf.fits')) == []
    assert identify_target({'TARGNAME': 'DARK', 'TARG_ID': '1_1'}) == []


def test_wildcard_override() -> None:
    # TARG_ID "13633_*" flags every target of program 13633 as TNO_SURVEY
    header = {'TARG_ID': '13633_5', 'TARGNAME': 'ANY'}
    bodies = identify_target(header)
    assert len(bodies) == 1
    assert bodies[0]['name'] == 'Survey HST-13633'


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


def test_parse_mt_lv_drops_free_text() -> None:
    # Program 6854: a scheduling comment follows the STD field after a comma; it must
    # not be glued onto the value
    header = {'MT_LV1_1': 'STD = SATURN,CML OF SATURN FROM EARTH BETWEEN 0 60'}
    assert _parse_mt_lv(header, 'MT_LV1') == ('STD', 'SATURN')
    bodies = identify_target(_header('6854/o4bd04vmq_spt.fits'))
    assert bodies[0]['name'] == 'Saturn'


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
