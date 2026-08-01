# The `src/targets/programs/` scripts

`src/targets/programs/` holds the maintenance and diagnostic tools. They refresh the caches
the library reads, rebuild the test corpus, and help diagnose a specific
observation. Run them from the repository root with the virtual environment
active:

```bash
python -m targets.programs.identify_visit JCIS01
```

They fall into three groups: **diagnosis** (run these often), **data refresh**
(run these when the outside world changes), and **corpus rebuild** (run these
rarely, and only with the SPT cache mounted).

They are included in the wheel, so `python -m targets.programs.<name>` works from an
installed copy — but most of them expect a source checkout and will not find
what they need without one. `identify_visit.py` and `reality_check_radec.py`
read `tests/SPT_TESTS.py`, which is not part of the package;
`build_spt_tests.py` needs `caches/SPT_CACHE`; `update_cometdb.py` and
`update_target_xml_cache.py` write into `caches/`. Only
`retrieve_mast_moving_target_spts.py`, which takes its output directory as an
argument, is genuinely standalone. Treat the rest as repository tools that
happen to be installed alongside the library.

## Diagnosis

### `identify_visit.py` — run one visit and watch it think

The tool you will use most. It feeds a visit's headers from the test corpus to
`identify_targets` and prints the whole narrative, then the context products
identified.

```bash
python -m targets.programs.identify_visit JCIS01
python -m targets.programs.identify_visit 'IENL0*' --by-visit     # wildcards allowed
python -m targets.programs.identify_visit U2G008 --level info     # less noise
python -m targets.programs.identify_visit IFFC01 --edit           # open the XML in $EDITOR
```

**When:** whenever a target identifies wrongly or not at all, and after any
change to the repair tables or the categorization logic, to confirm the visits
you care about still work.

**Why:** the log names every string that was tried, what it resolved to, which
strings resolved to nothing, and which test confirmed or rejected each
candidate. Nearly every diagnosis in this project starts here.

New `_local` context products go to the gitignored
`caches/TARGET_XML_OVERLAY`, never the committed cache, so it is safe to run
repeatedly. It needs only `tests/SPT_TESTS.py`, not the SPT cache.

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
repair and only need to see the effect. Note that the pickles themselves are
**not** committed; they are build products, regenerated automatically the first
time the library needs them.

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
