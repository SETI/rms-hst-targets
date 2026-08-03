# The `src/targets/programs/` scripts

`src/targets/programs/` holds the maintenance and diagnostic tools. They refresh the caches
the library reads, rebuild the test corpus, and help diagnose a specific
observation. Run them from the repository root with the virtual environment
active:

```bash
python -m targets.programs.identify_visit JCIS01
```

## Which of these you actually need

Most users need **none** of them. `identify_targets()` is the entry point of the
package, and nothing here is required to call it.

| Script | How often |
| ------ | --------- |
| `update_cometdb.py` | **Regularly** — the only two scripts in routine use |
| `update_target_xml_cache.py` | **Regularly** — likewise |
| `identify_visit.py` | Whenever a target identifies wrongly, or not at all |
| `reality_check_radec.py` | Rarely; a corpus-wide audit |
| `retrieve_mast_moving_target_spts.py` | Almost never; needs the external SSD |
| `build_spt_tests.py` | Almost never; needs the external SSD |

**The two `update_*` scripts are the only ones meant to be run on a schedule.**
They refresh this package's picture of the outside world: the comet database and
the PDS4 context products. Everything else is a diagnostic or a corpus-rebuild
tool.

Their output must be **committed to the repository to take effect anywhere
else.** Both write into `caches/`, which is version-controlled precisely so that
every installation resolves the same bodies without hitting the network. Running
an update locally and not committing it means your results silently differ from
everyone else's, and the next clone will not have the new bodies at all. Run the
script, read the diff, commit it.

`identify_visit.py` is the tool to reach for when something identifies wrongly
or not at all — it prints the whole decision narrative and is where nearly every
diagnosis starts. Expect to need it when new observations arrive with target
names the repair tables have not seen.

The remaining three exist for completeness and for rebuilding the test corpus
from scratch. A typical user will probably never run them; two require the SPT
cache on the external SSD.

Beyond that they fall into three groups: **diagnosis**, **data refresh** (when
the outside world changes), and **corpus rebuild** (rarely, and only with the
SPT cache mounted).

They are included in the wheel, so `python -m targets.programs.<name>` works from an
installed copy — but most of them expect a source checkout and will not find
what they need without one. `reality_check_radec.py` reads `tests/SPT_TESTS.py`,
which is not part of the package, as does `identify_visit.py` whenever it is
given a visit rather than a path;
`build_spt_tests.py` needs `caches/SPT_CACHE`; `update_cometdb.py` and
`update_target_xml_cache.py` write into `caches/`. Only
`retrieve_mast_moving_target_spts.py`, which takes its output directory as an
argument, is genuinely standalone. Treat the rest as repository tools that
happen to be installed alongside the library.

## Diagnosis

### `identify_visit.py` — run one visit and watch it think

The tool you will use most. It feeds headers to `identify_targets` and prints
the whole narrative, then the context products identified.

Each argument is either a **visit** from the test corpus or a **path**. A path
names an SPT/SHM/SHF/DMF FITS file, or a directory, which contributes every such
file at or below it — so it works on a directory of FITS files that were never
added to the corpus. The two kinds can be mixed in one command.

```bash
python -m targets.programs.identify_visit JCIS01
python -m targets.programs.identify_visit 'IENL0*' --by-visit     # wildcards allowed
python -m targets.programs.identify_visit U2G008 --level info     # less noise
python -m targets.programs.identify_visit IFFC01 --edit           # open the XML in $EDITOR
python -m targets.programs.identify_visit caches/SPT_CACHE/10102  # a whole directory
python -m targets.programs.identify_visit some/u8ta0101m_shm.fits # one file
python -m targets.programs.identify_visit JCIS01 /data/spt        # mixed
```

Headers are grouped by visit — the first six characters of the file's base name
— and each visit is identified separately, so one unidentifiable visit does not
abandon the rest; it prints a `****` line and the run continues. Unreadable
files are reported and skipped for the same reason. The context-product paths
printed at the end are deduplicated across everything identified.

**When:** whenever a target identifies wrongly or not at all, and after any
change to the repair tables or the categorization logic, to confirm the visits
you care about still work.

**Why:** the log names every string that was tried, what it resolved to, which
strings resolved to nothing, and which test confirmed or rejected each
candidate. Nearly every diagnosis in this project starts here.

New `_local` context products go to the gitignored
`caches/TARGET_XML_OVERLAY`, never the committed cache, so it is safe to run
repeatedly. The corpus is consulted only when a visit argument is given, so a
run over FITS-file paths alone needs neither `tests/SPT_TESTS.py` nor the SPT
cache.

### `reality_check_radec.py` — sanity-check the corpus pointing

Propagates the `MT_LV1_*` orbital elements of every asteroid and comet entry in
the corpus to the observing midpoint and compares the predicted sky position
against the header's `RA_TARG`/`DEC_TARG`.

```bash
python -m targets.programs.reality_check_radec               # both types
python -m targets.programs.reality_check_radec --comets      # comets only
python -m targets.programs.reality_check_radec -o /tmp/offsets.csv
```

It prints offset percentiles, a distribution histogram, and a table of the
worst offenders annotated with the likely cause — B1950 elements, a large
epoch gap, non-gravitational terms, or a dummy/slew target. The full table goes
to CSV.

