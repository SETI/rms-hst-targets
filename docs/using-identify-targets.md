# Using `identify_targets`

This is the user's guide to the two entry points of the `targets` package. For
the internals — how a raw `TARGNAME` becomes a body — see
[How target identification works](how-it-works.md). For what to do when a real
observation refuses to identify, see
[Handling identification failures](handling-identification-failures.md).

## The two entry points

Both take the same arguments and differ only in what they hand back.

```python
identify_targets(headers, *, comet_rms=0.1, mp_rms=0.08,
                 radec_delta=120.0, logger=None) -> list[pathlib.Path]

identify_target_dicts(headers, *, comet_rms=0.1, mp_rms=0.08,
                      radec_delta=120.0, logger=None) -> list[dict]
```

`identify_target_dicts` does the identification and returns one dictionary per
body. `identify_targets` calls it, then completes each dictionary and resolves
it to a PDS4 Target context product, returning the file paths. Use the dict
form when you want to inspect or post-process the bodies; use the path form
when you are generating a PDS4 bundle.

Import either from the package root:

```python
from targets import identify_targets, identify_target_dicts
```

## Input: the headers of one visit

`headers` is a **list** of header objects for a **single HST visit**. Each may
be a plain `dict` or an `astropy.io.fits.Header`; both are read the same way.

```python
from astropy.io import fits

paths = []
with fits.open('u6ht4501m_shm.fits') as hdul:
    paths = identify_targets([hdul[0].header])
```

Passing headers from more than one visit raises `ValueError`. A visit is
identified by the first six characters of `FILENAME`, so all the headers in one
call must agree on that prefix. Group them first if you are walking a directory:

```python
import collections

by_visit = collections.defaultdict(list)
for header in all_headers:
    by_visit[header['FILENAME'][:6].upper()].append(header)

for visit, headers in by_visit.items():
    paths = identify_targets(headers)
```

Give the function **every** header of the visit rather than one at a time. A
target is often named in one exposure's keywords and confirmed by another's
orbital elements, and co-observed bodies (a comet passing a planet, a satellite
against its primary) only emerge when the visit is considered as a whole.
Duplicate headers are harmless — identical target descriptions are collapsed
before any work is done.

The keywords that matter are `TARGNAME`, `TARDESCR`, `TARKEY1`–`TARKEY9`,
`TARGCAT`, the `MT_LV1_*`/`MT_LV2_*` ephemeris fields, `RA_TARG`/`DEC_TARG`,
`PSTRTIME`/`PSTPTIME`, `PROPOSID` and `TARG_ID`. Anything else is ignored.

## Output: body dictionaries

Every dictionary carries at least `name`, `full_name`, `ttype` and `naif_id`;
the rest depend on what kind of body it is.

| Key | Meaning |
| --- | ------- |
| `name` | Bare name, e.g. `'Io'`, `'Clete'`. Empty for an unnamed minor planet |
| `full_name` | Preferred display name, e.g. `'385695 Clete'`, `'73P/Schwassmann-Wachmann 3-C'` |
| `ttype` | One-letter `TargetType` code — see below |
| `naif_id` | NAIF integer ID, or `None` |
| `aliases` | Other names and designations for the same body |
| `lookups` | Every string that resolves to this body |
| `desig`, `mnum`, `alt_desigs` | Minor planets: designation, number, alternates |
| `parent_key` | Satellites and rings: the primary, e.g. `'Jupiter'` |
| `A`, `Q`, `E`, `I`, `O`, `W`, `M`, `T`, `EPOCH` | Small bodies: orbital elements |

The `ttype` codes are defined in `targets.targettype.TargetType`. The ones you
will meet most often are `P` planet, `S` satellite, `R` ring, `C` comet,
`A` asteroid, `H` Centaur, `T` trans-Neptunian object, `D` dwarf planet, and
`M` minor planet not yet refined into `A`/`H`/`T`/`D`.

```python
for body in identify_target_dicts(headers):
    print(body['full_name'], body['ttype'])
# (523955) 1998 UU43 T
```

`identify_targets` completes each dictionary before resolving it, adding
`title`, `alt_titles`, `description`, `type_name`, `lid` and `lid_tail`. Those
keys are what the context product is built from; they are not present on the
dictionaries returned by `identify_target_dicts`.

## Output: context-product paths

