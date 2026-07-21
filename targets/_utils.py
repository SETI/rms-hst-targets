##########################################################################################
# targets/_utils.py
##########################################################################################

import re

from targets.cometdb         import centaur_lookup
from targets.standard_bodies import STANDARD_BODY_LOOKUP
from targets.targettype      import TargetType


class TargetIdentificationFailure(ValueError):
    """Raised when no target can be identified for an observation, or when a target
    identified by name is incompatible with the orbital elements in the header.
    """


_STD_REGEX = re.compile(r'STD *= *([^,]+)')


def _collect_strings(header, *, std=False):
    """The target identification strings of a header: TARKEY*, TARGNAME, TARDESC*, TARCAT,
    and the last STD value in MT_LV*_1.

    If std is True, the last STD value in an MT_LV field is also included.
    """

    strings = []

    descr = [header.get('TARDESCR', '')]
    for i in range(2, 10):
        key = f'TARDESC{i}'
        if key in header:
            descr.append(header[key])
        else:
            break
    descr = ''.join(descr)
    strings.append(descr)

    strings.append(header.get('TARGNAME', ''))

    for i in range(1, 10):
        key = f'TARKEY{i}'
        if key in header:
            strings.append(header[key])

    targcat = header.get('TARGCAT', '')
    if targcat and targcat != 'SOLAR SYSTEM':
        strings.append(targcat)

    if std:
        last_match = None
        for i in range(1, 4):
            stdval = header.get(f'MT_LV{i}_1', '')
            match = _STD_REGEX.match(stdval)
            if match:
                last_match = match
            else:
                break

        if last_match:
            strings.append(last_match.group(1))

    return strings


def _norm_date(text):
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


##########################################################################################
##########################################################################################

_KEYWORD_REGEX = re.compile(r'[A-Z]\w*$')


def _parse_mt_lv(header, prefix, *, logger=None):
    """Parse the MT_LV1_* or MT_LV2_* keywords of a header.

    Parameters:
        header (FITS header or dict): The SPT/SHF header content.
        prefix (str): "MT_LV1" or "MT_LV2".
        logger (PdsLogger): Logger to use for parse warnings.

    Returns:
        dict: A dictionary of the parameter names and values.
    """

    # Join the continuation keywords in numeric order; values can be split mid-number
    parts = []
    for k in range(1, 6):
        key = f'{prefix}_{k}'
        if key not in header:
            break
        parts.append(header[key])
    content = ''.join(parts)

    # Handle empty content, known errors
    if not content or content == '^':
        return {}
    content = content.replace('EPOCH2=', ',EPOCH2=')

    # `sep` is a comma except for rare cases, e.g., "'TYPE=TORUS POLE_LAT=+90 LONG=180"
    sep = ','
    if ',' not in content and len(content.split('=')) > 2:
        sep = ' '
    fields = content.split(sep)

    # Split into KEY=VALUE fields; a numeric field without "=" is a value containing a
    # stray comma (e.g. "M=2,3.618253"), so re-attach it to the previous field.
    pairs = []
    prev_field = ''
    for field in fields:
        if not field:
            continue
        parts = field.split('=')
        if len(parts) == 1:
            if parts[0][0].isdigit():
                logger and logger.info(f'Merging fields: {prev_field!r}, {field!r}')
                pairs[-1][1] += parts[0]
                prev_field += parts[0]
            else:
                logger and logger.warning(f'Empty {prefix} field: {field!r}')
        elif len(parts) > 2:
            logger and logger.warning(f'Invalid {prefix} field value: {field!r}')
        else:
            name = parts[0].strip()
            if not _KEYWORD_REGEX.match(name):
                logger and logger.warning(f'Invalid {prefix} field name: {field!r}')
            else:
                pairs.append([name, parts[1].strip()])
            prev_field = field

    # Create dictionary
    values = {}
    for name, valstr in pairs:
        try:
            value = float(valstr)
        except ValueError:
            value = valstr.strip()
        values[name] = value

    return values


##########################################################################################
##########################################################################################


