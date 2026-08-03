# rms-hst-targets

Identify the small-body moving targets of Hubble Space Telescope observations —
comets, asteroids, Centaurs, trans-Neptunian objects, dwarf planets, and the
standard planets and satellites — from the target-description keywords of their
SPT/SHF support-file headers.

Maintained by the [RMS Node](https://pds-rings.seti.org) of the NASA Planetary
Data System at the SETI Institute.

**`identify_targets()` is the entry point** — the one function a caller needs.
It is a core stage of the RMS Node's **`rms-hst-pipeline`**, which is what this
package exists to serve: the pipeline hands it SPT/SHF headers and receives the
PDS4 Target context products for everything the observation looked at.

## What it does

Every HST moving-target observation carries a support ("SPT") header describing
what the telescope was pointed at: a free-form `TARGNAME`, descriptive keywords
(`TARDESCR`, `TARKEY1`–`TARKEY9`), the tracked ephemeris as orbital elements or
a standard-body name (`MT_LV1_*`, `MT_LV2_*`), and the planned sky position
(`RA_TARG`/`DEC_TARG`). These fields are inconsistent, abbreviated, misspelled,
and occasionally simply wrong — thirty-five years of proposal-writing habits.

`identify_targets()` turns that mess into the PDS4 Target context products for
the bodies observed. It recognizes bodies by name wherever possible, then
*confirms* each identification against the orbital elements embedded in the
header: comets by direct element comparison, minor planets by propagating their
catalog orbit to the observation time and comparing the predicted sky position
with `RA_TARG`/`DEC_TARG`. When no name can be recognized, it identifies the
body from the elements alone, by searching the local comet database or the
Minor Planet Center.

```python
from astropy.io import fits
from targets import identify_targets

with fits.open('u6ht4501m_shm.fits') as hdul:
    header = hdul[0].header

for path in identify_targets([header]):
    print(path.name)
# trans-neptunian_object.1998_uu43_1.2_local.xml
```

`lids_from_target_paths()` turns that list of paths into the PDS4 logical
identifiers of the same products, which is what a label referencing them needs:

```python
from targets import identify_targets, lids_from_target_paths

print(lids_from_target_paths(identify_targets([header])))
# ['urn:nasa:pds:context:target:trans-neptunian_object.1998_uu43']
```

Use `identify_target_dicts()` instead when you want the body dictionaries
rather than the context products:

```python
from targets import identify_target_dicts

for body in identify_target_dicts([header]):
    print(body['full_name'], body['ttype'], body['naif_id'])
# (523955) 1998 UU43 T 2523955
```

Pass a `Logger` to either one to get the full narrative of how each target was
identified.

See the documentation in [`docs/`](docs/):

* [Using identify_targets](docs/using-identify-targets.md) — the user's guide:
  inputs, outputs, tuning parameters, and what to do when it fails.
* [How target identification works](docs/how-it-works.md) — the pipeline from
  raw header keywords to normalized body dictionaries.
* [Handling identification failures](docs/handling-identification-failures.md)
  — the developer's guide: how to diagnose a failure and every mechanism
  available to fix one.
* [Data files and caches](docs/data-and-caches.md) — the on-disk caches and how
  they are refreshed.
* [The curated data tables](docs/data-tables.md) — the caps-named modules, what
  each controls, and when you need to edit one.
* [The src/targets/programs/ scripts](docs/programs.md) — of these, only
  `update_cometdb` and `update_target_xml_cache` are run regularly, and their
  results must be committed to take effect elsewhere; `identify_visit` is the
  tool for diagnosing an identification failure, and the rest will probably
  never be needed. Every maintenance script, what it
  does, and when to run it.

## Installation

Work inside a virtual environment at `./venv` (never the system Python):

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

Notes:

* The importable package is **`src/targets/`** (a `src/` layout). Everything
  imports under it, e.g. `from targets import identify_targets` or
  `from targets.mpc_tools import mpc_packing`. Because nothing is importable
  from the working tree, an editable install (`pip install -e ".[dev]"`) is
  required before the tests will run.
* `palpy` (the Starlink PAL/SLALIB astrometry library, used by
  `orbital_radec.py`) requires a C build. Without it, sky-position
  confirmation is skipped and `tests/test_orbital_radec.py` is skipped via
  `pytest.importorskip`.
* Name transliteration uses `anyascii`; logging uses `rms-pdslogger`.

## Package layout

| Path | Contents |
| ---- | -------- |
| `src/targets/identify_targets.py` | Both entry points: headers → context products or body dicts |
| `src/targets/identify_standard_body.py` | Planets, satellites, rings and torus identification |
| `src/targets/comet_identifiers.py` | Comet identification by name and/or orbital elements |
| `src/targets/minor_planet_identifiers.py` | Minor-planet identification via the MPC |
| `src/targets/categorize_minor_planet.py` | Asteroid vs. Centaur vs. TNO vs. dwarf planet |
| `src/targets/hst_repairs.py` | Normalization of raw HST target strings |
| `src/targets/standard_bodies.py` | Planets, satellites, dwarf planets, rings, the Io torus |
| `src/targets/target_xml_support.py` | Body dict → PDS4 context-product fields |
| `src/targets/target_xml_cache_support.py` | The context-product cache and overlay |
| `src/targets/orbital_radec.py` | Orbital elements → RA/Dec (requires `palpy`) |
| `src/targets/targettype.py` | The `TargetType` letter codes |
| `src/targets/_*.py` | Curated data tables (see [docs/data-tables.md](docs/data-tables.md)) |
| `src/targets/templates/` | The PDS4 label template used to generate new context products |
| `src/targets/cometdb/` | Comet/Centaur/damocloid database: builders, scrapers, queries |
| `src/targets/mpc_tools/` | Minor Planet Center queries and designation packing |
| `src/targets/programs/` | Maintenance scripts (see [docs/programs.md](docs/programs.md)) |
| `tests/` | pytest tests, plus caps-named fixture/baseline files not collected by pytest |
| `caches/` | On-disk data caches (see [docs/data-and-caches.md](docs/data-and-caches.md)) |

## Testing

```bash
python -m pytest -q -n auto tests
```

Tests run in parallel (`pytest-xdist`), entirely offline — an autouse fixture
blocks `requests`, so every MPC or comet-database lookup must be satisfied from
the committed caches in `caches/MPC_CACHE` and `caches/COMET_CACHE`. Coverage
of `src/targets/` is enforced by the pyproject gate.

Type checking runs on the tests only (mypy is `strict` but excludes `src/`):

```bash
python -m mypy tests
```

Lint and format with `ruff check` and `ruff format`. Style: 100-character
lines, single quotes, full type annotations, Google-style docstrings using
`Parameters:`.

`pyproject.toml` is the source of truth for all tooling configuration.
