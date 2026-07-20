##########################################################################################
# targets/mpc_tools/mpc_query_by_elements.py
##########################################################################################

import hashlib
import math
import re

import numpy as np
import requests

from ._utils import _MPC_BY_PROPERTIES, _MPC_CACHE, _MPC_CACHING
from .mpc_query_by_name import mpc_query_by_name

_OBJECT_COUNT_RE = re.compile(rb'(\d+) objects match search criteria.')
_OBJECT_NAME_RE = re.compile(rb'\(?<a href="(.*?)">(.*?)</a>\)? *')

DPR = 180. / math.pi


def mpc_query_by_elements(elements, delta=0.04, *, count=1, bodies=None, logger=None):
    """Identify a body in the MPC database based on orbital elements.

    Parameters:
        elements (dict): A dictionary containing any or all orbital elements keyed by
            element name, as follows:

            * "A": semimajor axis in AU.
            * "Q": perihelion distance in AU.
            * "I": inclination in degrees.
            * "O": ascending node in degrees.
            * "E": eccentricity.
            * "W": argument of pericenter in degrees.

        delta (float): Upper limit on the discrepancy in each orbital element or element
            pair. This is a fractional uncertainty for `A` and `Q` but an absolute
            uncertainty in the other elements (when `I`, `O`, and `W` are given in
            radians).
        count (int, optional): The maximum number of items to return. If 1, a single tuple
            (`body`, `rms`) is returned; otherwise, a list of `count` such tuples is
            returned.
        bodies (list[dict], optional): List of body dictionaries to check; if the list is
            empty, every known minor planet is checked.
        logger (PdsLogger, optional): PdsLogger for messages.

    Returns:
        tuple or list[tuple]: A tuple (`body`, `rms`) if `count` == 1; otherwise a list
        of up to `count` of these tuples.

            * `body` (dict): Dictionary of body parameters.
            * `rms` (float): The root-mean-square fractional discrepancy between the given
              `elements` and those in the database.

    Raises:
        requests.RequestException: If the query to the MPC "show_by_properties" tool
            fails. This will actually be an informative subclass of RequestException.
        RuntimeError: If the MPC returns a malformed web page.
    """

    if bodies:
        resids = []
        for body in bodies:
            rms, element_count = element_resid(elements, body)
            if element_count >= 3:
                resids.append((rms, body))

        if not resids:
            logger and logger.warning('No minor planet found matching the given elements')
            return []

        resids.sort()
        rms, body = resids[0]
        full_name = body['full_name']
        logger and logger.info(f'Minor planet "{full_name}" found with orbit residual '
                               f'{rms:.4f}')
        if count == 1:
            return body, rms

        rms_list = ', '.join([f'{resid[0]:.4f}' for resid in resids[1:count]])
        logger and logger.info(f'Next-best orbit residuals: [{rms_list}]')
        pairs = []
        for resid in resids[:count]:
            rms, body = resid
            pairs.append((body, rms))

        return pairs

    reduced = False
    for _ in range(5):
        url = _mpc_element_query_url(elements, delta)
        try:
            table = _read_mpc_element_table(url)
        except RuntimeError as err:
            if 'Too many objects to display' not in str(err):
                raise
            delta /= 1.5
            reduced = True
            logger and logger.debug(f'Reducing delta to {delta}')
        else:
            if len(table) < count and not reduced:
                delta *= 1.5
                logger and logger.debug(f'Increasing delta to {delta}')
            else:
                break

    if not table:
        logger and logger.warn('No object with matching elements found at MPC')
        return []

    resids = [(element_resid(elements, t)[0], key) for key, t in table.items()]
    resids.sort()

    rms, key = resids[0]
    logger and logger.debug(f'Minor planet "{key}" found with orbit residual {rms:.4f}')
    if count == 1:
        return (mpc_query_by_name(key), rms)

    rms_list = ', '.join([f'{resid[0]:.4f}' for resid in resids[1:count]])
    logger and logger.debug(f'Next-best orbit residuals: [{rms_list}]')

    return [(mpc_query_by_name(key), rms) for rms, key in resids[:count]]


