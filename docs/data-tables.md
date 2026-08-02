# The curated data tables

Seven modules in this project are named in `SCREAMING_SNAKE_CASE` rather than
the usual lowercase. The naming is deliberate: it marks them as **hand-curated
data**, not logic. They contain no algorithms — only tables that encode
knowledge about thirty-five years of HST target descriptions that could not be
derived from anything else.

They are the places you edit when identification gets something wrong for a
specific observation, so `ruff`'s module-naming rule (`N999`) is disabled
globally to keep them visibly distinct in a file listing.

| Module | Controls |
| ------ | -------- |
| `_STANDARD_BODY_LIST.py` | The planets, satellites, rings, dwarf planets and the Io torus |
| `_HST_PROGRAM_OVERRIDES.py` | Per-observation corrections and additions, keyed by `TARG_ID` |
| `_TARGET_STRING_REPAIRS.py` | Misspellings and abbreviations of specific bodies |
| `_UNDIAGNOSTIC_TARGET_WORDS.py` | Words that carry no target information and are deleted |
| `_TARGNAME_PREFIX_SUFFIX_PATTERNS.py` | Prefixes/suffixes stripped before anything else |
| `_DISALLOWED_MINOR_PLANET_NAMES.py` | Names shared by a satellite/comet and a minor planet |
| `_NON_MINOR_PLANET_STRINGS.py` | Strings never sent to the MPC, because it will never know them |
| `cometdb/_REPAIR_COMET.py` | Corrections to records scraped from the comet sources |

The first seven are read by `hst_repairs()` and the identification pipeline. The
eighth is applied when the comet database is rebuilt.

---

## `_STANDARD_BODY_LIST.py`

The definitive list of non-small-body targets: every planet, satellite,
planetary system, ring system and the Io torus, each as a tuple of name,
number, NAIF ID, target type, parent, and aliases.

**Edit when:** a newly named or newly discovered satellite is observed, a body
is renamed, or a NAIF ID is wrong. Also when a body needs an alias HST
proposers actually use that is not already listed.

**Watch for:** the aliases carry most of the weight. A satellite is usually
named in a header by something other than its formal name — `S/2003 U 1`,
`Uranus XXVI`, `U26` all mean Mab — and every such spelling has to be here or
the body will not be recognized.

## `_HST_PROGRAM_OVERRIDES.py`

Per-observation corrections, keyed by `TARG_ID` such as `"13936_1"`, or by
program with a wildcard, `"13936_*"`. The value is a dictionary whose entries
replace or supplement the SPT header's own. Beyond plain keyword replacement it
supports `"dict"` (describe an additional body outright) and `"addition"` (add a
named body to every observation of a program).

**Edit when:** a single observation or a whole program is wrong in a way no
general rule can fix — a proposer's private nickname, a mistyped element, a
co-observed body that appears in no keyword. Program 5642, the Shoemaker-Levy 9
Jupiter impact campaign, uses `"addition"` to attach the comet to every visit.

**Watch for:** this is the mechanism of last resort. It is exact and it does not
generalize, so prefer a repair pattern whenever the problem could recur. An
override that duplicates what a general rule already does is dead weight nobody
will dare delete later.

## `_TARGET_STRING_REPAIRS.py`

Patterns that convert a specific non-standard identification into a standard
one: `CG` and `CHURYUMOV-GERASIMENK` to `67P/Churyumov-Gerasimenko`, `SW3C` to
`73P/Schwassmann-Wachmann 3-C`, `KAGARA` to minor planet `(469705)`.

**Edit when:** a body is consistently written in a form no catalog recognizes.

**Watch for two traps**, both of which have produced real bugs:

*Anchoring.* Every pattern here is compiled with a trailing `$`, so it must
match to the end of the string. The generic comet-number pattern in
`hst_repairs.py` may fire first and append a type marker such as `|[C]`, after
which an anchored pattern can no longer match. If a repair mysteriously never
fires, this is usually why. The fix is to have the entry accept the numbered
form itself and supply the `/` and the `[C]` marker, as the Churyumov-Gerasimenko
and Schwassmann-Wachmann entries do.

*Ambiguity.* Expanding an abbreviation to a bare surname can make things worse.
A bare `SL` expanded to `SHOEMAKER_LEVY` matches thirteen comets, identifying
none of them, and was removed for that reason. Map to something that resolves —
a designation or a minor planet number — or leave the string alone.

## `_UNDIAGNOSTIC_TARGET_WORDS.py`

Roughly 400 regular expressions for words that appear in target descriptions
but say nothing about which body was observed: `BRIGHT`, `LIMB`, `MOSAIC`,
`OCCULTATION`, `TRAILING`, instrument names, filter names.

**Edit when:** a leftover word is reported as an unused string, or worse,
resolves to an unintended body. Adding it here removes it from consideration.

**Watch for:** the truncation of `TARDESCR` at the SPT keyword length produces
word fragments. `Rosetta` arrives as `Rose`, so the entry is `ROSE(TTA)?`.
Check whether the word you are adding also appears truncated. Conversely, be
careful that a word you delete is never part of a real name — `FIELD` was
removed from this list and had to be restored.

