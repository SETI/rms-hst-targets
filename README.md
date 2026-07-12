# rms-hst-targets

Identify the small-body moving targets of Hubble Space Telescope observations —
comets, asteroids, Centaurs, trans-Neptunian objects, dwarf planets, and the
standard planets and satellites — from the target-description keywords of their
SPT/SHF support-file headers.

Maintained by the [RMS Node](https://pds-rings.seti.org) of the NASA Planetary
Data System at the SETI Institute. **Early-stage / work in progress.**

## What it does

Every HST moving-target observation carries a support ("SPT") header describing
what the telescope was pointed at: a free-form `TARGNAME`, descriptive keywords
(`TARDESCR`, `TARKEY1`–`TARKEY9`), the tracked ephemeris as orbital elements or
a standard-body name (`MT_LV1_*`, `MT_LV2_*`), and the planned sky position
(`RA_TARG`/`DEC_TARG`). These fields are inconsistent, abbreviated, misspelled,
and occasionally simply wrong — thirty-five years of proposal-writing habits.

`identify_target()` turns that mess into a list of clean body dictionaries
suitable for generating PDS4 Target context products. It recognizes bodies by
name wherever possible, then *confirms* each identification against the orbital
elements embedded in the header: comets by direct element comparison, minor
planets by propagating their catalog orbit to the observation time and
comparing the predicted sky position with `RA_TARG`/`DEC_TARG`. When no name
can be recognized, it identifies the body from the elements alone, by searching
the local comet database or the Minor Planet Center.

```python
from astropy.io import fits
from targets.identify_target import identify_target, TargetIdentificationError

with fits.open('j8i701011_spt.fits') as hdul:
    header = hdul[0].header

bodies = identify_target(header)
for body in bodies:
    print(body['full_name'], body['ttype_name'], body['lid_suffix'])
# Quaoar  trans-neptunian_object  trans-neptunian_object.quaoar
```

Each returned dictionary is guaranteed to contain `name`, `full_name`, `ttype`
(a `TargetType` letter code), `ttype_name`, `naif_id` (or None), `aliases`,
`parent_key`, and `lid_suffix`; small bodies also carry their orbital elements.
Pass a `Logger` to get the full narrative of how each target was identified.

See the documentation in [`docs/`](docs/):

* [How target identification works](docs/how-it-works.md) — the pipeline from
  raw header keywords to normalized body dictionaries.
* [Handling identification failures](docs/handling-identification-failures.md)
  — the developer's guide: how to diagnose a failure and every mechanism
  available to fix one.
* [Data files and caches](docs/data-and-caches.md) — the on-disk caches, the
  curated data tables, and the `support/` maintenance scripts.

## Installation

Work inside a virtual environment at `./venv` (never the system Python):

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

Notes:

* The importable package is **`targets/`**; modules import bare (e.g.
  `from targets.identify_target import identify_target`, or `import
  identify_comet` inside the test suite, whose `pythonpath` includes
  `targets`).
* `palpy` (the Starlink PAL/SLALIB astrometry library, used by
  `orbital_radec.py`) requires a C build. Without it, sky-position
  confirmation is skipped and `tests/test_orbital_radec.py` is skipped via
  `pytest.importorskip`.
* Name transliteration uses `anyascii`; logging uses `rms-pdslogger`.

## Package layout

| Path | Contents |
| ---- | -------- |
| `targets/identify_target.py` | Top-level entry point: header → list of body dicts |
| `targets/identify_small_body.py` | Dispatch between comet and minor-planet identification |
| `targets/identify_comet.py` | Comet identification by name and/or orbital elements |
| `targets/identify_minor_planet.py` | Minor-planet identification via the MPC |
| `targets/hst_repairs.py` | Normalization of raw HST target strings |
| `targets/standard_bodies.py` | Planets, satellites, dwarf planets, rings, the Io torus |
| `targets/categorize_minor_planet.py` | Asteroid vs. Centaur vs. TNO vs. dwarf planet |
| `targets/orbital_radec.py` | Orbital elements → RA/Dec (requires `palpy`) |
| `targets/targettype.py` | The `TargetType` letter codes |
| `targets/_*.py` | Curated data tables (overrides, string repairs, body lists) |
| `targets/cometdb/` | Comet/Centaur database: builders, scrapers, and queries |
| `targets/mpc_tools/` | Minor Planet Center queries and designation packing |
| `tests/` | pytest tests, plus caps-named fixture/tester files not collected by pytest |
| `support/` | Data-refresh and validation scripts (not shipped) |
| `caches/` | On-disk data caches (see [docs/data-and-caches.md](docs/data-and-caches.md)) |

## Testing

```bash
python -m pytest -q -n auto tests
```

Tests run in parallel (`pytest-xdist`), entirely offline — an autouse fixture
blocks `requests`, so every MPC or comet-database lookup must be satisfied from
the committed caches in `caches/MPC_CACHE` and `caches/COMET_CACHE`. Coverage
of `targets/` is enforced by the pyproject gate.

Type checking runs on the tests only (mypy is `strict` but excludes
`targets/` and `support/`):

```bash
MYPYPATH=targets python -m mypy tests
```

Lint and format with `ruff check` and `ruff format`. Style: 100-character
lines, single quotes, full type annotations, Google-style docstrings using
`Parameters:`.

`pyproject.toml` is the source of truth for all tooling configuration.
