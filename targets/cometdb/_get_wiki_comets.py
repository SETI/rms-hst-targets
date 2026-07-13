##########################################################################################
# cometdb/_get_wiki_comets.py
##########################################################################################

import re
from logging import Logger

import anyascii
import bs4

from targets.mpc_tools import mpc_query_by_name

from ._utils import _compare_content, _fetch, _read_content

_WIKI_URLS = [('https://en.wikipedia.org/wiki/List_of_periodic_comets', 12),
              ('https://en.wikipedia.org/wiki/List_of_Halley-type_comets', 12),
              ('https://en.wikipedia.org/wiki/List_of_long-period_comets', 11),
              ('https://en.wikipedia.org/wiki/List_of_near-parabolic_comets', 11),
]
_WIKI_HEADERS = {
    'User-Agent': 'update_cometdb/0.9 (https://pds-rings.seti.org/; pds-rings@seti.org)'
}


def _get_wiki_comets(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the contents of the Wikipedia lists of comets.

    Parameters:
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `comets`), where `changed` is True if the online content is new;
        `comets` is a list of dictionaries of comet information.
    """

    changed, comets = _get_wiki_numbered_comets(update, logger)

    changed1, comets1 = _get_wiki_interstellar_comets(update, logger)
    comets += comets1
    changed |= changed1

    for url, columns in _WIKI_URLS:
        changed1, comets1 = _get_wiki_comet_list(url, columns, update, logger)
        comets += comets1
        changed |= changed1

    return changed, comets


_DESIG_FRAG_SPLITTER = re.compile(r'([CPDXI])\s*/\s*(-?\d*)\s*([A-Z][A-Z]?)\s*(\d*)'
                                  r'\s*(?P<dash>-)?(?(dash)(?P<fragment>[A-Z][A-Z]?\d?))')
_NAME_N = re.compile(r"(?P<name>[A-Za-z'][A-Za-z' -]*[A-Za-z]) *(?P<cnum>\d*).*")

def _get_wiki_comet_list(
    url: str,
    columns: int,
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the contents of a Wikipedia list of comets.

    Parameters:
        url: URL of the page.
        columns: Number of required columns per row.
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `comets`), where `changed` is True if the online content is new;
        `comets` is a list of dictionaries of comet information.
    """

    basename = url.rpartition('/')[-1] + '.html'

    if update:
        request = _fetch(url, logger=logger, headers=_WIKI_HEADERS)
        if request is None:
            update = False  # fall back to the cached copy
        else:
            html = request.content
    if not update:
        html = _read_content(basename, logger)

    soup = bs4.BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')

    comets = []
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != columns:
            continue

        name = anyascii.anyascii(cells[1].text).strip()
        if name:
            match = _NAME_N.fullmatch(name)
            if match:
                comet = match.groupdict()
                if comet['name'].endswith(' of'):
                    comet['name'] += ' ' + comet['cnum']
                    comet['cnum'] = ''
            else:
                logger and logger.error(f'Failed to match Wikipedia row "{name}"')
                continue
        else:
            comet = {}

        text = anyascii.anyascii(cells[0].text)
        parts = _DESIG_FRAG_SPLITTER.split(text)

        desigs = []
        year = '9999'
        for k in range(1, len(parts), 7):
            prefix, y, code, digits, dash, fragment = parts[k:k+6]
            desig = f'{prefix}/{y} {code}{digits}'
            comet['fragment'] = fragment
            if dash and k > 1:
                desig += '-' + fragment
            desigs.append(desig)
            year = min(year, y)
        # print(desigs, year)
        # print([x.strip() for x in parts[::7]])  # for testing/debugging

        if comet.get('fragment', '') is None:
            comet['fragment'] = ''

        comet['prefix'] = desigs[0][0]
        comet['desig'] = desigs[0]
        comet['alt_desigs'] = desigs[1:]
        comet['year'] = year
        for key, colno in [('E', 3), ('Q', 5), ('I', 6)]:
            text = anyascii.anyascii(cells[colno].text.strip())
            if text and text != '-':
                comet[key] = float(text)
        if 'E' in comet and 'Q' in comet:
            comet['A'] = comet['Q'] / (1. - comet['E'])

        comets.append(comet)

    if update:
        changed = _compare_content(html, basename, logger)
    else:
        changed = False

    return changed, comets

##########################################################################################

_WIKI_NUMBERED_URL = 'https://en.wikipedia.org/wiki/List_of_numbered_comets'

