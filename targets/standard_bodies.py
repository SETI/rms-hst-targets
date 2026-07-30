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

* "name": Standard name with preferred capitalization, with no annotations. This is the
  key in STANDARD_BODY_DICT. For as-yet unnamed moons, it is the temporary designation.
* "full_name": Standard name including minor planet number if any, and can be more
  complicated for satellites. This is to be used as the body's `title` in the context
  product.
* "lid_name": The name as it will be adapted for the LID, including a parent and "." for
  satellites, rings, and the Io torus.
* "ttype": A TargetType letter indication the target type: "P" for planet, "S" for
  satellite, "D" for dwarf planet, "p" for planetary system, "R" for ring, or "t" for
  plasma cloud.
* "parent_key": The key ("name") of the parent body, if any. This identifies the central
  body for all satellites (e.g. "Pluto" for Charon) and is blank for other bodies.
* "satnum" (int): The satellite number if assigned.
* "mnum" (str): The minor planet number if any, converted to string.
* "aliases": A list of standard aliases for this body, using standard capitalization.
  Each of these is always a key in the STANDARD_BODY_LOOKUP.
* "naif_id": The NAIF body ID, if any.
* "lookups": A set of all possible lookups for this body. This includes the name,
  standard aliases, and any non-standard alternatives (e.g., "J1" for Io). Names appear
  in their standard case and also upper case.

To use::

    from targets.standard_bodies import STANDARD_BODY_DICT, STANDARD_BODY_LOOKUP

