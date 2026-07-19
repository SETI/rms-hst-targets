##########################################################################################
# identify_target.py
##########################################################################################
"""Identify the target bodies of an HST observation from its SPT/SHF header.

The `identify_target` function examines the target description keywords of an SPT or SHF
header (TARGNAME, TARDESCR, TARKEY*, and the MT_LV* moving target descriptions) and
returns a list of dictionaries, one for each body relevant to the observation. Bodies
are identified by name whenever possible and are confirmed against the orbital elements
embedded in the MT_LV1_* keywords: comets by direct element comparison, minor planets by
propagating their catalog orbit to the observation time and comparing the sky position
to RA_TARG/DEC_TARG. When no name can be recognized, the body is identified by searching
the comet database or the Minor Planet Center for the nearest orbital elements.

To use::

    from targets.identify_target import identify_target, TargetIdentificationFailure

"""

import math
from datetime import datetime, timedelta
from logging import Logger

from targets                         import cometdb, mpc_tools
from targets._utils                  import (_collect_strings, _headers_by_visit,
                                             _parse_mt_lv, _unique_targets,
                                             categorize_minor_planet,
                                             TargetIdentificationFailure)
from targets._HST_PROGRAM_OVERRIDES  import _HST_PROGRAM_OVERRIDES
from targets.hst_repairs             import hst_repairs
from targets.identify_standard_body  import identify_standard_body
from targets.targettype              import TargetType

__all__ = ['identify_target']


from targets._DISALLOWED_MINOR_PLANET_NAMES import _DISALLOWED_MINOR_PLANET_NAMES
from targets.comet_identifiers import comet_identifiers
from targets.minor_planet_identifiers import minor_planet_identifiers

_DISALLOWED_UC = {name.upper() for name in _DISALLOWED_MINOR_PLANET_NAMES}

_MINOR_PLANET_TTYPES = set(TargetType.MCODES + TargetType.MINOR_PLANET)


# A minor planet identified by name is confirmed if its propagated sky position falls
# within max(radec_tolerance, _RADEC_TOLERANCE_PER_YEAR * epoch gap) of RA_TARG/DEC_TARG,
# capped at _RADEC_TOLERANCE_MAX. The per-year term allows for the drift between the
# ephemeris HST planned with and the (often much later) catalog orbit; newly discovered
# TNOs commonly show tens of arcsec of drift per year of epoch gap. The whole tolerance
# scales as 1/distance, because a fixed orbit uncertainty subtends a larger angle for a
# body observed close to the Earth (e.g., a near-Earth asteroid during a flyby).
_RADEC_TOLERANCE_PER_YEAR = 30.     # arcsec per year between catalog epoch and obs time
_RADEC_TOLERANCE_MAX = 600.         # arcsec, upper limit before distance scaling

# A minor planet identified by an element search alone (no name) must fall this close to
# RA_TARG/DEC_TARG (scaled as above) and must beat the second-nearest candidate by a
# factor of two to be believed.
_FALLBACK_RADEC_TOLERANCE = 60.     # arcsec
_FALLBACK_CANDIDATES = 25           # element-search candidates to test by sky position

# RA_TARG/DEC_TARG can only confirm or refute a body if it tracks the header's own
# ephemeris (it normally reproduces the MT_LV1 orbit to ~arcsec; see
# support/reality_check_radec.py). When it is farther than this from the header orbit,
# the pointing is offset from the body and the sky-position tests are skipped.
_SELF_CONSISTENCY_MAX = 60.         # arcsec, before distance scaling

# When a body identified by name fails the sky-position test but its catalog orbit still
# broadly matches the header elements, the mismatch is attributed to an orbit revision
# after the observation (common for single-opposition TNOs) rather than to a wrong
# identification. Larger discrepancies mean the name resolved to the wrong body.
_REVISED_ORBIT_RMS = 1.0

_MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
           'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

##########################################################################################
# Date handling
##########################################################################################


def _hst_time(text: str) -> datetime:
    """Parse an HST "YYYY.DDD:hh:mm:ss" (day-of-year) time into a datetime."""

    left, hh, mm, ss = text.strip().split(':')
    year, doy = left.split('.')
    return (datetime(int(year), 1, 1)
            + timedelta(days=int(doy) - 1, hours=int(hh), minutes=int(mm),
                        seconds=int(ss)))


