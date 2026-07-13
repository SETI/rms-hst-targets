##########################################################################################
# cometdb/_get_sbn_comets.py
##########################################################################################

import re
from logging import Logger

import bs4

from ._utils import _compare_content, _fetch, _read_content

_SBN_URL = 'https://pds-smallbodies.astro.umd.edu/data_sb/resources/periodic_comets.shtml'
_SBN_BASENAME = 'sbn_periodic_comets.txt'
_SBN_HEADERS = re.compile(r' *(Unnamed comets|Official|Designation|$)')

_COLUMN_TESTS = [(4, '/'), 15, 44, 74]


def _get_sbn_comets(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the list of comets from the PDS Small Bodies Node.

    Parameters:
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `comets`), where `changed` is True if the online content is new;
        `comets` is a list of dictionaries of comet information.
    """

    # Retrieve SBN content
    if update:
        request = _fetch(_SBN_URL, logger=logger)
        if request is None:
            update = False  # fall back to the cached copy
        else:
            # Create filtered list of strings
            soup = bs4.BeautifulSoup(request.content, 'html.parser')
            content = soup.find('pre').text
    if not update:
        content = _read_content(_SBN_BASENAME, logger)

    recs = content.split('\n')
    recs = [rec.rstrip() for rec in recs if not _SBN_HEADERS.match(rec)]

    # Extract comet info from table
    comets = []
    for k, rec in enumerate(recs):
        rec = rec.ljust(82)

        error_found = False
        for test in _COLUMN_TESTS:
            col, chars = test if isinstance(test, tuple) else (test, ' ')
            if rec[col] not in chars:
                logger and logger.error(f'Mis-aligned column at record[{k}][{col}]: '
                                        f'"{rec}"')
                error_found = True
                break
        if error_found:
            continue

        prefix = rec[:4].lstrip()
        desig = rec[3:15].strip()
        year = rec[5:9]
        name_num = rec[45:74].rstrip()
        extras = rec[82:].strip()

        desig, _, fragment = desig.partition('-')
        comet = {'prefix': prefix, 'desig': desig, 'year': year, 'fragment': fragment}
        if name_num:
            if name_num[-1].isdigit():
                name, _, num = name_num.rpartition(' ')
                comet['name'] = name
                comet['cnum'] = num
            elif name_num[0] == '(':
                comet['mnum'] = name_num[1:-1]
            else:
                comet['name'] = name_num
                comet['cnum'] = num

        # Construct list of alt_desigs and alt_names
        alt_desigs = []
        alt_names = []
        if len(prefix) > 1 and 'name' in comet:  # no desig for a named, numbered comet
            alt_desigs.append(desig)
            del comet['desig']

        if desig == 'P/2016 J1':  # fix known formatting error
            extras = 'P/2020 Y6-A, P/2021 K5-B'

        if ',' in extras:
            extras = extras.split(',')
        elif extras:
            extras = [extras]
        else:
            extras = []
        extras = [e.strip() for e in extras]

        for extra in extras:
            if '/' in extra:
                alt_desigs.append(extra)
            else:
                alt_names.append(extra)

        comet['alt_desigs'] = alt_desigs
        comet['alt_names'] = alt_names

        comets.append(comet)

    # Remove extraneous cnums
    by_name = {}
    for comet in comets:
        if 'name' in comet:
            by_name.setdefault(comet['name'], []).append(comet)

    for name, comet_list in by_name.items():
        if len(comet_list) == 1 and comet_list[0]['cnum'] == '1':
            comet = comet_list[0]
            alt_names = comet.setdefault('alt_names', [])
            comet['alt_names'].append(name + ' 1')
            comet['cnum'] = ''

    if update:
        changed = _compare_content(content, _SBN_BASENAME, logger=logger)
    else:
        changed = False

    return changed, comets


__all__ = ['_get_sbn_comets']

##########################################################################################
