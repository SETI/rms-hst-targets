##########################################################################################
# targets/tests/test_orbital_radec.py
##########################################################################################
"""Validate orbital_radec against JPL Horizons geocentric astrometric (J2000)
positions for an asteroid (Ceres) and a highly eccentric retrograde comet
(1P/Halley).  With perturb=True the agreement is ~0.01-0.02 arcsec; the pure
two-body path (perturb=False) is expected to drift a few arcsec away from the
element epoch, which is asserted as a loose sanity bound only.
"""

import math

import pytest

palpy = pytest.importorskip("palpy")            # skip if PAL wrapper absent

# Imported after importorskip: orbital_radec imports palpy at load, so this must
# follow the skip guard, not sit at the top of the file.
from orbital_radec import asteroid_radec, comet_radec  # noqa: E402


def _sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Angular separation between two (deg, deg) positions, in arcsec."""
    d = palpy.dsep(math.radians(ra1), math.radians(dec1),
                   math.radians(ra2), math.radians(dec2))
    return math.degrees(d) * 3600.0


# --- Ceres --------------------------------------------------------------------
# Osculating elements from JPL Horizons @ 2011-Dec-25 00:00 TDB
# (heliocentric, ecliptic J2000).  a & M drive the asteroid interface; the same
# orbit is also expressed as q & Tp for the comet interface.
_CERES = {'a': 2.767838198538331, 'e': 0.07812082423798181, 'incl': 10.58650752808586,
          'node': 80.36346438361552, 'arg_peri': 72.29347619416765,
          'mean_anom': 225.1783121980145, 'epoch': '25-DEC-2011:00:00:00'}
_CERES_Q = 2.551612397111145
_CERES_TP = "14-SEP-2013:21:25:49.149"          # perihelion time, TDB (JD 2456550.392929968)
# Horizons astrometric RA/Dec, geocentric J2000, @ 2012-Jun-25 00:00 UTC
_CERES_TIME = "25-JUN-2012:00:00:00"
_CERES_RADEC = (59.01557, 15.91885)

# --- 1P/Halley ----------------------------------------------------------------
# Osculating elements from JPL Horizons @ 2012-Jun-25 00:00 TDB; perihelion 1986.
_HALLEY = {'q': 0.5779409967071418, 'e': 0.9679696861149192, 'incl': 161.9933563732279,
           'node': 59.78974738386672, 'arg_peri': 112.6503018874864,
           'peri_time': '05-DEC-1985:02:41:21.140',   # Tp, TDB (JD 2446404.612050227)
           'epoch': '25-JUN-2012:00:00:00'}           # osculation date
# Horizons astrometric RA/Dec, geocentric J2000, @ 2013-Jun-25 00:00 UTC
_HALLEY_TIME = "25-JUN-2013:00:00:00"
_HALLEY_RADEC = (126.73603, 2.08732)


def test_asteroid_matches_horizons() -> None:
    r = asteroid_radec(**_CERES, time=_CERES_TIME,
                       epoch_scale="TDB", time_scale="UTC")
    assert _sep_arcsec(r.ra, r.dec, *_CERES_RADEC) < 0.1


def test_comet_matches_horizons() -> None:
    r = comet_radec(**_HALLEY, time=_HALLEY_TIME,
                    peri_time_scale="TDB", epoch_scale="TDB", time_scale="UTC")
    assert _sep_arcsec(r.ra, r.dec, *_HALLEY_RADEC) < 0.1


# --- B1950 elements (same orbits, referred to the B1950 ecliptic/equinox) -----
# From JPL Horizons REF_SYSTEM=B1950; equinox='B1950' must rotate these to J2000
# and reproduce the same sky position (to the frame-approximation floor ~0.5").
_CERES_B1950 = {'a': 2.767838198538330, 'e': 0.07812082423798154, 'incl': 10.58592578475366,
                'node': 79.69966433365853, 'arg_peri': 72.25812943239636,
                'mean_anom': 225.1783121980145, 'epoch': '25-DEC-2011:00:00:00'}
_HALLEY_B1950 = {'q': 0.5779409967071421, 'e': 0.9679696861149191, 'incl': 161.9905270507656,
                 'node': 59.07313305678021, 'arg_peri': 112.6313020090262,
                 'peri_time': '05-DEC-1985:02:41:21.140', 'epoch': '25-JUN-2012:00:00:00'}


def test_asteroid_b1950_rotated_to_j2000() -> None:
    r = asteroid_radec(**_CERES_B1950, time=_CERES_TIME, equinox="B1950",
                       epoch_scale="TDB", time_scale="UTC")
    assert _sep_arcsec(r.ra, r.dec, *_CERES_RADEC) < 1.0


def test_comet_b1950_rotated_to_j2000() -> None:
    r = comet_radec(**_HALLEY_B1950, time=_HALLEY_TIME, equinox="B1950",
                    peri_time_scale="TDB", epoch_scale="TDB", time_scale="UTC")
    assert _sep_arcsec(r.ra, r.dec, *_HALLEY_RADEC) < 1.0


def test_b1950_without_rotation_is_wrong() -> None:
    """Guard: treating B1950 elements as J2000 must be far off (~arcmin)."""
    r = asteroid_radec(**_CERES_B1950, time=_CERES_TIME, equinox="J2000",
                       epoch_scale="TDB", time_scale="UTC")
    assert _sep_arcsec(r.ra, r.dec, *_CERES_RADEC) > 60.0


def test_asteroid_and_comet_interfaces_agree() -> None:
    """The a,M (JFORM=2) and q,T (JFORM=3) forms of one orbit must coincide."""
    ra = asteroid_radec(**_CERES, time=_CERES_TIME,
                        epoch_scale="TDB", time_scale="UTC")
    rc = comet_radec(_CERES_Q, _CERES["e"], _CERES["incl"], _CERES["node"],
                     _CERES["arg_peri"], _CERES_TP, _CERES["epoch"],
                     time=_CERES_TIME, peri_time_scale="TDB",
                     epoch_scale="TDB", time_scale="UTC")
    assert _sep_arcsec(ra.ra, ra.dec, rc.ra, rc.dec) < 0.01


def test_twobody_is_exact_at_epoch() -> None:
    """Pure two-body reproduces the state exactly at the element epoch."""
    # Evaluate at the epoch instant in UTC to match the Horizons UTC reference
    # (the elements' TDB epoch and 00:00 UTC differ by TDB-UTC ~ 66 s).
    r = asteroid_radec(**_CERES, time="25-DEC-2011:00:00:00",
                       epoch_scale="TDB", time_scale="UTC", perturb=False)
    # Horizons astrometric @ 2011-Dec-25 00:00 UTC.
    assert _sep_arcsec(r.ra, r.dec, 357.17819, -11.93995) < 0.1


def test_perturbations_reduce_drift() -> None:
    """Perturbed propagation must beat pure two-body far from the epoch."""
    common = dict(**_CERES, time=_CERES_TIME, epoch_scale="TDB", time_scale="UTC")
    two_body = asteroid_radec(**common, perturb=False)
    perturbed = asteroid_radec(**common, perturb=True)
    err_2body = _sep_arcsec(two_body.ra, two_body.dec, *_CERES_RADEC)
    err_pert = _sep_arcsec(perturbed.ra, perturbed.dec, *_CERES_RADEC)
    assert err_pert < 0.1 < err_2body

##########################################################################################