def _mpc_element_query_url(elements, delta):
    """Construct the URL for a query to the MPC database.

    Parameters:
        elements (dict): A dictionary containing any or all orbital elements keyed by
            element name, as follows:

            * "A": semimajor axis in AU.
            * "Q": perihelion distance in AU.
            * "I": inclination in degrees.
            * "O": ascending node in degrees.
            * "E": eccentricity.
            * "W": argument of pericenter in degrees.

        delta (float): Upper limit on the discrepancy in each orbital element or element
            pair. This is a fractional uncertainty for `A` and `Q` but an absolute
            uncertainty in the other elements (when `I`, `O`, and `W` are given in
            radians).

    Returns:
        str: The URL to pass to the MPC's "show_by_properties" tool.
    """

    parts = []
    if 'A' in elements:
        a = elements['A']
        a_min = a * (1. - delta)
        a_max = a * (1. + delta)
        parts.append(f'semimajor_axis_min={a_min:.3f}')
        parts.append(f'semimajor_axis_max={a_max:.3f}')

    if 'Q' in elements:
        q = elements['Q']
        q_min = q * (1. - delta)
        q_max = q * (1. + delta)
        parts.append(f'perihelion_distance_min={q_min:.3f}')
        parts.append(f'perihelion_distance_max={q_max:.3f}')

    if 'I' in elements:
        i = elements['I'] / DPR
        if 'O' in elements:
            o = elements['O'] / DPR
            (i_min, i_max, o_min, o_max) = _polar_extrema(i, o, delta)
            if o_min is not None:
                i_min *= DPR
                i_max *= DPR
                o_min *= DPR
                o_max *= DPR
                o_min = max(o_min, 0.)
                parts.append(f'ascending_node_min={o_min:.3f}')
                parts.append(f'ascending_node_max={o_max:.3f}')
        else:
            i_min = DPR * max(0., i - delta)
            i_max = DPR * (i + delta)

        parts.append(f'inclination_min={i_min:.3f}')
        parts.append(f'inclination_max={i_max:.3f}')

    if 'E' in elements:
        e = elements['E']
        if 'W' in elements and 'O' in elements:
            w = elements['W'] / DPR
            o = elements['O'] / DPR
            (e_min, e_max, peri_min, peri_max) = _polar_extrema(e, w + o, delta)
            if peri_min is not None:
                w_min = (peri_min - o) * DPR
                w_max = (peri_max - o) * DPR
                if w_min > w_max:
                    w_min -= 360.
                w_min = max(w_min, 0.)
                parts.append(f'argument_of_perihelion_min={w_min:.3f}')
                parts.append(f'argument_of_perihelion_max={w_max:.3f}')
        else:
            e_min = DPR * max(0., e - delta)
            e_max = DPR * (e + delta)

        parts.append(f'eccentricity_min={e_min:.3f}')
        parts.append(f'eccentricity_max={e_max:.3f}')

    return _MPC_BY_PROPERTIES + '&'.join(parts)


