##########################################################################################
# targets/target_xml_cache_support.py
##########################################################################################
"""The target context product index is stored in `caches/TARGET_XML_CACHE/$LOOKUP.pickle`.
This pickle file contains a single dictionary keyed by `title`, every `alternate_title`,
and `logical identifier`. Small bodies are also keyed by any of their standard
designations, whether or not they appear in the XML file as an `alternate_title`. Keys
appear in their given case and also in upper case.

The dictionary returns the full path to the target context XML file (latest version), or
to a list of paths if there is more than one.
"""

import pathlib
import pickle
import re

import anyascii
import lxml.etree
import requests
from pdslogger import PdsLogger

from targets.remote_listdir import remote_listdir
from targets.targettype     import TargetType


_TARGET_URL = 'https://pds.nasa.gov/data/pds4/context-pds4/target/'
_TARGET_XML_CACHE = pathlib.Path(__file__).parent.parent / 'caches/TARGET_XML_CACHE'
_TARGET_DICT_BASENAME = '$LOOKUP.pickle'
_TARGET_DICT_PATH = _TARGET_XML_CACHE / _TARGET_DICT_BASENAME
_BASENAME_SPLITTER = re.compile(r'(.*)_(\d\.\d)(|_local)\.xml$')

_TARGET_XML_DICT = None   # filled in lazily


def target_xml_lookup() -> dict:
    """The target lookup dictionary, which returns a file path given a name, alias, or
    lid.
    """

    global _TARGET_XML_DICT

    if _TARGET_XML_DICT is None:
        with open(_TARGET_DICT_PATH, 'rb') as f:
            _TARGET_XML_DICT = pickle.load(f)

    return _TARGET_XML_DICT


def write_target_xml_lookup(lookup: dict):
    """Write the target context lookup dictionary."""

    global _TARGET_XML_DICT

    with open(_TARGET_DICT_PATH, 'wb') as f:
        pickle.dump(lookup, f)

    _TARGET_XML_DICT = lookup


