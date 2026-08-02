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
from targets.hst_repairs import hst_repairs
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


def test_std_io_torus_from_compound_targname() -> None:
    # Program 8169: STD=JUPITER with an MT_LV2 "TYPE=TORUS" and TARKEY "TORUS", but the
    # TARGNAME is the compound "IO-T1-C23". "IO" is only a hyphen-separated token, not a
    # bare string, so the Io-torus test must match it against the tokens (not by list
    # membership) to recognize the Io plasma torus.
    bodies = identify_target_dicts([_header('8169/o5h902010_spt.fits')])
    assert [(b['full_name'], b['ttype']) for b in bodies] == [
        ('Io Torus', 't'), ('Jupiter', 'P'), ('Io', 'S'), ('Jupiter System', 'p')]


def test_std_saturn_rings_from_equatorial_torus() -> None:
    # Program 8802: TARKEY "RING" + MT_LV2 "TYPE=TORUS" in the equatorial plane (POLE_LAT
    # 90, LAT 0, LONG 90) identifies Saturn's rings. The torus RAD=50000 sits below Saturn's
    # radius -- a nominal aperture-centering value for the F-ring ansa, not the ring radius
    # -- so RAD must not gate the identification. Pandora and Prometheus come from TARGNAME.
    bodies = identify_target_dicts([_header('8802/u6ema001m_shm.fits')])
    assert [(b['full_name'], b['ttype']) for b in bodies] == [
        ('Saturn Rings', 'R'), ('Saturn', 'P'), ('Pandora', 'S'), ('Prometheus', 'S'),
        ('Saturn System', 'p')]


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


def test_comet_designation_overrides_incompatible_elements() -> None:
    # Program 2231: TARGNAME "COMET-FAYE-1984XI" names 4P/Faye two independent ways -- the
    # discoverer name "FAYE" and the old-style designation "1984 XI". When the header
    # orbit is corrupted so it no longer matches Faye (here Q is forced to 4.78), the
    # agreeing designation+name is trusted over the unreliable orbit and Faye is still
    # identified (with a logged warning), rather than the identification failing.
    pytest.importorskip('palpy')
    header = _header('2231/w0sb0101t_shf.fits')
    assert 'Q = 1.5933855' in header['MT_LV1_1']
    header['MT_LV1_1'] = header['MT_LV1_1'].replace('Q = 1.5933855', 'Q = 4.78')
    bodies = identify_target_dicts([header])
    assert [(b['full_name'], b['ttype']) for b in bodies] == [('4P/Faye', 'C')]


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
    # C/1991 T2. The 97P designation is not corroborated by the discoverer name, so it is
    # not trusted over the elements.
    bodies = identify_target_dicts([_header('2442/w0yy0201t_shf.fits')])
    assert bodies[0]['full_name'] == 'C/1991 T2 (Shoemaker-Levy)'


def test_comet_designation_trusted_over_corrupt_ephemeris() -> None:
    # Visit U31501: the header names comet C/1984 K1 (Shoemaker) three ways ("C/1984 K1",
    # "1984f", "1985 XII") plus the surname "SHOEMAKER", but its orbital elements are
    # corrupted -- Shoemaker's perihelion distance and time are paired with the orbital
    # angles of C/1983 O1 (Cernis). The element test therefore matches Cernis, not
    # Shoemaker. Because a formal designation and the discoverer name agree on Shoemaker,
    # that identification is trusted over the unreliable orbit and Cernis is not
    # substituted.
    bodies = identify_target_dicts([_header('5834/u3150101t_shm.fits')])
    assert [(b['full_name'], b['ttype']) for b in bodies] == [('C/1984 K1 (Shoemaker)', 'C')]


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
    with pytest.raises(TargetIdentificationFailure, match='could not be identified'):
        identify_target_dicts([header])


