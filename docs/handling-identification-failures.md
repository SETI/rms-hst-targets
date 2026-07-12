# Developer's guide: handling identification failures

`identify_target()` is built around a corpus of ~35 years of inconsistent HST
header conventions, so new failures are expected as new observations (or new
header quirks) appear. This guide explains how a failure presents, how to
diagnose it, and — most importantly — **every mechanism available for fixing
one**, with guidance on choosing among them.

Read [How target identification works](how-it-works.md) first; this guide
assumes you know the pipeline stages.

## How failures present

`TargetIdentificationError` is raised from four places in
`targets/identify_target.py`:

1. **`Unresolved standard target "STD=..." in MT_LV1/2`** — an `MT_LV*`
   `STD=` field named something that isn't in `STANDARD_BODY_LOOKUP` and
   couldn't be resolved as a small body.
2. **`Comet "..." is incompatible with the header orbital elements`** — a
   comet was identified by name, but its catalog elements disagree with the
   header's `TYPE=COMET` elements (residual above `comet_rms`), and no other
   comet matches both the elements and the names.
3. **`Minor planet "..." is N″ from RA_TARG/DEC_TARG ... beyond the
   tolerance`** — a minor planet was identified by name, but its catalog
   orbit, propagated to the observation time, misses the header's target
   position, and neither the replacement nor the revised-orbit escape hatches
   applied.
4. **`No target identified for TARGNAME "..."`** — nothing was recognized at
   all.

There is a fifth, quieter failure mode: a **wrong identification that does not
raise**. These surface through the warnings in the log narrative (`"...
accepting on the assumption that the orbit was revised"`, `"... categorized as
X but the target description says Y"`), through the bulk validation runs
described below, or through human review. Treat a suspicious warning as
seriously as an exception.

## Step 1: reproduce with a logger

Always start by re-running the identification with a logger and reading the
narrative:

```python
import pdslogger
from targets.identify_target import identify_target

logger = pdslogger.EasyLogger()
bodies = identify_target(header, logger=logger)
```

The log shows the applied overrides, the collected strings, the repaired
identifiers and type votes from `hst_repairs`, every candidate considered with
its element residual and sky offset, and exactly which test failed. Most
diagnoses fall out of this narrative directly.

If the observation is in the test corpus, get its header from
`tests/SPT_TESTS.py`:

```python
import sys; sys.path.insert(0, 'tests')    # unless running under pytest
from SPT_TESTS import SPT_TESTS
header = dict(SPT_TESTS)['9678/j8i701011_spt.fits']
```

## Step 2: figure out what the header *should* have said

Useful resources, roughly in the order to try them:

* **The raw keywords.** Look at `TARGNAME`, `TARKEY1–9`, `TARDESCR`,
  `MT_LV1_*`/`MT_LV2_*`, `RA_TARG`/`DEC_TARG`, and `TARG_ID` together. Is the
  name garbled but recognizable? Are the elements plausible for the claimed
  body? Watch for `EQUINOX=B1950` and `EPOCHTIMESCALE=TDB` — both are handled,
  but both have caused confusion.
* **The MPC.** `https://minorplanetcenter.net/db_search/show_object?object_id=<name>`
  gives the catalog orbit and every designation for a body. This is the same
  page `mpc_query_by_name` scrapes.
* **The proposal itself.** The program's APT file and abstract (via the STScI
  program page for the proposal ID) often reveal what a cryptic internal
  `TARGNAME` (e.g. `"P72X4B2"`, `"OBJECTX"`) actually was. Several existing
  overrides are annotated "from APT file".
* **The mean anomaly cross-check.** For `TYPE=ASTEROID` headers, the orbital
  longitude `W + O + M + n·Δt (mod 360°)` computed from the header elements at
  their `EPOCH` can be compared against the MPC's elements to confirm or rule
  out a candidate even when the epochs differ by decades.
* **Sky position.** Propagate a candidate's catalog orbit to the observation
  midpoint and compare with `RA_TARG`/`DEC_TARG`:

  ```python
  from targets.orbital_radec import asteroid_radec
  result = asteroid_radec(a=..., e=..., incl=..., node=..., arg_peri=...,
                          mean_anom=..., epoch='27-APR-2019:00:00:00',
                          time='15-JUN-2003:07:42:30', perturb=True)
  print(result.ra, result.dec, result.delta)
  ```

  An offset of arcseconds confirms the candidate; degrees rules it out.
  Several existing overrides are annotated "confirmed by sky position".

## Step 3: choose the fix