def _read_mpc_element_table(url):
    """Query the MPC and return the table contents.

    Parameters:
        url (str): The MPC url string.

    Returns:
        dict[str, dict]: A dictionary keyed by MPC body name, returning a dictionary of
        orbital elements "A", "Q", "I", "O", "E", and "W".

    Raises:
        requests.RequestException: If the query fails.
        RuntimeError: If the MPC returns a malformed web page.
    """

    # Retrieve from cache if available; the query string uniquely determines the response,
    # so it is hashed into the cache filename. The "too many objects" and empty responses
    # are cached too, so the delta-tuning retry loop replays identically offline.
    html = b''
    filepath = None
    if _MPC_CACHING:
        query = url.partition('show_by_properties?')[2]
        digest = hashlib.md5(query.encode()).hexdigest()
        filepath = _MPC_CACHE / ('SEARCH-' + digest + '.html')
        if filepath.exists():
            html = filepath.read_bytes()

    if not html:
        request = requests.get(url, allow_redirects=True)
        request.raise_for_status()
        html = request.content
        if _MPC_CACHING and filepath is not None:
            with open(filepath, 'wb') as f:
                f.write(html)

    if html == b'Too many objects to display.':
        raise RuntimeError(f'MPC "show_by_properties" response is "{html.decode()}"')

    match = _OBJECT_COUNT_RE.search(html)
    if not match:
        raise RuntimeError('invalid "show_by_properties" table response from MPC')

    count = int(match.group(1))
    if not count:
        return {}

    table = html.rpartition(b'<table')[-1]
    table = table.partition(b'</table>')[0]
    parts = re.findall(b'<td.*?>(.*?)</td>', table)

    mpc_table = {}
    for k in range(count):
        row = parts[k*12:]
        name = _OBJECT_NAME_RE.match(row[0]).group(2).decode()
        mpc_table[name] = {
            'W': float(row[1]),
            'O': float(row[2]),
            'I': float(row[3]),
            'E': float(row[4]),
            'Q': float(row[5]),
            'A': float(row[6]),
        }

    return mpc_table


def _polar_extrema(radius, longitude, delta):
    """Extremes of radius and longitude given polar coordinates and an uncertainty.

    Parameters:
        radius (float): Polar radius value.
        longitude (float): Longitude in radians.
        delta (float): Uncertainty in `radius` and `longitude`.

    Returns:
        tuple: `(minimum radius, maximum radius, minimum longitude, maximum longitude)`.
        Longitudes are in radians.
    """

    if delta > radius:
        return (0., radius + delta, None, None)

    dlon = math.asin(delta / radius)
    return (radius - delta, radius + delta, longitude - dlon, longitude + dlon)


def element_resid(elements, reference):
    """Compare two dictionaries of orbital elements and return the RMS residual.

    Parameters:
        elements (dict): The dictionary of orbital elements for which a match is sought.
        reference (dict): A dictionary of orbital elements for a known body.

    Returns:
        tuple: `(rms, count)`, where `rms` is the root-mean-square residual and `count`
        is the number of elements compared. If no orbital elements are available, (0., 0)
        is returned.
    """

    errors = []
    if 'A' in elements and 'A' in reference and reference['A']:
        errors.append(elements['A']/reference['A'] - 1.)
    elif 'Q' in elements and 'Q' in reference and reference['Q']:
        errors.append(elements['Q']/reference['Q'] - 1.)

    if 'I' in elements and 'I' in reference:
        i1 = elements['I'] / DPR
        i2 = reference['I'] / DPR
        if 'O' in elements and 'O' in reference:
            o1 = elements['O'] / DPR
            o2 = reference['O'] / DPR
            errors.append(i1 * math.cos(o1) - i2 * math.cos(o2))
            errors.append(i1 * math.sin(o1) - i2 * math.sin(o2))
        else:
            errors.append(i1 - i2)

    if 'E' in elements and 'E' in reference:
        e1 = elements['E']
        e2 = reference['E']
        if 'W' in elements and 'O' in elements and 'W' in reference and 'O' in reference:
            peri1 = (elements['W'] + elements['O']) / DPR
            peri2 = (reference['W'] + reference['O']) / DPR
            errors.append(e1 * math.cos(peri1) - e2 * math.cos(peri2))
            errors.append(e1 * math.sin(peri1) - e2 * math.sin(peri2))
        else:
            errors.append(e1 - e2)

    count = len(errors)
    rms = np.sqrt(np.mean(np.array(errors)**2)) if count else 0.
    return (rms, count)


__all__ = [
    'element_resid',
    'mpc_query_by_elements',
]

##########################################################################################