**When:** after changing `orbital_radec.py`, or when you suspect the sky-position
confirmation is systematically too strict or too loose.

**Why:** it separates "our propagation is wrong" from "the header is wrong".
A correct entry should reproduce `RA_TARG` to about an arcsecond; the entries
that do not are nearly all explained by the annotations.

Requires `palpy`. It does not touch the network.

## Data refresh

### `update_cometdb.py` — rebuild the comet, Centaur and damocloid databases

Scrapes Wikipedia, the MPC, the SBN and JPL, and writes the three pickle
databases in `caches/COMET_CACHE`.

```bash
python -m targets.programs.update_cometdb                    # all three, checking the web
python -m targets.programs.update_cometdb --local            # rebuild from cached HTML only
python -m targets.programs.update_cometdb --comets           # just one database
python -m targets.programs.update_cometdb --rebuild          # rewrite even if unchanged
```

**When:** when a newly observed comet is missing from the database, when a
comet is renamed or renumbered, or periodically to pick up new discoveries.

**Why:** comet identification is driven entirely by these databases. If a comet
is not in them it cannot be found by name, and identification falls back to
element matching — which is where wrong answers come from.

`--local` rebuilds from the committed HTML in `caches/COMET_CACHE` without
contacting anything, which is what you want when you have edited a scraper or a
repair and only need to see the effect.

**Commit the result.** The pickles are build products and gitignored, but the
scraped HTML and CSV sources they are built from *are* committed, and those are
what a fresh clone regenerates from. A refresh that is not committed exists only
on your machine: other installations keep resolving the old set of comets, and a
new clone will not have the new ones at all. If a scraper gains a new source
file, `git add` it explicitly — an untracked source means nobody else can
rebuild.

The previous pickle is kept as `#COMETS_v001.pickle` and so on, so a bad
rebuild can be undone.

### `update_target_xml_cache.py` — sync the PDS4 context products

Compares `caches/TARGET_XML_CACHE` against the PDS Engineering Node, downloads
new context products, deletes superseded versions, and rebuilds the
`$LOOKUP.pickle` index.

```bash
python -m targets.programs.update_target_xml_cache
python -m targets.programs.update_target_xml_cache --offline   # just rebuild the index
python -m targets.programs.update_target_xml_cache --rebuild
```

**When:** when the Engineering Node publishes new or corrected targets, or
after hand-adding a `_local` product.

**Why:** `identify_targets` resolves each body to an existing context product
where one exists, and only generates a `_local` product when it must. A stale
cache means generating products that already exist under a different name.

**Commit the result.** `caches/TARGET_XML_CACHE`, including its
`$LOOKUP.pickle` index, is version-controlled so that every installation
resolves bodies to the same products offline. An uncommitted sync means your
runs generate `_local` products for bodies that other installations resolve to
published ones, and vice versa. Read the diff before committing: it should be
new and superseded products, nothing else.

To add or correct a product by hand, create the file with `_local` before
`.xml`. Local files are preserved until an official file of the same name and
version appears at the Engineering Node.

### `retrieve_mast_moving_target_spts.py` — download the SPT corpus from MAST

Queries MAST for every HST observation flagged as a moving target, keeps the
`_spt` / `_shm` / `_shf` / `_dmf` support files, writes a manifest, and
downloads them into per-program folders.

```bash
python -m targets.programs.retrieve_mast_moving_target_spts --outdir /Volumes/Data-SSD/SPT_CACHE
python -m targets.programs.retrieve_mast_moving_target_spts --manifest-only
```

**When:** rarely — to build the SPT cache from scratch, or to pick up
observations taken since the last retrieval.

**Why:** everything downstream derives from these files. They are the raw
evidence.

This is a large download across 845 programs, which is why the cache lives on
an external SSD and is gitignored. Downloads are resumable: a file already
present at the expected size is skipped, so re-running fills only the gaps.
Use `--manifest-only` first to see the size before committing to it.

## Corpus rebuild

### `build_spt_tests.py` — regenerate `tests/SPT_TESTS.py`

Reads every FITS file in `caches/SPT_CACHE`, extracts the target-description
keywords, deduplicates, and writes the corpus module keyed by six-character
visit.

```bash
python -m targets.programs.build_spt_tests
python -m targets.programs.build_spt_tests --limit 500        # a quick partial run
```

**When:** after retrieving new SPT files, and only then.

**Why:** `tests/SPT_TESTS.py` is the evidence base for the entire test suite
and for `SPT_TESTS_OUTPUT.txt`. Every visit-driven test reads from it.

**Requires `caches/SPT_CACHE`**, which is a symlink to an external SSD and is
gitignored. Without that volume mounted the script cannot run — but nothing
else needs it, because the corpus it produces is committed.

Regenerating the corpus will change `tests/SPT_TESTS.py` wholesale. Expect the
baseline `tests/SPT_TESTS_OUTPUT.txt` to need regenerating too:

```bash
python tests/test_hst_repairs_output.py
```

Review that diff carefully rather than accepting it — it is the main safety net
against a repair change quietly breaking unrelated targets.
