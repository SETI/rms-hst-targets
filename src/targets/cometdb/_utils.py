##########################################################################################
# cometdb/_utils.py
##########################################################################################

import datetime
import os
import pathlib
import pickle
import re
from collections.abc import Callable
from logging import Logger

import requests
from pdslogger import PdsLogger

try:
    _COMET_CACHE = (pathlib.Path(os.path.dirname(__file__)).parent.parent.parent
                    / 'caches/COMET_CACHE')
except NameError:
    _COMET_CACHE = pathlib.Path('./COMET_CACHE')

_COMET_BASENAME = '#COMETS.pickle'
_CENTAUR_BASENAME = '#CENTAURS.pickle'
_DAMOCLOID_BASENAME = '#DAMOCLOIDS.pickle'

# Used to report a pickle file that had to be regenerated, when the caller has provided no
# Logger of its own.
_LOGNAME = 'pds.cometdb'


def _fetch(
    url: str,
    logger: Logger | None = None,
    *,
    headers: dict | None = None,
    params: dict | None = None,
    timeout: int = 30,
) -> requests.Response | None:
    """Retrieve a URL, returning the Response, or None if the request failed.

    On any network error (timeout, connection failure, or HTTP error status), a warning
    is logged and None is returned. This signals the caller to fall back to the locally
    cached copy, so that a single unreachable source does not abort the entire update.

    Parameters:
        url: The URL to retrieve.
        logger: Optional Logger to use.
        headers: Optional request headers.
        params: Optional query parameters.
        timeout: Timeout in seconds for the request.

    Returns:
        The successful `requests.Response`, or None if the request failed.
    """

    try:
        logger and logger.info('Retrieving URL ' + url)
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger and logger.error(f'Unable to retrieve {url}: {e}')
        logger and logger.warn(f'Falling back to cached copy for {url}')
        return None


def _read_content(
    basename: str,
    logger: Logger | None = None
) -> str:
    """Get the locally cached content.

    Parameters:
        basename: Name of the file in the local cache directory.
        logger: Optional Logger to use.

    Returns:
        Content of the file.
    """

    logger and logger.info(f'Reading COMET_CACHE/{basename}')
    cache_path = _COMET_CACHE / basename
    content = cache_path.read_text()
    return content


def _compare_content(
    content: bytes | str | list[str],
    basename: str,
    logger: Logger | None = None
) -> bool:
    """Compare the remote file to the local file.

    Parameters:
        content: Content retrieved from remote site.
        basename: Name of the file in the local cache directory.
        logger: Optional Logger to use.

    Returns:
        True if the content online has changed.
    """

    # Convert content to string if necessary
    if isinstance(content, bytes):
        content = content.decode()
    if not isinstance(content, str):
        content = '\n'.join(content + [''])

    # Read locally cached content
    cache_path = _COMET_CACHE / basename
    found = False
    try:
        old_content = cache_path.read_text()
        found = True
    except FileNotFoundError:
        logger and logger.warn(f'Unable to read COMET_CACHE/{basename}')
        old_content = ''
    else:
        logger and logger.info(f'File COMET_CACHE/{basename} read')

    # Rename existing content if necessary
    changed = content != old_content
    if changed and found:
        logger and logger.info(f'{basename} content has been updated online')
        timestamp = cache_path.stat().st_ctime
        date = datetime.datetime.fromtimestamp(timestamp).isoformat()
        parts = basename.partition('.')
        saved_basename = parts[0] + '-' + date[:10] + '.' + parts[-1]
        cache_path.rename(_COMET_CACHE / saved_basename)
        logger and logger.info(f'COMET_CACHE/{basename} copied to {saved_basename}')

    # Save new content if necessary
    if changed:
        try:
            cache_path.write_text(content)
        except OSError as e:
            logger and logger.warn(f'Unable to write COMET_CACHE/{basename}: {e}')
        else:
            verb = 'rewritten' if found else 'written'
            logger and logger.info(f'COMET_CACHE/{basename} {verb}')
    else:
        logger and logger.info(f'COMET_CACHE/{basename} is unchanged')

    return changed


def _read_pickle(
    basename: str,
    logger: Logger | None = None
) -> tuple[dict[str, dict], dict[str, dict], dict[str, list[dict]]] | None:
    """Read the dictionaries from the pickle file."""

    cometdb_path = _COMET_CACHE / basename
    if not cometdb_path.exists():
        logger and logger.info(f'COMET_CACHE/{basename} not found')
        return None

    logger and logger.info(f'COMET_CACHE/{basename} read')
    with cometdb_path.open('rb') as f:
        comets, lookup, ambiguous = pickle.load(f)

    return comets, lookup, ambiguous


