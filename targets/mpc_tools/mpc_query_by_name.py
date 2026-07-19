##########################################################################################
# mpc_tools/mpc_query_by_name.py
##########################################################################################

import bs4
import requests

# noqa: I0001
from ._utils import (_mpc_body_dict, _mpc_date_to_str, _MPC_BY_NAME, _MPC_CACHE,
                     _MPC_CACHING)


def mpc_query_by_name(name, *, logger=None):
    """Get aliases and orbital elements for a body in the MPC database.

    Parameters:
        name (str): The name of the body as used by the MPC.
        logger (PdsLogger, optional): A Logger for messages.

    Returns:
        dict or None: A dictionary of body parameters, including the body's aliases and
        its orbital elements. If the name is not found in the MPC database, a warning
        message is logged and None is returned. Orbital elements are keyed as follows:

        * "A": semimajor axis in AU.
        * "Q": perihelion distance in AU.
        * "I": inclination in degrees.
        * "O": ascending node in degrees.
        * "E": eccentricity.
        * "W": argument of pericenter in degrees.
        * "M": mean anomaly at EPOCH in degrees, if available.
        * "T": time of perihelion passage as "DD-MON-YYYY:hh:mm:ss", if available.
        * "EPOCH": epoch of the elements as "DD-MON-YYYY:hh:mm:ss", if available.

        If the name is not found, a warning is issued to the `logger` and None is
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
        logger and logger.warning(f'No MPC info found for "{name}"')
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
        raise RuntimeError(f'non-standard "show_object" response for MPC key '
                           f'"{name}"') from None

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
            names = [parts[0][1:], parts[2].lstrip(), *names[1:]]
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
                      ('M', 'mean anomaly (°)')]:
        cell = soup.find('td', string=text)
        if not cell:
            continue
        cells = cell.parent.find_all('td')
        try:
            elements[key] = float(cells[1].get_text())
        except ValueError:  # elements can be missing
            pass

    if not elements:
        logger and logger.warning(f'MPC has no orbital elements for "{name}"')
    elif len(elements) < 5:
        logger and logger.warning(f'Orbital element parsing error for "{name}"')

    # Mean anomaly, plus the element epoch and perihelion time as date strings; these
    # support sky-position calculations via orbital_radec.
    cell = soup.find('td', string='mean anomaly (°)')
    if cell:
        try:
            elements['M'] = float(cell.parent.find_all('td')[1].get_text())
        except ValueError:  # pragma: no cover - malformed cell
            pass

    for key, text in [('T', 'perihelion date'),     # e.g., 2027-07-13.44931
                      ('EPOCH', 'epoch')]:          # e.g., 2025-11-21.0
        cell = soup.find('td', string=text)
        if not cell:
            continue
        try:
            elements[key] = _mpc_date_to_str(cell.parent.find_all('td')[1].get_text())
        except ValueError:  # pragma: no cover - malformed cell
            pass

    return _mpc_body_dict(names, elements)


__all__ = ['mpc_query_by_name']

##########################################################################################