There is a hierarchy of remedies, from the most general to the most surgical.
**Prefer the most general mechanism that safely applies**: a pattern fix
benefits every program that shares the quirk, while a per-program override
fixes exactly one target and nothing else.

### 3.1 A string quirk that can occur across programs → the repair tables

If the problem is that `hst_repairs()` fails to normalize a name — an
abbreviation, decoration, misspelling, or format that other programs could
plausibly also use — fix it in the repair data:

| Table | Fix it here when... |
| ----- | ------------------- |
| `targets/_TARGNAME_SUFFIX_PATTERNS.py` (`_TARGNAME_SUFFIX_PATTERNS`) | An instrument/pointing decoration after a dash pollutes the name (`-ACQ`, `-EPOCH2`, `-HRC`). A trailing `-<digits>` / `-<letter>` is stripped along with it. |
| ibid. (`_TARGNAME_SUFFIX_PATTERNS_NO_TAIL`) | Same, but the pattern is short/ambiguous enough that it should only be stripped as a last resort, after everything else has been tried. |
| ibid. (`_TARGNAME_PREFIX_PATTERNS`) | Junk before a dash at the start (`OBJ-`, `RD-`). |
| `targets/_UNDIAGNOSTIC_TARGET_WORDS.py` | A word contributes nothing and should simply be deleted (`AURORAL`, `MOSAIC`). Short words go in `_UNDIAGNOSTIC_SHORT_WORDS`. |
| `targets/_TARGET_STRING_REPAIRS.py` | A specific misspelling or idiom maps to a canonical identifier (`SW3` → `73P/SCHWASSMANN_WACHMANN 3`, `SANTA` → `HAUMEA`). |
| `_TARGET_TRANSFORM_PATTERNS` in `targets/hst_repairs.py` | A whole *syntactic family* needs converting (`COMET-98-P1` → `C/1998 P1`, packed designations, transposed year/letters). |
| `_TARGET_CATEGORIZER_PATTERNS` in `targets/hst_repairs.py` | A category word should be consumed and turned into a `TargetType` vote instead of being mistaken for a name. |

Conventions inside replacement templates: `|` splits the result into separate
identifiers; `$` marks a piece to be re-processed through the tables; `[X]`
(a `TargetType` letter in brackets) casts a type vote; underscores stand in
for dashes that must survive the second, dash-splitting repair pass.