def _update_target_cache(*, logger: PdsLogger | None = None, rebuild: bool = False):
    """Update the target cache.

    Parameters:
        logger: Logger to use.
        rebuild: True to rebuild the index even if no files have changed.
    """

    global _TARGET_XML_DICT

    # Check the local context products
    logger and logger.info(f'Checking local targets: {_TARGET_XML_CACHE}')
    local_basenames = set(p.name for p in _TARGET_XML_CACHE.iterdir())
    local_basenames.remove(_TARGET_DICT_BASENAME)

    # Get the list of remote context products
    logger and logger.info(f'Checking remote targets: {_TARGET_URL}')
    remote_info = remote_listdir(_TARGET_URL, logger=logger, verbose=False)
    remote_basenames = set(t[0] for t in remote_info)

    # Delete deprecated local files
    sorted_basenames = list(local_basenames)
    sorted_basenames.sort()
    for basename in sorted_basenames:
        if basename.endswith('_local.xml'):
            continue
        if basename not in remote_basenames:
            if basename.endswith('.xml'):
                logger and logger.info('Deprecated file removed', basename)
            else:
                logger and logger.info('Extraneous file removed', basename)
            (_TARGET_XML_CACHE / basename).unlink()

    # Replace files updated remotely
    updates = 0
    remote_basenames = _latest_basenames(remote_basenames)
    remote_basenames.sort()
    for basename in remote_basenames:
        if basename in local_basenames:
            continue

        updates += 1

        # Retrieve remote content
        url = _TARGET_URL + basename
        logger and logger.info('Retrieving', basename)
        try:
            request = requests.get(url, allow_redirects=True, timeout=60)
        except requests.RequestException as e:
            logger and logger.error(f'Unable to retrieve {basename}: {e}')
            continue
        if request.status_code != 200:
            logger and logger.error(f'Response {request.status_code} received', basename)
            continue

        # Remove old versions of this target from local cache
        # This will also remove the _local.xml file if the remote copy is the same version
        lid, vid, _ = _BASENAME_SPLITTER.match(basename).groups()
        for old_version in _TARGET_XML_CACHE.glob(lid + '_*.xml'):
            _, old_vid, suffix = _BASENAME_SPLITTER.match(old_version.name).groups()
            if old_vid > vid and suffix:    # if local update is still newer
                continue
            logger and logger.debug('Superseded file removed', old_version)
            old_version.unlink()

        # Save the local version to the cache
        (_TARGET_XML_CACHE / basename).write_bytes(request.content)

    # Summarize local updates
    for basename in sorted_basenames:
        if basename.endswith('_local.xml') and (_TARGET_XML_CACHE / basename).exists():
            logger and logger.info('Local update retained', basename)

    if not updates:
        logger and logger.info('Target cache is up to date')

    if not (updates or rebuild):
        logger and logger.blankline()
        return

    # Re-index...
    logger and logger.info('Rebuilding index', _TARGET_DICT_BASENAME)

    # Determine which local copies still supersede the remote versions
    local_updates = {b for b in local_basenames if b.endswith('_local.xml')}
    local_updates = {b for b in local_updates if (_TARGET_XML_CACHE / b).exists()}
    # ^This filters out the local versions that were just superseded

    local_update_dict = {_BASENAME_SPLITTER.match(b).group(1): b for b in local_updates}

    # lookup_by_name[title, alias, or lid] -> context file basename or list if multiple
    lookup_by_name = {}
    for basename in remote_basenames:
        key, version, suffix = _BASENAME_SPLITTER.match(basename).groups()
        basename = local_update_dict.get(key, basename)  # use "_local" basename if any

        tree = _get_etree(_TARGET_XML_CACHE / basename)
        title = tree.xpath('//title')[0].text
        alts = {node.text for node in tree.xpath('//alternate_title')}
        lid = tree.xpath('//logical_identifier')[0].text
        lid_tail = lid.rpartition(':')[-1]
        keys = _lookup_keys(title, alts, lid_tail)
        for key in keys:
            if key in lookup_by_name:
                other = lookup_by_name[key]
                if isinstance(other, list):
                    other.append(basename)
                    first = other[0]
                else:
                    lookup_by_name[key] = [other, basename]
                    first = other
                logger.debug(f'Duplicated target "{key}": {first}, {basename}')
            else:
                lookup_by_name[key] = basename

    # Save the dictionaries as a pickle file
    write_target_xml_lookup(lookup_by_name)
    logger and logger.info('Index rebuilt', _TARGET_DICT_BASENAME)


def _latest_basenames(basenames: list[str]) -> str:
    """Filter out all but the latest version of each target context file.

    Also remove any "collection_target" files, which can appear in the online directory.
    """

    # Remove "collection_target" files, deprecated files, and anything not ending in .xml
    basenames = [b for b in basenames if b.endswith('.xml')]
    basenames = [b for b in basenames if not b.endswith('_deprecated.xml')]
    basenames = [b for b in basenames if not b.startswith('collection_target')]
    basenames = [b for b in basenames if not b.startswith('Collection_target')]

    # Example basename: dwarf_planet.136108_haumea_1.2.xml
    version_dict = {}
    for basename in basenames:
        lid = _BASENAME_SPLITTER.match(basename).group(1)
        version_dict.setdefault(lid, []).append(basename)

    latest = []
    for lid, version_list in version_dict.items():
        version_list.sort()
        latest.append(version_list[-1])

    return latest


# MPNAME: Matches a name including diacritics, apostrophes and internal dashes; no digits
# or spaces. Note that "[^\W\d_]" only matches letters but they can have diacritics.
# Dashes cannot appear at the beginning or end.
_MPNAME = r"(?:[^\W\d_]|['`]){3,}"  # at least 3 letters

