##########################################################################################
# mpc_tools/mpc_query_by_name.py
##########################################################################################

from logging import Logger
import math
import os
import pathlib
import re

import bs4
import requests

from .mpc_body_dict import mpc_body_dict

try:
    _MPC_CACHE = pathlib.Path(os.path.dirname(__file__)).parent.parent / 'caches/MPC_CACHE'
except NameError:
    _MPC_CACHE = pathlib.Path('./MPC_CACHE')

_MPC_BY_NAME = 'https://minorplanetcenter.net/db_search/show_object?object_id='
_MPC_BY_PROPERTIES = 'https://www.minorplanetcenter.net/db_search/show_by_properties?'
_MPC_CACHING = True


def mpc_query_by_name(
    name: str, *,
    logger: Logger | None = None
) -> dict | None:
    """Get aliases and orbital elements for a body in the MPC database.

    Parameters:
        name: The name of the body as used by the MPC.
        logger: An optional Logger for messages.

    Returns:
        A tuple (`body`, `rms`) (if `count` == 1) or a list thereof. Here, `body` is the
        dictionary of body parameters and `rms` is the root-mean-square fractional
        discrepancy between the given `elements` and those in the database.

        (names, elements): A list of body aliases (probably including `name`) and a
            dictionary of orbital elements keyed by element name, as follows:

            * "A": semimajor axis in AU.
            * "Q": perihelion distance in AU.
            * "I": inclination in degrees.
            * "O": ascending node in degrees.
            * "E": eccentricity.
            * "W": argument of pericenter in degrees.

        If the name is not found, a warning is issued to the `logger` and ([], {}) is
        returned.

    Raises:
        requests.RequestException: If the query to the MPC "show_object" tool fails. This
            will actually be an informative subclass of RequestException.
        RuntimeError: If the MPC returns a malformed web page.
    """

    # Retrieve from cache if available
    html = b''
    if _MPC_CACHING:
        filepath = _MPC_CACHE / (name.upper().replace('/', '-') + '.html')
        if filepath.exists():
            html = filepath.read_bytes()

    # Otherwise, retrieve from MPC
    if not html:
        url = _MPC_BY_NAME + requests.utils.quote(str(name), safe='/')
        request = requests.get(url, allow_redirects=True)
        request.raise_for_status()

        html = request.content
        if _MPC_CACHING:
            # Delete observation table because it can be huge
            parts = html.partition(b'<h2>Observations</h2>')
            if parts[2]:
                before_table = parts[2].partition(b'<table>')[0]
                after_table = parts[2].partition(b'</table>')[2]
                html = parts[0] + parts[1] + before_table + after_table

            with open(filepath, 'wb') as f:
                f.write(html)

    # You might get a list of "Vaguely similar sounding possible matches"
    if not html or b'Vaguely similar sounding' in html:
        logger and logger.warn(f'No MPC info found for "{name}"')
        return None

    soup = bs4.BeautifulSoup(html, 'html.parser')
    divs = soup.find_all('div')
    divs = [d for d in divs if 'id' in d.attrs and d.attrs['id'] == 'main']

    # Mal-formed pages indicate an unknown error
    if len(divs) == 0:
        raise RuntimeError(f'invalid "show_object" response for MPC key "{name}"; '
                           'no main <div>')

    if len(divs) > 1:
        raise RuntimeError(f'invalid "show_object" response for MPC key "{name}"; '
                           'multiple main <div>s')

    # One sign of failure
    try:
        info = divs[0].h3.text
    except AttributeError:
        raise RuntimeError(f'non-standard "show_object" response for MPC key "{name}"')

    # Another sign of failure
    if info.strip().startswith('Data about'):
        raise RuntimeError(f'No MPC info found for "{name}"')

    # Get names
    divs = soup.find_all('div')
    divs = [d for d in divs if 'id' in d.attrs and d.attrs['id'] == 'main']

    info = divs[0].h3.text
    parts = info.split()
    info = ' '.join(parts)

    parts = info.split('=')
    names = [p.strip() for p in parts]

    # Split a leading minor planet number from a name
    if names[0].startswith('('):
        parts = names[0].partition(')')
        if parts[2]:  # if it has a name as well as a number
            names = [parts[0][1:], parts[2].lstrip()] + names[1:]
        else:
            names[0] = parts[0][1:]

    # Get orbital elements
    elements = {}
    for key, text in [('A', 'semimajor axis (AU)'),
                      ('Q', 'perihelion distance (AU)'),
                      ('I', 'inclination (°)'),
                      ('O', 'ascending node (°)'),
                      ('E', 'eccentricity'),
                      ('W', 'argument of perihelion (°)'),
                     ]:
        cell = soup.find('td', string=text)
        if not cell:
            continue
        cells = cell.parent.find_all('td')
        try:
            elements[key] = float(cells[1].get_text())
        except ValueError:  # elements can be missing
            pass

    if not elements:
        logger and logger.warn('MPC has no orbital elements for "{name}"')
    elif len(elements) < 5:
        logger and logger.warn('Orbital element parsing error for "{name}"')

    return mpc_body_dict(names, elements)

##########################################################################################
