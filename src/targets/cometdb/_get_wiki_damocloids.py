##########################################################################################
# cometdb/_get_wiki_damocloids.py
##########################################################################################

import re
from logging import Logger

import anyascii
import bs4
import requests

from ._utils import _compare_content, _read_content
from targets.targettype import TargetType

_WIKI_DAMOCLOID_URL = 'https://en.wikipedia.org/wiki/Damocloid'
_WIKI_HEADERS = {
    'User-Agent': 'update_cometdb/0.9 (https://pds-rings.seti.org/; pds-rings@seti.org)'
}

_NUM_NAME = re.compile(r'(?P<mnum>\d+)\s+'
                       r"(?P<name>[A-Za-z'`][A-Za-z'` -]*[A-Za-z])\s*$")
_NUM_DESIG = re.compile(r'\((?P<mnum>\d+)\)\s+'
                        r'(?P<desig>[12]\d\d\d [A-Z][A-Z]?\d*)\s*$')
_DESIG = re.compile(r'(?P<desig>(?:A/|)[12]\d\d\d [A-Z][A-Z]?\d*)\s*$')

_TTYPE_LOOKUP = {'CEN': TargetType.CENTAUR,
                 'MBA': TargetType.ASTEROID,
                 'NEO': TargetType.ASTEROID,
                 'TNO': TargetType.TRANS_NEPTUNIAN_OBJECT,
                 'other': TargetType.ASTEROID}


def _get_wiki_damocloids(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the contents of a Wikipedia list of damocloids, which are classified as either
    TNO or centaur.

    Parameters:
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `centaurs`), where `changed` is True if the online content is new;
        `centaurs` is a list of dictionaries of centaur information.
    """

    basename = _WIKI_DAMOCLOID_URL.rpartition('/')[-1] + '.html'

    if update:
        logger and logger.info('Retrieving URL ' + _WIKI_DAMOCLOID_URL)
        request = requests.get(_WIKI_DAMOCLOID_URL, headers=_WIKI_HEADERS, timeout=30)
        request.raise_for_status()
        html = request.content
    else:
        html = _read_content(basename, logger)

    soup = bs4.BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')

    damocloids = []
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != 13:  # these tables all have 13 columns per row
            continue

        name = anyascii.anyascii(cells[0].text).strip()
        for regex in (_DESIG, _NUM_DESIG, _NUM_NAME):
            match = regex.fullmatch(name)
            if match:
                damocloid = match.groupdict()
                # print('matched!', repr(name))
                break
        if not match:
            logger and logger.error(f'Failed to match Wikipedia row "{name}"')
            continue

        key = cells[4].text.strip()
        try:
            damocloid['ttype'] = _TTYPE_LOOKUP[key]
        except KeyError:
            logger and logger.error(f'Unrecognized damocloid type "{key}"')
            continue

        damocloids.append(damocloid)

    if update:
        changed = _compare_content(html, basename, logger)
    else:
        changed = False

    return changed, damocloids

##########################################################################################
