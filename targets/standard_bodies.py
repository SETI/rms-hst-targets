##########################################################################################
# standard_bodies.py
##########################################################################################

from .roman import int_to_roman
from .STANDARD_BODY_LIST import *

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
    lookup = {info[_NAME]: info for info in STANDARD_BODY_LIST}

    # Update aliases
    for k, info in enumerate(STANDARD_BODY_LIST):
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
            STANDARD_BODY_LIST[k] = info[:_ALIASES] + (new_aliases,) + info[_ALT_KEYS:]

# Execute at import
_replace_dollars()


_BY_NAME = {info[0]: info for info in STANDARD_BODY_LIST}

def _to_dict(info):
    """Convert one tuple in STANDARD_BODY_LIST to a dictionary."""

    parent_key = info[_PNAME]
    body = {'name': info[_NAME], 'ttype': info[_TTYPE], 'parent_key': parent_key}

    aliases = info[_ALIASES]
    if info[_NUMBER]:
        if info[_TTYPE] == 'S':
            aliases.append(info[_PNAME] + ' ' + int_to_roman(info[_NUMBER]))
        else:
            body['mnum'] = info[_NUMBER]
    body['aliases'] = aliases

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

    body['lookups'] = lookups
    body['ambiguous'] = []

    return body


def _build_dicts():
    """Convert the standard body list to dictionaries."""

    global STANDARD_BODY_DICT, STANDARD_BODY_LOOKUP

    STANDARD_BODY_DICT = {}
    for info in STANDARD_BODY_LIST:
        body = _to_dict(info)
        STANDARD_BODY_DICT[info[_NAME]] = body

    STANDARD_BODY_LOOKUP = {}
    for key, body in STANDARD_BODY_DICT.items():
        lookups = body['lookups']
        uppercase = [k.upper() for k in lookups]
        lookups = lookups + uppercase
        print(lookups)
        for lookup in lookups:
            STANDARD_BODY_LOOKUP[lookup] = body

# Execute at import
_build_dicts()

##########################################################################################
