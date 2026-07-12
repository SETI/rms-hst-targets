# Data files and caches

The identification pipeline runs almost entirely from local data: curated
Python tables inside `targets/`, and on-disk caches under `caches/`. Network
access happens only as a fallback (MPC lookups for uncached objects) or when
the maintenance scripts in `support/` are run explicitly — never at import.

## Cache directories

Modules locate `caches/<NAME>` relative to the repository root, falling back
to `./<NAME>` when the package layout doesn't match.

| Directory | Committed? | Contents |
| --------- | ---------- | -------- |
| `caches/COMET_CACHE` | yes | The merged comet/Centaur database pickles plus raw snapshots of each web source |
| `caches/MPC_CACHE` | yes | One saved MPC `show_object` HTML page per queried body |
| `caches/TARGET_XML_CACHE` | yes | PDS4 target context products and their name-lookup index |
| `caches/SPT_CACHE` | **no** — gitignored symlink | Every HST moving-target support file (`_spt`/`_shm`/`_shf.fits`), on an external SSD |

`caches/SPT_CACHE` is a symlink to `/Volumes/Data-SSD/SPT_CACHE`; any work
that reads SPT files (corpus regeneration, bulk validation) fails unless that
volume is mounted.

### COMET_CACHE

`cometdb.comet_dicts()` / `centaur_dicts()` lazily unpickle and memoize:

* `#COMETS.pickle` — a 3-tuple `(comets, by_lookup, by_ambiguous)`:
  * `comets`: keyed by unique comet key — the numbered id (`"1P"`, `"2I"`) or
    year designation (`"D/1993 F2"`), with fragments suffixed (`"73P-B"`).
  * `by_lookup`: every unambiguous identifier string → comet dict.
  * `by_ambiguous`: shared names (`"Encke"`, `"Shoemaker-Levy"`) → list of
    candidate dicts.
* `#CENTAURS.pickle` — the same shape for Centaurs, keyed by minor-planet
  number (or designation).

Comet dictionaries carry `prefix`, `desig`, `name`, `cnum`, `fragment`,
`alt_prefixes`, `alt_frags`, `alt_names`, `alt_desigs`, `old_desigs`, `mnum`,
`naif_id`, `ttype` (`"C"`), elements `A Q I O E W`, `year`, `key`,
`parent_key`, `full_name`, `aliases`, `lookups`, and `ambiguous`.