_DESIG_SPLITTER = re.compile(r'([CPDXI])\s*/\s*(-?\d*)\s*([A-Z][A-Z]?)\s*(\d*)')

_NP_NAME_NAME_N = re.compile(r'(?P<prefix>\d+[CPDXI])/'
                             r"(?P<name>[A-Za-z'`][A-Za-z'` -]*[A-Za-z])\s*"
                             r'\(\2\s+(?P<cnum>\d+)', re.DOTALL)
_NP_DESIG_MNUM = re.compile(r'(?P<prefix>\d+[CPDXI])/'
                            r'(?P<desig1>[12]\d\d\d [A-Z][A-Z]?)\s*'
                            r'(?P<desig2>\d*)\s.*=\s*\((?P<mnum>\d+)', re.DOTALL)
_NP_NAME = re.compile(r'(?P<prefix>\d+[CPDXI])/'
                      r"(?P<name>[A-Za-z'`][A-Za-z`' -]*[A-Za-z])",
                      re.UNICODE)

_NP_NAME_N_FRAG = re.compile(r"(?P<prefix>\d+[CPDXI])/(?P<name>[A-Za-z' -]+[A-Za-z])\s*"
                             r'(?P<cnum>\d*)-(?P<fragment>[A-Z][A-Z]?\d?)'
                             r'(\(.*\)|)\s*$', re.DOTALL)
# full name after at end inside parentheses (needed for 141P/Machholz fragments)
_NP_NAME_N_FRAG2 = re.compile(r'.*\(\s*' + _NP_NAME_N_FRAG.pattern[:-1] + r'\s*\)\s*$',
                              re.DOTALL)

# Extracted from https://en.wikipedia.org/wiki/Halley%27s_Comet#List_of_apparitions
_HALLEY_DESIGS = ['P/-239 K1', 'P/-163 U1', 'P/-86 Q1', 'P/-11 Q1', 'P/66 B1',
                  'P/141 F1', 'P/218 H1', 'P/295 J1', 'P/374 E1', 'P/451 L1',
                  'P/530 Q1', 'P/607 H1', 'P/684 R1', 'P/760 K1', 'P/837 F1',
                  'P/912 J1', 'P/989 N1', 'P/1066 G1', 'P/1145 G1', 'P/1222 R1',
                  'P/1301 R1', 'P/1378 S1', 'P/1456 K1', 'P/1531 P1', 'P/1607 S1',
                  'P/1682 Q1', 'P/1758 Y1', 'P/1835 P1', 'P/1909 R1', 'P/1982 U1']
_HALLEY_OLD_DESIGS = ['1759 I', '1835 III', '1909c', '1986 III', '1982i']


