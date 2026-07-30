##########################################################################################
# targets/_utils.py
##########################################################################################

import re


class TargetIdentificationFailure(ValueError):
    """Raised when no target can be identified for an observation, or when a target
    identified by name is incompatible with the orbital elements in the header.
    """


class TargetCategorizationFailure(ValueError):
    """Raised when a minor planet cannot be categorized as TNO, Centaur, asteroid, or
    dwarf planet.
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
