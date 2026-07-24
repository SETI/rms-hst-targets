#!/usr/bin/env python3
##########################################################################################
# programs/identify_visit.py
##########################################################################################
"""Identify the targets of one or more SPT_TESTS visits, print the context-product paths,
and optionally open them in $EDITOR.

The SPT_TESTS corpus (``tests/SPT_TESTS.py``, built by ``build_spt_tests.py``) is keyed by
six-character HST visit. This program resolves each visit argument -- the wildcards ``*``,
``?`` and ``[...]`` are expanded against the corpus -- feeds each visit's headers to
`targets.identify_targets`, writes the identification narrative to stdout, and finally
prints the full path of every XML context product identified. Any newly generated "_local"
products are written to the gitignored overlay directory (``caches/TARGET_XML_OVERLAY``),
never the committed ``TARGET_XML_CACHE``.

Type::

    identify_visit --help

for more information.
"""

import argparse
import fnmatch
import os
import pathlib
import shlex
import subprocess
import sys

import pdslogger

from targets import TargetIdentificationFailure, identify_targets
from targets.target_xml_cache_support import use_local_xml_dir

# tests/SPT_TESTS.py is a plain data module (not part of the importable package); add the
# tests directory to the path so it can be imported, exactly as the test suite does.
_TESTS_DIR = pathlib.Path(__file__).resolve().parent.parent / 'tests'


def _load_spt_tests() -> dict[str, list[dict]]:
    """The SPT_TESTS dictionary, keyed by six-character visit."""

    if str(_TESTS_DIR) not in sys.path:
        sys.path.insert(0, str(_TESTS_DIR))
    from SPT_TESTS import SPT_TESTS

    return SPT_TESTS


def _resolve_visits(patterns: list[str]) -> tuple[list[str], list[str]]:
    """Expand visit patterns against the corpus keys.

    Each pattern is matched against every visit with `fnmatch` (so a literal visit matches
    only itself, while `*`, `?` and `[...]` expand). Order follows the patterns, then the
    corpus, and duplicates are dropped.

    Parameters:
        patterns: The visit arguments, possibly containing wildcards.

    Returns:
        A tuple (resolved visits, patterns that matched nothing).
    """

    keys = list(_load_spt_tests())
    resolved: list[str] = []
    seen: set[str] = set()
    unmatched: list[str] = []
    for pattern in patterns:
        matches = [key for key in keys if fnmatch.fnmatchcase(key, pattern)]
        if not matches:
            unmatched.append(pattern)
        for key in matches:
            if key not in seen:
                seen.add(key)
                resolved.append(key)

    return resolved, unmatched


def _make_logger(level: str) -> pdslogger.PdsLogger:
    """A PdsLogger that writes the narrative to stdout at the given level."""

    logger = pdslogger.PdsLogger(
        'pds.identify_visit', lognames=False, indent=True, timestamps=True, digits=3,
        level=level, blanklines=False
    )
    logger.add_handler(pdslogger.NULL_HANDLER)  # suppress the default stdout handler
    logger.add_handler(pdslogger.STDOUT_HANDLER)
    return logger


def identify_visit(visit: str,  logger: pdslogger.PdsLogger,
                   by_visit: bool = False) -> list[pathlib.Path]:
    """Identify the targets of one SPT_TESTS visit and return their context-product paths.

    The identification narrative is logged. Returns an empty list if no target can be
    identified for the visit.

    Parameters:
        visit: The six-character visit key.
        by_visit: True to print the XML file list after each visit.
        logger: The logger receiving the narrative.
    """

    headers = _load_spt_tests()[visit]
    logger.blankline()
    try:
        paths = identify_targets(headers, logger=logger)
    except TargetIdentificationFailure as err:
        print('**** TargetIdentificationFailure')
        return []

    if by_visit:
        for path in paths:
            print(f'  {path}')
        return []

    return paths


def _open_in_editor(paths: list[pathlib.Path]) -> None:
    """Open the given files in the editor named by $EDITOR."""

    editor = os.environ['EDITOR']
    try:
        subprocess.run(shlex.split(editor) + [str(p) for p in paths])
    except OSError as err:
        print(f'Could not launch $EDITOR ({editor!r}): {err}', file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Run identify_targets on one or more SPT_TESTS visits, print the '
        'paths of the XML context products identified, and optionally open them in '
        '$EDITOR. New "_local" products are written to the overlay directory, '
        'never the committed TARGET_XML_CACHE.'
    )
    parser.add_argument(
        'visits',
        nargs='+',
        metavar='VISIT',
        help='one or more six-character visit keys; the wildcards *, ? and '
        '[...] are expanded against the corpus',
    )
    parser.add_argument(
        '--level',
        '-l',
        choices=('debug', 'info', 'warning'),
        default='debug',
        help='minimum level of log messages to show (default: %(default)s)',
    )
    parser.add_argument(
        '--edit', action='store_true', help='open the identified XML files in $EDITOR'
    )
    parser.add_argument(
        '--by-visit', action='store_true',
        help='print out XML file paths visit by visit.'
    )
    args = parser.parse_args(argv)

    if args.edit and not os.environ.get('EDITOR'):
        parser.error('--edit requires the $EDITOR environment variable to be set')

    visits = [v.lower() for v in args.visits]
    visits, unmatched = _resolve_visits(visits)
    for pattern in unmatched:
        print(f'Warning: no visit in the SPT_TESTS corpus matches {pattern!r}',
              file=sys.stderr)
    if not visits:
        parser.error(f'no visits in the SPT_TESTS corpus match {args.visits}')

    logger = _make_logger(args.level)

    # New "_local" products go to the overlay (caches/TARGET_XML_OVERLAY), never the
    # committed TARGET_XML_CACHE.
    paths: list[pathlib.Path] = []
    seen: set[pathlib.Path] = set()
    with use_local_xml_dir():
        for visit in visits:
            for path in identify_visit(visit, logger, args.by_visit):
                if path not in seen:
                    seen.add(path)
                    paths.append(path)

    if not args.by_visit:
        print(f'Identified {len(paths)} XML file(s):')
        for path in paths:
            print(f'  {path}')

    if args.edit and paths:
        if len(paths) <= 10:
            _open_in_editor(paths)
        else:
            print(f'Editing option suspended for {len(paths)} files')


############################################

if __name__ == '__main__':
    main()

##########################################################################################