`identify_targets` returns `pathlib.Path` objects. A path may point into the
committed mirror `caches/TARGET_XML_CACHE`, or — when the body is new, or the
existing product needs a correction — into the writable overlay
`caches/TARGET_XML_OVERLAY`, with `_local` in the filename.

If you do not want the run to write anything into the overlay, wrap it:

```python
import pathlib, tempfile
from targets.target_xml_cache_support import use_local_xml_dir

with tempfile.TemporaryDirectory() as tmp:
    with use_local_xml_dir(pathlib.Path(tmp)):
        paths = identify_targets(headers)
```

This is what the test suite does, and it is the right thing for exploratory
runs. The committed `TARGET_XML_CACHE` is a read-only Engineering Node mirror
and must never be modified directly.

## Watching it work

Pass a `Logger` — either a standard `logging.Logger` or a `pdslogger.PdsLogger`
— to see how each decision was reached. This is by far the fastest way to
understand a surprising result.

```python
import pdslogger

logger = pdslogger.PdsLogger('identify', lognames=False, timestamps=False)
logger.add_handler(pdslogger.STDOUT_HANDLER)

identify_targets(headers, logger=logger)
```

```text
INFO | Repairing: ['ASTEROID', 'KBO', '98UU43', 'ASTEROID', 'KBO']
INFO | Repaired: ['1998 UU43'], "AATT"
INFO | Minor planet identified: "(523955) 1998 UU43"
INFO | "(523955) 1998 UU43" is a TNO (a = 36.27 AU)
INFO | "(523955) 1998 UU43" elements confirmed; RMS 0.010 <= 0.08
```

The narrative names the strings that were tried, the body each one resolved to,
the strings that resolved to nothing ("Unused ... strings"), and the test that
finally confirmed or rejected each candidate. `programs/identify_visit.py` is a
ready-made wrapper for exactly this, over the corpus in `tests/SPT_TESTS.py`.

## The tuning parameters

You will rarely change these, but they decide how strict confirmation is.

**`comet_rms`** (default `0.1`) — the largest element residual at which a comet
is accepted. The residual is the RMS of fractional differences between the
header's orbital elements and the catalog's. Raise it to accept looser matches;
lower it to demand near-exact agreement.

**`mp_rms`** (default `0.08`) — the same threshold for minor planets.

**`radec_delta`** (default `120.0`, arcsec) — the base tolerance on the
distance between a minor planet's propagated sky position and
`RA_TARG`/`DEC_TARG`. The effective tolerance grows with the gap between the
catalog epoch and the observation, at 30 arcsec per year, capped at 600 arcsec,
because an orbit determined decades later will not reproduce the ephemeris HST
actually pointed with.

A caution learned from a real misidentification: a permissive threshold plus a
name that resolves to nothing can produce a confident wrong answer. Loosening
`comet_rms` makes the element test accept more distant candidates, and if no
name was recognized there is nothing else to arbitrate. Tighten rather than
loosen when a result looks suspicious.

## When it fails

`TargetIdentificationFailure` is raised when no target can be identified. Its
message names the file and the strings involved:

```python
from targets import TargetIdentificationFailure

try:
    paths = identify_targets(headers)
except TargetIdentificationFailure as err:
    print(f'no target: {err}')
```

Some failures are correct and expected — anti-solar pointings, slew tests,
internal calibration exposures and dark frames have no celestial target at all.
The exception is the intended outcome for those, not a bug.

`TargetCategorizationFailure` is the narrower case where a minor planet was
identified but could not be refined into asteroid / Centaur / TNO, because its
orbital elements are ambiguous and the SPT file's own type hints contradict each
other.

For anything else, [Handling identification
failures](handling-identification-failures.md) is the diagnostic guide, and
[The curated data tables](data-tables.md) covers the override mechanisms
available to fix a specific observation.

## Offline operation

Identification consults the local comet database and the Minor Planet Center.
The comet, Centaur and damocloid databases are built from the committed caches
in `caches/COMET_CACHE`, and are regenerated automatically if missing. MPC
lookups are cached per object in `caches/MPC_CACHE`.

A body that has never been queried requires network access. Everything already
in the corpus resolves offline, which is why the test suite can block
`requests` outright. If you are processing new observations, expect MPC traffic
the first time each unfamiliar body appears, and expect it to be cached
thereafter.
