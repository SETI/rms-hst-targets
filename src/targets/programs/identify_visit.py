#!/usr/bin/env python3
##########################################################################################
# targets/programs/identify_visit.py
##########################################################################################
"""Identify the targets of one or more HST visits or FITS files, print the context-product
paths, and optionally open them in $EDITOR.

Each argument is either a visit or a path. A visit is a six-character HST visit key from
the SPT_TESTS corpus (``tests/SPT_TESTS.py``, built by ``build_spt_tests.py``), and the
wildcards ``*``, ``?`` and ``[...]`` are expanded against it. A path names an SPT/SHM/SHF/
DMF support file, or a directory, which contributes every such file at or below it. The
two kinds can be mixed in one run, and the corpus is only consulted when a visit argument
is given, so a pure-path run needs no source checkout.

Headers are grouped by visit -- the first six characters of the file's base name -- and
each visit is fed to `targets.identify_targets` separately, so a failure in one visit does
not abandon the rest. The identification narrative is written to stdout, followed by the
full path of every XML context product identified. Any newly generated "_local" products
are written to the gitignored overlay directory (``caches/TARGET_XML_OVERLAY``), never the
committed ``TARGET_XML_CACHE``.

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
from astropy.io import fits

from targets import TargetIdentificationFailure, identify_targets
from targets._utils import _headers_by_visit
from targets.programs.build_spt_tests import _extract
from targets.target_xml_cache_support import use_local_xml_dir

# tests/SPT_TESTS.py is a plain data module (not part of the importable package); add the
# tests directory to the path so it can be imported, exactly as the test suite does.
_TESTS_DIR = pathlib.Path(__file__).resolve().parents[3] / 'tests'

# The support-file types retrieved by retrieve_mast_moving_target_spts.py; "_dmf.fits" is
# the FGS analog of "_spt.fits".
_FITS_SUFFIXES = ('_spt.fits', '_shm.fits', '_shf.fits', '_dmf.fits')


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


def _fits_paths(path: pathlib.Path) -> list[pathlib.Path]:
    """Every SPT/SHM/SHF/DMF FITS file named by one path argument.

    An explicitly named file is returned as itself whatever it is called, so an oddly named
    file can always be forced. A directory contributes every matching file at or below it,
    sorted by name; the search is recursive so that it covers both a flat directory and the
    per-proposal subdirectories of ``caches/SPT_CACHE``.

    Parameters:
        path: An existing file or directory.
    """

    if path.is_file():
        return [path]

    return sorted(p for p in path.rglob('*.fits')
                  if p.is_file() and p.name.lower().endswith(_FITS_SUFFIXES))


def _read_fits_headers(paths: list[pathlib.Path]) -> list[dict]:
    """Read the target-description keywords of each FITS file into a header dictionary.

    Each dictionary has the same shape as an SPT_TESTS entry -- "FILENAME" (the base name,
    from which the visit is taken) followed by the target-description keywords extracted by
    `build_spt_tests._extract` -- so a file and a corpus entry are indistinguishable to
    `targets.identify_targets`. Unreadable files are reported on stderr and skipped, so one
    bad file does not abandon a whole directory.

    Parameters:
        paths: The FITS files to read.
    """

    headers: list[dict] = []
    for path in paths:
        try:
            header = fits.getheader(path, 0)
        except Exception as err:        # report and continue with the next file
            print(f'Warning: skipped unreadable {path}: {err}', file=sys.stderr)
            continue

        headers.append({'FILENAME': path.name} | dict(_extract(header)))

    return headers


def _split_inputs(inputs: list[str]) -> tuple[list[pathlib.Path], list[str]]:
    """Separate the positional arguments into paths and visit patterns.

    An argument is a path if it exists, or if it merely looks like one -- it contains a
    path separator or names a ".fits" file -- so that a mistyped path is reported as a
    missing file rather than as a visit that matched nothing.

    Parameters:
        inputs: The raw positional arguments.

    Returns:
        A tuple (paths, lowercased visit patterns).
    """

    paths: list[pathlib.Path] = []
    visits: list[str] = []
    for arg in inputs:
        if pathlib.Path(arg).exists() or os.sep in arg or arg.lower().endswith('.fits'):
            paths.append(pathlib.Path(arg))
        else:
            visits.append(arg.lower())

    return paths, visits


def _make_logger(level: str) -> pdslogger.PdsLogger:
    """A PdsLogger that writes the narrative to stdout at the given level."""

    logger = pdslogger.PdsLogger(
        'pds.identify_visit', lognames=False, indent=True, timestamps=True, digits=3,
        level=level, blanklines=False
    )
    logger.add_handler(pdslogger.NULL_HANDLER)  # suppress the default stdout handler
    logger.add_handler(pdslogger.STDOUT_HANDLER)
    return logger


def _identify(headers: list[dict], visit: str, logger: pdslogger.PdsLogger,
              by_visit: bool) -> list[pathlib.Path]:
    """Identify the targets of one visit's headers and return their context-product paths.

    The identification narrative is logged. Returns an empty list if no target can be
    identified, so that one unidentifiable visit does not abandon the others.

    Parameters:
        headers: The headers of a single visit.
        visit: The visit key, used to attribute a failure.
        logger: The logger receiving the narrative.
        by_visit: True to print the XML file list here instead of returning it.
    """

    logger.blankline()
    try:
        paths = identify_targets(headers, logger=logger)
    except TargetIdentificationFailure as err:
        # The message says which strings and elements were rejected and why, which is the
        # only useful part; the traceback is always the same and is not printed.
        print(f'**** {visit}: TargetIdentificationFailure: {err}')
        return []

    if by_visit:
        for path in paths:
            print(f'  {path}')
        return []

    return paths


def identify_visit(visit: str,  logger: pdslogger.PdsLogger,
                   by_visit: bool = False) -> list[pathlib.Path]:
    """Identify the targets of one SPT_TESTS visit and return their context-product paths.

    Parameters:
        visit: The six-character visit key.
        logger: The logger receiving the narrative.
        by_visit: True to print the XML file list after each visit.
    """

    return _identify(_load_spt_tests()[visit], visit.upper(), logger, by_visit)


def identify_files(paths: list[pathlib.Path], logger: pdslogger.PdsLogger,
                   by_visit: bool = False) -> list[pathlib.Path]:
    """Identify the targets of FITS files and return their context-product paths.

    The files may span any number of visits. Their headers are grouped by visit and each
    visit is identified separately, exactly as a corpus visit would be, so a failure in one
    does not abandon the rest.

    Parameters:
        paths: The FITS files to read, already expanded from any directory arguments.
        logger: The logger receiving the narrative.
        by_visit: True to print the XML file list after each visit.
    """

    results: list[pathlib.Path] = []
    for headers in _headers_by_visit(_read_fits_headers(paths)):
        visit = headers[0]['FILENAME'][:6].upper()
        results += _identify(headers, visit, logger, by_visit)

    return results


def _open_in_editor(paths: list[pathlib.Path]) -> None:
    """Open the given files in the editor named by $EDITOR."""

    editor = os.environ['EDITOR']
    try:
        subprocess.run(shlex.split(editor) + [str(p) for p in paths])
    except OSError as err:
        print(f'Could not launch $EDITOR ({editor!r}): {err}', file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Run identify_targets on one or more SPT_TESTS visits and/or FITS '
        'files, print the paths of the XML context products identified, and optionally '
        'open them in $EDITOR. New "_local" products are written to the overlay '
        'directory, never the committed TARGET_XML_CACHE.'
    )
    parser.add_argument(
        'inputs',
        nargs='+',
        metavar='VISIT_OR_PATH',
        help='six-character visit keys, in which the wildcards *, ? and [...] are '
        'expanded against the SPT_TESTS corpus, and/or paths to SPT/SHM/SHF/DMF FITS '
        'files or to directories holding them; the two kinds can be mixed',
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

    path_args, patterns = _split_inputs(args.inputs)

    fits_paths: list[pathlib.Path] = []
    for path in path_args:
        if not path.exists():
            print(f'Warning: no such file or directory: {path}', file=sys.stderr)
            continue
        matches = _fits_paths(path)
        if not matches:
            print(f'Warning: no SPT/SHM/SHF/DMF FITS files in {path}', file=sys.stderr)
        fits_paths += matches

    # Only consult the corpus when a visit was actually named, so that a run over FITS
    # files alone does not require tests/SPT_TESTS.py to be present.
    visits: list[str] = []
    if patterns:
        visits, unmatched = _resolve_visits(patterns)
        for pattern in unmatched:
            print(f'Warning: no visit in the SPT_TESTS corpus matches {pattern!r}',
                  file=sys.stderr)

    if not visits and not fits_paths:
        parser.error(f'nothing to identify among {args.inputs}')

    logger = _make_logger(args.level)

    # New "_local" products go to the overlay (caches/TARGET_XML_OVERLAY), never the
    # committed TARGET_XML_CACHE.
    results: list[pathlib.Path] = []
    with use_local_xml_dir():
        for visit in visits:
            results += identify_visit(visit, logger, args.by_visit)
        if fits_paths:
            results += identify_files(fits_paths, logger, args.by_visit)

    paths: list[pathlib.Path] = []
    seen: set[pathlib.Path] = set()
    for path in results:
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
