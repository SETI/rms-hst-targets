#!/usr/bin/env python3
##########################################################################################
# programs/build_spt_tests.py
##########################################################################################
"""Build a Python module of unique HST target descriptions from the SPT cache, organized
by visit.

This reads every FITS file in ``caches/SPT_CACHE`` (the ``_spt.fits``/``_shm.fits``/
``_shf.fits``/``_dmf.fits`` support files retrieved by
``retrieve_mast_moving_target_spts.py``; ``_dmf.fits`` is the FGS analog) and extracts
the key target-description keywords from each primary header:

    PSTRTIME, PSTPTIME, TARG_ID, TAR_TYPE, TARGTYPE, TARDESC*, TARGCAT, TARKEY*,
    MT_LV*, TARGNAME, RA_TARG, DEC_TARG, PROPOSID

Because `identify_target_dicts` now works one HST visit at a time, the output is organized by
visit rather than as a flat list. A visit is the first six characters of the rootname
(the file's base name), which encodes the program and visit and is unique across HST. The
output module defines a single dictionary ``SPT_TESTS`` mapping each visit string to a
list of per-file header dictionaries::

    SPT_TESTS = {
        "y0zz03": [
            {"FILENAME": "y0zz0301t_shf.fits", "PSTRTIME": ..., ...},
            ...
        ],
        ...
    }

Each header dictionary begins with FILENAME (the base name, which `identify_target_dicts` uses
to group headers by visit) and then the keywords above, in the order listed, omitting any
keyword absent from the header.

Within a single visit, only files with a distinct *target description* are kept: two files
collapse to one when they share an identical set of values for the keywords matching
``targets._utils._KEYWORD_PREFIX_REGEX`` (TARGNAME, TARDESC*, TARKEY*, and MT_LV*), which
is exactly the subset `identify_target_dicts` uses to decide target uniqueness. The first file
encountered (in sorted base-name order) is kept. Duplicates are removed only within a
visit, so the same target description reappears once per visit that contains it.

Type::

    build_spt_tests --help

for more information.
"""

import argparse
import pathlib
import re
import sys

from astropy.io import fits

# Fixed keywords emitted before the TARDESC*/TARKEY*/MT_LV* groups, in this order.
_LEADING_KEYS = ('PSTRTIME', 'PSTPTIME', 'TARG_ID', 'TAR_TYPE', 'TARGTYPE')

# Fixed keyword emitted between the TARDESC* group and the TARKEY* group.
_MIDDLE_KEYS = ('TARGCAT',)

# Fixed keywords emitted after the TARKEY*/MT_LV* groups, in this order.
_TRAILING_KEYS = ('TARGNAME', 'RA_TARG', 'DEC_TARG', 'PROPOSID')

# The keywords that define a target's identity, matching targets._utils._KEYWORD_PREFIX_
# REGEX. Two files within a visit are duplicates when these values all agree.
_KEYWORD_PREFIX_REGEX = re.compile(r'(TARGNAME|TARDESC|TARKEY|MT_LV)')

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_DEFAULT_CACHE = _REPO_ROOT / 'caches' / 'SPT_CACHE'
_DEFAULT_OUTPUT = _REPO_ROOT / 'tests' / 'SPT_TESTS.py'


def _extract(header):
    """The target-description keywords of one header as an ordered list of (key, value).

    Keywords absent from the header are omitted. TARKEY* and MT_LV* keywords are included
    in the order they appear in the header.
    """

    tardescs = [k for k in header.keys() if k.startswith('TARDESC')]
    tarkeys = [k for k in header.keys() if k.startswith('TARKEY')]
    mt_lvs = [k for k in header.keys() if k.startswith('MT_LV')]

    ordered = (list(_LEADING_KEYS) + tardescs + list(_MIDDLE_KEYS)
               + tarkeys + mt_lvs + list(_TRAILING_KEYS))

    items = []
    for key in ordered:
        if key in header:
            items.append((key, header[key]))
    return items


