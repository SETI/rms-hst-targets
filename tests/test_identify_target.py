##########################################################################################
# tests/test_identify_target.py
##########################################################################################

import pathlib
import sys
from types import ModuleType
from typing import Any, cast

import pytest
from astropy.io import fits
from SPT_TESTS import SPT_TESTS

from targets import (
    TargetIdentificationFailure,
    identify_target_dicts,
    identify_targets,
)
from targets._utils import _collect_strings, _norm_date, _parse_mt_lv
from targets.mpc_tools.mpc_query_by_name import _mpc_date_to_str, mpc_query_by_name
from targets.target_xml_cache_support import use_local_xml_dir

# SPT_TESTS is keyed by six-character visit; each value is the list of per-file header
# dictionaries for that visit, each carrying its own "FILENAME".
_SPT = dict(SPT_TESTS)


def _header(spec: str) -> dict[str, Any]:
    """A private copy of one SPT_TESTS header, safe to modify.

    Parameters:
        spec: "<program>/<basename>", e.g. "1083/v0zf0101t_shf.fits". The basename's
            first six characters are the visit key; the file is found within that visit.
    """

    basename = spec.split('/')[1]
    for header in _SPT[basename[:6]]:
        if header['FILENAME'] == basename:
            return dict(header)
    raise KeyError(spec)


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
    bodies = identify_target_dicts([_header('1083/v0zf0101t_shf.fits')])
    assert len(bodies) == 1
    body = bodies[0]
    assert body['name'] == 'Uranus'
    assert body['ttype'] == 'P'


def test_satellite_observed() -> None:
    # MT_LV1 "STD = JUPITER", MT_LV2 "STD = IO": the satellite observed is returned
    bodies = identify_target_dicts([_header('1206/z1cw0101t_shf.fits')])
    assert bodies[0]['name'] == 'Io'
    assert bodies[0]['ttype'] == 'S'
    assert bodies[0]['naif_id'] == 501
    assert bodies[0]['parent_key'] == 'Jupiter'


def test_satellite_from_tardescr_alone() -> None:
    # Io must be found even when TARDESCR is the only keyword naming it
    header = _header('1206/z1cw0101t_shf.fits')
    del header['TARKEY1']
    del header['TARGNAME']
    assert header['TARDESCR'] == 'SOLAR SYSTEM;SATELLITE IO'
    bodies = identify_target_dicts([header])
    assert bodies[0]['name'] == 'Io'


def test_offset_pointing() -> None:
    # TARGNAME "...-BACKGROUND" with TARKEY "OFFSET JUPITER": only Jupiter is relevant
    bodies = identify_target_dicts([_header('1080/y0zz0301t_shf.fits')])
    assert [b['name'] for b in bodies] == ['Jupiter']


def test_astropy_header_input() -> None:
    header = fits.Header()
    for key, value in _header('1083/v0zf0101t_shf.fits').items():
        header[key] = value
    bodies = identify_target_dicts([header])
    assert [b['name'] for b in bodies] == ['Uranus']


##########################################################################################
# STD fields naming small bodies
##########################################################################################

def test_std_ceres_is_dwarf_planet() -> None:
    # MT_LV1 "STD = 1 (CERES)"
    bodies = identify_target_dicts([_header('1268/x0xa0101t_shf.fits')])
    assert len(bodies) == 1
    assert bodies[0]['name'] == 'Ceres'
    assert bodies[0]['ttype'] == 'D'