"""

from targets._STANDARD_BODY_LIST import _STANDARD_BODY_LIST
from targets.roman               import int_to_roman
from targets.targettype          import TargetType as TT

_NAME     = 0
_NUMBER   = 1
_NAIF_ID  = 2
_TTYPE    = 3
_PNAME    = 4
_ALIASES  = 5
_ALT_KEYS = 6

STANDARD_BODY_DICT = {}
STANDARD_BODY_LOOKUP = {}


_BY_NAME = {info[0]: info for info in _STANDARD_BODY_LIST}


def _name(info):
    """The name (primary key) of a standard body."""

    name = info[_NAME] or info[_ALIASES][0]

    # The provisional designation of a minor planet's moon embeds the primary's number,
    # e.g. "S/2015 $ 1" -> "S/2015 (136472) 1"
    if '$' in name:
        name = name.replace('$', f'({_BY_NAME[info[_PNAME]][_NUMBER]})')

    return name


def _full_name(info):
    """The full_name of a standard body."""

    # Treat Pluto like a planet here for backward compatibility
    if info[_PNAME] == 'Pluto':
        return _name(info)

    return _long_name(info)


def _long_name(info):
    """full_name, including the extended name for minor planet satellites, e.g.,
    "50000 Quaoar I (Weywot)"."""

    if info[_TTYPE] in TT.MCODES:
        return f'{info[_NUMBER]} {_name(info)}'

    if info[_TTYPE] == TT.SATELLITE:
        # An as-yet unnamed moon is known only by its designation, e.g. "S/2003 J 5"
        if not info[_NAME]:
            return _name(info)

        parent = _BY_NAME[info[_PNAME]]
        if parent[_TTYPE] == TT.PLANET:
            return info[_NAME]
        else:
            return f'{_full_name(parent)} {int_to_roman(info[_NUMBER])} ({info[_NAME]})'

    return _name(info)


def _lid_name(info):
    """The lid_name of a standard body."""

    if info[_TTYPE] == TT.SATELLITE:
        parent = _BY_NAME[info[_PNAME]]
        if info[_NAME]:
            return _full_name(parent) + '.' + info[_NAME]

        # An unnamed moon has slash stripped and maybe spaces
        if parent[_TTYPE] == TT.PLANET:
            squeezed = _name(info).replace('/', '').replace(' ', '')
        else:
            squeezed = _name(info).replace('/', '')
        return f'{_full_name(parent)}.{squeezed}'

    if info[_TTYPE] == TT.RING:
        parent = _BY_NAME[info[_PNAME]]
        return _full_name(parent) + '.Rings'

    if info[_TTYPE] == TT.TORUS:
        parent = _BY_NAME[info[_PNAME]]
        return _full_name(parent) + '.' + info[_NAME]

    return _full_name(info)


def _aliases(info):
    """The alias list of a standard body."""

    full_name = _full_name(info)
    aliases = [full_name, _name(info), _long_name(info)]
    # don't worry about duplicates for now

    if info[_TTYPE] in TT.MCODES:
        aliases += info[_ALIASES]
        num = info[_NUMBER]
        if num:
            # E.g., "(1) 1899 OF"
            aliases += [f'({num}) ' + a for a in info[_ALIASES]]

    elif info[_TTYPE] == TT.SATELLITE:
        pname = info[_PNAME]
        parent = _BY_NAME[pname]

        # The provisional designation of a named moon is still an alias, e.g. Callirrhoe
        # is "S/1999 J 1". A "$" designation belongs to the moon of a numbered primary and
        # is only usable once substituted, just below.
        aliases += [a for a in info[_ALIASES] if '$' not in a]

        if info[_NUMBER]:
            roman = int_to_roman(info[_NUMBER])
            # E.g., "50000 Quaoar I", "Quaoar II"
            aliases += [_full_name(parent) + ' ' + roman, pname + ' ' + roman]
            if parent[_NUMBER]:
                # E.g., "S/2006 (50000) 1", "S/2006 Quaoar 1"
                for sub in (f'({parent[_NUMBER]})', pname):
                    aliases += [a.replace('$', sub) for a in info[_ALIASES]]

    else:
        aliases += info[_ALIASES]

    aliases = [a for a in aliases if a != full_name]
    return _unique_strings(aliases)


def _lookups(body, info):
    """The alias list of a standard body."""

    lookups = {body['name'], body['full_name']} | set(body['aliases'])
    if len(info) > _ALT_KEYS:
        lookups |= set(info[_ALT_KEYS])

    # Add extra variations for moons of a planet
    if body['ttype'] == TT.SATELLITE:
        pname = info[_PNAME]
        parent = _BY_NAME[pname]
        satnum = body.get('satnum')
        extras = set()      # an unnumbered moon of a minor planet gets no extras

        if parent[_TTYPE] == TT.PLANET:
            if satnum:
                # Letter + number options, e.g. Europa = "J3" or "J III"
                extras |= {f'{pname[0]}{satnum}', f'{pname[0]} {int_to_roman(satnum)}'}

            # Allow every possible permutation of removed slashes and spaces, whether or
            # not the moon has since been named, e.g. Callirrhoe is also "S1999J1"
            for alias in info[_ALIASES]:
                if alias.startswith('S/'):
                    year = alias[2:6]
                    letter = alias[7]
                    num = alias[9:]
                    for p1 in ('S/', 'S'):
                        for p2 in (' ', ''):
                            for p3 in (' ', ''):
                                extras.add(p1 + year + p2 + letter + p3 + num)
        elif satnum:
            roman = int_to_roman(satnum)
            pnum = str(parent[_NUMBER])

            # E.g., "50000 Quaoar I", "50000 (Quaoar) I", "(50000) I",
            pnames = [f'{pnum} {pname}', f'{pnum} ({pname})', f'({pnum}) {pname}', pname]
            extras = {f'{p} {roman}' for p in pnames}

            # E.g., "S/2006 (50000) 1", "S/2006 Quaoar 1"
            for sub in (f'({pnum})', pname, f'({pname})'):
                extras |= {a.replace('$', sub) for a in info[_ALIASES]}

        lookups |= extras

    # Add three-letter abbreviations of the planets
    elif info[_TTYPE] == TT.PLANET:
        lookups.add(info[_NAME][:3].upper())

    # Add extra variations for minor planets
    if info[_TTYPE] in TT.MCODES:
        mnum = body['mnum']
        name = body['name']

        # Parentheses options for names, e.g., "(1)", "(1) Ceres", "1 (Ceres)"
        lookups |= {f'({mnum})', f'({mnum}) {name}', f'{mnum} ({name})'}

        # A bare number if it's > 3 digits
        if len(mnum) >= 4:
            lookups.add(mnum)

    lookups |= {key.upper() for key in lookups}
    return lookups


def _to_dict(info):
    """Convert one tuple in _STANDARD_BODY_LIST to a dictionary."""

    body = {'name'      : _name(info),
            'ttype'     : info[_TTYPE],
            'parent_key': info[_PNAME],
            'full_name' : _full_name(info),
            'lid_name'  : _lid_name(info),
            'aliases'   : _aliases(info)}

    if info[_NAIF_ID]:
        body['naif_id'] = info[_NAIF_ID]

    if info[_NUMBER]:
        if info[_TTYPE] == TT.SATELLITE:
            body['satnum'] = info[_NUMBER]
        else:
            body['mnum'] = str(info[_NUMBER])  # string format!

    body['lookups'] = _lookups(body, info)
    return body


def _build_dicts():
    """Convert the standard body list to dictionaries."""

    global STANDARD_BODY_DICT, STANDARD_BODY_LOOKUP

    STANDARD_BODY_DICT = {}
    for info in _STANDARD_BODY_LIST:
        body = _to_dict(info)
        STANDARD_BODY_DICT[body['name']] = body

    STANDARD_BODY_LOOKUP = {}
    for body in STANDARD_BODY_DICT.values():
        lookups = body['lookups']
        uppercase = {k.upper() for k in lookups}
        for lookup in lookups | uppercase:
            STANDARD_BODY_LOOKUP[lookup] = body


def _unique_strings(keys):
    """Remove duplicated items from the given list of strings."""
    unique_strings = []
    for key in keys:
        if key not in unique_strings:
            unique_strings.append(key)
    return unique_strings


# Execute at import
_build_dicts()

__all__ = ['STANDARD_BODY_DICT', 'STANDARD_BODY_LOOKUP']

##########################################################################################
