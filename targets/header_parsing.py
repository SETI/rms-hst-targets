##########################################################################################
# header_parsing.py
##########################################################################################
"""Parse the target-description keywords of an HST SPT/SHF header.

These helpers extract the raw target information an SPT/SHF header carries, independently
of how it is later identified: `_collect_strings` gathers the free-text identification
strings (TARKEY*, TARGNAME, TARDESCR/TARDESC*), and `_parse_mt_lv` decodes the MT_LV1_* /
MT_LV2_* moving-target descriptions into a standard body name, a set of orbital elements,
or a pointing/file marker. They are shared by `identify_target` and
`identify_standard_body`.
"""

import re
from logging import Logger


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

    # Split into KEY=VALUE fields; a numeric field without "=" is a value containing a
    # stray comma (e.g. "M=2,3.618253"), so re-attach it to the previous field. Anything
    # else without "=" is free text (e.g. a scheduling comment) and is dropped.
    merged: list[str] = []
    for field in full.split(','):
        if '=' in field:
            merged.append(field)
        elif merged and re.fullmatch(r'[0-9.Ee+-]+', field.strip()):
            merged[-1] += field.strip()
        elif field.strip():
            logger and logger.debug(f'Ignored {prefix} field {field.strip()!r}')

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