def _signature(items):
    """A hashable per-visit duplicate-detection key: the values of every keyword matching
    ``_KEYWORD_PREFIX_REGEX`` (TARGNAME, TARDESC*, TARKEY*, MT_LV*), in header order."""

    return tuple((k, v) for k, v in items if _KEYWORD_PREFIX_REGEX.match(k))


def _format_value(value):
    """Render a header value as a Python literal, using double-quoted strings to match
    the style of tests/SPT_TESTS.py."""

    if isinstance(value, str):
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return repr(value)


def _fits_files(cache):
    """Every FITS file under the cache, as (proposal_id, path), sorted by numeric
    proposal id and then by filename."""

    program_dirs = [p for p in cache.iterdir() if p.is_dir() and p.name.isdigit()]
    program_dirs.sort(key=lambda p: int(p.name))

    for program_dir in program_dirs:
        for path in sorted(program_dir.glob('*.fits')):
            yield program_dir.name, path


def build_spt_tests(cache, output, limit=0):
    """Read the cache, drop within-visit duplicates, and write the SPT_TESTS module.

    Parameters:
        cache (pathlib.Path): Directory of per-proposal subdirectories of FITS files.
        output (pathlib.Path): Path of the Python file to write.
        limit (int): If positive, stop after reading this many files (for testing).
    """

    files = list(_fits_files(cache))
    if limit:
        files = files[:limit]
    total = len(files)
    print(f'Reading {total} FITS headers from {cache}', flush=True)

    # visit -> list of (filename, items); visit -> set of signatures already kept
    visits = {}
    visit_order = []
    seen = {}
    read = 0
    unreadable = 0
    duplicates = 0
    for i, (proposal_id, path) in enumerate(files):
        try:
            header = fits.getheader(path, 0)
        except Exception as exc:                    # noqa: BLE001 - log and continue
            unreadable += 1
            sys.stderr.write(f'  skipped unreadable {path}: {exc}\n')
            continue
        read += 1

        visit = path.name[:6]
        items = _extract(header)
        signature = _signature(items)

        if visit not in visits:
            visits[visit] = []
            visit_order.append(visit)
            seen[visit] = set()

        if signature in seen[visit]:
            duplicates += 1
            continue
        seen[visit].add(signature)

        visits[visit].append((path.name, items))

        if (i + 1) % 5000 == 0 or (i + 1) == total:
            print(f'  {i + 1:6d} / {total:6d}   visits: {len(visit_order)}   '
                  f'entries: {sum(len(v) for v in visits.values())}', flush=True)

    entry_count = sum(len(v) for v in visits.values())

    lines = ['SPT_TESTS = {']
    for visit in visit_order:
        lines.append(f'    "{visit}": [')
        for filename, items in visits[visit]:
            lines.append('        {')
            lines.append(f'            "FILENAME": {_format_value(filename)},')
            for name, value in items:
                lines.append(f'            "{name}": {_format_value(value)},')
            lines.append('        },')
        lines.append('    ],')
    lines.append('}')
    lines.append('')

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines))

    print(f'\nRead {read} files ({unreadable} unreadable), '
          f'{duplicates} within-visit duplicates dropped.', flush=True)
    print(f'Wrote {len(visit_order)} visits, {entry_count} entries -> {output}',
          flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Build a Python module of unique HST target descriptions from the '
                    'FITS files in the SPT cache, organized by visit, in the form of '
                    'tests/SPT_TESTS.py.')
    parser.add_argument('--cache', type=pathlib.Path, default=_DEFAULT_CACHE,
                        help='directory of the SPT cache (default: %(default)s)')
    parser.add_argument('--output', '-o', type=pathlib.Path, default=_DEFAULT_OUTPUT,
                        help='Python file to write (default: %(default)s)')
    parser.add_argument('--limit', type=int, default=0,
                        help='read at most this many files, for testing (default: all)')
    args = parser.parse_args(argv)

    build_spt_tests(args.cache, args.output, limit=args.limit)


############################################

if __name__ == '__main__':
    main()

##########################################################################################
