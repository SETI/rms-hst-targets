# Using `identify_targets`

`identify_targets()` is the entry point of this package. It is the one function
a caller needs, and it is how the RMS Node's **`rms-hst-pipeline`** obtains the
PDS4 target context products for every HST observation it archives — this
package exists to serve that pipeline, and target identification is one of its
core stages.

For the internals — how a raw `TARGNAME` becomes a body — see
[How target identification works](how-it-works.md). For what to do when a real
observation refuses to identify, see
[Handling identification failures](handling-identification-failures.md).

## The entry point

```python
from targets import identify_targets

identify_targets(headers, *, comet_rms=0.1, mp_rms=0.08,
                 radec_delta=120.0, logger=None) -> list[pathlib.Path]
```

Give it SPT/SHF headers, get back the path of one PDS4 Target context product
per identified body. That is the whole interface. A pipeline stage needs
nothing else.

`identify_target_dicts()` sits underneath it and returns the body dictionaries
instead of paths. It is public, and useful when you want to inspect a body
rather than archive it, but it is a lower-level view: it handles exactly one
visit and it does not produce context products. Prefer `identify_targets()`
unless you specifically need the dictionaries.

## Input: SPT/SHF headers

`headers` is a **list** of header objects. Each may be a plain `dict` or an
`astropy.io.fits.Header`; both are read the same way.

```python
from astropy.io import fits
from targets import identify_targets

with fits.open('u6ht4501m_shm.fits') as hdul:
    paths = identify_targets([hdul[0].header])
```

The headers may span **any number of visits**. `identify_targets()` groups them
by visit — the first six characters of `FILENAME` — and identifies each visit
independently, so a whole directory can be handed over in one call:

```python
paths = identify_targets(every_header_in_the_directory)
```

The results are concatenated in visit order, and a target common to several
visits appears once per visit, so deduplicate if you want a unique set. Note
that a failure in any one visit abandons the rest; see
[When it fails](#when-it-fails) for how to isolate them.

`identify_target_dicts()` does **not** do this. It handles a single visit and
raises `ValueError` on headers spanning more than one.

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

`identify_targets` returns `pathlib.Path` objects, one per identified body,
each pointing at a PDS4 Target context product. A path leads either into the
committed mirror `caches/TARGET_XML_CACHE` or into the writable overlay
`caches/TARGET_XML_OVERLAY`, where the filename carries a `_local` suffix.

### What a `_local` file is, and when one appears

`caches/TARGET_XML_CACHE` is a read-only mirror of the products published by the
PDS Engineering Node. When identification produces a body the mirror cannot
serve as-is, the package writes its own product rather than modifying the
mirror. That file is a `_local` file, and it is generated in exactly two
circumstances:

1. **The body has no context product at all.** No published product matches the
   body's logical identifier, so a new one is written as
   `<lid_tail>_1.0_local.xml` — version 1.0, because nothing preceded it. Newly
   designated comets and TNOs are the usual cause, along with targets the
   Engineering Node has not yet published.

2. **A published product exists but is out of date.** The identification carries
   information the published product lacks — a corrected title, a refined body
   type, or aliases that would let a future observation resolve by a name the
   product does not currently list. The existing version is copied, amended, and
   written with the version incremented by 0.1 and the suffix appended, e.g.
   `..._1.2_local.xml` beside a published `..._1.1.xml`. If nothing needs
   changing, no file is written and the path of the published product is
   returned unchanged.

A `_local` file is a complete, valid `Product_Context` label, not a fragment.
It carries the logical identifier, the version, the title, the alias list, the
`Target` name/type/description, and a `Modification_History` in which a new
`Modification_Detail` records what this package changed while every earlier
entry is preserved:

```xml
<logical_identifier>urn:nasa:pds:context:target:centaur.144908_2004_yh32</logical_identifier>
<version_id>1.2</version_id>
<title>(144908) 2004 YH32</title>
...
<Modification_Detail>
  <modification_date>2026-07-31</modification_date>
  <version_id>1.2</version_id>
  <description>
    Updated by the RMS Node's HST pipeline: revised type (was "Centaur").
    Note that the logical_identifier has not been modified.
  </description>
</Modification_Detail>
```

The logical identifier is deliberately **not** changed when a name is corrected,
because the LID is what everything else references; the mismatch is recorded in
the description instead.

Reads resolve overlay-first, so once a `_local` file exists it is what later
runs get. The overlay is gitignored: `_local` products are working output, and
promoting one into the published set is an Engineering Node action, not
something this package does.

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
finally confirmed or rejected each candidate. `src/targets/programs/identify_visit.py` is a
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
message names the file and the strings involved. Because one bad visit ends the
whole call, process visit by visit when you are working through many:

```python
import collections
from targets import identify_targets, TargetIdentificationFailure

by_visit = collections.defaultdict(list)
for header in all_headers:
    by_visit[header['FILENAME'][:6].upper()].append(header)

for visit, headers in by_visit.items():
    try:
        paths = identify_targets(headers)
    except TargetIdentificationFailure as err:
        print(f'{visit}: {type(err).__name__}: {err}')
```

`NotPlanetaryError` is a **subclass**, so the code above catches it too. It
means something more specific: the visit is not a planetary observation at all,
so there is nothing here to archive, as opposed to "we could not work out what
this is". Instrument calibration programs pointed at a star are the usual case.
A visit is accepted as planetary if any of its headers tracks a moving target,
declares `TARGCAT` `SOLAR SYSTEM`, or was taken with FGS or HSP — the
occultation instruments, whose targets are the occulted stars rather than the
body. Catch it by name if you want to treat "nothing to archive" differently
from a genuine failure.

Other failures are correct and expected too — anti-solar pointings, slew tests,
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
