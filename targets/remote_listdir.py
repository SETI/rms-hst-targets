##########################################################################################
# target_cache/remote_listdir.py
##########################################################################################

import datetime
import numbers
import re

import requests

_HTML_TAG = re.compile(r'<.*?>')
_END_OF_TABLE = re.compile('.*(</pre>|<hr>|</table|<th colspan).*')
_SIZE_FACTORS = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}


def remote_listdir(url, *, depth=0, tz_delta=0, verbose=False, timeout=60, logger=None):
    """The content of a fancy index as a list of tuples (subpath, datetime, bytes).

    If the URL does not point to a fancy index, this function returns an empty list.

    Parameters:
        url (str): The URL of an online fancy index.
        depth (int, optional): The maximum number of subdirectories to read, recursively.
        tz_delta (int, float, or datetime.timedelta, optional):
            Optional time shift to add to the remote file date/time to obtain the
            local date/time; can be used if the remote server is in a different time
            zone. Provide either a timedelta object or a number in units of hours.
        verbose (bool, optional): True to print to stdout the URL of each remote
            subdirectory as it is read.
        timeout (int or float, optional): Timeout in seconds for each HTTP request, so a
            stalled server raises an error instead of hanging indefinitely.
        logger (logging.Logger or pdslogger.PdsLogger, optional): Logger to which to
            write messages.

    Returns:
        list(tuple(str, str, str)): A list of tuples (subpath, datetime, bytes). Note that
            the number of bytes is rounded to the nearest kilo-, mega-, or gigabytes.

    Raises:
        ConnectionError: If the URL could not be accessed.
    """

    if isinstance(tz_delta, numbers.Real):
        seconds = int(tz_delta * 3600)
        tz_delta = datetime.timedelta(seconds=seconds)

    if verbose:
        if logger:
            logger.info('Reading ' + url)
        else:
            print('Reading ' + url)

    request = requests.get(url, allow_redirects=True, timeout=timeout)
    if request.status_code != 200:
        message = f'response {request.status_code} received from {url}'
        logger and logger.error(f'Connection error: {message}')
        raise ConnectionError(message)

    text = request.content.decode('latin1')

    # The first line of the fancy index always contains "Parent Directory".
    parts = text.partition('Parent Directory')
    if not parts[-1]:
        logger and logger.error(f'Not a recognized fancy index: {url}')
        raise ValueError(f'Not a recognized fancy index: {url}')

    # Rows are always split by "\n".
    # Sometimes it's a table, sometimes just pre-formatted text
    recs = parts[-1].split('\n')

    # The record after the last table row always contains one of these:
    # "</pre>", "<hr>", "<table", or "<th colspan"
    last = [k for k, rec in enumerate(recs) if _END_OF_TABLE.fullmatch(rec)]

    # Select the table rows
    recs = recs[1:last[0]]

    # Interpret each row
    row_tuples = []
    for rec in recs:

        rec = rec.replace('&nbsp;', '').strip()

        # Remove anything inside quotes
        parts = rec.split('"')
        rec = ''.join(parts[::2])

        # Insert a space before "<td"
        rec = rec.replace('<td', ' <td')

        # Remove anything inside HTML tags
        parts = _HTML_TAG.split(rec)
        rec = ''.join(parts)

        # Interpret the fields
        parts = rec.split()
        basename = parts[0]
        date_str = parts[1] + 'T' + parts[2]
        date = datetime.datetime.fromisoformat(date_str) + tz_delta
        size = _int_size(parts[3])
        row_tuples.append((basename, date, size))

    # Continue recursively
    if depth > 0:
        more_tuples = []
        url = url.rstrip('/')
        for basename, _, _ in row_tuples:
            if basename.endswith('/'):
                subdir = remote_listdir(url + '/' + basename, depth=depth-1,
                                        tz_delta=tz_delta, verbose=verbose,
                                        timeout=timeout, logger=logger)
                more_tuples += [(basename + t[0], t[1], t[2]) for t in subdir]

        row_tuples += more_tuples

    return row_tuples


def _int_size(size):
    """Internal method to convert a size string to a size in bytes."""

    if size == '-':
        return 0

    if size[-1] in _SIZE_FACTORS:
        return int(float(size[:-1]) * _SIZE_FACTORS[size[-1]] + 0.5)

    return int(size)

##########################################################################################
