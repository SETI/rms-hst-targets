# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Identifies HST small-body moving targets (comets, asteroids/minor planets, standard bodies) from FITS SPT header keywords. RMS Node (SETI). The working tree on `main` is usually dirty.

**`identify_targets(headers, ...) -> list[pathlib.Path]` is the entry point** and the only one callers need; it is a core stage of the RMS Node's `rms-hst-pipeline`. It accepts headers spanning any number of visits, groups them by visit (first six characters of `FILENAME`), and returns one PDS4 Target context-product path per identified body. `lids_from_target_paths()` converts that list of paths to the products' LIDs, which are encoded in their file names. `identify_target_dicts()` is the lower-level form: one visit only (`ValueError` otherwise), returns body dicts, generates no context products. Failure raises `TargetIdentificationFailure`, or its subclass `NotPlanetaryError` when the visit is not a planetary observation at all — a visit qualifies if any header is a `MOVING TARGET`, declares `TARGCAT` `SOLAR SYSTEM`, or is FGS/HSP (occultations); `_HST_PROGRAM_OVERRIDES` overrides either way. A failure in one visit abandons the rest, so callers looping over many should catch per visit.

## Package layout

The importable package is **`src/targets/`** (a `src/` layout). `pyproject.toml` sets `packages.find where = ["src"]` / `include = ["targets", "targets.*"]`, so everything is imported under the package, e.g. `from targets import identify_targets`, `from targets.mpc_tools import mpc_packing`. There is **no pytest `pythonpath`**: nothing is importable from the working tree, so `pip install -e ".[dev]"` is required before the tests will run. That is deliberate — it makes the suite exercise the same artifact users install, catching packaging bugs (missing package data, a bad `packages.find` filter) that a flat layout hides.

- `src/targets/` — main package: identification logic (`identify_targets.py`, `identify_standard_body.py`, `comet_identifiers.py`, `minor_planet_identifiers.py`, `standard_bodies.py`, `orbital_radec.py`), target-XML context-product support (`target_xml_support.py`, `target_xml_cache_support.py`, `targettype.py`), data modules (`_STANDARD_BODY_LIST.py`, `_HST_PROGRAM_OVERRIDES.py`, etc.), subpackages `cometdb/` (comet/centaur DB builders & scrapers) and `mpc_tools/` (MPC packing/queries), and `templates/` (the PDS4 label template, shipped as package data and read at run time).
- `tests/` — pytest tests. Also holds non-pytest fixtures/baselines named in caps (`SPT_TESTS.py`, `SPT_TESTS_OUTPUT.txt`) — these are not collected by pytest.
- `src/targets/programs/` — maintenance / diagnostic scripts (`identify_visit.py`, `update_cometdb.py`, `update_target_xml_cache.py`, `build_spt_tests.py`, `retrieve_mast_moving_target_spts.py`, `reality_check_radec.py`), run as `python -m targets.programs.<name>`. Only the two `update_*` scripts are in routine use, and **their output must be committed** or other installations keep resolving the old data; `identify_visit` is the diagnosis tool for an identification failure; the rest are rarely needed and two require the external SSD. Shipped in the wheel, but most assume a source checkout (they read `tests/SPT_TESTS.py` or `caches/`); see `docs/programs.md`. Excluded from coverage — as a subpackage they would otherwise be measured by `source = ["targets"]`.
- `caches/` — on-disk data caches: `COMET_CACHE/`, `MPC_CACHE/`, `TARGET_XML_CACHE/` (committed). Modules find these by repo-relative path, falling back to `./NAME`. `TARGET_XML_CACHE/` is a read-only Engineering Node mirror; newly generated "_local" context products go to the gitignored `TARGET_XML_OVERLAY/` (activated via `use_local_xml_dir()`), which reads resolve overlay-first so the committed mirror stays pristine.

## Commands