def _write_pickle(
    basename: str,
    dicts: dict[str, dict],
    logger: Logger | None = None
) -> None:
    """Write new pickle file, backing up an existing file."""

    cometdb_path = _COMET_CACHE / basename

    # Back up existing file
    if cometdb_path.exists():

        # Get the version number for the existing comet DB file
        parts = basename.rpartition('.')
        versions = list(_COMET_CACHE.glob(parts[0] + '_v*.' + parts[-1]))
        regex = re.compile(r'.*/' + parts[0] + r'_v(\d+)\.' + parts[-1])
        pairs = [(int(regex.fullmatch(str(v)).group(1)), v) for v in versions]
        if pairs:
            pairs.sort()
            number = pairs[-1][0] + 1
        else:
            number = 1

        # Rename the file
        numbered_basename = parts[0] + f'_v{number:03d}.' + parts[-1]
        cometdb_path.rename(_COMET_CACHE / numbered_basename)
        logger and logger.info(f'COMET_CACHE/{basename} renamed to {numbered_basename}')

    with cometdb_path.open('wb') as f:
        pickle.dump(dicts, f)

    logger and logger.info(f'COMET_CACHE/{basename} written')


def _dicts_from_pickle(
    basename: str,
    builder: Callable[..., tuple[dict[str, dict], dict[str, dict], dict[str, list[dict]]]],
) -> tuple[dict[str, dict], dict[str, dict], dict[str, list[dict]]]:
    """Read the dictionaries from the pickle file, regenerating it first if it is missing.

    The pickle files are build products rather than versioned content, so a fresh checkout
    contains none of them. Each one is rebuilt from the locally cached web resources, just
    as `update_cometdb --local` would do, without querying any website. Exactly one
    info-level message is logged for each file that has to be generated; the read, write,
    and build steps are otherwise silent.

    Parameters:
        basename: Name of the pickle file in the local cache directory.
        builder: The `_build_*_dicts` function that regenerates the content.

    Returns:
        (`dicts`, `by_lookup`, `by_ambiguous`), the three dictionaries from `builder`.
    """

    dicts = _read_pickle(basename)
    if dicts is None:
        dicts = builder(update=False)
        _write_pickle(basename, dicts)
        PdsLogger.get_logger(_LOGNAME).info(
            f'COMET_CACHE/{basename} generated from the local cache')

    return dicts


_COMET_DICTS = None
_CENTAUR_DICTS = None
_DAMOCLOID_DICTS = None


def _comet_dicts():
    """Comet dict by primary key, dict by any key; list of dicts by ambiguous key."""
    global _COMET_DICTS
    if not _COMET_DICTS:
        from ._build_comet_dicts import _build_comet_dicts  # here; it imports this module
        _COMET_DICTS = _dicts_from_pickle(_COMET_BASENAME, _build_comet_dicts)
    return _COMET_DICTS


def comet_dict():
    """Comet dictionary based on primary key."""
    return _comet_dicts()[0]


def comet_lookup():
    """Comet dictionary based on any key including upper case."""
    return _comet_dicts()[1]


def comet_ambiguous_lookup():
    """List of comet dictionaries based on any ambiguous key including upper case."""
    return _comet_dicts()[1]


def _centaur_dicts():
    """Centaur dict by primary key, dict by any key; list of dicts by ambiguous key."""
    global _CENTAUR_DICTS
    if not _CENTAUR_DICTS:
        from ._build_centaur_dicts import _build_centaur_dicts  # imports this module
        _CENTAUR_DICTS = _dicts_from_pickle(_CENTAUR_BASENAME, _build_centaur_dicts)
    return _CENTAUR_DICTS


def centaur_dict():
    """Centaur dictionary based on primary key."""
    return _centaur_dicts()[0]


def centaur_lookup():
    """Centaur dictionary based on any key including upper case."""
    return _centaur_dicts()[1]


def _damocloid_dicts():
    """Damocloid dict by primary key, dict by any key; list of dicts by ambiguous key."""
    global _DAMOCLOID_DICTS
    if not _DAMOCLOID_DICTS:
        from ._build_damocloid_dicts import _build_damocloid_dicts  # imports this module
        _DAMOCLOID_DICTS = _dicts_from_pickle(_DAMOCLOID_BASENAME, _build_damocloid_dicts)
    return _DAMOCLOID_DICTS


def damocloid_dict():
    """Damocloid dictionary based on primary key."""
    return _damocloid_dicts()[0]


def damocloid_lookup():
    """Damocloid dictionary based on any key including upper case."""
    return _damocloid_dicts()[1]


__all__ = [
    '_CENTAUR_BASENAME',
    '_COMET_BASENAME',
    '_COMET_CACHE',
    '_compare_content',
    '_dicts_from_pickle',
    '_fetch',
    '_read_content',
    '_read_pickle',
    '_write_pickle',
    'centaur_dict',
    'centaur_lookup',
    'comet_ambiguous_lookup',
    'comet_dict',
    'comet_lookup',
    'damocloid_dict',
    'damocloid_lookup',
]

##########################################################################################
