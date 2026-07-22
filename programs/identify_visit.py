#!/usr/bin/env python3
##########################################################################################
# programs/identify_visit.py
##########################################################################################
"""Run `identify_target` on a single visit from the SPT_TESTS corpus and print its log.

The SPT_TESTS corpus (``tests/SPT_TESTS.py``, built by ``build_spt_tests.py``) is keyed by
six-character HST visit; each value is the list of per-file header dictionaries for that
visit. This program looks up one such visit, feeds its headers to
`targets.identify_target`, and writes the resulting log narrative to stdout. It is a
convenience for inspecting, at any verbosity, exactly how the identification code reasons
about a given visit.

Type::

    identify_visit --help

for more information.
"""

import argparse
import pathlib
import sys

import pdslogger

from targets import TargetIdentificationFailure, identify_target

# tests/SPT_TESTS.py is a plain data module (not part of the importable package); add the
# tests directory to the path so it can be imported, exactly as the test suite does.
_TESTS_DIR = pathlib.Path(__file__).resolve().parent.parent / 'tests'


def _load_spt_tests() -> dict[str, list[dict]]:
    """The SPT_TESTS dictionary, keyed by six-character visit."""

    if str(_TESTS_DIR) not in sys.path:
        sys.path.insert(0, str(_TESTS_DIR))
    from SPT_TESTS import SPT_TESTS

    return SPT_TESTS


def identify_visit(visit: str, *, level: str = 'info') -> None:
    """Identify the target(s) of one SPT_TESTS visit, logging the narrative to stdout.

    Parameters:
        visit: The six-character visit key, e.g. "y0zz03".
        level: The minimum level of log messages to print: "debug", "info", or "warning".

    Raises:
        KeyError: If the visit is not present in the SPT_TESTS corpus.
    """

    headers = _load_spt_tests()[visit]

    logger = pdslogger.PdsLogger(
        'pds.identify_visit', lognames=False, indent=True, timestamps=True, digits=3, level=level
    )
    logger.add_handler(pdslogger.NULL_HANDLER)  # suppress the default stdout handler
    logger.add_handler(pdslogger.STDOUT_HANDLER)

    logger.info(f'Identifying visit {visit} ({len(headers)} header(s))')
    try:
        bodies = identify_target(headers, logger=logger)
    except TargetIdentificationFailure as err:
        # The failure has already been logged at ERROR level by identify_target.
        logger.info(f'No target identified: {err}')
        return

    logger.blankline()
    logger.info(
        f'Identified {len(bodies)} target(s): {", ".join(body["full_name"] for body in bodies)}'
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Run identify_target on a single SPT_TESTS visit and write its log '
        'narrative to stdout.'
    )
    parser.add_argument('visit', help='the six-character visit key, e.g. "y0zz03"')
    parser.add_argument(
        '--level',
        '-l',
        choices=('debug', 'info', 'warning'),
        default='info',
        help='minimum level of log messages to show (default: %(default)s)',
    )
    args = parser.parse_args(argv)

    # Validate the visit up front so that a genuine KeyError raised *inside* the
    # identification code is never mistaken for a missing visit.
    if args.visit not in _load_spt_tests():
        parser.error(f'visit {args.visit!r} is not in the SPT_TESTS corpus')

    identify_visit(args.visit, level=args.level)


############################################

if __name__ == '__main__':
    main()

##########################################################################################