def _get_wiki_numbered_comets(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the contents of the Wikipedia lists of numbered comets.

    Parameters:
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `comets`), where `changed` is True if the online content is new;
        `comets` is a list of dictionaries of comet information.
    """

    basename = _WIKI_NUMBERED_URL.rpartition('/')[-1] + '.html'

    if update:
        request = _fetch(_WIKI_NUMBERED_URL, logger=logger, headers=_WIKI_HEADERS)
        if request is None:
            update = False  # fall back to the cached copy
        else:
            html = request.content
    if not update:
        html = _read_content(basename, logger)

    soup = bs4.BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')

    comets = []
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != 12:  # these tables all have 12 columns per row
            continue

        name = anyascii.anyascii(cells[0].text).strip()
        year = '9999'
        for regex in (_NP_NAME_NAME_N, _NP_DESIG_MNUM, _NP_NAME):
            match = regex.match(name)
            if match:
                comet = match.groupdict()
                break
        if not match:
            logger and logger.error(f'Failed to match Wikipedia row "{name}"')
            continue

        if 'desig1' in comet:
            year = comet['desig1'][:4]
            comet['desig'] = comet['prefix'][-1] + '/' + comet['desig1'] + comet['desig2']
            del comet['desig1']
            del comet['desig2']

        text = anyascii.anyascii(cells[1].text)
        parts = _DESIG_SPLITTER.split(text)
        alt_desigs = []
        for k in range(1, len(parts), 5):
            lett, y, code, digits = parts[k:k+4]
            alt_desig = f'{lett}/{y} {code}{digits}'
            alt_desigs.append(alt_desig)
            year = min(year, y)
            # print([x.strip() for x in parts[::5]])  # for testing/debugging

        if year == '9999' and comets:   # skip test for 1P/Halley
            logger and logger.warning(f'Year unavailable for Wikipedia row "{name}"')
            year = ''

        if comet.get('fragment', '') is None:
            comet['fragment'] = ''

        comet['alt_desigs'] = alt_desigs
        comet['year'] = year
        comet['E'] = float(cells[4].text.strip())
        comet['A'] = float(cells[5].text.strip())
        comet['I'] = float(cells[6].text.strip())
        comet['Q'] = comet['A'] * (1. - comet['E'])

        comets.append(comet)

    # 1P/Halley comet designations (from a different Wikipedia page)
    comets[0]['alt_desigs'] = _HALLEY_DESIGS
    comets[0]['old_desigs'] = _HALLEY_OLD_DESIGS
    comets[0]['year'] = _HALLEY_DESIGS[0][3:7]

    # Read the fragment tables
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != 10:  # these tables all have 10 columns per row
            continue

        name = anyascii.anyascii(cells[0].text).strip()
        matches = []
        for regex in (_NP_NAME_N_FRAG, _NP_NAME_N_FRAG2):
            match = regex.match(name)
            if match:
                matches.append(match)

        if matches:
            comet = matches[0].groupdict()
            comet['E'] = float(cells[2].text)
            comet['A'] = float(cells[3].text)
            comet['I'] = float(cells[4].text)
            comet['Q'] = comet['A'] * (1. - comet['E'])
            comets.append(comet)

        for match in matches[1:]:
            alt = match.groupdict()
            comet['alt_frags'] = [alt['fragment']]

    if update:
        changed = _compare_content(html, basename, logger=logger)
    else:
        changed = False

    return changed, comets

##########################################################################################

_WIKI_INTERSTELLAR_URL = 'https://en.wikipedia.org/wiki/Interstellar_object'

_I_DESIG_NAME = re.compile(r'(?P<prefix>\d+[CPDXI])/'
                           r'(?P<desig>[12]\d\d\d [A-Z][A-Z]?\d*)\s*'
                           r"\((?P<name>[A-Za-z'`][A-Za-z'` -]*[A-Za-z])"
                           r' *(?P<cnum>\d*)\)$')
_I_DESIG = re.compile(r'(?P<prefix>\d+[CPDXI])/(?P<desig>[12]\d\d\d [A-Z][A-Z]?\d*)$')
_I_NAME = re.compile(r"(?P<prefix>\d+[CPDXI])/(?P<name>[A-Za-z'`][A-Za-z'` -]*[A-Za-z])"
                     r' *(?P<cnum>\d*)$')

def _get_wiki_interstellar_comets(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the contents of the Wikipedia lists of numbered comets.

    Parameters:
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `comets`), where `changed` is True if the online content is new;
        `comets` is a list of dictionaries of comet information.
    """

    basename = _WIKI_INTERSTELLAR_URL.rpartition('/')[-1] + '.html'

    if update:
        request = _fetch(_WIKI_INTERSTELLAR_URL, logger=logger, headers=_WIKI_HEADERS)
        if request is None:
            update = False  # fall back to the cached copy
        else:
            html = request.content
    if not update:
        html = _read_content(basename, logger)

    # Brute force: look for the appropriate headers in the Interstellar Objects page
    soup = bs4.BeautifulSoup(html, 'html.parser')
    headers = soup.find_all('h4')
    names = [anyascii.anyascii(h.text.strip()).replace('`', "'") for h in headers]
    names = [n for n in names if 'I/' in n]

    comets = []
    for name in names:
        for regex in (_I_NAME, _I_DESIG_NAME, _I_DESIG):
            match = regex.fullmatch(name)
            if match:
                comet = match.groupdict()
                break
        if not match:
            logger and logger.error(f'Failed to match Wikipedia row "{name}"')
            continue

        # Ignore the Wikipedia designation
        if 'desig' in comet:
            del comet['desig']

        body = mpc_query_by_name(comet['prefix'], logger=logger)
        if body:
            desigs = ([body['desig']] if body['desig'] else []) + body['alt_desigs']
            desigs = [d.replace(' (' + comet['name'] + ')', '') for d in desigs]
            desigs = [d for d in desigs if '/2' in d]
            elements = {k: body[k] for k in 'AQIOEW' if k in body}

            comet['alt_desigs'] = desigs
            comet.update(elements)
        comets.append(comet)

    if update:
        changed = _compare_content(html, basename, logger=logger)
    else:
        changed = False

    return changed, comets


__all__ = ['_get_wiki_comets']

##########################################################################################