def test_sw3_fragment_abbreviated_in_targname() -> None:
    # TARGNAME "SW3C" abbreviates 73P/Schwassmann-Wachmann 3 fragment C. The repair has to
    # supply the comet number, the "/" and the fragment letter, because the generic
    # comet-number pattern would otherwise claim the string first.
    bodies = identify_target_dicts([_header('8699/u65z7u01m_shm.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '73P/Schwassmann-Wachmann 3-C'
    assert bodies[0]['ttype'] == 'C'


def test_sw3_accepts_either_separator_and_a_missing_fragment() -> None:
    # The comet number may be attached with a slash as well as a dash, and the fragment
    # letter may be absent. A slash form left to the generic comet-number pattern becomes
    # "73P/SW 3", and an absent fragment used to leave a trailing dash; neither identifies
    # anything.
    assert hst_repairs('73P-SW3-C') == (['73P/SCHWASSMANN-WACHMANN 3-C'], 'C')
    assert hst_repairs('73P/SW3-C') == (['73P/SCHWASSMANN-WACHMANN 3-C'], 'C')
    assert hst_repairs('73P/SW3') == (['73P/SCHWASSMANN-WACHMANN 3'], 'C')
    assert hst_repairs('SW3') == (['73P/SCHWASSMANN-WACHMANN 3'], 'C')


def test_one_linear_chosen_from_many_by_elements() -> None:
    # TARGNAME and TARDESCR say only "LINEAR", which names 208 comets and the asteroid
    # 118401 LINEAR. Only the orbital elements can single one out.
    pytest.importorskip('palpy')
    bodies = identify_target_dicts([_header('8276/o67r09010_spt.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == 'C/1999 S4 (LINEAR)'
    assert bodies[0]['ttype'] == 'C'


def test_shoemaker_levy_chosen_from_many_by_elements() -> None:
    # Two headers: "WAVE" names nothing, and "COMET-SL-OFFSET" reduces to a bare "SL",
    # which is deliberately not expanded because the Shoemaker-Levy name alone spans 13
    # comets. The elements pick C/1991 T2 out of them.
    bodies = identify_target_dicts([_header('2442/z0yy0e01t_shf.fits'),
                                    _header('2442/z0yy0e02t_shf.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == 'C/1991 T2 (Shoemaker-Levy)'
    assert bodies[0]['ttype'] == 'C'


def test_minor_planet_designation_names_a_comet() -> None:
    # TARGNAME "04PY42" and TARDESCR "scattered centaur" both describe a minor planet, but
    # 2004 PY42 was later found to be the comet 167P/CINEOS. The categorizer recognizes the
    # comet designation and overrides the minor planet type.
    bodies = identify_target_dicts([_header('10514/j9fwo9010_spt.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '167P/CINEOS'
    assert bodies[0]['ttype'] == 'C'


def test_two_digit_year_designation_repaired() -> None:
    # The step the test above depends on: "04PY42" is expanded to a full designation, and
    # only then can it be recognized as 167P/CINEOS.
    assert hst_repairs('04PY42') == (['2004 PY42'], '')


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
    # Patch the name as imported into identify_targets, where the element search is called.
    # Use the module object (via sys.modules) rather than the dotted string, because the
    # `targets.identify_targets` attribute is shadowed by the identify_targets function
    # re-exported from the package.
    monkeypatch.setattr(sys.modules['targets.identify_targets'], 'mpc_query_by_elements',
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
# Minor planets whose catalog entry has moved on since the observation
##########################################################################################

def test_tno_designation_has_since_been_numbered() -> None:
    # TARGNAME "98UU43" carries only the provisional designation; the body has been
    # numbered since, so the identification supplies the number the header never had.
    bodies = identify_target_dicts([_header('9060/u6ht4501m_shm.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '(523955) 1998 UU43'
    assert bodies[0]['mnum'] == '523955'
    assert bodies[0]['ttype'] == 'T'


def test_tno_designation_has_since_been_named() -> None:
    # TARGNAME "05TO74" is a bare designation; 2005 TO74 has since become 385695 Clete, so
    # the identification supplies both the number and the name.
    bodies = identify_target_dicts([_header('11113/u9yzf901m_shm.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '385695 Clete'
    assert bodies[0]['name'] == 'Clete'
    assert bodies[0]['desig'] == '2005 TO74'
    assert bodies[0]['ttype'] == 'T'


def test_tno_carries_an_alternate_designation() -> None:
    # 2000 FS53 is also catalogued as 1999 KS16. The alias travels with the body, which is
    # what lets an existing context product gain the designation it was missing.
    bodies = identify_target_dicts([_header('9060/u6htc701r_shm.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '2000 FS53'
    assert bodies[0]['aliases'] == ['1999 KS16']
    assert bodies[0]['ttype'] == 'T'


def test_reidentified_tno_keeps_its_earlier_designation() -> None:
    # 2001 OQ108 was re-identified with the earlier apparition 2001 KR76, which survives as
    # an alias rather than replacing the designation the header used.
    bodies = identify_target_dicts([_header('10800/u9rp2501m_shm.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '2001 OQ108'
    assert bodies[0]['aliases'] == ['2001 KR76']
    assert bodies[0]['ttype'] == 'T'


def test_alternate_designation_reaches_the_context_product(
        tmp_path: pathlib.Path) -> None:
    # The alias is what the context product is updated with, so drive the full path into a
    # throwaway overlay and confirm a product is produced for the body.
    with use_local_xml_dir(tmp_path):
        paths = identify_targets([_header('9060/u6htc701r_shm.fits')])
    assert len(paths) == 1
    assert paths[0].name.startswith('trans-neptunian_object.2000_fs53')
    assert paths[0].exists()


##########################################################################################
# Refining a minor planet into asteroid, Centaur or TNO
##########################################################################################

def test_neptune_trojan_is_a_tno_not_a_centaur() -> None:
    # 2005 TN53 is a Neptune Trojan with a = 30.04 AU, just above the 30.03 AU boundary.
    # Were the boundary Neptune's own 30.1 AU, this body would fall through to the Centaur
    # test -- its perihelion of 28.1 AU is far beyond Jupiter -- and be mislabelled.
    bodies = identify_target_dicts([_header('12468/ibtp01dmq_spt.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '2005 TN53'
    assert bodies[0]['ttype'] == 'T'
    assert 30.03 <= bodies[0]['A'] < 30.1


def test_jupiter_crosser_is_an_asteroid() -> None:
    # 2003 CC22 has a = 7.27 AU and q = 4.17 AU, so the JPL test (a >= 5.5) calls it a
    # Centaur while the MPC test (q >= 5.2) does not. With the elements ambiguous and the
    # body absent from the Centaur database, the SPT file's "ASTEROID" decides.
    bodies = identify_target_dicts([_header('10800/u9rpe301m_shm.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '2003 CC22'
    assert bodies[0]['ttype'] == 'A'


def test_jupiter_crosser_with_wider_orbit_is_still_an_asteroid() -> None:
    # The same ambiguity for 2004 DA62, further out at a = 7.67 AU
    bodies = identify_target_dicts([_header('10800/j9rpe5010_spt.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '2004 DA62'
    assert bodies[0]['ttype'] == 'A'


def test_damocloid_database_settles_ambiguous_elements() -> None:
    # 2004 PA44 has the same ambiguous signature, a = 14.21 AU with q = 3.41 AU, and its
    # SPT file likewise says "ASTEROID". The damocloid database is consulted before the
    # orbit is examined at all, and it calls this one a Centaur.
    bodies = identify_target_dicts([_header('10800/j9rpe6010_spt.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '(154783) 2004 PA44'
    assert bodies[0]['ttype'] == 'H'


def test_hidalgo_is_an_asteroid_not_a_centaur() -> None:
    # 944 Hidalgo has a = 5.74 AU, beyond the 5.5 AU the JPL definition would accept as a
    # Centaur, but its perihelion of 1.95 AU is well inside Jupiter's orbit.
    bodies = identify_target_dicts([_header('4784/y19y0301t_shf.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '944 Hidalgo'
    assert bodies[0]['ttype'] == 'A'


##########################################################################################
# Minor planets identified without a usable name
##########################################################################################

def test_kbo_without_a_designation_identified_by_orbit() -> None:
    # Neither TARGNAME "OBJ-KBO30726D" nor TARDESCR "KBO K30726D" contains a designation
    # any catalog knows; the body is reached from its orbit alone.
    pytest.importorskip('palpy')
    bodies = identify_target_dicts([_header('10545/j9fs17011_spt.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '(120178) 2003 OP32'
    assert bodies[0]['ttype'] == 'T'


def test_unambiguous_name_kept_despite_sky_position_mismatch() -> None:
    # TARGNAME "00WW12" names 2000 WW12 unambiguously, but the header's orbit puts it far
    # from RA_TARG/DEC_TARG and no catalog body lands near the pointing either. The name is
    # trusted rather than discarded, and the mismatch is reported as a warning.
    pytest.importorskip('palpy')
    bodies = identify_target_dicts([_header('11113/u9yzg201m_shm.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '2000 WW12'
    assert bodies[0]['ttype'] == 'T'


def test_kagara_identified_by_number() -> None:
    # TARGNAME "KAGARA" is a mangled rendering of 469705 ǂKá̦gára. The MPC resolves no
    # spelling of the name, so the repair supplies the minor planet number instead, and the
    # orbit then refines the body to a TNO.
    # The repair itself: anyascii's "qcKagara" is a faithful transliteration but resolves
    # nothing, so the number is the only usable handle.
    assert hst_repairs('KAGARA') == (['(469705)'], 'M')

    bodies = identify_target_dicts([_header('17707/iffc01neq_spt.fits')])
    assert len(bodies) == 1
    assert bodies[0]['mnum'] == '469705'
    assert bodies[0]['full_name'] == '469705 ǂKá̦gára'
    assert bodies[0]['ttype'] == 'T'


##########################################################################################
# 288P, a comet number that names a minor planet
##########################################################################################

def test_288p_with_numeric_suffix() -> None:
    # TARGNAME "288P3" carries a trailing visit index. 288P is absent from the comet
    # database, existing only as the minor planet (300163) 2006 VW139.
    bodies = identify_target_dicts([_header('16192/ieaf52g0q_spt.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '(300163) 2006 VW139'
    assert bodies[0]['ttype'] == 'A'


def test_288p_binary_component_is_not_a_cometary_fragment() -> None:
    # TARGNAME "288P-B" names a component of the binary, not a fragment, and both share the
    # system's heliocentric orbit. Read as a fragment it becomes "288P/B", which identifies
    # nothing; element matching then settles on 133P/Elst-Pizarro, 1.85 degrees away in
    # inclination.
    bodies = identify_target_dicts([_header('16687/ienl03oxq_spt.fits')])
    assert len(bodies) == 1
    assert bodies[0]['full_name'] == '(300163) 2006 VW139'
    assert bodies[0]['ttype'] == 'A'


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


def test_standard_body_plus_co_observed_comet_via_override() -> None:
    # Program 13936 target 13936_1 is "Mars during the Comet Siding Spring encounter"
    # (STD=MARS); the comet C/2013 A1 is named only in TARDESCR. A '13936_1' override adds
    # it as an extra 'dict', so Mars is still identified and the comet appended.
    bodies = identify_target_dicts([_header('13936/icpe22biq_spt.fits')])
    assert [(b['full_name'], b['ttype']) for b in bodies] == [
        ('Mars', 'P'), ('C/2013 A1 (Siding Spring)', 'C')]

    # The override is scoped to 13936_1, not the whole program: target 13936_3 is plain
    # Mars and must not pick up the comet.
    mars = identify_target_dicts([_header('13936/jcpea2011_spt.fits')])
    assert [b['full_name'] for b in mars] == ['Mars']


def test_shoemaker_levy_9_added_to_jupiter_impact_program() -> None:
    # Program 5642 (Storrs) monitored Jupiter (STD=JUPITER) through the 1994 Shoemaker-Levy
    # 9 impacts without naming the comet in its headers. A '5642_*' override adds the parent
    # comet D/1993 F2 (Shoemaker-Levy 9) to every target in the program.
    disk = identify_target_dicts([_header('5642/u2fi0c01t_shm.fits')])   # JUPITER-WF
    assert [(b['full_name'], b['ttype']) for b in disk] == [
        ('Jupiter', 'P'), ('D/1993 F2 (Shoemaker-Levy 9)', 'C')]

    # The comet is appended even on the campaign's Io-torus visits (target 5642_11), after
    # Jupiter and its torus/satellite/system bodies. The full visit is needed for the torus
    # geometry to resolve.
    torus = identify_target_dicts([dict(h) for h in _SPT['z2fi1x']])     # IO-TORUS-W1
    names = [b['full_name'] for b in torus]
    assert names[0] == 'Jupiter'
    assert 'Io Torus' in names
    assert names[-1] == 'D/1993 F2 (Shoemaker-Levy 9)'

    # A concurrent, unrelated Jupiter program (5217, aurora/airglow) must not pick up SL9.
    aurora = identify_target_dicts([_header('5217/u2eq0101t_shm.fits')])
    assert [b['full_name'] for b in aurora] == ['Jupiter']


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
                       match='could not be identified'):
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


def test_identify_targets_spans_multiple_visits(tmp_path: pathlib.Path) -> None:
    # identify_target_dicts() handles exactly one visit and rejects headers from more than
    # one; identify_targets() groups them by visit and identifies each independently, so a
    # caller can hand it a whole directory of files. The result is the per-visit results
    # concatenated in visit order, duplicates included.
    jupiter = _header('1080/y0zz0301t_shf.fits')
    saturn = _header('6854/o4bd04vmq_spt.fits')
    assert jupiter['FILENAME'][:6] != saturn['FILENAME'][:6]

    with pytest.raises(ValueError, match='Multiple visits among headers provided'):
        identify_target_dicts([jupiter, saturn])

    with use_local_xml_dir(tmp_path):
        paths = identify_targets([jupiter, saturn])
        separately = identify_targets([jupiter]) + identify_targets([saturn])

    assert [p.name for p in paths] == [p.name for p in separately]
    assert paths[0].name.startswith('planet.jupiter')
    assert paths[-1].name.startswith('planet.saturn')


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
