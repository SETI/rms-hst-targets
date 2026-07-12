##########################################################################################
# cometdb/_get_ssd_comets.py
##########################################################################################

import re
from logging import Logger

from ._utils import _compare_content, _fetch, _read_content

_SSD_URL = 'https://ssd-api.jpl.nasa.gov/sbdb_query.api'
_SSD_BASENAME = 'sbdb_query_results.csv'
_SSD_PARAMS = {
    'sb-kind': 'c',
    'fields': 'spkid,full_name,a,q,i,om,e,w',
    'full-prec': 'true'
}

_SSD_NUMBERED = re.compile(r'(?P<prefix>\d+[CPDXI])/'
                           r"(?P<name>[A-Za-z'][A-Za-z' -]*[A-Za-z])"
                           r'(?P<space> )?(?(space)(?P<cnum>\d*))'
                           r'(?P<dash>-)?(?(dash)(?P<fragment>[A-Z][A-Z]?\d?))$')
_SSD_FRAGMENT = re.compile(r'(?P<prefix>[CPDXI])/(?P<desig>-?\d+ [A-Z][A-Z]?\d*)'
                           r'(?P<dash>-)?(?(dash)(?P<fragment>[A-Z][A-Z]?\d?))'
                           r" ?\(?(?P<name>[A-Za-z' -]*?) ?(?P<cnum>\d*)\)?$")
_SSD_NAMED = re.compile(r'(?P<prefix>[CPDXI])/(?P<desig>-?\d+ [A-Z][A-Z]?\d*)'
                        r" ?\(?(?P<name>[A-Za-z'].*?)\)$")


def _get_ssd_comets(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the list of comets from the JPL Horizons system.

    Parameters:
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `comets`), where `changed` is True if the online content is new;
        `comets` is a list of dictionaries of comet information.
    """

    # Retrieve Horizons content
    if update:
        request = _fetch(_SSD_URL, logger=logger, params=_SSD_PARAMS)
        if request is None:
            update = False  # fall back to the cached copy
        else:
            table = request.json()['data']
    if not update:
        content = _read_content(_SSD_BASENAME, logger)
        table = eval(content)

    # Convert to list of dicts
    comets = []
    for row in table:
        full_name = row[1].strip()
        for regex in (_SSD_NUMBERED, _SSD_FRAGMENT, _SSD_NAMED):
            match = regex.match(full_name)
            if match:
                comet = match.groupdict()
                break
        if not match:
            logger and logger.error(f'Failed to match SSD row "{full_name}"')
            continue

        if 'desig' in comet:
            comet['year'] = comet['desig'].partition(' ')[0]
            comet['desig'] = comet['prefix'] + '/' + comet['desig']

        if 'name' in comet and not comet.get('fragment', ''):
            parts = comet['name'].rpartition('-')
            if len(parts[-1]) <= 2 and parts[-1].isupper():
                comet['fragment'] = parts[-1]
                comet['name'] = parts[0]

        if 'name' in comet and ' comet' in comet['name'] and 'year' in comet:
            comet['name'] += ' of ' + comet['year']

        comet['naif_id'] = int(row[0])
        comet['A'] = float(row[2]) if row[2] is not None else 0.
        comet['Q'] = float(row[3])
        comet['I'] = float(row[4])
        comet['O'] = float(row[5])
        comet['E'] = float(row[6])
        comet['W'] = float(row[7])

        if 'dash' in comet:
            del comet['dash']
        if 'space' in comet:
            del comet['space']
        for key, value in comet.items():
            if value is None:
                comet[key] = ''

        comets.append(comet)

    if update:
        changed = _compare_content(repr(table), _SSD_BASENAME, logger=logger)
    else:
        changed = False

    return changed, comets

##########################################################################################
