# How target identification works

This document walks through the identification pipeline in
`targets/identify_target.py` and its supporting modules, from raw SPT/SHF
header keywords to the normalized body dictionaries it returns.

See also:

* [Handling identification failures](handling-identification-failures.md) —
  what to do when the pipeline gets it wrong.
* [Data files and caches](data-and-caches.md) — where the reference data
  comes from.

## The input: SPT/SHF header keywords

`identify_target(header)` accepts either an `astropy.io.fits.Header` or a
plain dictionary. It uses these keywords:

| Keyword | Meaning |
| ------- | ------- |
| `TARG_ID` | `"<program>_<target>"`, e.g. `"12535_3"` — keys the per-program overrides |
| `TARGNAME` | Free-form target name chosen by the proposer |
| `TARDESCR`, `TARDESC2`–`TARDESC9` | Semicolon-separated target description |
| `TARKEY1`–`TARKEY9` | Target keywords (category words, alternate names) |
| `TARGCAT` | Target category (used only to exclude redundant description pieces) |
| `MT_LV1_*` | The moving-target ephemeris HST tracked (level 1) |
| `MT_LV2_*` | A second level: the body in the field of view, or pointing geometry |
| `RA_TARG`, `DEC_TARG` | Planned target position (degrees, J2000) |
| `PSTRTIME`, `PSTPTIME` | Observation start/stop, `"YYYY.DDD:hh:mm:ss"` |

The `MT_LV*` keyword groups are continuation series (`MT_LV1_1`, `MT_LV1_2`,
...) that concatenate into one comma-separated `KEY=VALUE` string. Values can
be split mid-number across keywords; `_parse_mt_lv()` handles the re-joining.
Each level parses to one of:

* `STD=<name>` — a standard body (planet, satellite) or occasionally a minor
  planet given by number, e.g. `STD=JUPITER` or `STD=1 (CERES)`.
* `TYPE=COMET` with elements `Q, E, I, O, W, T, EPOCH` — perihelion-based
  orbital elements.
* `TYPE=ASTEROID` with elements `A, Q, E, I, O, W, M, EPOCH` — semimajor-axis
  based elements.
* `FILE=...` — the ephemeris was delivered to HST as a file; no elements are
  available.
* Any other `TYPE` (e.g. `TYPE=POS_ANGLE`) — pointing geometry, not a body
  (reported as kind `OFFSET`).

Elements may carry `EQUINOX` (`J2000` or `B1950`; B1950 elements are rotated
to J2000 via `orbital_radec.rotate_elements_to_j2000` when `palpy` is
available) and `TTIMESCALE`/`EPOCHTIMESCALE` (`UTC` or `TDB`).

## Pipeline overview

```
header
  │
  ├─ 1. _apply_overrides()      per-program repairs and sentinels
  │        (targets/_HST_PROGRAM_OVERRIDES.py)
  │
  ├─ 2. _collect_strings()      gather TARKEY*, TARGNAME, TARDESCR pieces
  ├─ 3. _parse_mt_lv()          parse MT_LV1 (tracked) and MT_LV2 (FOV)
  │
  ├─ 4. STD resolution          standard bodies named by MT_LV* "STD" fields
  ├─ 5. hst_repairs()           normalize the name strings; extract type hints
  ├─ 6. standard-body names     repaired strings that match STANDARD_BODY_LOOKUP
  │
  ├─ 7. identify_small_body()   comet / minor-planet identification by name,
  │                             cross-checked against the MT_LV1 elements
  ├─ 8. confirmation            comets: element residual; minor planets:
  │                             propagated sky position vs. RA_TARG/DEC_TARG
  ├─ 9. position fallback       no name recognized: MPC element search,
  │                             select the candidate nearest RA_TARG/DEC_TARG
  │
  └─ 10. normalize & dedupe     _normalize_body(); FOV bodies first,
                                tracked body last
```

### 1. Per-program overrides

`SPT_REPAIRS` in `targets/_HST_PROGRAM_OVERRIDES.py` is consulted first, keyed
by `TARG_ID` — an exact key like `'10514_3'` is tried before the wildcard
`'10514_*'` that covers a whole program. (A few headers carry non-numeric
`TARG_ID`s such as `'ANTISUN'`; those key directly.) An entry is either:

* **a dict of keyword replacements**, merged into a copy of the header before
  anything else runs — used to fix a bad `TARGNAME`, supply a missing
  `MT_LV1_1`, correct mis-entered orbital elements, or neutralize decoy
  elements with `{'MT_LV1_1': 'FILE='}`; or
* **a sentinel string** for observations with no identifiable target:

| Sentinel | Result |
| -------- | ------ |
| `ANTISOLAR_POINTING` | `[]` — pointing is the anti-solar point, no body |
| `SLEW_TEST` | `[]` — engineering slew with dummy elements |
| `TNO_SURVEY` | one placeholder body `"Survey HST-nnnnn"` (`ttype` `"T"`, `desig` `""`) |
| `UNDESIGNATED_TNO` | one placeholder body `"Unknown HST-nnnnn"` (`ttype` `"T"`, `desig` `""`) |

where `nnnnn` is the five-digit, zero-padded HST program ID from `TARG_ID`.
`TNO_SURVEY` marks blind Kuiper-belt searches with no specific target;
`UNDESIGNATED_TNO` marks real TNOs known only by a survey-internal name that
never received an MPC designation.

### 2–3. String collection and MT_LV parsing

`_collect_strings()` gathers every `TARKEY*` value, the `TARGNAME`, and each
semicolon-separated piece of the target description, dropping pieces that
merely repeat the category (`"SOLAR SYSTEM"`, the `TARGCAT` value).

A `TARGNAME` in `_NON_TARGET_TARGNAMES` (`ANY`, `BIAS`, `DARK`, `WAVE`, ...)
marks an internal calibration exposure or a placeholder. It identifies nothing
by itself, but the other keywords may still name a body; only if they don't is
the absence of a target treated as expected (empty list) rather than an error.

If `MT_LV2` is `TYPE=POS_ANGLE`-style geometry, or the `TARGNAME` contains
`OFFSET`, `BACKGROUND`, `SLEW`, or `DUMMY`, the pointing is offset from the
body: `RA_TARG`/`DEC_TARG` is not the body's position and all sky-position
tests are skipped.

### 4. Standard bodies from `STD` fields