# Comet names can have spaces but no punctuation at end
_CNAME = r"(?:[^\W\d_]|['`])(?:[^\W\d_]|['` -])*(?:[^\W\d_])"

_MP_NUMBER_DESIG = re.compile(r'\((\d+)\) ([12]\d\d\d [A-HJ-Y][A-HJ-Z]\d*)$')
_MP_NUMBER_SURVEY = re.compile(r'\((\d+)\) (\d\d\d\d (?:P-L|T-[123]))$')
_MP_NUMBER_NAME = re.compile(rf'\(?(\d+)\)? ({_MPNAME})$')

_C_PREFIX_NAME_FRAG = re.compile(rf'(\d+[CPDXI])/{_CNAME}(?: \d+|)(-[A-Z][A-Z]?\d*)$')
_C_NAME = re.compile(rf'{_CNAME}(?: \d+|)(-[A-Z][A-Z]?\d*)$')


def _lookup_keys(title: str, alts: list[str], lid_tail: str) -> list[str]:

    category = lid_tail.split('.')[0]

    old_keys = {title} | alts
    new_keys = old_keys.copy()

    if category in {'asteroid', 'centaur', 'comet', 'dwarf_planet',
                    'trans-neptunian_object'}:
        # Split number from name or designation
        for key in old_keys:
            for regex in (_MP_NUMBER_DESIG, _MP_NUMBER_SURVEY, _MP_NUMBER_NAME):
                match = regex.match(key)
                if match:
                    new_keys |= set(match.groups())
                    break

    elif category == 'comet':
        # Append fragment to designation if name intervenes
        for key in old_keys:
            match = _C_PREFIX_NAME_FRAG.match(key)
            if match:
                new_keys.add(match.group(1) + '-' + match.group(2))

    new_keys |= {anyascii.anyascii(key).replace('`', "'") for key in new_keys}
    new_keys |= {key.upper() for key in new_keys}

    return new_keys


_XMLNS = re.compile(r'\s*(?:xmlns|xsi)(?:|:\w+)\s*=\s*"[^"]+"')


def _get_etree(xml_path: str) -> lxml.etree._Element:
    """The content of the given XML file as an etree; header and namespaces stripped."""

    content = pathlib.Path(xml_path).read_text()
    content = content.rpartition('?>')[-1].lstrip()
    content = ''.join(_XMLNS.split(content))
    return lxml.etree.fromstring(content)


def read_target_xml(key: str) -> dict | None:
    """Return a target dictionary containing the core content of a target XML file.

    Parameters:
        key: Any key defining the body, as found in the LOOKUP dictionary.

    Returns:
        A dictionary containing keys "lid", "lid_tail", "version_id", "title",
        "alt_titles", "type_name", "ttype", "description", and "xml_path". None if there
        is no existing XML file for this body.
    """

    try:
        basename = target_xml_lookup()[key.upper()]
    except KeyError:
        return None

    xml_path = _TARGET_XML_CACHE / basename
    tree = _get_etree(xml_path)
    target_dict = {
        'lid': tree.xpath('//logical_identifier')[0].text,
        'version_id': tree.xpath('//version_id')[0].text,
        'title': tree.xpath('//title')[0].text,
        'alt_titles': [node.text for node in tree.xpath('//alternate_title')],
        'type_name': tree.xpath('//type')[-1].text,
        'xml_path': xml_path,
    }

    target_dict['lid_tail'] = target_dict['lid'].rpartition(':')[-1]
    target_dict['ttype'] = TargetType.LOOKUP[target_dict['type_name']]

    desc = tree.xpath('//description')[-1].text
    if not desc or desc == 'none':
        target_dict['description'] = []
    else:
        desc = [line.strip() for line in desc.split('\n')]
        target_dict['description'] = [line for line in desc if line]

    return target_dict


__all__ = ['target_xml_lookup', 'read_target_xml', 'write_target_xml_lookup']

##########################################################################################