The comet database is built by `_build_comet_dicts()` from five sources
(Johnston's Archive feeds the separate Centaur database), merged in
decreasing order of authoritativeness, each snapshotted in the cache under a
fixed basename:

| Source | URL | Cache file |
| ------ | --- | ---------- |
| Wikipedia comet lists (periodic, Halley-type, long-period, near-parabolic, numbered, interstellar) | `en.wikipedia.org/wiki/List_of_*` | `<page-name>.html` |
| MPC periodic-comet codes | `minorplanetcenter.net/iau/lists/PeriodicCodes.html` | `mpc_PeriodicCodes.txt` |
| PDS Small Bodies Node | `pds-smallbodies.astro.umd.edu/.../periodic_comets.shtml` | `sbn_periodic_comets.txt` |
| JPL SBDB query API (elements, NAIF IDs) | `ssd-api.jpl.nasa.gov/sbdb_query.api` | `sbdb_query_results.csv` |
| ICQ comet names | `icq.eps.harvard.edu/names1.html` | `icq_names1.txt` |
| Johnston's Archive (Centaurs only) | `johnstonsarchive.net/astro/tnoslist.html` | `johnstonarchive_tnoslist.txt` |

Hand corrections to individual source records live in
`targets/cometdb/repair_comet.py` and are applied during every build. When a
freshly fetched source page differs from the cached copy, the old copy is
kept as `<stem>-<YYYY-MM-DD>.<ext>`; superseded pickles are kept as
`#COMETS_v<NNN>.pickle`.

Runtime queries (`query_comet_by_name`, `query_comet_by_elements`,
`query_centaur_by_name`) never touch the network — only the pickles.

### MPC_CACHE

`mpc_tools.mpc_query_by_name(name)` resolves a minor planet (or
dual-designated comet) via the MPC's
`db_search/show_object?object_id=<name>` page. Pages are cached as
`<KEY>.html`, where `<KEY>` is the query string uppercased with `/` replaced
by `-`:

* `"103P"` → `MPC_CACHE/103P.html`
* `"C/1995 O1"` → `MPC_CACHE/C-1995 O1.html`

A cached page short-circuits the network entirely, which is what allows the
test suite to run with `requests` blocked. Retrieved pages have the bulky
Observations table stripped before caching. The parsed result is normalized
by `mpc_body_dict()` into `mnum`, `name`, `desig`, `alt_desigs`, `mpc_key`,
`full_name`, `naif_id`, `ttype` (`"M"`, refined later), and elements
`A Q I O E W` plus `M`, `EPOCH`, `T` when present.

`mpc_query_by_elements()` (no name available) queries the MPC
`show_by_properties` search over element ranges, adaptively widening or
narrowing the search window, then ranks the returned bodies by
`element_resid` and resolves each candidate through `mpc_query_by_name`
(and hence through the same page cache).

### TARGET_XML_CACHE

A mirror of the PDS4 target context products from
`https://pds.nasa.gov/data/pds4/context-pds4/target/`, plus a pickled
name-lookup index (`$LOOKUP.pickle`). Maintained by
`support/update_target_xml_cache.py`, which downloads new products, removes
superseded versions, and rebuilds the index. To stage a product locally
before it exists remotely, name it with a `_local` suffix before `.xml`.

## Curated data tables in `targets/`

These are Python modules, maintained by hand, that encode the accumulated
knowledge about HST's header conventions. They are the primary levers for
fixing identification failures — see the
[developer's guide](handling-identification-failures.md).

| Module | Contents |
| ------ | -------- |
| `_HST_PROGRAM_OVERRIDES.py` | `SPT_REPAIRS`: per-`TARG_ID` keyword patches and no-target sentinels, each with a comment recording the evidence |
| `_TARGET_STRING_REPAIRS.py` | Regex → replacement pairs for specific misspellings and idioms |
| `_TARGNAME_PREFIX_SUFFIX_PATTERNS.py` | Ignorable decorations at the start/end of a `TARGNAME` |
| `_UNDIAGNOSTIC_TARGET_WORDS.py` | Words that never identify a target, deleted outright |
| `_DISALLOWED_MINOR_PLANET_NAMES.py` | Names reserved for satellites/comets that must not match asteroids |
| `_STANDARD_BODY_LIST.py` | Planets, satellites, dwarf planets, systems, rings, torus — names, numbers, NAIF IDs, aliases |

## Maintenance scripts in `support/`

Not shipped with the package; all are run directly with Python and accept
`--help`.

### `retrieve_mast_moving_target_spts.py`

Downloads the support files (`_spt.fits`, `_shm.fits`, `_shf.fits`) for every
HST observation flagged as a moving target at MAST (~845 programs) into
`caches/SPT_CACHE/<proposal_id>/`, writing a `manifest.csv`. Resumable —
files already present at the expected size are skipped. Options:
`--manifest-only`, `--limit-programs N`, `--outdir`, `--workers`, `--chunk`.

### `build_spt_tests.py`

Reads every FITS header in the SPT cache and regenerates
`tests/SPT_TESTS.py`: the list of *unique* target descriptions
(`("<proposal>/<file>", {keyword: value, ...})` tuples) that serves as the
offline test corpus. Two headers are duplicates when they agree on all
`TARDESC*`, `TARGTYPE`, `TARGCAT`, `TARKEY*`, `MT_LV*`, and `TARGNAME`
values. Options: `--cache`, `--output`, `--limit`.

### `reality_check_radec.py`

Sanity-checks the corpus itself: for every `SPT_TESTS` entry with `MT_LV1`
elements, propagates the elements to the observation midpoint
(`orbital_radec`, perturbed with two-body fallback) and compares the result
with the header's `RA_TARG`/`DEC_TARG`. Prints offset percentiles, highlights
offsets ≥ 60″, and categorizes the causes (dummy/slew targets, B1950
elements, nongravitational comets, large epoch gaps, unexplained). Writes a
CSV (`--asteroids`/`--comets` to restrict; the committed
`reality_check_asteroids.csv` / `reality_check_comets.csv` are its outputs).
Requires `palpy`.

### `update_cometdb.py`

Refreshes the comet and Centaur databases in `COMET_CACHE`. Fetches the web
sources (falling back to cached snapshots when offline), applies
`repair_comet`, merges, and rewrites the pickles only when the content
changed. Options: `--rebuild`/`-r` (force), `--local` (rebuild from cached
source pages without network), `--comets`, `--centaurs`, `--debug`,
`--quiet`, `--log PATH`.

### `update_target_xml_cache.py`

Synchronizes `TARGET_XML_CACHE` with the PDS Engineering Node and rebuilds
the pickled name-lookup index. Options: `--rebuild`, `--debug`, `--quiet`,
`--log`.

## Test fixtures in `tests/`

Per project convention, caps-named files in `tests/` are fixtures or
interactive tester artifacts, **not** collected by pytest:

* `SPT_TESTS.py` — the generated corpus described above (~2.9 MB), imported
  by the pytest tests, the reality checker, and bulk validation loops.
* `SPT_TESTS_OUTPUT.txt` — baseline output of running `hst_repairs` over the
  whole corpus (regenerate via the `if False:` block at the bottom of
  `targets/hst_repairs.py`); diff after changing the repair tables.
* `_IDENTIFY_SMALL_BODY_TESTER_OUPUT.txt` — captured log of a bulk
  `identify_small_body` run over the corpus, with each `*** FAILED! ***` case
  and its full log narrative; the driver loop it records is preserved in git
  history as `_IDENTIFY_SMALL_BODY_TESTER.py`.