def _obs_midpoint(header: dict) -> datetime | None:
    """The midpoint of PSTRTIME/PSTPTIME, rounded to the second; None if unavailable."""

    try:
        t0 = _hst_time(str(header['PSTRTIME']))
        t1 = _hst_time(str(header['PSTPTIME']))
    except (KeyError, ValueError):
        return None

    mid = t0 + (t1 - t0) / 2
    return (mid + timedelta(seconds=0.5)).replace(microsecond=0)


def _dt_to_str(dt: datetime) -> str:
    """Format a datetime as "DD-MON-YYYY:hh:mm:ss"."""

    return (f'{dt.day:02d}-{_MONTHS[dt.month - 1]}-{dt.year:04d}:'
            f'{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}')


def _epoch_dt(text: str) -> datetime:
    """Parse a normalized "DD-MON-YYYY:hh:mm:ss" date back into a datetime."""

    datep, _, timep = text.partition(':')
    dd, mon, yy = datep.split('-')
    hh, mm, ss = timep.split(':')
    return datetime(int(yy), _MONTHS.index(mon.upper()) + 1, int(dd),
                    int(hh), int(mm), int(ss))


def _angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Great-circle separation between two (RA, Dec) points in degrees, in arcsec."""

    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    a = (math.sin((d2 - d1) / 2.)**2
         + math.cos(d1) * math.cos(d2) * math.sin((r2 - r1) / 2.)**2)
    return math.degrees(2. * math.asin(min(1., math.sqrt(a)))) * 3600.


##########################################################################################
# Sky positions
##########################################################################################

def _elements_to_j2000(elements: dict, logger: Logger | None) -> dict:
    """Rotate B1950 orbital elements to J2000 if needed and possible."""

    if elements.get('EQUINOX', 'J2000') not in ('B1950', '1950', 'FK4'):
        return elements

    try:
        from targets.orbital_radec import rotate_elements_to_j2000
    except ImportError:                                     # pragma: no cover
        logger and logger.warning('palpy unavailable; B1950 elements not rotated '
                                  'to J2000')
        return elements

    logger and logger.info('Rotating B1950 orbital elements to J2000')
    return rotate_elements_to_j2000(elements, equinox=elements['EQUINOX'])


def radec_offset(
    body: dict,
    obs_time: datetime,
    ra_targ: float,
    dec_targ: float,
    logger: Logger | None
) -> tuple[float, float] | None:
    """Propagate a set of minor planet orbital elements to the observation time and
    compare the sky position to the header target position.

    Parameters:
        body: A dictionary of orbital elements including "A", "E", "I", "O", "W", "M",
            and "EPOCH": either a minor planet dictionary carrying its catalog elements
            or the parsed MT_LV1 elements of the header itself.
        obs_time: The observation midpoint.
        ra_targ: The header RA_TARG in degrees.
        dec_targ: The header DEC_TARG in degrees.
        logger: An optional Logger for messages.

    Returns:
        A tuple `(offset, gap, delta)` giving the angular offset in arcsec, the time
        between the element epoch and the observation in years, and the geocentric
        distance in AU; None if the position could not be calculated.
    """

    missing = [key for key in ('A', 'E', 'I', 'O', 'W', 'M', 'EPOCH')
               if key not in body]
    if missing:
        logger and logger.info(f'Sky position not computed; elements missing {missing}')
        return None

    try:
        from targets.orbital_radec import asteroid_radec
    except ImportError:
        logger and logger.warning('palpy unavailable; sky position check skipped')
        return None

    obs = _dt_to_str(obs_time)
    try:
        # Propagate with major-planet perturbations so a stale catalog epoch is not
        # itself the source of the offset; fall back to two-body if the perturbation
        # integrator rejects the elements
        try:
            result = asteroid_radec(a=body['A'], e=body['E'], incl=body['I'],
                                    node=body['O'], arg_peri=body['W'],
                                    mean_anom=body['M'], epoch=body['EPOCH'],
                                    time=obs, perturb=True)
        except Exception:
            result = asteroid_radec(a=body['A'], e=body['E'], incl=body['I'],
                                    node=body['O'], arg_peri=body['W'],
                                    mean_anom=body['M'], epoch=body['EPOCH'],
                                    time=obs, perturb=False)
    except Exception as e:
        logger and logger.warning(f'Sky position calculation failed: {e}')
        return None

    offset = _angsep_arcsec(ra_targ, dec_targ, result.ra, result.dec)
    gap = abs((obs_time - _epoch_dt(body['EPOCH'])).days) / 365.25
    return (offset, gap, result.delta)


def _position_tolerance(base: float, gap: float, delta: float) -> float:
    """The tolerance in arcsec on a sky-position offset.

    Parameters:
        base: The base tolerance in arcsec.
        gap: Years between the catalog epoch and the observation.
        delta: The geocentric distance of the body in AU.
    """

    tolerance = min(max(base, _RADEC_TOLERANCE_PER_YEAR * gap), _RADEC_TOLERANCE_MAX)
    return tolerance * max(1., 1. / delta)


def minor_planet_by_radec(
    elements: dict,
    obs_time: datetime | None,
    ra_targ: float | None,
    dec_targ: float | None,
    mp_rms: float,
    logger: Logger | None
) -> tuple[dict, float] | None:
    """Identify a minor planet by searching the MPC for nearby orbital elements and
    selecting the candidate closest to the header target position.

    Parameters:
        elements: The J2000 orbital elements from the header.
        obs_time: The observation midpoint; None if unavailable.
        ra_targ: The header RA_TARG in degrees; None if unavailable.
        dec_targ: The header DEC_TARG in degrees; None if unavailable.
        mp_rms: Upper limit on the fractional RMS element discrepancy for a candidate to
            be considered at all.
        logger: An optional Logger for messages.

    Returns:
        A tuple `(body, rms)` for the winning candidate, or None if no candidate came
        believably close to the target position.
    """

    if obs_time is None or ra_targ is None or dec_targ is None:
        logger and logger.info('Position-based identification unavailable; observation '
                               'time or target position missing')
        return None

    # A position search is meaningless unless RA_TARG tracks the header ephemeris
    self_info = radec_offset(elements, obs_time, ra_targ, dec_targ, logger)
    if self_info is not None:
        self_offset, _, self_delta = self_info
        if self_offset > _position_tolerance(_SELF_CONSISTENCY_MAX, 0., self_delta):
            logger and logger.info(f'RA_TARG/DEC_TARG is {self_offset:.1f}" from the '
                                   'header ephemeris; position-based identification '
                                   'unavailable')
            return None

    try:
        results = mpc_tools.mpc_query_by_elements(elements,
                                                  count=_FALLBACK_CANDIDATES,
                                                  logger=logger)
    except Exception as e:
        logger and logger.error(f'MPC element search failed: {e}')
        return None

    candidates = []     # (offset, gap, delta, body, rms)
    for body, rms in results:
        if rms > mp_rms:
            continue
        info = radec_offset(body, obs_time, ra_targ, dec_targ, logger)
        if info is None:
            continue
        offset, gap, delta = info
        candidates.append((offset, gap, delta, body, rms))
        logger and logger.info(f'Candidate {body["full_name"]}: element rms '
                               f'{rms:.4f}, sky offset {offset:.1f}"')

    if not candidates:
        logger and logger.info('No MPC candidate passed the element and position tests')
        return None

    candidates.sort(key=lambda c: c[0])
    offset, gap, delta, body, rms = candidates[0]

    tol = _position_tolerance(_FALLBACK_RADEC_TOLERANCE, gap, delta)
    if offset > tol:
        logger and logger.info(f'Nearest candidate {body["full_name"]} is {offset:.1f}" '
                               f'from RA_TARG/DEC_TARG, beyond tolerance {tol:.1f}"')
        return None
    if len(candidates) > 1 and offset > candidates[1][0] / 2.:
        logger and logger.info('Position test is ambiguous; the two nearest candidates '
                               f'are {offset:.1f}" and {candidates[1][0]:.1f}" from '
                               'RA_TARG/DEC_TARG')
        return None

    logger and logger.info(f'Minor planet selected by sky position: {body["full_name"]} '
                           f'({offset:.1f}" from RA_TARG/DEC_TARG)')
    return (body, rms)


##########################################################################################
# identify_target()
##########################################################################################


def _is_mp(ttypes):
    return bool(_MINOR_PLANET_TTYPES & set(ttypes))


def _is_comet(ttypes):
    return TargetType.COMET in ttypes


def _has_orbital_elements(elements):
    """True if a parsed MT_LV1 dictionary carries usable orbital elements (as opposed to
    an "STD =", "FILE =", or empty ephemeris field)."""
    return 'E' in elements and ('A' in elements or 'Q' in elements)


def identify_target(
    headers: list[dict], *,
    comet_rms: float = 0.1,
    mp_rms: float = 0.08,
    radec_delta: float = 120.,
    logger: Logger | None = None
) -> list[dict]:
    """Identify the target bodies of an HST observation from its SPT/SHF header.

    An observation whose MT_LV1_* keywords track a standard body (a planet or satellite,
    given as an "STD" field) is a standard-body observation; `identify_standard_body`
    resolves it from the header alone, including any additional standard bodies named in
    the target description, and its result is returned directly.

    Otherwise the target is a small body. It is identified by name using the TARGNAME,
    TARDESCR, and TARKEY* keywords and then confirmed against the orbital elements in the
    MT_LV1_* keywords: a comet by comparing Q, E, I, O, and W directly; a minor planet by
    propagating its catalog orbit to the observation midpoint and comparing the sky
    position to RA_TARG/DEC_TARG. When no name can be recognized, a comet is identified by
    searching the comet database for the nearest orbital elements, and a minor planet by
    retrieving Minor Planet Center bodies with nearby elements and selecting the one
    closest to RA_TARG/DEC_TARG.

    Parameters:
        header: The SPT/SHF header, either an astropy.io.fits.Header or a plain
            dictionary of keyword values. The keywords used are TARG_ID, TARGNAME,
            TARDESCR/TARDESC*, TARKEY1-9, MT_LV1_*, MT_LV2_*, RA_TARG, DEC_TARG,
            PSTRTIME, and PSTPTIME.
        comet_rms: Upper limit on the fractional root-mean-square discrepancy between
            the header orbital elements and those of an identified comet.
        mp_rms: Upper limit on the fractional root-mean-square discrepancy between the
            header orbital elements and those of an identified minor planet.
        radec_delta: Base tolerance in arcsec on the offset between the propagated
            sky position of an identified minor planet and RA_TARG/DEC_TARG. The
            tolerance is scaled up when the catalog epoch is far from the observation
            and when the body is much closer to the Earth than 1 AU.
        logger: An optional Logger; the full narrative of how each target was identified
            is reported at INFO level, and failures at ERROR level.

    Returns:
        A list of body dictionaries, one per relevant target, with the body observed in
        the field of view first and the body HST tracked (if distinct) last. Every
        dictionary contains at least "name", "full_name", "ttype", "ttype_name",
        "naif_id" (or None), "aliases", "parent_key", and "lid_suffix"; small bodies
        also carry their orbital elements. Blind TNO surveys yield a single placeholder
        body named "Survey HST-nnnnn", and TNOs that never received an MPC designation
        one named "Unknown HST-nnnnn", where nnnnn is the five-digit HST program ID.
        The list is empty only for programs known to have no identifiable target (e.g.,
        anti-solar pointings and slew tests).

    Raises:
        TargetIdentificationFailure: If no target can be identified, or if a target
            identified by name is incompatible with the orbital elements or target
            position in the header.
    """

    header_lists = _headers_by_visit(headers)
    if len(header_lists) > 1:
        raise ValueError('Multiple visits among headers provided')

    unique_headers = _unique_targets(headers)

    # Apply repairs
    repaired_headers = []
    unrepaired_headers = []
    for header in unique_headers:
        targ_id = str(header.get('TARG_ID', ''))
        keys = [targ_id, targ_id.partition('_')[0] + '_*']
        repair = None
        for key in keys:
            if key in _HST_PROGRAM_OVERRIDES:
                repair = _HST_PROGRAM_OVERRIDES[key]
                logger and logger.info(f'Target repair applied: {repair}')
                header = dict(header)
                header.update(repair)

        if repair is None:
            unrepaired_headers.append(header)
        else:
            repaired_headers.append(header)

    # Check for special overrides
    for header in repaired_headers:
        if 'reject' in header:
            message = 'Not a planetary observation; do not re-archive'
            logger and logger.error(message)
            raise TargetIdentificationFailure(message)

        if 'dict' in header:
            return [header['dict']]

    headers = repaired_headers + unrepaired_headers

    # A standard-body observation is identified entirely from the header
    bodies = identify_standard_body(headers, logger=logger)
    if bodies is not None:
        return bodies

    # Handle each unique header
    cdict_lookup = {}       # name -> (body dict, mt_lv1 elements)
    mdict_lookup = {}
    unique_elements = []
    ttype_lookup = {}       # filename -> ttype string
    for header in headers:
        logger and logger.blankline()
        logger and logger.info(f'{header["FILENAME"]}...')

        strings = _collect_strings(header, std=True)
        strings, ttypes = hst_repairs(strings, logger=logger)
        ttype_lookup[header['FILENAME']] = ttypes

        # Decide on comet and minor planet tests
        ctest = _is_comet(ttypes)
        mtest = _is_mp(ttypes)
        if not ctest and not mtest:
            ctest = True
            mtest = True

        # Test for comet if selected
        cdicts = {}
        if ctest:
            cdicts, _, _, _ = comet_identifiers(strings, logger=logger)

        # Test for minor planet if selected
        mdicts = {}
        if mtest:
            mdicts, _, _, _ = minor_planet_identifiers(strings, logger=logger)

        # On no minor planet results, test comets anyway
        if mtest and not mdicts and not ctest:
            cdicts, _, _, _ = comet_identifiers(strings, logger=logger)

        # On no comet results, test minor planets anyway
        if ctest and not cdicts and not mtest:
            mdicts, _, _, _ = minor_planet_identifiers(strings, logger=logger)

        # Save every identified body along with elements for further validation
        elements = _parse_mt_lv(header, 'MT_LV1', logger=logger)
        for cdict in cdicts:
            cdict_lookup[cdict['full_name']] = (cdict, elements)
        for mdict in mdicts:
            categorize_minor_planet(mdict, ttypes)
            mdict_lookup[mdict['full_name']] = (mdict, elements)

        if _has_orbital_elements(elements) and elements not in unique_elements:
            unique_elements.append(elements)

    # Validate by elements and/or RA/dec
    obs_time = _obs_midpoint(header)
    ra_targ = header.get('RA_TARG')
    dec_targ = header.get('DEC_TARG')
    radec_testable = obs_time is not None and ra_targ is not None and dec_targ is not None

    results = []
    for key, (cdict, elements) in cdict_lookup.items():
        rms, _ = mpc_tools.element_resid(elements, cdict)
        if rms > comet_rms:
            logger and logger.info(f'Comet {key} rejected; '
                                   f'element RMS {rms:.03} > {comet_rms}')
        else:
            logger and logger.info(f'Comet {key} confirmed; '
                                   f'element RMS {rms:.03} <= {comet_rms}')
            results.append(cdict)
            unique_elements = [e for e in unique_elements if e != elements]

    for key, (mdict, elements) in mdict_lookup.items():
        rms, _ = mpc_tools.element_resid(elements, mdict)

        # The element test is quick and easy and does not produce false positives
        if rms <= mp_rms:
            logger and logger.info(f'Minor planet {key} confirmed; '
                                   f'element RMS {rms:.03} <= {mp_rms}')
            results.append(mdict)
            unique_elements = [e for e in unique_elements if e != elements]

        # Otherwise, try the full orbital element test
        elif radec_testable:
            info = radec_offset(mdict, obs_time, ra_targ, dec_targ, logger=logger)
            offset = info[0] if info is not None else float('inf')
            if offset <= radec_delta:
                logger and logger.info(f'Minor planet {key} confirmed; RA/dec offset '
                                       f'{offset:.02} <= {radec_delta} arcsec')
                results.append(mdict)
                unique_elements = [e for e in unique_elements if e != elements]
            else:
                logger and logger.info(f'Minor planet {key} rejected; RA/dec offset '
                                       f'{offset:.02} > {radec_delta} arcsec')
        else:
            logger and logger.info(f'Minor planet {key} rejected; '
                                   f'element RMS {rms:.03} > {mp_rms}')
            logger and logger.info('RA/dec testing is unavailable')

    # Try a global search for any remaining elements
    indices = []
    for k, elements in enumerate(unique_elements):
        result = cometdb.query_comet_by_elements(elements, logger=logger)
        if result and result[1] <= comet_rms:
            cdict, rms = result
            logger and logger.info(f'Comet {cdict["full_name"]} identified by elements; '
                                   f'{rms:.03} <= {comet_rms}')
            results.append(cdict)
            indices.append(k)
    for k in indices[::-1]:
        unique_elements.pop(k)

    indices = []
    for k, elements in enumerate(unique_elements):
        result = minor_planet_by_radec(elements, obs_time, ra_targ, dec_targ,
                                       mp_rms, logger=logger)
        if result is not None:
            mdict, _ = result
            logger and logger.info(f'Minor planet {mdict["full_name"]} identified by '
                                   'RA/dec')
            results.append(mdict)
            indices.append(k)
    for k in indices[::-1]:
        unique_elements.pop(k)

    # Report any unidentified targets
    for elements in unique_elements:
        # Reverse lookup the header from which these elements were obtained
        for header in headers:
            test_elements = _parse_mt_lv(header, 'MT_LV1')
            if test_elements == elements:
                message = (f'Target could not be determined: file = {header["FILENAME"]}; '
                           f'TARGNAME={header.get("TARGNAME")}')
                logger and logger.error(message)
                raise TargetIdentificationFailure(message)

    return results


##########################################################################################
