##########################################################################################
# tests/test_hst_repairs_output.py
##########################################################################################
"""Regression test for `hst_repairs` over the whole SPT_TESTS corpus.

Running `hst_repairs` on the TARKEY*/TARGNAME strings of every SPT_TESTS entry must
reproduce the committed baseline `SPT_TESTS_OUTPUT.txt`, so that any change to the repair
tables that alters an identification is caught here.

Each baseline line is `repr(filename) --- (answers, types)`, exactly what
`print(repr(filename), '---', hst_repairs(strings))` produces.

After an *intentional* change to the repair tables, regenerate the baseline by running
this file as a script from the repository root::

    PYTHONPATH=.:targets python tests/test_hst_repairs_output.py

then review the diff before committing.
"""

import pathlib
from typing import Any

from hst_repairs import hst_repairs
from SPT_TESTS import SPT_TESTS

_BASELINE = pathlib.Path(__file__).parent / 'SPT_TESTS_OUTPUT.txt'


def _spt_strings(spt: dict[str, Any]) -> list[str]:
    """The identification strings of one SPT entry: TARKEY1-6 up to the first absent
    key, followed by TARGNAME.
    """

    strings = []
    for k in range(1, 7):
        key = f'TARKEY{k}'
        if key not in spt:
            break
        strings.append(str(spt[key]))
    strings.append(str(spt['TARGNAME']))
    return strings


def _output_line(filename: str, spt: dict[str, Any]) -> str:
    """The baseline line for one SPT entry: `repr(filename) --- (answers, types)`."""

    result = hst_repairs(_spt_strings(spt), logger=None)
    return f'{filename!r} --- {result}'


def test_hst_repairs_matches_baseline() -> None:
    expected = _BASELINE.read_text().splitlines()
    actual = [_output_line(filename, spt) for filename, spt in SPT_TESTS]

    assert len(actual) == len(expected), (
        f'{len(actual)} SPT_TESTS entries but {len(expected)} baseline lines; '
        'regenerate SPT_TESTS_OUTPUT.txt with `python tests/test_hst_repairs_output.py`')

    mismatches = [(i, e, a)
                  for i, (e, a) in enumerate(zip(expected, actual, strict=True)) if e != a]
    if mismatches:
        preview = '\n'.join(f'  line {i + 1}:\n    baseline: {e}\n    current:  {a}'
                            for i, e, a in mismatches[:5])
        raise AssertionError(
            f'hst_repairs output differs from the baseline on {len(mismatches)} of '
            f'{len(actual)} lines. If the change is intentional, regenerate with '
            f'`python tests/test_hst_repairs_output.py` and review the diff.\n{preview}')


if __name__ == '__main__':
    lines = [_output_line(filename, spt) for filename, spt in SPT_TESTS]
    _BASELINE.write_text('\n'.join(lines) + '\n')
    print(f'Wrote {len(lines)} lines to {_BASELINE}')

##########################################################################################
