##########################################################################################
# cometdb/_get_johnston_centaurs.py
##########################################################################################

from logging import Logger

import bs4

from ._utils import _compare_content, _fetch, _read_content

_JOHNSTON_URL = 'https://www.johnstonsarchive.net/astro/tnoslist.html'
_JOHNSTON_BASENAME = 'johnstonarchive_tnoslist.txt'

# int indicates a column index that must be blank.
# (int, char) indicates a column index where the char must appear.
_COLUMN_TESTS = [0, (8, ') '), 9, 35, 50, 65, 75, 105, 113]


def _get_johnston_centaurs(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the contents of a Johnston list of centaurs.

    Other objects such as TNOs are deleted from the list.

    Parameters:
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `centaurs`), where `changed` is True if the online content is new;
        `centaurs` is a list of dictionaries of centaur information.
    """

    if update:
        request = _fetch(_JOHNSTON_URL, logger=logger)
        if request is None:
            update = False  # fall back to the cached copy
        else:
            # Create filtered list of strings
            soup = bs4.BeautifulSoup(request.content, 'html.parser')
            content = soup.find('pre').text
    if not update:
        content = _read_content(_JOHNSTON_BASENAME, logger)

    recs = content.split('\n')
    recs = [rec.rstrip() for rec in recs if 'Centaur ' in rec]

    # Extract centaur info from table
    centaurs = []
    for k, rec in enumerate(recs):
        error_found = False
        for test in _COLUMN_TESTS:
            col, chars = test if isinstance(test, tuple) else (test, ' ')
            if rec[col] not in chars:
                logger and logger.error(f'Mis-aligned column at record[{k}][{col}]: '
                                        f'"{rec[:114]}"')
                error_found = True
                break
        if error_found:
            continue

        number = rec[:8].lstrip(' (')
        name = rec[10:36].rstrip()
        desig = rec[36:51].rstrip()
        a = float(rec[66:75])
        e = float(rec[75:84])
        i = float(rec[105:113])
        centaur = {'mnum': number, 'name': name, 'desig': desig, 'A':a, 'E':e, 'I':i}
        centaurs.append(centaur)

    if update:
        changed = _compare_content(recs, _JOHNSTON_BASENAME, logger)
    else:
        changed = False

    return changed, centaurs


__all__ = ['_get_johnston_centaurs']

##########################################################################################
