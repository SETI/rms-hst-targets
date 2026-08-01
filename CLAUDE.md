# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Identifies HST small-body moving targets (comets, asteroids/minor planets, standard bodies) from FITS SPT header keywords. RMS Node (SETI). Early-stage / WIP — the working tree on `main` is usually dirty.

## Package layout

The importable package is **`targets/`** (not `src/`). `pyproject.toml` sets `packages.find where = ["."]` / `include = ["targets", "targets.*"]` and pytest `pythonpath = ["."]`, so everything is imported under the package, e.g. `from targets import identify_targets`, `from targets.mpc_tools import mpc_packing`.

- `targets/` — main package: identification logic (`identify_targets.py`, `identify_standard_body.py`, `comet_identifiers.py`, `minor_planet_identifiers.py`, `standard_bodies.py`, `orbital_radec.py`), target-XML context-product support (`target_xml_support.py`, `target_xml_cache_support.py`, `targettype.py`), data modules (`_STANDARD_BODY_LIST.py`, `_HST_PROGRAM_OVERRIDES.py`, etc.), and subpackages `cometdb/` (comet/centaur DB builders & scrapers) and `mpc_tools/` (MPC packing/queries).
- `tests/` — pytest tests. Also holds non-pytest fixtures/baselines named in caps (`SPT_TESTS.py`, `SPT_TESTS_OUTPUT.txt`) — these are not collected by pytest.
- `programs/` — maintenance / diagnostic scripts (`identify_visit.py`, `update_cometdb.py`, `update_target_xml_cache.py`, `build_spt_tests.py`, `retrieve_mast_moving_target_spts.py`, `reality_check_radec.py`). Not shipped; see `docs/programs.md`.
- `caches/` — on-disk data caches: `COMET_CACHE/`, `MPC_CACHE/`, `TARGET_XML_CACHE/` (committed). Modules find these by repo-relative path, falling back to `./NAME`. `TARGET_XML_CACHE/` is a read-only Engineering Node mirror; newly generated "_local" context products go to the gitignored `TARGET_XML_OVERLAY/` (activated via `use_local_xml_dir()`), which reads resolve overlay-first so the committed mirror stays pristine.

## Commands

- Install dev env: `pip install -e ".[dev]"` (work inside a venv at `./venv`; never system Python).
- Run all tests: `python -m pytest -q -n auto tests` (xdist, coverage, `--strict-markers` come from pyproject `addopts`; source is `targets`; branch-coverage gate `fail_under = 75`).
- Single test: `pytest tests/test_orbital_radec.py::test_name`.
- Type-check: `python -m mypy tests` — mypy is `strict` but **excludes `targets/` and `programs/`; it only ever runs on `tests/`.** Don't run mypy against the package.
- Lint: `ruff check` — the whole repo is clean; keep it that way. **Do not run `ruff format`**: the code is hand-aligned (import blocks, pattern tables) and ~49 files would be reformatted. `I001` is disabled for the same reason.
- Docs: `sphinx-build -W -b html docs docs/_build` and `pymarkdown scan docs/ README.md CONTRIBUTING.md`. Both are clean and both run in CI.
- Run one visit end to end: `python -m programs.identify_visit <VISIT>`.

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
