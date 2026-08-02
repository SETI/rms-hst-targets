##########################################################################################
# _NON_MINOR_PLANET_STRINGS.py
##########################################################################################
"""
==========================
_NON_MINOR_PLANET_STRINGS
==========================

This is a maintained set of strings that survive target-string repair looking like a
minor-planet name, but that the Minor Planet Center does not know and never will.

`minor_planet_identifiers()` drops them before querying the MPC. Without this, each one
costs a network round trip whose "not found" reply is then written into
``caches/MPC_CACHE`` (`mpc_query_by_name` caches the response before checking whether it is
valid), so the junk becomes permanent and is served from the cache forever after.

Every entry here was confirmed absent from the MPC database by an actual query -- the
cached reply is either its "Vaguely similar sounding possible matches" page or its "Exact
match ... not found" page. Membership is tested case-insensitively.

Why this is not just more entries in `_UNDIAGNOSTIC_TARGET_WORDS`
----------------------------------------------------------------

The two do different things, and the difference is **bare string versus embedded token**.
An undiagnostic word is *deleted from the target string* wherever it appears as a token,
including inside a longer name. A string listed here is only refused as a *whole* MPC
query; any longer string containing it is untouched.

That distinction is load-bearing. "MOUNTAIN" alone is not in the MPC, but "PURPLE MOUNTAIN"
is (3494) Purple Mountain -- which is why `hst_repairs` builds a name pattern that spans a
space. Deleting the word would reduce that target to "PURPLE" and identify nothing. The
same hazard applies to MAIN, FLAT, STAR and GALAXY, each of which could be one word of a
real name.

Two further rules keep this set small:

* If `hst_repairs` already deletes a word, it never reaches the MPC and does **not** belong
  here. Check with ``hst_repairs('WORD')`` before adding: an empty result means the word is
  handled already.
* A word consumed into a `TargetType` vote -- ASTEROID yields "A", KBO yields "T" -- must
  not be listed in either place, because suppressing it would discard the vote.

Do **not** add a misspelling or an alternative name of a real body (QUAUAR for Quaoar,
OUMUAMUA for 1I, XENA for Eris). Those belong in `_TARGET_STRING_REPAIRS`, which maps them
onto the identifier the MPC does recognize; listing them here would throw away an
identification that a repair could rescue.

Two-letter leftovers (BD, WR, HV, LR, SL, UB, ...) are **not** listed here. They are
rejected structurally instead, because no minor planet has a name shorter than three
letters; see `minor_planet_identifiers`.
"""

_NON_MINOR_PLANET_STRINGS = {

    # Observing conditions, calibration and instrument vocabulary that reached the MPC as
    # a bare word.
    'FLAT', 'PHOTOMETRIC',

    # Class and structure words. A target string reduced to one of these names no body.
    'GALAXY', 'MAIN', 'STAR', 'TRINARY',

    # Geometry words.
    'ANTISUN',

    # Catalog prefixes of three or more letters, left behind when the numeric part of a
    # star designation was split off (the two-letter prefixes are caught by the length
    # rule instead).
    'AGK', 'COL',

    # Spacecraft and mission names, which accompany a target without being one.
    'DART',
}

__all__ = ['_NON_MINOR_PLANET_STRINGS']

##########################################################################################