def test_std_number_is_centaur() -> None:
    # MT_LV1 "STD=2060" identifies Chiron by minor planet number
    bodies = identify_target_dicts([_header('3769/w1a70201t_shf.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '2060 Chiron'
    assert bodies[0]['ttype'] == 'H'


def test_std_metis_is_the_asteroid() -> None:
    # MT_LV1 "STD = 9(METIS)": the asteroid 9 Metis, not the satellite of Jupiter
    bodies = identify_target_dicts([_header('4521/w1k10r01t_shf.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '9 Metis'
    assert bodies[0]['ttype'] == 'A'


def test_std_wrong_number_right_name() -> None:
    # MT_LV1 "STD = 1 (VESTA)": the name is right, the number is not
    bodies = identify_target_dicts([_header('5175/x2it0101t_shf.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '4 Vesta'
    assert bodies[0]['ttype'] == 'A'


def test_std_comet() -> None:
    # MT_LV1 "STD = HARTLEY-2,ACQ = 0.25" names a comet
    bodies = identify_target_dicts([_header('2481/y0rib201t_shf.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '103P/Hartley 2'
    assert bodies[0]['ttype'] == 'C'


def test_std_io_torus_named_by_targname() -> None:
    # Program 5218: TARGNAME "IO-TORUS-WEST" names the Io plasma torus directly (no MT_LV2
    # "TYPE=TORUS" geometry, and the STD body is Io rather than Jupiter). The plasma-cloud
    # marker from hst_repairs must still yield the Io Torus, alongside Io itself.
    bodies = identify_target_dicts([_header('5218/u2bn0101t_shm.fits')])
    assert [(b['full_name'], b['ttype']) for b in bodies] == [('Io Torus', 't'), ('Io', 'S')]


##########################################################################################
# Comets
##########################################################################################

def test_comet_by_name_b1950_elements() -> None:
    # TARGNAME "COMET-FAYE-1984XI" with B1950 elements in MT_LV1
    pytest.importorskip('palpy')    # for the B1950 -> J2000 element rotation
    bodies = identify_target_dicts([_header('2231/w0sb0101t_shf.fits')])
    assert len(bodies) == 1
    body = bodies[0]
    assert body['full_name'] == '4P/Faye'
    assert body['ttype'] == 'C'
    assert body['Q'] is not None       # orbital elements ride along


def test_comet_fragment() -> None:
    bodies = identify_target_dicts([_header('10625/j9fr01010_spt.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '73P/Schwassmann-Wachmann 3-C'
    assert bodies[0]['ttype'] == 'C'


def test_comet_incompatible_elements_raises() -> None:
    pytest.importorskip('palpy')
    header = _header('2231/w0sb0101t_shf.fits')
    assert 'Q = 1.5933855' in header['MT_LV1_1']
    header['MT_LV1_1'] = header['MT_LV1_1'].replace('Q = 1.5933855', 'Q = 4.78')
    with pytest.raises(TargetIdentificationFailure, match='could not be determined'):
        identify_target_dicts([header])


def test_comet_by_elements_alone() -> None:
    # An unrecognizable name with Faye's orbital elements identifies Faye from the
    # comet database
    pytest.importorskip('palpy')
    header = _header('2231/w0sb0101t_shf.fits')
    header['TARGNAME'] = 'ZZZZZ'
    del header['TARKEY1']
    del header['TARDESCR']
    bodies = identify_target_dicts([header])
    assert bodies[0]['full_name'] == '4P/Faye'


def test_comet_rescued_by_elements_and_name() -> None:
    # Program 2442: the TARGNAME resolves to the wrong comet (an old designation
    # shared with 97P), but the elements plus the name "SHOEMAKER-LEVY" identify
    # C/1991 T2
    bodies = identify_target_dicts([_header('2442/w0yy0201t_shf.fits')])
    assert bodies[0]['full_name'] == 'C/1991 T2 (Shoemaker-Levy)'


def test_element_typo_fixed_by_override() -> None:
    # Program 6841 header had Q=.05320503 (10x too small); the override repairs it
    bodies = identify_target_dicts([_header('6841/u33k0201t_shm.fits')])
    assert bodies[0]['full_name'] == '45P/Honda-Mrkos-Pajdusakova'


def test_comet_confirmed_by_name_without_elements() -> None:
    # Program 5590: "COMET SHOEMAKER-LEVY 1993E-15" repairs to the unambiguous old-style
    # designation D/1993 F2 (Shoemaker-Levy 9). MT_LV1 is a FILE ephemeris with no orbital
    # elements, so the comet is confirmed on the strength of the unambiguous name alone.
    bodies = identify_target_dicts([_header('5590/u2640401t_shm.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == 'D/1993 F2 (Shoemaker-Levy 9)'


def test_ambiguous_comet_name_without_elements_raises() -> None:
    # The bare name "Shoemaker-Levy" is ambiguous across 13 comets, and a FILE ephemeris
    # carries no orbital elements to disambiguate. No comet may be confirmed -- the element
    # test must not treat "no elements to compare" as a perfect (RMS 0.0) match.
    header = _header('5590/u2640401t_shm.fits')
    header['TARDESCR'] = 'COMET SHOEMAKER-LEVY'
    header['TARKEY1'] = 'COMET SHOEMAKER-LEVY'
    header['TARGNAME'] = 'SHOEMAKER-LEVY'
    with pytest.raises(TargetIdentificationFailure, match='No target could be identified'):
        identify_target_dicts([header])


##########################################################################################
# Minor planets
##########################################################################################

def test_asteroid_named_pholus_is_centaur() -> None:
    # TARGNAME "1992AD", header says ASTEROID; the body is the Centaur 5145 Pholus and
    # its sky position confirms the identification
    pytest.importorskip('palpy')
    bodies = identify_target_dicts([_header('2432/w0xh0101t_shf.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '5145 Pholus'
    assert bodies[0]['ttype'] == 'H'


def test_tno() -> None:
    bodies = identify_target_dicts([_header('9110/o6e939010_spt.fits')])
    assert bodies[0]['full_name'] == '66652 Borasisi'
    assert bodies[0]['ttype'] == 'T'


def test_dwarf_planet_via_override() -> None:
    # TARG_ID 10545_22 has a TARKEY2 override replacing "KBO-Santa" with "HAUMEA"
    header = _header('10545/j9fs20011_spt.fits')
    assert header['TARG_ID'] == '10545_22'
    bodies = identify_target_dicts([header])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '136108 Haumea'
    assert bodies[0]['ttype'] == 'D'


def test_arrokoth() -> None:
    bodies = identify_target_dicts([_header('14053/ict101efq_spt.fits')])
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

    bodies = identify_target_dicts([header])
    assert bodies[0]['full_name'] == '66652 Borasisi'


def test_pholus_pointing_not_at_body() -> None:
    # Program 7239: RA_TARG is ~68 degrees from where both the header orbit and the
    # catalog put Pholus; the body is still identified from the name and elements
    pytest.importorskip('palpy')
    bodies = identify_target_dicts([_header('7239/n4je09010_spt.fits')])
    assert bodies[0]['full_name'] == '5145 Pholus'


def test_mislabeled_targname_fixed_by_override() -> None:
    # The 11113_14 entry with its TARGNAME override identifies the body actually observed
    pytest.importorskip('palpy')
    bodies = identify_target_dicts([_header('11113/u9yz1401m_shm.fits')])
    assert bodies[0]['full_name'] == '(308634) 2005 XU100'


def test_revised_orbit_accepted() -> None:
    # (19308) 1996 TO66: the catalog orbit was revised after the observation, so the
    # propagated position misses RA_TARG, but the elements still match; accept
    pytest.importorskip('palpy')
    bodies = identify_target_dicts([_header('8258/o5lk05g2q_spt.fits')])
    assert bodies[0]['full_name'] == '(19308) 1996 TO66'
    assert bodies[0]['ttype'] == 'T'


def test_comet_rescued_from_wrong_name() -> None:
    # TARGNAME "KUSHIDA" resolves to 144P/Kushida, but the elements identify
    # 147P/Kushida-Muramatsu, whose name also matches
    bodies = identify_target_dicts([_header('8699/u65z7a01r_shm.fits')])
    assert bodies[0]['full_name'] == '147P/Kushida-Muramatsu'

    bodies = identify_target_dicts([_header('8699/u65z7i01r_shm.fits')])
    assert bodies[0]['full_name'] == 'C/1999 T1 (McNaught-Hartley)'


def test_palpy_unavailable_degrades(monkeypatch: pytest.MonkeyPatch) -> None:
    # Without palpy the sky position check is skipped and the element match decides
    monkeypatch.setitem(sys.modules, 'targets.orbital_radec',
                        cast(ModuleType, None))
    bodies = identify_target_dicts([_header('2432/w0xh0101t_shf.fits')])
    assert bodies[0]['full_name'] == '5145 Pholus'


##########################################################################################
# Overrides and sentinels
##########################################################################################

def test_nh_survey_field_override() -> None:
    # Programs flagged as New Horizons KBO survey fields resolve to a placeholder body
    # via the _NH_SURVEY_DICT override.
    for spec in ('12535/ibr001faq_spt.fits',    # 12535_*
                 '6497/o45001010_spt.fits',      # 6497_1
                 '16183/iedk11dbq_spt.fits',     # 16183_*
                 '12887/ibzx01g4q_spt.fits'):    # 12887_1
        bodies = identify_target_dicts([_header(spec)])
        assert len(bodies) == 1
        assert bodies[0]['full_name'] == 'New Horizons survey field'
        assert bodies[0]['ttype'] == 'T'


def test_wildcard_override() -> None:
    # TARG_ID "13633_*" flags every target of program 13633 as a survey field
    header = {'FILENAME': 'x.fits', 'TARG_ID': '13633_5', 'TARGNAME': 'ANY'}
    bodies = identify_target_dicts([header])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == 'New Horizons survey field'


def test_nicknamed_targets_resolved_by_override() -> None:
    # Survey-internal and pre-announcement names mapped to real designations
    pytest.importorskip('palpy')
    bodies = identify_target_dicts([_header('9110/o6e945010_spt.fits')])    # "MINIXENA"
    assert bodies[0]['full_name'] == '55565 Aya'
    # Found only by the RA/dec element search (no name match); it must still be categorized
    # (ttype 'M' -> 'T'), not left as a raw minor planet.
    assert bodies[0]['ttype'] == 'T'

    # MT_LV1 is a FILE ephemeris, not a standard-body STD field, so Quaoar is identified
    # through the small-body path in its numbered minor-planet form.
    bodies = identify_target_dicts([_header('9678/j8i701011_spt.fits')])    # "OBJECTX"
    assert bodies[0]['full_name'] == '50000 Quaoar'
    assert bodies[0]['ttype'] == 'T'

    bodies = identify_target_dicts([_header('14498/id3t01n9q_spt.fits')])   # "P2010-V-C-OFFSET"
    assert bodies[0]['full_name'] == '332P/Ikeya-Murakami-C'


def test_occultation_adds_occulted_star() -> None:
    # Occultation overrides record the occulting body plus the occulted star (an added
    # 'dict'), exercising both the standard-body and small-body extra-body paths.
    def _names(visit: str) -> list[str]:
        return [b['full_name'] for b in identify_target_dicts([dict(h) for h in _SPT[visit]])]

    saturn = _names('v0qj04')          # 2771: Saturn-rings occultation (standard body)
    assert 'Saturn Rings' in saturn
    assert 'GSC 06323-01466' in saturn

    pluto = _names('f5br01')           # 8105: FGS Pluto occultation (standard body)
    assert '134340 Pluto' in pluto
    assert '2MASS J16324364-1038237' in pluto

    arrokoth = _names('fdfm01')        # 15003: Arrokoth occultation (small-body + dict)
    assert '486958 Arrokoth' in arrokoth
    assert '2MASS J19000829-2039378' in arrokoth


def test_no_target_sentinels() -> None:
    # Anti-solar pointings, slew tests, and parallel fields have no identifiable target
    for spec in ('1431/w0aqxp01t_shf.fits',     # ANTISUN (reject)
                 '3069/v0e10101t_shf.fits',     # ASLAG (reject)
                 '8800/u69va201r_shm.fits',     # 8800_* (reject)
                 '12537/ibu5110e1_spt.fits'):   # parallel field
        with pytest.raises(TargetIdentificationFailure):
            identify_target_dicts([_header(spec)])


def test_internal_calibration_targnames() -> None:
    # Lamp/calibration exposures (COS "WAVE", FOS "TALED") are not sky targets
    with pytest.raises(TargetIdentificationFailure):
        identify_target_dicts([_header('17780/lfee01fgq_spt.fits')])
    with pytest.raises(TargetIdentificationFailure):
        identify_target_dicts([_header('2569/y11e0c03t_shf.fits')])
    with pytest.raises(TargetIdentificationFailure):
        identify_target_dicts([{'FILENAME': 'x.fits', 'TARGNAME': 'DARK', 'TARG_ID': '1_1'}])


def test_unidentifiable_raises() -> None:
    header = {'FILENAME': 'x.fits', 'TARG_ID': '9999_1', 'TARGNAME': 'XYZZYQ'}
    with pytest.raises(TargetIdentificationFailure,
                       match='No target could be identified'):
        identify_target_dicts([header])


##########################################################################################
# Header parsing
##########################################################################################

def test_parse_mt_lv_std() -> None:
    header = _header('1206/z1cw0101t_shf.fits')
    assert _parse_mt_lv(header, 'MT_LV1') == {'STD': 'JUPITER'}
    assert _parse_mt_lv(header, 'MT_LV2') == {'STD': 'IO'}


def test_parse_mt_lv_value_split_mid_number() -> None:
    # The Pholus entry splits "O = 119.3837" across MT_LV1_1/MT_LV1_2 and
    # "EQUINOX = J2000" across MT_LV1_2/MT_LV1_3
    elements = _parse_mt_lv(_header('2432/w0xh0101t_shf.fits'), 'MT_LV1')
    assert elements['TYPE'] == 'ASTEROID'
    assert elements['A'] == 20.464038
    assert elements['O'] == 119.3837
    assert elements['M'] == 2.9208644
    assert elements['EPOCH'] == '27-JUN-1992'
    assert elements['EQUINOX'] == 'J2000'


def test_parse_mt_lv_stray_commas() -> None:
    # The 7239 Pholus entry has a leading comma and a comma inside the M value
    # ("M=2,3.618253" means M=23.618253)
    elements = _parse_mt_lv(_header('7239/n4je09010_spt.fits'), 'MT_LV1')
    assert elements['TYPE'] == 'ASTEROID'
    assert elements['M'] == 23.618253
    assert elements['A'] == 20.23369318
    assert elements['W'] == 354.569235


def test_parse_mt_lv_b1950_comet() -> None:
    elements = _parse_mt_lv(_header('2231/w0sb0101t_shf.fits'), 'MT_LV1')
    assert elements['TYPE'] == 'COMET'
    assert elements['Q'] == 1.5933855
    assert elements['T'] == '16-NOV-1991:04:38:54'
    assert elements['EPOCH'] == '31-OCT-1991'
    assert elements['EQUINOX'] == 'B1950'


def test_parse_mt_lv_other_kinds() -> None:
    assert _parse_mt_lv({'MT_LV1_1': 'FILE='}, 'MT_LV1') == {'FILE': ''}
    assert _parse_mt_lv({'MT_LV2_1': 'TYPE=POS_ANGLE, RAD = 0.001'},
                        'MT_LV2') == {'TYPE': 'POS_ANGLE', 'RAD': 0.001}
    assert _parse_mt_lv({}, 'MT_LV1') == {}
    assert _parse_mt_lv({'MT_LV1_1': '   '}, 'MT_LV1') == {}


def test_parse_mt_lv_drops_free_text() -> None:
    # Program 6854: a scheduling comment follows the STD field after a comma; it must
    # not be glued onto the value
    header = {'MT_LV1_1': 'STD = SATURN,CML OF SATURN FROM EARTH BETWEEN 0 60'}
    assert _parse_mt_lv(header, 'MT_LV1') == {'STD': 'SATURN'}
    bodies = identify_target_dicts([_header('6854/o4bd04vmq_spt.fits')])
    assert bodies[0]['name'] == 'Saturn'


def test_identify_targets_returns_context_product_paths(tmp_path: pathlib.Path) -> None:
    # identify_targets() is identify_target_dicts() followed by get_target_xml_path() on
    # each completed dict, so it returns the path of each body's context product. Wrap in
    # an overlay so any generated "_local" product cannot touch the committed cache.
    with use_local_xml_dir(tmp_path):
        paths = identify_targets([_header('1080/y0zz0301t_shf.fits')])   # Jupiter
    assert len(paths) == 1
    assert paths[0].name.startswith('planet.jupiter')
    assert paths[0].exists()


def test_collect_strings_skips_category() -> None:
    header = {'TARGNAME': 'IO-IN', 'TARKEY1': 'SATELLITE IO', 'TARGCAT': 'SOLAR SYSTEM',
              'TARDESCR': 'SOLAR SYSTEM;SATELLITE IO'}
    assert _collect_strings(header) == ['SOLAR SYSTEM;SATELLITE IO', 'IO-IN',
                                        'SATELLITE IO']


def test_norm_date() -> None:
    assert _norm_date('16-NOV-1991:04:38:54') == '16-NOV-1991:04:38:54'
    assert _norm_date('31-Oct-91') == '31-OCT-1991:00:00:00'
    assert _norm_date('5-JAN-05') == '05-JAN-2005:00:00:00'
    assert _norm_date('27-JUN-1992.') == '27-JUN-1992:00:00:00'


def test_mpc_date_to_str() -> None:
    assert _mpc_date_to_str('2019-04-27.0') == '27-APR-2019:00:00:00'
    assert _mpc_date_to_str('1991-08-26.19791') == '26-AUG-1991:04:44:59'

##########################################################################################
