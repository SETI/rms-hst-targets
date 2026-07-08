#!/usr/bin/env python3
##########################################################################################
# target_cache/update_target_xml_cache.py
##########################################################################################
"""
.. update_target_xml_cache:

#######################
update_target_xml_cache
#######################

This is a stand-alone program that can be used to manage a local cache of all the
currently defined target context products. Type::

    update_target_xml_cache --help

for more information.
"""

import argparse
import os
import pathlib
import pickle
import re

import anyascii
import lxml.etree
import pdslogger
import requests

from targets.remote_listdir import remote_listdir

TARGET_URL = 'https://pds.nasa.gov/data/pds4/context-pds4/target/'
TARGET_CACHE = pathlib.Path(os.path.dirname(__file__)).parent / 'caches/TARGET_XML_CACHE'
TARGET_DICT_BASENAME = '$LOOKUP.pickle'

BASENAME_SPLITTER = re.compile(r'(.*)_(\d\.\d)(|_local)\.xml$')

# Set up parser
PARSER = argparse.ArgumentParser(
    description='Update the local cache of all the target context products, which is '
                'found inside the `TARGET_XML_CACHE` subdirectory. It compares the local '
                'cache contents to what is at the Engineering Node and retrieves any new '
                'XML files that are missing from the cache. It also deletes any '
                'superseded or deprecated versions of context products from the local '
                'cache.',
    epilog = 'NOTE: to add or update a context product locally, create a properly named '
             'file but append the suffix "_local" before ".xml". This file will be '
             'preserved in the cache until a file of the same name and version, but no '
             '"_local" suffix, appears at the Engineering Node.')

PARSER.add_argument('--debug', '-d', action='store_true',
                    help='see warnings about duplicated aliases.')

PARSER.add_argument('--rebuild', '-r', action='store_true',
                    help='rebuild the index even if the cache is up to date.')

PARSER.add_argument('--quiet', '-q', action='store_true',
                    help='Do not log to the terminal.')

PARSER.add_argument('--log', '-l', type=str,
                    help='Path to a log file, if any.')


def main():

    args = PARSER.parse_args()

    logger = pdslogger.PdsLogger('pds.update_target_cache',
                                 roots=[TARGET_CACHE], lognames=False, indent=False,
                                 timestamps=True, digits=3,
                                 level='debug' if args.debug else 'info')

    logger.add_handler(pdslogger.NULL_HANDLER)  # suppress automatic logging to stdout
    if not args.quiet:
        logger.add_handler(pdslogger.STDOUT_HANDLER)
    if args.log:
        logger.add_handler(pdslogger.file_handler(args.log, rotation='none'))

    _update_target_cache(logger=logger, rebuild=args.rebuild)


def _update_target_cache(logger=None, rebuild=False):
    """Update the target cache.

    Parameters:
        rebuild (bool, optional): True to rebuild the index even if no files have changed.
        logger (pdslogger.PdsLogger, optional): Logger to use.
    """

    # Check the local context products
    logger and logger.info(f'Checking local targets: {TARGET_CACHE}')
    local_basenames = set(p.name for p in TARGET_CACHE.iterdir()) - {TARGET_DICT_BASENAME}

    # Get the list of remote context products
    logger and logger.info(f'Checking remote targets: {TARGET_URL}')
    remote_info = remote_listdir(TARGET_URL, logger=logger, verbose=False)
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
            (TARGET_CACHE / basename).unlink()

    # Replace files updated remotely
    updates = 0
    remote_basenames = latest_basenames(remote_basenames)
    remote_basenames.sort()
    for basename in remote_basenames:
        if basename in local_basenames:
            continue

        updates += 1

        # Retrieve remote content
        url = TARGET_URL + basename
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
        lid, vid, _ = BASENAME_SPLITTER.match(basename).groups()
        for old_version in TARGET_CACHE.glob(lid + '_*.xml'):
            _, old_vid, suffix = BASENAME_SPLITTER.match(old_version.name).groups()
            if old_vid > vid and suffix:    # if local update is still newer
                continue
            logger and logger.debug('Superseded file removed', old_version)
            old_version.unlink()

        # Save the local version to the cache
        (TARGET_CACHE / basename).write_bytes(request.content)

    # Summarize local updates
    for basename in sorted_basenames:
        if basename.endswith('_local.xml') and (TARGET_CACHE / basename).exists():
            logger and logger.info('Local update retained', basename)

    if not updates:
        logger and logger.info('Target cache is up to date')

    if not (updates or rebuild):
        logger and logger.blankline()
        return

    # Re-index...
    logger and logger.info('Rebuilding index', TARGET_DICT_BASENAME)

    # Determine which local copies still supersede the remote versions
    local_updates = {b for b in local_basenames if b.endswith('_local.xml')}
    local_updates = {b for b in local_updates if (TARGET_CACHE / b).exists()}
    # ^This filters out the local versions that were just superseded

    local_update_dict = {BASENAME_SPLITTER.match(b).group(1):b for b in local_updates}

    # lookup_by_name[title, alias, or lid] -> context file basename or list if multiple
    lookup_by_name = {}
    for basename in remote_basenames:
        key, version, suffix = BASENAME_SPLITTER.match(basename).groups()
        basename = local_update_dict.get(key, basename)  # use "_local" basename if any

        tree = _get_etree(TARGET_CACHE / basename)
        title = tree.xpath('//title')[0].text
        alts = {node.text for node in tree.xpath('//alternate_title')}
        lid = tree.xpath('//logical_identifier')[0].text
        lid_tail = lid_tail = lid.rpartition(':')[-1]
        keys = lookup_keys(title, alts, lid_tail)
        for key in keys:
            if key in lookup_by_name:
                other = lookup_by_name[key]
                if isinstance(other, list):
                    other.append(basename)
                    first = other[0]
                else:
                    lookup_by_name[key] = [other, basename]
                    first = other
                logger.debug(f'Duplicated target "{key}": {other}, {basename}')
            else:
                lookup_by_name[key] = basename

    # Save the dictionaries as a pickle file
    dict_file = TARGET_CACHE / TARGET_DICT_BASENAME
    with dict_file.open('wb') as f:
        pickle.dump(lookup_by_name, f)

    logger and logger.info('Index rebuilt', TARGET_DICT_BASENAME)
    logger and logger.blankline()


