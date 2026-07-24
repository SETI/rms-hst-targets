##########################################################################################
# identify_standard_body.py
##########################################################################################
"""Identify the standard bodies (including rings, systems, Io torus) named by an HST
header.
"""

import re

from targets._utils          import _collect_strings, _parse_mt_lv, _unique_targets
from targets.hst_repairs     import hst_repairs
from targets.standard_bodies import STANDARD_BODY_LOOKUP
from targets.targettype      import TargetType

_STD_REGEX = re.compile(r'STD *= *([^,]+)')
_TARDESCR_REGEX = re.compile(r'SOLAR SYSTEM;(?:PLANET|SATELLITE|FEATURE|OFFSET) (\w+)')

_PLANET_RADII = {
    'MARS'   :  3500.,
    'JUPITER': 73000.,
    'SATURN' : 62000.,
    'URANUS' : 26000.,
    'NEPTUNE': 26000.,
}


def _identify_standard_names(header, *, logger=None):
    """Identify the standard bodies (bodies, rings, systems, Io torus) of an HST
    observation.

    Parameters:
        headers (FITS header | dict): The SPT/SHF header for a single file.
        logger (Logger, optional): A Logger for messages.

    Returns:
        list[str]: The body names identified.
    """

    # Find the last STD value
    stdval = ''
    for key in ('MT_LV1_1', 'MT_LV2_1'):
        if key in header:
            match = _STD_REGEX.match(header[key])
            if match:
                stdval = match.group(1).upper()
            elif header[key] in STANDARD_BODY_LOOKUP:
                stdval = header[key].upper()        # e.g., "TETHYS" without "STD="
            else:
                break

    # An STD field is missing for some older programs, TARDESCR is unambiguous
    if not stdval:
        tardescr = header.get('TARDESCR', '') + header.get('TARDESC2', '')
        match = _TARDESCR_REGEX.match(tardescr)
        if match:
            name = match.group(1).upper()
            if name in STANDARD_BODY_LOOKUP:
                stdval = name

    # If this is not a standard standard value, return None
    if not stdval:
        return []
    if stdval not in STANDARD_BODY_LOOKUP:
        return []

    # Log value found
    filename = header['FILENAME'].upper()
    logger and logger.info(f'Identifying {filename}: STD={stdval}')

    # Search for additional strings
    strings = _collect_strings(header, std=False)
    strings, ttypes = hst_repairs(strings, logger=logger)
    strings = [s.upper() for s in strings]

    # Look for TYPE=TORUS, interpret as planet, ring, or torus
    mt_lv2 = header.get('MT_LV2_1', '').replace(' ', '')
    if mt_lv2.startswith('TYPE=TORUS'):
        torus = _parse_mt_lv(header, 'MT_LV2', logger=logger)
        planet_radius = _PLANET_RADII.get(stdval, 0)

        if stdval == 'JUPITER' and TargetType.PLASMA_CLOUD in ttypes and 'IO' in strings:
            stdval = 'IO TORUS'
        elif (TargetType.RING in ttypes and TargetType.PLASMA_CLOUD not in ttypes
              and torus.get('POLE_LAT', 90) == 90
              and torus.get('LAT', 0) == 0
              and torus.get('LONG', 90) in {90, 270}
              and planet_radius < torus['RAD'] < 10.*planet_radius):
            test = stdval + ' RINGS'
            if test in STANDARD_BODY_LOOKUP:
                stdval = test

    # Augment the list of targets based on other strings
    names = [stdval]
    unused = []
    for string in strings:
        if string in STANDARD_BODY_LOOKUP:
            if string not in names:
                names.append(string)
        else:
            for substring in string.split():
                if substring in STANDARD_BODY_LOOKUP:
                    if substring not in names:
                        names.append(substring)
                elif '-' in substring:
                    subparts = []
                    for part in substring.split('-'):
                        if part in STANDARD_BODY_LOOKUP:
                            if part not in names:
                                names.append(part)
                        else:
                            subparts.append(part)
                    if subparts:
                        unused.append('-'.join(subparts))
                else:
                    unused.append(substring)

    # Add the "system" target
    if len(names) > 1:
        # parent_key is the parent's full_name; resolve it to the parent body so the
        # "<parent> SYSTEM" name is built from the parent's plain name.
        child_count = {}
        for name in names:
            parent_key = STANDARD_BODY_LOOKUP[name].get('parent_key', '')
            if parent_key:
                if parent_key in child_count:
                    child_count[parent_key] += 1
                else:
                    child_count[parent_key] = 1

        for parent_key in child_count:
            parent = STANDARD_BODY_LOOKUP.get(parent_key)
            if parent and parent['name'].upper() in names:
                child_count[parent_key] += 1    # so "IO" + "JUPITER" -> "JUPITER SYSTEM"

        for parent_key, count in child_count.items():
            if count > 1:
                parent = STANDARD_BODY_LOOKUP.get(parent_key)
                if parent is None:
                    continue
                key = parent['name'].upper() + ' SYSTEM'
                if key in STANDARD_BODY_LOOKUP and key not in names:
                    names.append(key)
                    break

    # Log the result
    logger and logger.info(f'Standard targets: {names}')
    if unused:
        logger and logger.info(f'Unused strings: {unused}')

    return names


def identify_standard_body(headers, *, logger=None):
    """Identify the standard bodies (bodies, rings, systems, Io torus) of an HST visit.

    Parameters:
        headers (list[FITS header | dict]): All the SPT/SHF headers for a single visit.
        logger (Logger, optional): A Logger for messages.

    Returns:
        list[str]: The body names identified.
    """

    unique_headers = _unique_targets(headers)

    # An order-preserving list (not a set) so the merged result is deterministic; the
    # order follows the visit's files, which is stable across runs.
    name_tuples = []
    filenames_unused = []
    for header in unique_headers:
        names = _identify_standard_names(header, logger=logger)
        if not names:
            filenames_unused.append(header['FILENAME'])
        else:
            name_tuple = tuple(names)
            if name_tuple not in name_tuples:
                name_tuples.append(name_tuple)

    if not name_tuples:
        return None

    for filename in filenames_unused:
        logger and logger.info(f'{filename}: No STD body')

    if len(name_tuples) == 1:
        merged_names = list(name_tuples[0])
        wording = 'Targets'
    else:
        # Different answers from within a single visit
        # Try to retain order of unique names
        length = max(len(t) for t in name_tuples)
        merged_names = []
        for k in range(length):
            for name_tuple in name_tuples:
                name = name_tuple[min(k, len(name_tuple)-1)]
                if name not in merged_names:
                    merged_names.append(name)
        wording = 'Merged targets'

    used_count = len(unique_headers) - len(filenames_unused)
    full_count = len(headers)
    logger and logger.info(f'{wording} from {used_count}/{full_count} files: '
                           f'{merged_names}')

    # Different lookup keys can resolve to the same body (e.g., "SATURN" and the
    # abbreviation "SAT"), so deduplicate by body while preserving order.
    bodies = []
    seen = set()
    for n in merged_names:
        body = STANDARD_BODY_LOOKUP[n]
        if body['name'] not in seen:
            seen.add(body['name'])
            bodies.append(body)

    return bodies


__all__ = ['identify_standard_body']

##########################################################################################
