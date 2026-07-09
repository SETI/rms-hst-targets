# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Identifies HST small-body moving targets (comets, asteroids/minor planets, standard bodies) from FITS SPT header keywords. RMS Node (SETI). Early-stage / WIP — the working tree on `main` is usually dirty.

## Package layout

The importable package is **`targets/`** (not `src/`). `pyproject.toml` sets `packages.find where = ["targets"]` and pytest `pythonpath = ["targets"]`, so modules import bare, e.g. `import identify_comet`, `from mpc_tools import mpc_packing`.

- `targets/` — main package: identification logic (`identify_small_body.py`, `identify_comet.py`, `identify_minor_planet.py`, `standard_bodies.py`, `orbital_radec.py`), data modules (`_STANDARD_BODY_LIST.py`, `_HST_PROGRAM_OVERRIDES.py`, etc.), and subpackages `cometdb/` (comet/centaur DB builders & scrapers) and `mpc_tools/` (MPC packing/queries).
- `tests/` — pytest tests. Also holds non-pytest tester scripts and fixtures named in caps (`_IDENTIFY_SMALL_BODY_TESTER.py`, `SPT_TESTS.py`, `_TEST_OUTPUT.txt`) — these are not collected by pytest.
- `support/` — maintenance / data-refresh scripts (`update_cometdb.py`, `retrieve_mast_moving_target_spts.py`, `reality_check_radec.py`). Not shipped.
- `caches/` — on-disk data caches: `COMET_CACHE/`, `MPC_CACHE/`, `TARGET_XML_CACHE/` (committed). Modules find these by repo-relative path, falling back to `./NAME`.

## Commands

- Install dev env: `pip install -e ".[dev]"` (work inside a venv at `./venv`; never system Python).
- Run all tests: `python -m pytest -q -n auto tests` (xdist, coverage, `--strict-markers` come from pyproject `addopts`; source is `targets`; branch-coverage gate `fail_under = 90`).
- Single test: `pytest tests/test_orbital_radec.py::test_name`.
- Type-check: `MYPYPATH=targets python -m mypy tests` — mypy is `strict` but **excludes `targets/` and `support/`; it only ever runs on `tests/`.** Don't run mypy against the package.
- Lint / format: `ruff check` and `ruff format`.

**Do not use `scripts/run-all-checks.sh`, `.github/workflows/run-tests.yml`, or `README.md` as references** — they are stale project-template artifacts. They point ruff/bandit/coverage at a nonexistent `src/`, have literal `REPONAME` job names, and the README's env vars (`HST_STAGING`, etc.) belong to a different project. `pyproject.toml` is the source of truth.

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
- Scrapers in `cometdb/` and `support/` hit external services (MPC, JPL Horizons, MAST) — only when those scripts run, never at import.
- Logging uses `rms-pdslogger` (imported as `pdslogger`); name transliteration uses `anyascii` (not `unidecode`).