def get_index():
    """Read and return the index as two dictionaries, lookups by name and by number."""

    # Save the dictionary as a pickle file
    dict_file = TARGET_CACHE / TARGET_DICT_BASENAME
    with dict_file.open('rb') as f:
        lookup_by_name, lookup_by_number = pickle.load(f)

    return (lookup_by_name, lookup_by_number)


def latest_basenames(basenames):
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
        lid = BASENAME_SPLITTER.match(basename).group(1)
        version_dict.setdefault(lid, []).append(basename)

    latest = []
    for lid, version_list in version_dict.items():
        version_list.sort()
        latest.append(version_list[-1])

    return latest


# MPNAME: Matches a name including diacritics, apostrophes and internal dashes; no digits
# or spaces. Note that "[^\W\d_]" only matches letters but they can have diacritics.
# Dashes cannot appear at the beginning or end.
MPNAME = r"(?:[^\W\d_]|['`]){3,}"  # at least 3 letters

# Comet names can have spaces but no punctuation at end
CNAME = r"(?:[^\W\d_]|['`])(?:[^\W\d_]|['` -])*(?:[^\W\d_])"

MP_NUMBER_DESIG = re.compile(r'\((\d+)\) ([12]\d\d\d [A-HJ-Y][A-HJ-Z]\d*)$')
MP_NUMBER_SURVEY = re.compile(r'\((\d+)\) (\d\d\d\d (?:P-L|T-[123]))$')
MP_NUMBER_NAME = re.compile(rf'\(?(\d+)\)? ({MPNAME})$')

C_PREFIX_NAME_FRAG = re.compile(rf'(\d+[CPDXI])/{CNAME}(?: \d+|)(-[A-Z][A-Z]?\d*)$')
C_NAME = re.compile(rf'{CNAME}(?: \d+|)(-[A-Z][A-Z]?\d*)$')

def lookup_keys(title: str, alts: list[str], lid_tail: str) -> list[str]:

    category = lid_tail.split('.')[0]

    old_keys = {title} | alts
    new_keys = old_keys.copy()

    if category in {'asteroid', 'centaur', 'comet', 'dwarf_planet',
                    'trans-neptunian_object'}:
        # Split number from name or designation
        for key in old_keys:
            for regex in (MP_NUMBER_DESIG, MP_NUMBER_SURVEY, MP_NUMBER_NAME):
                match = regex.match(key)
                if match:
                    new_keys |= set(match.groups())
                    break

    elif category == 'comet':
        # Append fragment to designation if name intervenes
        for key in old_keys:
            match = C_PREFIX_NAME_FRAG.match(key)
            if match:
                new_keys.add(match.group(1) + '-' + match.group(2))

    new_keys |= {anyascii.anyascii(key).replace('`', "'") for key in new_keys}
    new_keys |= {key.upper() for key in new_keys}

    return new_keys


XMLNS = re.compile(r'\s*(?:xmlns|xsi)(?:|:\w+)\s*=\s*"[^"]+"')

def _get_etree(xml_path):
    """The content of the given XML file as an etree; header and namespaces stripped."""

    content = pathlib.Path(xml_path).read_text()
    content = content.rpartition('?>')[-1].lstrip()
    content = ''.join(XMLNS.split(content))
    return lxml.etree.fromstring(content)


############################################

if __name__ == '__main__':
    main()

##########################################################################################
