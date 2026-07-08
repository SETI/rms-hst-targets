#!/usr/bin/env python3
##########################################################################################
# support/update_cometdb.py
##########################################################################################
"""
.. update_cometdb:

###############
update_cometdb
###############

This is a stand-alone program that can be used to manage a local cache of comets based on
three different web resources. Type::

    update_cometdb --help

for more information.
"""

import argparse

import pdslogger

from targets.cometdb._build_centaur_dicts import _build_centaur_dicts
from targets.cometdb._build_comet_dicts import _build_comet_dicts
from targets.cometdb._utils import _read_pickle, _write_pickle
from targets.cometdb._utils import _COMET_CACHE, _COMET_BASENAME, _CENTAUR_BASENAME


# Set up parser
PARSER = argparse.ArgumentParser(
    description='Update the databases of comet and centaur information, which are found '
                'inside the `COMET_CACHE` subdirectory.')

PARSER.add_argument('--debug', '-d', action='store_true',
                    help='see additional messages in the log.')

PARSER.add_argument('--rebuild', '-r', action='store_true',
                    help='rebuild the database even if the cached files are up to date.')

PARSER.add_argument('--local', action='store_true',
                    help='rebuild the database from the local cache without first '
                         'checking the websites for new content.')

PARSER.add_argument('--comets', action='store_true',
                    help='only update the comets database.')

PARSER.add_argument('--centaurs', action='store_true',
                    help='only update the centaurs database.')

PARSER.add_argument('--quiet', '-q', action='store_true',
                    help='Do not log to the terminal.')

PARSER.add_argument('--log', '-l', type=str,
                    help='Path to a log file, if any.')


def main():

    def db_updater(basename, dict_builder_func):

        # Read the current database if any
        old_dicts = _read_pickle(basename, logger=logger)

        # Generate the new content
        new_dicts = dict_builder_func(update=not args.local, logger=logger)

        # If nothing has changed, don't save
        unchanged = old_dicts is not None and old_dicts[0] == new_dicts[0]
        if unchanged and not args.rebuild:
            logger.info(f'Database COMET_CACHE/{basename} is unchanged')
            return

        # Save the new database file; backup if necessary
        _write_pickle(basename, new_dicts, logger=logger)


    args = PARSER.parse_args()

    # Set up logger
    logger = pdslogger.PdsLogger('pds.update_cometdb',
                                 roots=[_COMET_CACHE], lognames=False, indent=False,
                                 timestamps=True, digits=3,
                                 level='debug' if args.debug else 'info')

    logger.add_handler(pdslogger.NULL_HANDLER)  # suppress automatic logging to stdout
    if not args.quiet:
        logger.add_handler(pdslogger.STDOUT_HANDLER)
    if args.log:
        logger.add_handler(pdslogger.file_handler(args.log, rotation='none'))

    # Update the comet database if necessary
    if args.comets or not args.centaurs:
        db_updater(_COMET_BASENAME, _build_comet_dicts)

    # Update the centaur database if necessary
    if args.centaurs or not args.comets:
        db_updater(_CENTAUR_BASENAME, _build_centaur_dicts)

############################################

if __name__ == '__main__':
    main()

##########################################################################################