`MT_LV2 STD=` names the body in the field of view; `MT_LV1 STD=` names the
body HST tracked. `_resolve_std()` looks the token up in
`STANDARD_BODY_LOOKUP` (see below). A token of the form `"N"`, `"N (NAME)"`,
or `"(N) NAME"` identifies a minor planet by number; the name alone is not
trusted, because satellites share names with asteroids (e.g. `"9 (METIS)"` is
the asteroid, not Jupiter's moon). Unresolvable `STD` values raise
`TargetIdentificationError`.

### 5. String repair: `hst_repairs()`

`hst_repairs(strings)` is the workhorse that turns raw HST strings into
canonical body identifiers. It returns `(answers, types)`: a list of repaired
identifier strings, plus a string of single-letter `TargetType` codes voted by
category words found along the way (e.g. `"KUIPER BELT OBJECT"` contributes
`"T"`).

The repair tables are applied repeatedly, in priority order, until nothing
changes; strings that resist repair whole are re-attempted with trailing and
leading words stripped one at a time (first space-separated, then
dash-separated). The tables, all curated by hand:

1. **Suffix patterns** (`_TARGNAME_SUFFIX_PATTERNS`) — instrument and pointing
   decorations after a dash (`-ACQ`, `-COPY`, `-EPOCH3`, `-HRC`, ...) are
   deleted and the remainder re-processed.
2. **Prefix patterns** (`_TARGNAME_PREFIX_PATTERNS`) — junk before a dash
   (`OBJ-`, `RD-`, ...).
3. **String repairs** (`_TARGET_STRING_REPAIRS`) — regex → replacement pairs
   for specific misspellings and idioms seen across programs (`SW3` →
   `73P/SCHWASSMANN_WACHMANN 3`, `SANTA` → `HAUMEA`, ...). In replacement
   templates, `|` splits the output into separate identifiers, `$` marks a
   part to re-process, `[X]` embeds a `TargetType` vote, and underscores stand
   in for dashes that must survive the dash-splitting pass.
4. **Transform patterns** (in `hst_repairs.py`) — general syntactic
   conversions: `COMET-98-P1` → `C/1998 P1`, packed MPC designations
   (`K14Od3S` → `2014 OS133` via `mpc_tools.mpc_unpack`), `MP-1234-NAME` →
   `(1234) NAME`, transposed designations, and more.
5. **Categorizer patterns** — words like `ASTEROID`, `KBO`, `CENTAUR`,
   `NUCLEUS` are consumed and converted to `TargetType` votes.
6. **Undiagnostic words** (`_UNDIAGNOSTIC_TARGET_WORDS`) — hundreds of words
   that never identify anything (`ACQ`, `AURORAL`, `ATMOSPHERE`, ...) are
   deleted.

### 6. Standard bodies by name

Each repaired answer is checked against `STANDARD_BODY_LOOKUP`
(`targets/standard_bodies.py`), built from the curated `_STANDARD_BODY_LIST`:
the planets, their satellites, the IAU dwarf planets, planetary systems,
rings, and the Io torus, each with an extensive set of lookup aliases
(`"J1"`, `"JUPITER I"`, `"S/2003 J 1"` variants, three-letter planet
abbreviations, ...). This is how a satellite observed against a tracked planet
gets identified.

### 7. Small-body identification

`identify_small_body(strings, elements)` (note: the *raw* strings — it runs
`hst_repairs` itself) dispatches between comet and minor-planet
identification:

* Names in `_DISALLOWED_MINOR_PLANET_NAMES` (`Io`, `Halley`, `Pan`, ...) are
  excluded from the minor-planet search unless the header explicitly marks the
  target as a minor planet — those names belong to satellites and comets
  first.
* `comet_identifiers()` and `minor_planet_identifiers()` score the strings
  against designation-shaped regexes, each yielding a 0–9 **confidence**
  (`"C/1995 O1"` scores 9 as a comet; a bare name scores 1). Whichever family
  scores higher is tried first; the other is tried if it fails.

**Comets** (`identify_comet`) are looked up in the local comet database
(`cometdb.query_comet_by_name`, built from five web sources into
`caches/COMET_CACHE/#COMETS.pickle`). An ambiguous name (`"MCNAUGHT"` matches
dozens of comets) is resolved by comparing the header elements against every
candidate (`query_comet_by_elements`). With no usable name at all, the whole
database is searched by elements; the best match is accepted only if its
residual beats the threshold *and* is less than half the runner-up's.

**Minor planets** (`identify_minor_planet`) are looked up at the Minor Planet
Center (`mpc_tools.mpc_query_by_name`, cached per object in
`caches/MPC_CACHE`). Multiple candidate bodies are resolved by element
residual, like comets.

The **element residual** (`mpc_tools.element_resid`) is the RMS of fractional
and near-fractional error terms between the header elements and a candidate's
catalog elements — semimajor axis (or perihelion distance) as a fraction, and
inclination/eccentricity as vector components combined with the node and the
longitude of perihelion. At least three comparable terms are required.

A high name confidence (> 5) can outvote a bad element residual: the
identification is kept `valid` with a logged warning, on the theory that a
cleanly-formatted designation is more trustworthy than decades-stale header
elements.

### 8. Confirmation against the header

Identification by name is only half the job; `identify_target` then confirms
the result against the header's own ephemeris:

* **Comets** (`MT_LV1 TYPE=COMET`): the element residual must fall within
  `comet_rms` (default 0.1). If the name resolved to the wrong comet — or to
  none — `_rescue_comet_by_elements()` searches for a comet matching *both*
  the elements and one of the name strings (this recovers, e.g., an old
  designation shared by two comets). Otherwise the mismatch raises
  `TargetIdentificationError`.

* **Minor planets** (`MT_LV1 TYPE=ASTEROID`): `_confirm_minor_planet()`
  propagates the body's catalog orbit to the observation midpoint
  (`orbital_radec.asteroid_radec`, with planetary perturbations and a two-body
  fallback) and compares the predicted position with `RA_TARG`/`DEC_TARG`.
  First, though, it checks that `RA_TARG` actually tracks the header's own
  elements (within `_SELF_CONSISTENCY_MAX` = 60″, distance-scaled); if not,
  the pointing is offset and the whole test is skipped.

  The tolerance is `min(max(base, 30″ × epoch-gap-years), 600″)`, scaled up by
  `1/delta` for bodies nearer than 1 AU — newly discovered TNOs drift tens of
  arcsec per year of gap between the catalog epoch and the observation, and a
  fixed orbit error subtends a larger angle close to Earth. When the body
  misses, the failure is resolved in order of preference:

  1. **Replacement**: a different body matching both the header elements and
     the sky position supersedes the named one (catches mislabeled
     `TARGNAME`s).
  2. **Revised orbit**: if the catalog orbit still broadly matches the header
     elements (rms ≤ 1.0), the miss is attributed to an orbit revision after
     the observation — common for single-opposition TNOs — and the body is
     accepted with a warning.
  3. Otherwise `TargetIdentificationError`.

### 9. Position-based fallback

When no name was recognized at all and `MT_LV1` carries elements (either
type — TNOs and Centaurs are often filed as comet elements),
`_identify_asteroid_by_position()` retrieves up to 25 MPC bodies with nearby
elements and picks the one closest to `RA_TARG`/`DEC_TARG` at the observation
midpoint. The winner must fall within 60″ (scaled as above) and beat the
runner-up by a factor of two.

### 10. Output normalization

Field-of-view bodies come first, the tracked body (if distinct) last;
duplicates are removed by minor-planet number or name. `_normalize_body()`
guarantees every dictionary has:

| Key | Contents |
| --- | -------- |
| `name` | Body name (may be `''`) |
| `full_name` | Display name, e.g. `"1P/Halley"`, `"136108 Haumea"` |
| `ttype` | Specific `TargetType` letter — never the generic `"M"` |
| `ttype_name` | e.g. `"comet"`, `"trans-neptunian_object"` |
| `naif_id` | NAIF integer ID, or None |
| `aliases` | Alternate designations |
| `parent_key` | Parent body for satellites/fragments, else `''` |
| `lid_suffix` | PDS4 LID tail, e.g. `"asteroid.253_mathilde"` |

Small bodies additionally carry their catalog identifiers (`mnum`, `desig`,
`alt_desigs`) and orbital elements (`A`, `Q`, `E`, `I`, `O`, `W`, and where
known `M`, `EPOCH`, `T`).

Generic minor planets are categorized by `minor_planet_ttype()`
(`targets/categorize_minor_planet.py`): IAU dwarf planets by fixed list, then
Centaurs by the Centaur database, then by elements (a ≥ 30.1 AU → TNO;
q > 5.2 AU with a < 30.1 AU → Centaur; else asteroid), then by the header's
type hints, defaulting to asteroid with a warning.

If nothing was identified and the `TARGNAME` was not a calibration
placeholder, `TargetIdentificationError` is raised.

## TargetType codes

From `targets/targettype.py`:

| Code | Name | | Code | Name |
| ---- | ---- |-| ---- | ---- |
| `A` | asteroid | | `P` | planet |
| `C` | comet | | `R` | ring |
| `D` | dwarf_planet | | `S` | satellite |
| `H` | centaur | | `T` | trans-neptunian_object |
| `t` | plasma_cloud (torus) | | `p` | planetary_system |

(`*` star, `a` astrophysical, and several calibration codes also exist.)
`M` is the generic "minor planet" placeholder used internally; it is always
resolved to `A`/`H`/`D`/`T` before a body is returned.

## Tunable thresholds

Per-call parameters of `identify_target`:

| Parameter | Default | Meaning |
| --------- | ------- | ------- |
| `comet_rms` | 0.1 | Max element residual for a comet identification |
| `mp_rms` | 0.08 | Max element residual for a minor-planet identification |
| `radec_tolerance` | 120″ | Base sky-position tolerance for a named minor planet |

Module constants in `identify_target.py`:

| Constant | Value | Meaning |
| -------- | ----- | ------- |
| `_RADEC_TOLERANCE_PER_YEAR` | 30″ | Tolerance growth per year of catalog-epoch gap |
| `_RADEC_TOLERANCE_MAX` | 600″ | Cap on the gap-scaled tolerance |
| `_FALLBACK_RADEC_TOLERANCE` | 60″ | Position tolerance for element-search-only IDs |
| `_FALLBACK_CANDIDATES` | 25 | MPC candidates tested in the position fallback |
| `_SELF_CONSISTENCY_MAX` | 60″ | Max RA_TARG offset from the header's own ephemeris |
| `_REVISED_ORBIT_RMS` | 1.0 | Element rms below which a position miss is forgiven |

## Logging

Every step reports its reasoning through the optional `logger` argument at
INFO level, with failures at ERROR. When investigating any identification,
always pass a logger — the narrative (recognized identifiers, candidate
residuals, sky offsets, tolerances) is the primary diagnostic tool. The
project convention is `pdslogger` (`rms-pdslogger`), e.g.
`pdslogger.EasyLogger()`, but any `logging.Logger` works.
