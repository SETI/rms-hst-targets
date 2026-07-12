##########################################################################################
# cometdb/_get_wiki_centaurs.py
##########################################################################################

import re
from logging import Logger

import anyascii
import bs4
import requests

from ._utils import _compare_content, _read_content

_WIKI_CENTAUR_URL = ('https://en.wikipedia.org/wiki/List_of_centaurs_(small_Solar_System'
                     '_bodies)')
_WIKI_HEADERS = {
    'User-Agent': 'update_cometdb/0.9 (https://pds-rings.seti.org/; pds-rings@seti.org)'
}

_NUM_NAME = re.compile(r'(?P<mnum>\d+)\s+'
                       r"(?P<name>[A-Za-z'`][A-Za-z'` -]*[A-Za-z])\s*$")
_NUM_DESIG = re.compile(r'\((?P<mnum>\d+)\)\s+'
                        r'(?P<desig>[12]\d\d\d [A-Z][A-Z]?\d*)\s*$')
_DESIG = re.compile(r'(?P<desig>[12]\d\d\d [A-Z][A-Z]?\d*)\s*$')


def _get_wiki_centaurs(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the contents of a Wikipedia list of centaurs.

    Parameters:
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `centaurs`), where `changed` is True if the online content is new;
        `centaurs` is a list of dictionaries of centaur information.
    """

    raise RuntimeError('Do not use _get_wiki_centaurs(); the page is not kept up to date')

    basename = _WIKI_CENTAUR_URL.rpartition('/')[-1] + '.html'

    if update:
        logger and logger.info('Retrieving URL ' + _WIKI_CENTAUR_URL)
        request = requests.get(_WIKI_CENTAUR_URL, headers=_WIKI_HEADERS, timeout=30)
        request.raise_for_status()
        html = request.content
    else:
        html = _read_content(basename, logger)

    soup = bs4.BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')

    centaurs = []
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != 15:  # these tables all have 15 columns per row
            continue

        # Skip rows that are grayed out
        if cells[5].text[2:] != 'CEN':
            continue

        # "Lists of comets (more)" also has 15 columns, but it's after the table
        name = anyascii.anyascii(cells[0].text).strip()
        if name.startswith('Lists '):
            break

        for regex in (_NUM_NAME, _NUM_DESIG, _DESIG):
            match = regex.fullmatch(name)
            if match:
                centaur = match.groupdict()
                # print('matched!', repr(name))
                break
        if not match:
            logger and logger.error(f'Failed to match Wikipedia row "{name}"')
            continue

        for key, colno in [('A', 7), ('E', 8), ('I', 9), ('Q', 10)]:
            centaur[key] = float(cells[colno].text)

        centaurs.append(centaur)

    if update:
        changed = _compare_content(html, basename, logger)
    else:
        changed = False

    return changed, centaurs

##########################################################################################