- Install dev env: `pip install -e ".[dev]"` (work inside a venv at `./venv`; never system Python).
- Run all tests: `python -m pytest -q -n auto tests` (xdist, coverage, `--strict-markers` come from pyproject `addopts`; source is `targets`; branch-coverage gate `fail_under = 75`).
- Single test: `pytest tests/test_orbital_radec.py::test_name`.
- Type-check: `python -m mypy tests` — mypy is `strict` but **excludes `src/`; it only ever runs on `tests/`.** Don't run mypy against the package.
- Lint: `ruff check` — the whole repo is clean; keep it that way. **Do not run `ruff format`**: the code is hand-aligned (import blocks, pattern tables) and ~49 files would be reformatted. `I001` is disabled for the same reason.
- Docs: `sphinx-build -W -b html docs docs/_build` and `pymarkdown scan docs/ README.md CONTRIBUTING.md`. Both are clean and both run in CI.
- Run one visit end to end: `python -m targets.programs.identify_visit <VISIT>`.

`pyproject.toml` is the source of truth for tooling. Documentation lives in `README.md` and `docs/`: `using-identify-targets.md` (user's guide), `how-it-works.md` (pipeline internals), `handling-identification-failures.md` (diagnosis), `data-and-caches.md` (caches), `data-tables.md` (the caps-named modules), `programs.md` (the scripts). Keep these in sync with behavior changes.

## Style

- Line length **100**; **single quotes** (`ruff.format quote-style = "single"`); target `py310`. (`.cursor/rules/*` say 90 / 3.12 — stale; ignore.)
- Full type annotations including `-> None`; modern generics (`list[str]`, `X | None`).
- Google-style docstrings using `Parameters:` (not `Args:`) on every module/class/function.
- Prefix internals with `_`; declare public API via `__all__`.
- Imports at top, three alphabetized groups (stdlib / third-party / local); inline imports only for heavy optional deps.
- Tests must be parallel-safe under `-n auto` (independent, restore any mutated globals via fixture/`try-finally`); assert exact values and exception-message content via `pytest.raises` as a context manager.

## Gotchas

- `caches/SPT_CACHE` is a **symlink to an external SSD** (`/Volumes/Data-SSD/SPT_CACHE`) and is gitignored — SPT-based work fails unless that volume is mounted.
- `palpy` (SLALIB/PAL astrometry, used by `orbital_radec.py`) needs a C build; `test_orbital_radec.py` does `pytest.importorskip("palpy")`.
- Scrapers in `cometdb/` and `programs/` hit external services (MPC, JPL Horizons, MAST) — only when those scripts run, never at import.
- Logging uses `rms-pdslogger` (imported as `pdslogger`); name transliteration uses `anyascii` (not `unidecode`).
- The `#*.pickle` databases in `caches/COMET_CACHE` are build products, gitignored, and regenerated from the committed HTML/CSV sources on first use. The sources themselves **are** committed — a new scraper source must be `git add`ed or a fresh clone cannot rebuild.
- Editing a repair table changes `tests/SPT_TESTS_OUTPUT.txt`. Regenerate with `python tests/test_hst_repairs_output.py` and **read the diff** — it is the main guard against a repair change breaking unrelated targets.
- Every pattern in `_TARGET_STRING_REPAIRS.py` is anchored with `$`, so a general transform that appends a type marker (`|[C]`) can silently prevent it from ever matching. See `docs/data-tables.md`.
- A word added to `_UNDIAGNOSTIC_TARGET_WORDS.py` is deleted **wherever it appears as a token, including inside a longer name**. `MOUNTAIN` would reduce `PURPLE MOUNTAIN` — (3494) Purple Mountain — to `PURPLE`. Check that no real body name contains the word before adding it, and check `hst_repairs('WORD')` first: an empty result means it is already handled.
- `mpc_query_by_name` writes the MPC reply to `caches/MPC_CACHE` **before** checking that it is valid, so a query the MPC cannot answer leaves a "not found" page that then satisfies the same query forever. That is also what lets the offline suite resolve a known-bad name, so it is deliberate; just expect junk to accumulate. The MPC says "not found" two ways (`Vaguely similar sounding`, `Exact match for … not found`) and both return `None`; a third, `Unknown object`, means the *query* was malformed and still raises.