## `_TARGNAME_PREFIX_SUFFIX_PATTERNS.py`

Prefixes and suffixes stripped from a `TARGNAME` before any other pattern runs:
pointing qualifiers, visit indices, detector names, `-BACKGROUND`, `-OFFSET`.

**Edit when:** a `TARGNAME` differs from a recognizable name only by a decorative
prefix or suffix.

**Watch for:** these run *first*, so they are blunt. A suffix stripped too
eagerly can remove a fragment letter or a comet number that mattered.

## `_DISALLOWED_MINOR_PLANET_NAMES.py`

Names belonging to both a satellite or comet and a minor planet — `Io`,
`Halley`, `Pan`, `Metis`. These always resolve to the satellite or comet unless
the header explicitly says minor planet.

**Edit when:** a newly named minor planet collides with a satellite or comet name
and the wrong one is being chosen.

**Watch for:** the asymmetry is deliberate. HST observes the satellite far more
often than the asteroid of the same name, so the satellite is the safer default;
`9 Metis` is still reachable when the header says `ASTEROID`.

## `_NON_MINOR_PLANET_STRINGS.py`

Strings that survive repair looking like a minor-planet name but that the Minor
Planet Center does not know — observing vocabulary (`FLAT`, `PHOTOMETRIC`), class
words (`STAR`, `GALAXY`), catalog prefixes (`AGK`, `COL`) and mission names
(`DART`). `minor_planet_identifiers()` drops them before querying.

This matters more than a wasted round trip. `mpc_query_by_name()` writes the MPC
reply into `caches/MPC_CACHE` *before* checking whether it is valid, so every
impossible query leaves a permanent "not found" page that is then served from the
cache forever.

**Why not just more `_UNDIAGNOSTIC_TARGET_WORDS`?** Because the two differ in
*bare string vs. embedded token*. An undiagnostic word is deleted from the target
string wherever it appears, including inside a longer name; a string listed here
is only refused as a whole MPC query. `MOUNTAIN` alone is not in the MPC, but
`PURPLE MOUNTAIN` is (3494) Purple Mountain — deleting the word would reduce that
target to `PURPLE` and identify nothing. The same applies to `MAIN`, `FLAT`,
`STAR` and `GALAXY`.

Alongside it, `minor_planet_identifiers` rejects any purely alphabetic string of
one or two letters. No minor planet has a name that short — the shortest are
`Ate`, `Ida` and `Oda` — so these are always leftovers: half of a split
designation (`1977 UB` → `UB`), a two-letter star-catalog prefix (`BD`, `WR`,
`HV`), or an aperture code.

**Edit when:** a junk `.html` file appears in `caches/MPC_CACHE` for a word that is
plainly not a body. Confirm the MPC really does not know it — the cached page will
say "Vaguely similar sounding" or "Exact match … not found" — then check
`hst_repairs('WORD')` first. An empty result means the repairs already delete the
word and it never reaches the MPC, so it does not belong here. A word consumed
into a `TargetType` vote (`ASTEROID` → `A`, `KBO` → `T`) belongs in neither table:
suppressing it would discard the vote.

**Watch for:** do *not* add a misspelling or alternative name of a real body
(`QUAUAR` for Quaoar, `OUMUAMUA` for 1I, `XENA` for Eris). Those belong in
`_TARGET_STRING_REPAIRS`, which maps them onto an identifier the MPC recognizes;
listing them here throws away an identification a repair could rescue.

## `cometdb/_REPAIR_COMET.py`

Unlike the others this is a function, applied to each comet record as the
database is built, correcting known errors in the online sources before they
reach the database.

**Edit when:** a source publishes a record that is wrong or inconsistent —
a fragment designation attached to the wrong comet, a missing alias, a
designation that belongs to the parent rather than the fragment.

**Watch for:** these corrections only take effect when the database is rebuilt
(`python -m targets.programs.update_cometdb`). Editing this file changes nothing until
then. It is also the least-tested file in the project, so verify the effect by
querying the rebuilt database directly rather than assuming.

---

## The caps-named files in `tests/`

Two more files use the same convention for the same reason — they are data, not
code, and pytest does not collect them.

**`tests/SPT_TESTS.py`** is the corpus: every unique target description
harvested from the SPT cache, keyed by six-character visit. It is the evidence
base for the whole test suite. Regenerate with
`python -m targets.programs.build_spt_tests`, which needs the external SPT cache
mounted.

**`tests/SPT_TESTS_OUTPUT.txt`** is the baseline: the exact output of
`hst_repairs()` for all 8557 corpus entries. `test_hst_repairs_matches_baseline`
compares against it, so any change to a repair table shows up as a diff.

Regenerate it with:

```bash
python tests/test_hst_repairs_output.py
```

**Read that diff before accepting it.** It is the main protection against a
repair change quietly breaking unrelated targets, and it has caught real
regressions repeatedly — a tightened pattern that stopped recognizing
low-numbered minor planets, a word removal that lost a satellite. A diff of a
few lines you can explain is fine; a diff of hundreds you have not read is how a
regression gets committed.
