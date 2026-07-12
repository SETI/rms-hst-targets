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

    from targets.identify_target import identify_target, TargetIdentificationError

"""

import math
import re
from datetime import datetime, timedelta
from logging import Logger

from targets import cometdb, mpc_tools
from targets._HST_PROGRAM_OVERRIDES import SPT_REPAIRS
from targets.categorize_minor_planet import minor_planet_ttype
from targets.hst_repairs import hst_repairs
from targets.identify_small_body import identify_small_body
from targets.standard_bodies import STANDARD_BODY_LOOKUP
from targets.targettype import TargetType

__all__ = ['TargetIdentificationError', 'identify_target']


class TargetIdentificationError(ValueError):
    """Raised when no target can be identified for an observation, or when a target
    identified by name is incompatible with the orbital elements in the header.
    """


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

# TARGNAME words indicating that RA_TARG/DEC_TARG is not the position of the body
_OFFSET_TARGNAME_WORDS = ('OFFSET', 'BACKGROUND', 'SLEW', 'DUMMY')

_MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
           'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

_STD_NUMBER_NAME = re.compile(r'\(?([1-9]\d*)\)?(?: *\((.+)\)| +(.+))?')


##########################################################################################
# Header parsing
##########################################################################################

def _apply_overrides(header: dict, logger: Logger | None) -> tuple[dict, str | None]:
    """Apply any per-program repairs from _HST_PROGRAM_OVERRIDES to a copy of the header.

    Parameters:
        header: The SPT/SHF header as a dictionary.
        logger: An optional Logger for messages.

    Returns:
        A tuple `(header, sentinel)`, where `header` is a copy of the input header with
        any keyword overrides applied, and `sentinel` is the override string (e.g.,
        "TNO_SURVEY") for programs known to have no identifiable target, or None.
    """

    header = dict(header)
    targ_id = str(header.get('TARG_ID', ''))
    keys = [targ_id, targ_id.partition('_')[0] + '_*']
    for key in keys:
        if key in SPT_REPAIRS:
            repair = SPT_REPAIRS[key]
            logger and logger.info(f'Program override for TARG_ID "{key}": {repair!r}')
            if isinstance(repair, str):
                return (header, repair)
            header.update(repair)
            return (header, None)

    return (header, None)


def _collect_strings(header: dict) -> list[str]:
    """The target identification strings of a header: TARKEY*, TARGNAME, and the
    semicolon-separated pieces of TARDESCR/TARDESC*.

    Pieces of the target description that merely repeat the target category (e.g., the
    leading "SOLAR SYSTEM" of most TARDESCR values) are excluded.
    """

    strings = []
    for i in range(1, 10):
        value = header.get(f'TARKEY{i}', '')
        if value:
            strings.append(str(value))

    if header.get('TARGNAME', ''):
        strings.append(str(header['TARGNAME']))

    descr = str(header.get('TARDESCR', ''))
    for i in range(2, 10):
        descr += str(header.get(f'TARDESC{i}', ''))

    categories = {'SOLAR SYSTEM', str(header.get('TARGCAT', '')).strip().upper()}
    for part in descr.split(';'):
        part = part.strip()
        if part and part.upper() not in categories:
            strings.append(part)

    return strings


def _parse_mt_lv(header: dict, prefix: str,
                 logger: Logger | None = None) -> tuple[str | None, dict | str | None]:
    """Parse the MT_LV1_* or MT_LV2_* keywords of a header.

    Parameters:
        header: The SPT/SHF header as a dictionary.
        prefix: "MT_LV1" or "MT_LV2".
        logger: An optional Logger for messages.

    Returns:
        A tuple `(kind, payload)`, one of:

        * `("STD", name)`: the level tracks a standard body; `name` is the value of the
          "STD" field, which usually names a planet or satellite but can also be a minor
          planet number such as "2060" or "1 (CERES)".
        * `("COMET", elements)` or `("ASTEROID", elements)`: the level defines orbital
          elements; see below.
        * `("FILE", None)`: the ephemeris was supplied to HST as a file; no elements are
          available.
        * `("OFFSET", None)`: the level defines pointing geometry (e.g., TYPE=POS_ANGLE)
          rather than a body.
        * `(None, None)`: the keywords are absent or empty.

        The `elements` dictionary contains any of the float values "A" (semimajor axis in
        AU), "Q" (perihelion distance in AU), "E" (eccentricity), "I" (inclination in
        degrees), "O" (ascending node in degrees), "W" (argument of pericenter in
        degrees), and "M" (mean anomaly in degrees), plus the strings "T" (perihelion
        time) and "EPOCH" (element epoch) as "DD-MON-YYYY:hh:mm:ss", "EQUINOX" ("J2000"
        or "B1950"), and any "TTIMESCALE"/"EPOCHTIMESCALE" values ("UTC" or "TDB").
    """

    # Join the continuation keywords in numeric order; values can be split mid-number
    parts = []
    i = 1
    while f'{prefix}_{i}' in header:
        parts.append(str(header[f'{prefix}_{i}']))
        i += 1

    full = ''.join(parts)
    if not full.strip():
        return (None, None)

    # Split into KEY=VALUE fields; a field without "=" is a value containing a stray
    # comma, so re-attach it to the previous field
    merged: list[str] = []
    for field in full.split(','):
        if '=' in field:
            merged.append(field)
        elif merged and field.strip():
            merged[-1] += field.strip()

    fields = {}
    for field in merged:
        key, _, value = field.partition('=')
        fields[key.strip().upper()] = value.strip()

    if 'STD' in fields:
        return ('STD', fields['STD'])
    if 'FILE' in fields:
        return ('FILE', None)

    kind = fields.pop('TYPE', '').upper()
    if kind == 'COMET':
        float_keys = ('Q', 'E', 'I', 'O', 'W')
    elif kind == 'ASTEROID':
        float_keys = ('A', 'Q', 'E', 'I', 'O', 'W', 'M')
    elif kind:
        return ('OFFSET', None)
    else:
        return (None, None)

    elements: dict = {}
    for key in float_keys:
        if key in fields:
            try:
                elements[key] = float(fields[key])
            except ValueError:
                logger and logger.warning(f'Unparseable {prefix} element '
                                          f'{key}={fields[key]!r}')

    for key in ('T', 'EPOCH'):
        if key in fields:
            try:
                elements[key] = _norm_date(fields[key])
            except ValueError:
                logger and logger.warning(f'Unparseable {prefix} date '
                                          f'{key}={fields[key]!r}')

    elements['EQUINOX'] = fields.get('EQUINOX', 'J2000').upper()
    for key in ('TTIMESCALE', 'EPOCHTIMESCALE'):
        if key in fields:
            elements[key] = fields[key].upper()

    return (kind, elements)


##########################################################################################
# Date handling
##########################################################################################

def _norm_date(text: str) -> str:
    """Normalize "DD-MON-YY[YY][:hh:mm:ss][.]" to "DD-MON-YYYY:hh:mm:ss"."""

    text = text.strip().rstrip('.').strip()
    datep, _, timep = text.partition(':')
    dd, mon, yy = [p.strip() for p in datep.split('-')]
    year = int(yy)
    if year < 100:
        year = 1900 + year if year >= 50 else 2000 + year      # HST-era pivot
    tp = [*timep.split(':'), '0', '0', '0'][:3]
    hh, mm, ss = int(tp[0] or 0), int(tp[1] or 0), int(float(tp[2] or 0))
    return f'{int(dd):02d}-{mon.upper()}-{year:04d}:{hh:02d}:{mm:02d}:{ss:02d}'


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


def _body_radec_offset(
    body: dict,
    obs_dt: datetime,
    ra_targ: float,
    dec_targ: float,
    logger: Logger | None
) -> tuple[float, float] | None:
    """Propagate a minor planet's catalog elements to the observation time and compare
    the sky position to the header target position.

    Parameters:
        body: A minor planet dictionary including the catalog elements "A", "E", "I",
            "O", "W", "M", and "EPOCH".
        obs_dt: The observation midpoint.
        ra_targ: The header RA_TARG in degrees.
        dec_targ: The header DEC_TARG in degrees.
        logger: An optional Logger for messages.

    Returns:
        A tuple `(offset, gap, delta)` giving the angular offset in arcsec, the time
        between the catalog epoch and the observation in years, and the geocentric
        distance in AU; None if the position could not be calculated.
    """

    missing = [key for key in ('A', 'E', 'I', 'O', 'W', 'M', 'EPOCH')
               if key not in body]
    if missing:
        logger and logger.info('Sky position check skipped; catalog elements '
                               f'missing {missing}')
        return None

    try:
        from targets.orbital_radec import asteroid_radec
    except ImportError:
        logger and logger.warning('palpy unavailable; sky position check skipped')
        return None

    obs = _dt_to_str(obs_dt)
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
    gap = abs((obs_dt - _epoch_dt(body['EPOCH'])).days) / 365.25
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


def _name_supported(body: dict, answers: list[str]) -> bool:
    """True if any of the recognized name strings refers to this body."""

    names = {str(body.get(key, '')).upper()
             for key in ('mnum', 'name', 'desig', 'full_name')}
    names |= {str(alias).upper() for alias in body.get('alt_desigs', [])}
    names |= {str(alias).upper() for alias in body.get('aliases', [])}
    names |= {str(alias).upper() for alias in body.get('lookups', [])}
    names -= {''}
    return bool({answer.upper() for answer in answers} & names)


def _rescue_comet_by_elements(
    elements: dict,
    answers: list[str],
    comet_rms: float,
    logger: Logger | None
) -> tuple[dict, float] | None:
    """Search the comet database for a comet that matches both the orbital elements and
    one of the recognized name strings.

    This handles observations whose name strings resolved to the wrong comet (e.g., an
    old designation shared by two comets), when the orbital elements point clearly at
    another comet carrying one of the same names.

    Parameters:
        elements: The J2000 orbital elements from the header.
        answers: The repaired identification strings.
        comet_rms: Upper limit on the fractional RMS element discrepancy.
        logger: An optional Logger for messages.

    Returns:
        A tuple `(comet, rms)`, or None if no comet matches both tests.
    """

    results = cometdb.query_comet_by_elements(elements, count=5, fragments=True,
                                              logger=logger)
    if not results:
        return None

    comet, rms = results[0]
    if rms > comet_rms:
        return None
    if len(results) > 1 and rms > results[1][1] / 2.:
        return None
    if not _name_supported(comet, answers):
        return None

    logger and logger.info(f'Comet {comet["full_name"]} matches both the orbital '
                           'elements and the name strings')
    return (comet, rms)


def _identify_asteroid_by_position(
    elements: dict,
    obs_dt: datetime | None,
    ra_targ: float | None,
    dec_targ: float | None,
    mp_rms: float,
    logger: Logger | None
) -> tuple[dict, float] | None:
    """Identify a minor planet by searching the MPC for nearby orbital elements and
    selecting the candidate closest to the header target position.

    Parameters:
        elements: The J2000 orbital elements from the header.
        obs_dt: The observation midpoint; None if unavailable.
        ra_targ: The header RA_TARG in degrees; None if unavailable.
        dec_targ: The header DEC_TARG in degrees; None if unavailable.
        mp_rms: Upper limit on the fractional RMS element discrepancy for a candidate to
            be considered at all.
        logger: An optional Logger for messages.

    Returns:
        A tuple `(body, rms)` for the winning candidate, or None if no candidate came
        believably close to the target position.
    """

    if obs_dt is None or ra_targ is None or dec_targ is None:
        logger and logger.info('Position-based identification unavailable; observation '
                               'time or target position missing')
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
        info = _body_radec_offset(body, obs_dt, ra_targ, dec_targ, logger)
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

    tolerance = _position_tolerance(_FALLBACK_RADEC_TOLERANCE, gap, delta)
    if offset > tolerance:
        logger and logger.info(f'Nearest candidate {body["full_name"]} is {offset:.1f}" '
                               f'from RA_TARG/DEC_TARG, beyond tolerance {tolerance:.1f}"')
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
# Standard bodies
##########################################################################################

def _resolve_std(token: str, logger: Logger | None) -> tuple[dict | None, str, str]:
    """Resolve the value of an MT_LV* "STD" field.

    Parameters:
        token: The value of the "STD" field, e.g., "JUPITER", "2060", or "1 (CERES)".
        logger: An optional Logger for messages.

    Returns:
        A tuple `(body, name, number)`. If the token names a standard body, `body` is
        its dictionary and the strings are empty. Otherwise `body` is None, `name` is
        the small-body name or number to look up instead, and `number` is the minor
        planet number if the token supplied one.
    """

    token = ' '.join(str(token).split()).upper()
    if token in STANDARD_BODY_LOOKUP:
        return (STANDARD_BODY_LOOKUP[token], '', '')

    # "N", "N (NAME)", or "(N) NAME" identifies a minor planet by number. The name alone
    # can match a standard body that shares it (e.g., "9 (METIS)" is the asteroid, not
    # the satellite of Jupiter), so a standard body is accepted only if its own minor
    # planet number agrees.
    match = _STD_NUMBER_NAME.fullmatch(token)
    if match:
        number = match.group(1)
        name = match.group(2) or match.group(3) or ''
        if name and name in STANDARD_BODY_LOOKUP:
            body = STANDARD_BODY_LOOKUP[name]
            if str(body.get('mnum', '')) == number:
                return (body, '', '')
        return (None, name or number, number)

    return (None, token, '')


##########################################################################################
# Output normalization
##########################################################################################

def _normalize_body(body: dict, hints: str, logger: Logger | None) -> dict:
    """Return a copy of a body dictionary with the keys required for a PDS4 Target
    context product guaranteed to be present.

    Parameters:
        body: A standard body, comet, Centaur, or minor planet dictionary.
        hints: TargetType letter codes derived from the header's target description,
            used to categorize minor planets when nothing better is available.
        logger: An optional Logger for messages.

    Returns:
        A copy of `body` guaranteed to contain "name", "full_name", "ttype" (a specific
        TargetType code, never "M"), "ttype_name", "naif_id" (or None), "aliases",
        "parent_key", and "lid_suffix".
    """

    body = dict(body)

    if body.get('ttype') == TargetType.MINOR_PLANET:
        body['ttype'] = minor_planet_ttype(body, hints=hints, logger=logger)

    body.setdefault('name', '')
    if not body.get('full_name'):
        body['full_name'] = body['name'] or body.get('desig', '')
    body.setdefault('naif_id', None)
    if 'aliases' not in body:
        aliases = [body.get('desig', ''), *body.get('alt_desigs', [])]
        body['aliases'] = [a for a in aliases if a]
    body.setdefault('parent_key', '')

    body['ttype_name'] = TargetType.NAME[body['ttype']]
    suffix = body['full_name'].lower().replace('/', '_').replace(' ', '_')
    suffix = re.sub(r'[^a-z0-9_.-]', '', suffix)
    body['lid_suffix'] = body['ttype_name'] + '.' + suffix

    return body


def _body_key(body: dict) -> str:
    """A key identifying a body for de-duplication.

    The minor planet number is preferred because the same body can be described by both
    a standard body dictionary and an MPC dictionary under different names (e.g.,
    "Haumea" and "136108 Haumea").
    """

    if body.get('mnum'):
        return str(body['mnum'])
    return str(body.get('full_name') or body.get('name') or body.get('desig', '')).upper()


##########################################################################################
# identify_target()
##########################################################################################

def identify_target(
    header: dict, *,
    comet_rms: float = 0.1,
    mp_rms: float = 0.08,
    radec_tolerance: float = 120.,
    logger: Logger | None = None
) -> list[dict]:
    """Identify the target bodies of an HST observation from its SPT/SHF header.

    Identification by name is always attempted using the TARGNAME, TARDESCR, and TARKEY*
    keywords, because these can identify bodies (e.g., a satellite or an impacting comet)
    beyond the one that HST tracked. Any body identified by name is then confirmed
    against the orbital elements in the MT_LV1_* keywords: a comet by comparing Q, E, I,
    O, and W directly; a minor planet by propagating its catalog orbit to the observation
    midpoint and comparing the sky position to RA_TARG/DEC_TARG. When no name can be
    recognized, a comet is identified by searching the comet database for the nearest
    orbital elements, and a minor planet by retrieving Minor Planet Center bodies with
    nearby elements and selecting the one closest to RA_TARG/DEC_TARG.

    Parameters:
        header: The SPT/SHF header, either an astropy.io.fits.Header or a plain
            dictionary of keyword values. The keywords used are TARG_ID, TARGNAME,
            TARDESCR/TARDESC*, TARKEY1-9, MT_LV1_*, MT_LV2_*, RA_TARG, DEC_TARG,
            PSTRTIME, and PSTPTIME.
        comet_rms: Upper limit on the fractional root-mean-square discrepancy between
            the header orbital elements and those of an identified comet.
        mp_rms: Upper limit on the fractional root-mean-square discrepancy between the
            header orbital elements and those of an identified minor planet.
        radec_tolerance: Base tolerance in arcsec on the offset between the propagated
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
        also carry their orbital elements. The list is empty only for programs known to
        have no identifiable target (e.g., blind TNO surveys).

    Raises:
        TargetIdentificationError: If no target can be identified, or if a target
            identified by name is incompatible with the orbital elements or target
            position in the header.
    """

    if not isinstance(header, dict):
        header = dict(header.items())       # accept an astropy.io.fits.Header

    header, sentinel = _apply_overrides(header, logger)
    if sentinel:
        logger and logger.info(f'No identifiable target: program is flagged '
                               f'"{sentinel}"')
        return []

    targname = str(header.get('TARGNAME', ''))
    logger and logger.info(f'Identifying targets for TARGNAME "{targname}"')

    strings = _collect_strings(header)
    kind1, payload1 = _parse_mt_lv(header, 'MT_LV1', logger=logger)
    kind2, payload2 = _parse_mt_lv(header, 'MT_LV2', logger=logger)

    # When the pointing is offset from the body, RA_TARG/DEC_TARG is not the body's
    # position and cannot be used for confirmation
    offset_pointing = (kind2 == 'OFFSET'
                       or any(word in targname.upper()
                              for word in _OFFSET_TARGNAME_WORDS))

    obs_dt = _obs_midpoint(header)
    ra_targ = header.get('RA_TARG')
    dec_targ = header.get('DEC_TARG')

    answers, types = hst_repairs(strings, logger=logger)

    fov_bodies = []         # bodies identified by name; the subject of the observation
    tracked_bodies = []     # the body HST tracked, per MT_LV1

    # Standard bodies named by the MT_LV* "STD" fields. MT_LV2 names the body in the
    # field of view; MT_LV1 names the body HST tracked.
    for kind, payload, level, target_list in [
            (kind2, payload2, 'MT_LV2', fov_bodies),
            (kind1, payload1, 'MT_LV1', tracked_bodies)]:
        if kind != 'STD':
            continue
        body, small_name, number = _resolve_std(payload, logger)
        if body is None:
            # The STD field names a minor planet or comet; identify it by name
            body, _, valid = identify_small_body([small_name], {}, logger=logger)
            if not valid:
                body = None
        if body is None and number and number != small_name:
            # The name did not resolve (e.g., it is reserved for a satellite), but the
            # minor planet number is authoritative
            try:
                body = mpc_tools.mpc_query_by_name(number, logger=logger)
            except RuntimeError:
                body = None
        if body is None:
            message = f'Unresolved standard target "STD={payload}" in {level}'
            logger and logger.error(message)
            raise TargetIdentificationError(message)
        logger and logger.info(f'{level} standard target: '
                               + (body.get('full_name') or body['name']))
        target_list.append(body)

    # Standard bodies identified by name from the target description
    consumed = set()
    for answer in answers:
        body = STANDARD_BODY_LOOKUP.get(answer.upper())
        if body:
            consumed.add(answer)
            logger and logger.info(f'Standard body identified by name: {body["name"]} '
                                   f'(from "{answer}")')
            fov_bodies.append(body)

    # Small-body identification from the orbital elements and the original strings
    # (identify_small_body repairs them itself; repaired strings must not be repaired
    # twice). When a body has already been identified and there are no orbital elements,
    # the attempt is made only if the target description suggests a small body; this
    # still catches, e.g., a named comet observed against a tracked planet.
    elements = payload1 if kind1 in ('COMET', 'ASTEROID') else {}
    match_elements = _elements_to_j2000(elements, logger) if elements else {}
    remaining = [a for a in answers if a not in consumed]

    small_body_codes = set(TargetType.MCODES + TargetType.MINOR_PLANET
                           + TargetType.COMET)
    attempt = (bool(elements)
               or not (fov_bodies or tracked_bodies)
               or bool(small_body_codes & set(types)))

    small_body = None
    if (remaining and attempt) or elements:
        small_body, rms, _ = identify_small_body(strings, match_elements,
                                                 comet_rms=comet_rms, mp_rms=mp_rms,
                                                 logger=logger)

        # Confirm a named comet by its orbital elements alone. If they disagree, the
        # name may have resolved to the wrong comet; see whether another comet matches
        # both the elements and the names before giving up.
        if small_body and kind1 == 'COMET' and rms > comet_rms:
            rescued = _rescue_comet_by_elements(match_elements, answers, comet_rms,
                                                logger)
            if rescued:
                small_body, rms = rescued
            else:
                message = (f'Comet "{small_body["full_name"]}" is incompatible with '
                           'the header orbital elements: residual '
                           f'rms={rms:.4f} > {comet_rms}; TARGNAME="{targname}"')
                logger and logger.error(message)
                raise TargetIdentificationError(message)

        # Confirm a named minor planet by its propagated sky position. If the position
        # disagrees, the name may have resolved to the wrong body; see whether an MPC
        # element search finds a body at the right position carrying one of the names.
        if small_body and kind1 == 'ASTEROID':
            if offset_pointing:
                logger and logger.info('Sky position check skipped; RA_TARG/DEC_TARG '
                                       'is offset from the body')
            elif obs_dt is None or ra_targ is None or dec_targ is None:
                logger and logger.info('Sky position check skipped; observation time '
                                       'or target position missing')
            else:
                info = _body_radec_offset(small_body, obs_dt, float(ra_targ),
                                          float(dec_targ), logger)
                if info is not None:
                    offset, gap, delta = info
                    tolerance = _position_tolerance(radec_tolerance, gap, delta)
                    if offset <= tolerance:
                        logger and logger.info(f'Sky position confirmed: {offset:.1f}" '
                                               'from RA_TARG/DEC_TARG at '
                                               + _dt_to_str(obs_dt))
                    else:
                        result = _identify_asteroid_by_position(
                            match_elements, obs_dt, float(ra_targ), float(dec_targ),
                            mp_rms, logger)
                        if result and _name_supported(result[0], answers):
                            logger and logger.info(
                                f'"{small_body["full_name"]}" rejected in favor of '
                                f'{result[0]["full_name"]}, which matches the sky '
                                'position and the name strings')
                            small_body, rms = result
                        else:
                            message = (f'Minor planet "{small_body["full_name"]}" is '
                                       f'{offset:.1f}" from RA_TARG/DEC_TARG at '
                                       f'{_dt_to_str(obs_dt)}, beyond the tolerance of '
                                       f'{tolerance:.1f}"; TARGNAME="{targname}"')
                            logger and logger.error(message)
                            raise TargetIdentificationError(message)

    # When a minor planet could not be identified by name or by elements alone, search
    # the MPC for nearby orbits and select by sky position
    if small_body is None and kind1 == 'ASTEROID' and not offset_pointing:
        result = _identify_asteroid_by_position(
            match_elements, obs_dt,
            None if ra_targ is None else float(ra_targ),
            None if dec_targ is None else float(dec_targ),
            mp_rms, logger)
        if result:
            small_body, rms = result

    if small_body:
        fov_bodies.insert(0, small_body)

    # Combine, de-duplicate, and normalize; the field-of-view bodies come first and the
    # tracked body last
    bodies = []
    seen = set()
    for body in fov_bodies + tracked_bodies:
        key = _body_key(body)
        if key and key in seen:
            continue
        seen.add(key)
        bodies.append(body)

    if not bodies:
        message = f'No target identified for TARGNAME "{targname}"'
        if 'TARG_ID' in header:
            message += f' (TARG_ID "{header["TARG_ID"]}")'
        logger and logger.error(message)
        raise TargetIdentificationError(message)

    results = []
    for body in bodies:
        body = _normalize_body(body, types, logger)
        results.append(body)
        logger and logger.info(f'Target identified: {body["full_name"]} '
                               f'({body["ttype_name"]})')

    return results

##########################################################################################