# A body with a semimajor axis at or beyond Neptune's is a trans-Neptunian object.
_TNO_BOUNDARY_AU = 30.1

# A body with perihelion beyond Jupiter's semimajor axis and a semimajor axis inside
# Neptune's is a Centaur (the standard JPL/MPC working definition).
_CENTAUR_PERIHELION_AU = 5.2


def categorize_minor_planet(body, ttypes, *, logger=None):
    """Fill in the `ttype` if the given body is a minor planet."""

    if body['ttype'] != TargetType.MINOR_PLANET:
        return

    name = body.get('full_name') or body.get('name') or body.get('desig')
    key = body.get('mnum') or name
    key = key.upper()

    if key in STANDARD_BODY_LOOKUP:  # handles all dwarf planets, a few others
        body['ttype'] = STANDARD_BODY_LOOKUP[key]['ttype']
        return

    if key in centaur_lookup():
        body['ttype'] = TargetType.CENTAUR
        return

    # Categorize based on orbit
    a = body.get('A')
    q = body.get('Q')
    e = body.get('E')
    if e is not None and e < 1.:
        if a is None and q is not None:
            a = q / (1. - e)
        elif q is None and a is not None:
            q = a * (1. - e)

    if a is None:
        test = set(ttypes) - {TargetType.DWARF_PLANET, TargetType.CENTAUR}
        if test == {TargetType.TRANS_NEPTUNIAN_OBJECT}:
            body['ttype'] = TargetType.TRANS_NEPTUNIAN_OBJECT
            logger and logger.debug(f'{name} is a TNO from SPT file')
        elif test == {TargetType.ASTEROID}:
            body['ttype'] = TargetType.ASTEROID
            logger and logger.debug(f'{name} is an asteroid from SPT file')
        else:
            body['ttype'] = TargetType.ASTEROID
            logger and logger.warning(f'Unable to categorize {name}; '
                                      'defaulting to asteroid')

    elif a >= _TNO_BOUNDARY_AU:
        body['ttype'] = TargetType.TRANS_NEPTUNIAN_OBJECT
        logger and logger.debug(f'{name} is a TNO (a = {a:.2f} AU)')
    elif q is None and a < _CENTAUR_PERIHELION_AU:
        body['ttype'] = TargetType.ASTEROID
        logger and logger.debug(f'{name} is an asteroid (a = {a:.2f} AU)')
    elif q is None:
        logger and logger.error(f'{name} cannot be categorized')
        raise ValueError(f'{name} cannot be categorized')
    elif q > _CENTAUR_PERIHELION_AU:
        body['ttype'] = TargetType.CENTAUR
        logger and logger.debug(f'{name} is a Centaur '
                                f'(a = {a:.2f} AU; q = {q:.2f} AU)')
    else:
        body['ttype'] = TargetType.ASTEROID
        logger and logger.debug(f'{name} is an asteroid '
                                f'(a = {a:.2f} AU; q = {q:.2f} AU)')


##########################################################################################
##########################################################################################

_KEYWORD_PREFIX_REGEX = re.compile(r'(TARGNAME|TARDESC|TARKEY|MT_LV)')


def _reduced_header(header):
    """The subset of items in the given header that define target uniqueness."""

    header_dict = {}
    for key, value in header.items():
        if _KEYWORD_PREFIX_REGEX.match(key):
            header_dict[key] = value
    return header_dict


def _unique_targets(headers):
    """The subset of the given headers that contain distinct target information."""

    reduced_headers = []
    for header in headers:
        reduced_headers.append(_reduced_header(header))

    indices = []
    unique_headers = []
    for k, reduced_header in enumerate(reduced_headers):
        if reduced_header not in unique_headers:
            unique_headers.append(reduced_header)
            indices.append(k)

    return [headers[k] for k in indices]


def _headers_by_visit(headers):
    """Convert a list of headers to a list of lists, one for each HST visit."""

    header_dict = {}
    for header in headers:
        key = header['FILENAME'][:6]
        header_dict.setdefault(key, []).append(header)

    return list(header_dict.values())


##########################################################################################
