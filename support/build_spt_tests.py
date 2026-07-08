#!/usr/bin/env python3
##########################################################################################
# support/build_spt_tests.py
##########################################################################################
"""Build a Python module of unique HST target descriptions from the SPT cache.

This reads every FITS file in ``caches/SPT_CACHE`` (the ``_spt.fits``/``_shm.fits``/
``_shf.fits`` support files retrieved by ``retrieve_mast_moving_target_spts.py``) and
extracts the key target-description keywords from each primary header:

    PSTRTIME, PSTPTIME, TARG_ID, TAR_TYPE, TARGTYPE, TARDESC*, TARGCAT, TARKEY*,
    MT_LV*, TARGNAME, RA_TARG, DEC_TARG, PROPOSID

It writes a single Python file in the same form as ``tests/SPT_TESTS.py``: a list
``SPT_TESTS`` of ``("<proposal_id>/<filename>", {<keyword>: <value>, ...})`` tuples.
Only keywords that are actually present in a header are emitted. Unlike the hand-built
``tests/SPT_TESTS.py``, MTFLAG, RA_REF, and DEC_REF are not included.

Duplicate entries are removed. Two files are considered duplicates when they share an
identical set of values for TARDESC*, TARGTYPE, TARGCAT, TARKEY*, MT_LV*, and TARGNAME;
the first one encountered (in sorted proposal-id, then filename order) is kept.

Type::

    build_spt_tests --help

for more information.
"""

import argparse
import pathlib
import sys

from astropy.io import fits

# Fixed keywords emitted before the TARDESC*/TARKEY*/MT_LV* groups, in this order.
_LEADING_KEYS = ('PSTRTIME', 'PSTPTIME', 'TARG_ID', 'TAR_TYPE', 'TARGTYPE')

# Fixed keyword emitted between the TARDESC* group and the TARKEY* group.
_MIDDLE_KEYS = ('TARGCAT',)

# Fixed keywords emitted after the TARKEY*/MT_LV* groups, in this order.
_TRAILING_KEYS = ('TARGNAME', 'RA_TARG', 'DEC_TARG', 'PROPOSID')

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
    """A hashable duplicate-detection key: the values of TARDESC*, TARGTYPE, TARGCAT,
    TARKEY*, MT_LV*, and TARGNAME."""

    values = dict(items)
    tardesc_vals = tuple(v for k, v in items if k.startswith('TARDESC'))
    tarkey_vals = tuple(v for k, v in items if k.startswith('TARKEY'))
    mt_lv_vals = tuple(v for k, v in items if k.startswith('MT_LV'))
    return (tardesc_vals, values.get('TARGTYPE'), values.get('TARGCAT'),
            tarkey_vals, mt_lv_vals, values.get('TARGNAME'))


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
    """Read the cache, drop duplicates, and write the SPT_TESTS module.

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

    seen = set()
    entries = []
    read = 0
    unreadable = 0
    for i, (proposal_id, path) in enumerate(files):
        try:
            header = fits.getheader(path, 0)
        except Exception as exc:                    # noqa: BLE001 - log and continue
            unreadable += 1
            sys.stderr.write(f'  skipped unreadable {path}: {exc}\n')
            continue
        read += 1

        items = _extract(header)
        signature = _signature(items)
        if signature in seen:
            continue
        seen.add(signature)

        key = f'{proposal_id}/{path.name}'
        entries.append((key, items))

        if (i + 1) % 5000 == 0 or (i + 1) == total:
            print(f'  {i + 1:6d} / {total:6d}   unique so far: {len(entries)}',
                  flush=True)

    lines = ['SPT_TESTS = [']
    for key, items in entries:
        lines.append(f'    ("{key}", {{')
        for name, value in items:
            lines.append(f'        "{name}": {_format_value(value)},')
        lines.append('    }),')
    lines.append(']')
    lines.append('')

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines))

    print(f'\nRead {read} files ({unreadable} unreadable), '
          f'{read - len(entries)} duplicates dropped.', flush=True)
    print(f'Wrote {len(entries)} unique entries -> {output}', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Build a Python module of unique HST target descriptions from the '
                    'FITS files in the SPT cache, in the form of tests/SPT_TESTS.py.')
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
