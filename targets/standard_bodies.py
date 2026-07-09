##########################################################################################
# targets/standard_bodies.py
##########################################################################################
"""Define STANDARD_BODY_DICT and STANDARD_BODY_LOOKUP.

Read the complete list of standard body definitions in _STANDARD_BODY_LIST.py and create
two lookup dictionaries:

* STANDARD_BODY_DICT is a dictionary keyed by the default PDS4 name of the body, using
  standard capitalization.
* STANDARD_BODY_LOOKUP is keyed by almost every alternative name for each body, in both
  standard capitalization and upper case.

The entries in the table includes all standard bodies as defined for HST (planets, dwarf
planets, and their satellites), plus the planetary systems, ring (including "Mars Rings"),
and the Io torus.

Each dictionary value is a dictionary with these items:

* "name": Standard name with preferred capitalization.
* "ttype": A TargetType letter indication the target type: "P" for planet, "S" for
  satellite, "D" for dwarf planet, "p" for planetary system, "R" for ring, or "t" for
  plasma cloud.
* "parent_key": Key for the parent body, if any. This identifies the central body for all
  satellites, the "system" for the planets with multiple satellites, and is blank for
  other bodies.
* "aliases": A list of standard aliases for this body, using standard capitalization.
  Each of these is always a key in the STANDARD_BODY_LOOKUP.
* "naif_id": The NAIF body ID, if any.
* "lookups": A list of all possible lookups for this body. This includes the name,
  standard aliases, and any non-standard alternatives (e.g., "J1" for Io).
* "ambiguous": A list of potentially ambiguous names for the bodies. This list is always
  empty for the standard bodies.

To use::

    from targets.standard_bodies import STANDARD_BODY_DICT, STANDARD_BODY_LOOKUP

"""

from targets.roman import int_to_roman
from targets._STANDARD_BODY_LIST import _STANDARD_BODY_LIST

_NAME     = 0
_NUMBER   = 1
_NAIF_ID  = 2
_TTYPE    = 3
_PNAME    = 4
_ALIASES  = 5
_ALT_KEYS = 6

STANDARD_BODY_DICT = {}
STANDARD_BODY_LOOKUP = {}

def _replace_dollars():
    """Replace the dollar sign in each alias with the name of the parent body."""

    # Construct a dictionary
    lookup = {info[_NAME]: info for info in _STANDARD_BODY_LIST}

    # Update aliases
    for k, info in enumerate(_STANDARD_BODY_LIST):
        old_aliases = info[5]
        new_aliases = []
        changed = False
        for alias in old_aliases:
            if '$' in alias:
                pname = info[_PNAME]
                pnum = lookup[pname][_NUMBER]
                new_aliases += [alias.replace('$', f'({pnum})'),
                                alias.replace('$', f'{pname}')]
                changed = True
            else:
                new_aliases.append(alias)
        if changed:
            _STANDARD_BODY_LIST[k] = info[:_ALIASES] + (new_aliases,) + info[_ALT_KEYS:]

# Execute at import
_replace_dollars()


def _unique_keys(keys):
    """Remove duplicated items from the given list of keys."""
    unique_keys = []
    for key in keys:
        if key not in unique_keys:
            unique_keys.append(key)
    return unique_keys


_BY_NAME = {info[0]: info for info in _STANDARD_BODY_LIST}


def _to_dict(info):
    """Convert one tuple in _STANDARD_BODY_LIST to a dictionary."""

    parent_key = info[_PNAME]
    body = {'name': info[_NAME], 'ttype': info[_TTYPE], 'parent_key': parent_key}

    aliases = info[_ALIASES]
    if info[_NUMBER]:
        if info[_TTYPE] == 'S':
            aliases.append(info[_PNAME] + ' ' + int_to_roman(info[_NUMBER]))
        else:
            body['mnum'] = info[_NUMBER]
    body['aliases'] = _unique_keys(aliases)

    if info[_NAIF_ID]:
        body['naif_id'] = info[_NAIF_ID]

    lookups = [info[_NAME]] + list(aliases)
    if len(info) > _ALT_KEYS:
        lookups += info[_ALT_KEYS]

    if info[_TTYPE] == 'S' and info[_NUMBER] and _BY_NAME[parent_key][_TTYPE] == 'P':
        # Extra variations for moons of a planet
        extras = [parent_key[0] + ' ' + int_to_roman(info[_NUMBER]),
                  parent_key[0] + str(info[_NUMBER])]
        for lookup in lookups:
            if lookup.startswith('S/') and lookup[6] == ' ' and lookup[8] == ' ':
                year = lookup[2:6]
                letter = lookup[7]
                num = lookup[9:]
                for p1 in ('S/', 'S'):
                    for p2 in (' ', ''):
                        for p3 in (' ', ''):
                            extras.append(p1 + year + p2 + letter + p3 + num)
                    extras.append(p1 + year + ' ' + parent_key + ' ' + num)
        lookups += extras

    # Add three-letter abbreviations of the planets
    if info[_TTYPE] == 'P':
        lookups.append(info[_NAME][:3].upper())

    body['lookups'] = _unique_keys(lookups)
    body['ambiguous'] = []

    return body


def _build_dicts():
    """Convert the standard body list to dictionaries."""

    global STANDARD_BODY_DICT, STANDARD_BODY_LOOKUP

    STANDARD_BODY_DICT = {}
    for info in _STANDARD_BODY_LIST:
        body = _to_dict(info)
        STANDARD_BODY_DICT[info[_NAME]] = body

    STANDARD_BODY_LOOKUP = {}
    for key, body in STANDARD_BODY_DICT.items():
        lookups = body['lookups']
        uppercase = [k.upper() for k in lookups]
        lookups = lookups + uppercase
        for lookup in lookups:
            STANDARD_BODY_LOOKUP[lookup] = body


# Execute at import
_build_dicts()

__all__ = ['STANDARD_BODY_DICT', 'STANDARD_BODY_LOOKUP']

##########################################################################################
