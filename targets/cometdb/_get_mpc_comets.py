##########################################################################################
# cometdb/_get_mpc_comets.py
##########################################################################################

import re
from logging import Logger

import bs4

from ._utils import _compare_content, _fetch, _read_content

_MPC_URL = 'https://www.minorplanetcenter.net/iau/lists/PeriodicCodes.html'
_MPC_BASENAME = 'mpc_PeriodicCodes.txt'
_MPC_HEADERS = re.compile(r'(Number|$)')

_COLUMN_TESTS = [0, (4, 'PD'), 5, 6, 48]

def _get_mpc_comets(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the list of comets from the Minor Planet Center.

    Parameters:
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `comets`), where `changed` is True if the online content is new;
        `comets` is a list of dictionaries of comet information.
    """

    # Retrieve content
    if update:
        request = _fetch(_MPC_URL, logger=logger)
        if request is None:
            update = False  # fall back to the cached copy
        else:
            soup = bs4.BeautifulSoup(request.content, 'html.parser')
            content = soup.find('pre').text
    if not update:
        content = _read_content(_MPC_BASENAME, logger)

    recs = content.split('\n')
    recs = [rec.rstrip() for rec in recs if not _MPC_HEADERS.match(rec)]

    # Extract comet info from table
    comets = []
    for k, rec in enumerate(recs):
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

        rec = rec.ljust(90)
        prefix = rec[:5].strip()
        name = rec[7:48].strip()
        desig = rec[49:].strip()

        # Fix known errors
        if prefix == '420P' and name == 'McNaught':
            prefix = '421P'
        if prefix in ('282P', '288P', '362P', '433P'):
            name = ''  # unnamed minor planets, not comets

        comet = {'prefix': prefix, 'name': name, 'desig': desig}
        comets.append(comet)

    if update:
        changed = _compare_content(content, _MPC_BASENAME, logger=logger)
    else:
        changed = False

    return changed, comets[::-1]


__all__ = ['_get_mpc_comets']

##########################################################################################
