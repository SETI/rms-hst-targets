#!/usr/bin/env python3
##########################################################################################
# support/update_target_xml_cache.py
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

A lookup table is stored in `caches/TARGET_XML_CACHE/$LOOKUP.pickle`. This pickle file
contains a single dictionary keyed by `title`, every `alternate_title`, and `logical
identifier`. Small bodies are also keyed by any of their standard designations, whether or
not they appear in the XML file as an `alternate_title`. Keys appear in their given case
and also in upper case.

The dictionary returns the full path to the target context XML file (latest version), or
to a list of paths if there is more than one.
"""

import argparse

import pdslogger

from targets.target_xml_support import _update_target_cache, _TARGET_XML_CACHE

# Set up parser
PARSER = argparse.ArgumentParser(
    description='Update the local cache of all the target context products, which is '
                'found inside the `TARGET_XML_CACHE` subdirectory. It compares the local '
                'cache contents to what is at the Engineering Node and retrieves any new '
                'XML files that are missing from the cache. It also deletes any '
                'superseded or deprecated versions of context products from the local '
                'cache.',
    epilog='NOTE: to add or update a context product locally, create a properly named '
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
                                 roots=[_TARGET_XML_CACHE], lognames=False, indent=False,
                                 timestamps=True, digits=3,
                                 level='debug' if args.debug else 'info')

    logger.add_handler(pdslogger.NULL_HANDLER)  # suppress automatic logging to stdout
    if not args.quiet:
        logger.add_handler(pdslogger.STDOUT_HANDLER)
    if args.log:
        logger.add_handler(pdslogger.file_handler(args.log, rotation='none'))

    _update_target_cache(logger=logger, rebuild=args.rebuild)


if __name__ == '__main__':
    main()

##########################################################################################