Patterns apply in the order listed above, repeatedly until the string stops
changing — so a new pattern can interact with existing ones. After editing,
sanity-check broadly (see [Step 4](#step-4-verify)); the transform tables are
the most regression-prone part of the system.

### 3.2 A problem specific to one program or target → `SPT_REPAIRS`

If the header of one particular program/target is simply *wrong* — and no
generalization exists — add an entry to `SPT_REPAIRS` in
`targets/_HST_PROGRAM_OVERRIDES.py`, keyed by `TARG_ID`:

* `'12345_6'` matches one target of one program; `'12345_*'` matches every
  target of the program. Exact keys win over wildcards.
* The value is a **dict of keyword replacements** applied to a copy of the
  header before anything else runs. Established uses:

  ```python
  '11113_52' : {'TARGNAME': '05SD278'},        # typo'd designation
  '10545_22' : {'TARKEY2':  'HAUMEA'},         # survey nickname → real name
  '2890_9'   : {'MT_LV1_1': 'STD=SATURN'},     # missing MT_LV1 supplied
  '9678_1'   : {'TARGNAME': 'QUAOAR',          # pre-announcement code name...
                'MT_LV1_1': 'FILE='},          # ...and decoy elements disabled
  '6841_2'   : {'MT_LV1_1': 'TYPE=COMET,Q=.5320503,...'},  # corrected elements
  ```

  Note the two special idioms: `'MT_LV1_1': 'FILE='` neutralizes orbital
  elements that are decoys or garbage (identification then rests on the name
  and, for minor planets, the sky position), and `'MT_LV1_1': 'STD=<body>'`
  supplies standard-body tracking that the header omitted.

* **Always leave a comment** stating what the original value was and the
  evidence for the fix ("from APT file", "confirmed by sky position (1.7″)",
  "elements match C/1984 K1"). The file is the audit trail for every manual
  intervention.

Rule of thumb, from the project notes: an error or abbreviation that *could
appear in multiple programs* belongs in `_TARGET_STRING_REPAIRS.py` (§3.1); a
fix tied to one program/target key belongs in `_HST_PROGRAM_OVERRIDES.py`.

### 3.3 There is genuinely no identifiable target → sentinels

When the observation *has no target that can ever be named*, don't force an
identification — flag the `TARG_ID` with a sentinel string instead of a
repair dict:

| Sentinel | Use for | `identify_target` returns |
| -------- | ------- | ------------------------- |
| `'ANTISOLAR_POINTING'` | Pointing at the anti-solar point (zodiacal light etc.) | `[]` |
| `'SLEW_TEST'` | Engineering exposures with dummy ephemerides | `[]` |
| `'TNO_SURVEY'` | Blind Kuiper-belt searches with no specific target | one placeholder body `"Survey HST-nnnnn"` |
| `'UNDESIGNATED_TNO'` | A real TNO known only by a survey-internal name, never designated by the MPC | one placeholder body `"Unknown HST-nnnnn"` |

The placeholders carry `ttype = 'T'` (`trans-neptunian_object`), `desig = ''`,
and a `lid_suffix` like `trans-neptunian_object.survey_hst-13633`, so
downstream PDS4 labeling still gets a well-formed target. `nnnnn` is the
five-digit zero-padded program ID.

Before choosing `UNDESIGNATED_TNO`, make a real attempt to resolve the
internal name: program 16183's hexadecimal survey names were checked one by
one, and the ones the MPC had since designated became `TARGNAME` overrides
(§3.2) while only the rest were flagged. An object can also *lose* its
designation — `2011 UH413` (program 15344) was retracted by the MPC — in
which case `UNDESIGNATED_TNO` is also the right call.

### 3.4 A name resolves to the wrong kind of body → disallowed names

If a name identifies a satellite or comet but the MPC also has a minor planet
by that name (there are many: 85 Io, 9 Metis, 2688 Halley...), add it to
`targets/_DISALLOWED_MINOR_PLANET_NAMES.py`. Such names never resolve to the
minor planet unless the header's own type votes say the target *is* a minor
planet.

### 3.5 A standard body isn't recognized → the standard body list

If a planet, satellite, dwarf planet, ring, or torus is being missed because
of an unrecognized alias (a provisional `S/2003 J 1`-style designation, an
abbreviation, an unusual spelling), add the alias to that body's entry in
`targets/_STANDARD_BODY_LIST.py`. Aliases become `STANDARD_BODY_LOOKUP` keys
automatically, with case variants and (for satellites) generated
`"<planet> <roman>"`, `"J1"`, and `S/`-designation permutations. Use the
optional trailing `alt_keys` element of the tuple for lookup-only strings
that aren't legitimate aliases.

### 3.6 The comet database is wrong or incomplete → `cometdb`

Comet identification runs against the merged local database
(`caches/COMET_CACHE/#COMETS.pickle`), not the live web. If a comet is
missing, misnamed, or carries a wrong designation/fragment:

* **Record-level corrections** go in `targets/cometdb/repair_comet.py`, which
  patches each source record during the build (name normalizations like
  `PANSTARRS` → `PanSTARRS`, fragment fixes, designation corrections via
  `_DESIG_REPAIRS`).
* **Refresh or rebuild** the database with
  `python support/update_cometdb.py` (`--rebuild` to force, `--local` to
  rebuild from cached source pages without hitting the web). Sources are
  merged in decreasing authoritativeness: Wikipedia lists → MPC PeriodicCodes
  → PDS SBN → JPL SBDB → ICQ.
* A body can also be *deliberately routed away* from the comet database: the
  `288P` overrides map the dual-designated body to its minor-planet number
  `(300163)` "which is not in the comet database".

See [Data files and caches](data-and-caches.md) for the build details.

### 3.7 The MPC lookup fails or must work offline → `MPC_CACHE` pages

`mpc_query_by_name` caches each MPC `show_object` page in `caches/MPC_CACHE`
as `<KEY>.html`, where `<KEY>` is the query string uppercased with `/`
replaced by `-` (`"103P"` → `103P.html`, `"C/1995 O1"` → `C-1995 O1.html`).
The cache is consulted before the network, so:

* **Tests must never touch the network** — `tests/test_identify_target.py`
  has an autouse fixture that makes any `requests` call raise. Every MPC
  lookup a test performs (including lookups for *candidates* considered along
  the way, not just the final answer) must have its page committed to
  `caches/MPC_CACHE`. The practical workflow: run the failing identification
  once with the network available, then `git add` the pages that appear in
  `caches/MPC_CACHE` — this is the "Add MPC cache pages" pattern visible in
  the commit history.
* To create a page manually, save the object's `show_object` HTML under the
  key-derived filename; the element table must be intact (the bulky
  Observations table is stripped automatically on normal retrieval and may be
  omitted).
* A stale cache page can itself cause a failure (e.g. after the MPC revises
  an orbit or adds a designation): delete the page and re-fetch.

### 3.8 The thresholds are wrong for a class of observations → tolerances

`identify_target` exposes `comet_rms` (0.1), `mp_rms` (0.08), and
`radec_tolerance` (120″) as per-call parameters, and the module constants
(`_RADEC_TOLERANCE_PER_YEAR`, `_REVISED_ORBIT_RMS`, ...) encode the current
policy. Loosening a threshold is almost never the right fix for a single
failure — it weakens every other identification. Reach for it only when a
*class* of legitimate identifications fails for a structural reason, and
prefer encoding the reason itself (the way the per-year drift term and the
1/distance scaling were added) over inflating a constant.

Also know the escape hatches that already exist before adding one:

* High name-confidence (> 5) outvotes a bad element residual in
  `identify_comet`/`identify_minor_planet` (a clean designation like
  `2014 OS133` unpacked from `K14OD3S` shouldn't be vetoed by stale header
  elements).
* `_rescue_comet_by_elements` re-resolves a name that matched the wrong comet.
* `_confirm_minor_planet` replaces a body contradicted by the sky position
  with one matching both elements and position, and forgives a position miss
  when the element rms ≤ `_REVISED_ORBIT_RMS` (post-observation orbit
  revision).

If a failure looks like it *should* have been caught by one of these, the bug
may be in the escape hatch, not the data.

### Choosing: a quick decision table

| Symptom | First resort |
| ------- | ------------ |
| Name garbled in a way other programs might share | Repair tables (§3.1) |
| Name/keywords wrong in exactly one program | `SPT_REPAIRS` keyword patch (§3.2) |
| Header elements are decoys or nonsense | `SPT_REPAIRS` with `'MT_LV1_1': 'FILE='` or corrected elements (§3.2) |
| `STD=` value unresolvable | Alias in `_STANDARD_BODY_LIST` (§3.5), or `SPT_REPAIRS` `MT_LV1_1` patch (§3.2) |
| Blind survey field, no target | `'TNO_SURVEY'` sentinel (§3.3) |
| Survey-internal name, no MPC designation exists | `'UNDESIGNATED_TNO'` sentinel — after trying to resolve it (§3.3) |
| Name belongs to a satellite/comet, matches an asteroid | `_DISALLOWED_MINOR_PLANET_NAMES` (§3.4) |
| Comet missing/wrong in the database | `repair_comet.py` + rebuild (§3.6) |
| MPC lookup fails offline / in tests | Commit the `MPC_CACHE` page (§3.7) |
| A whole class of valid IDs fails a threshold | Tolerance/policy change — last resort (§3.8) |

## Step 4: verify

1. **Unit tests.** Add or extend a test in `tests/test_identify_target.py`.
   If the observation's header is in `tests/SPT_TESTS.py`, use the `_header()`
   helper; otherwise a minimal literal header dict is fine (see
   `test_wildcard_override`). Assert the exact `full_name`/`ttype` and, for a
   failure case, the exact exception message via `pytest.raises(...,
   match=...)`. Remember the tests are network-blocked (§3.7) and must be
   parallel-safe under `-n auto`.

2. **Run the suite**: `python -m pytest -q -n auto tests`, plus
   `MYPYPATH=targets python -m mypy tests` and `ruff check`.

3. **Bulk regression.** For changes to the repair tables or identification
   logic, run the corpus checks:

   * The full test corpus `tests/SPT_TESTS.py` holds every *unique* target
     description harvested from the SPT cache (regenerate with
     `python support/build_spt_tests.py` — requires the `caches/SPT_CACHE`
     SSD to be mounted). Loop `identify_target` (or `identify_small_body`)
     over it and diff the failures against the previous run.
   * `hst_repairs` regressions: run the `if False:` block at the bottom of
     `targets/hst_repairs.py` over `SPT_TESTS` and diff the output against
     `tests/SPT_TESTS_OUTPUT.txt`.
   * Header sanity: `python support/reality_check_radec.py` compares every
     header's `RA_TARG`/`DEC_TARG` against its own `MT_LV1` elements and
     highlights offsets ≥ 60″ with a categorized breakdown (dummy targets,
     B1950, nongravitational comets, epoch gaps, unexplained).

4. **Document the evidence.** Whatever the fix, leave the reasoning where the
   next person will find it: a comment in the override/repair table, and MPC
   cache pages committed alongside (the commit history convention pairs each
   batch of resolutions with its cache pages).
