##########################################################################################
# targets/mpc_tools/_utils.py
##########################################################################################

import pathlib

from targets._DISALLOWED_MINOR_PLANET_NAMES import _DISALLOWED_MINOR_PLANET_NAMES
from targets.targettype import TargetType

_MPC_CACHE = pathlib.Path(__file__).parent.parent.parent / 'caches/MPC_CACHE'
_MPC_CACHING = True

_MPC_BY_NAME = 'https://minorplanetcenter.net/db_search/show_object?object_id='
_MPC_BY_PROPERTIES = 'https://www.minorplanetcenter.net/db_search/show_by_properties?'

_MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
           'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']


def _mpc_date_to_str(text):
    """Convert an MPC date of the form "YYYY-MM-DD.ddddd" to "DD-MON-YYYY:hh:mm:ss"."""

    year, month, day = text.strip().split('-')
    dd = int(float(day))
    secs = min(round((float(day) - dd) * 86400.), 86399)
    hh, remainder = divmod(secs, 3600)
    mm, ss = divmod(remainder, 60)
    return (f'{dd:02d}-{_MONTHS[int(month) - 1]}-{int(year):04d}:'
            f'{hh:02d}:{mm:02d}:{ss:02d}')


def _mpc_body_dict(aliases, elements):
    """Get aliases and orbital elements for a body in the MPC database.

    Parameters:
        aliases (list[str]): The possible number, name, and designations of a body. The
            number if any must come first; the assigned name if any must come second.
            Other designations can follow.
        elements (dict[str, float]): The orbital elements keyed by element name: "A",
            "Q", "A", "Q", "I", "O", "E", "W", "M", "T", and "EPOCH".

    Returns:
        dict[str]: A dictionary of minor planet parameters.

            * "name" (str): The body name if any, e.g., "Quaoar".
            * "mnum" (int): The minor planet number if any, e.g., 50000.
            * "naif_id (int): The NAIF ID of the body, e.g, 2050000.
            * "desig" (str): The body designation, e.g., "2002 LM60".
            * "alt_desigs" (str): Alternative designations.
            * "full_name" (str): The full name to be used in the LID.
            * "aliases" (str): The complete list of aliases.
            * "mpc_key" (str): A string suitable for looking up the body at the MPC.
            * "ttype" (str): The body TargetType character, always "M" for minor planet.
              This can be updated later for a more specific value ("A" = asteroid; "H" =
              Centaur; "D" = dwarf planet, or "T" = Trans-Neptunian object).
            * "full_name" (str): The full name to be used by the LID. E.g., "50000
              Quaoar" or "(123456) 2000 WO137".
            * "A", "Q", "A", "Q", "I", "O", "E", "W", "M", "T", "EPOCH": Orbital
              elements.
    """

    body = {}

    # Minor planet number, if any
    if aliases[0].isdigit():
        mnum = aliases[0]
        body['naif_id'] = 2000000 + int(aliases[0])
        aliases = aliases[1:]
    else:
        mnum = ''
    body['mnum'] = mnum

    # Name, if any
    if aliases[0].replace(' ', '').isalpha():
        name = aliases[0]
        aliases = aliases[1:]
    else:
        name = ''
    body['name'] = name

    # Designations...
    if aliases:
        aliases.sort()
        for k, alias in enumerate(aliases):
            if alias[:4].isdigit() and alias[4] != ' ':
                aliases[k] = alias[:4] + ' ' + alias[4:]
        body['desig'] = aliases[0]
        body['alt_desigs'] = aliases[1:]
    else:
        body['desig'] = ''
        body['alt_desigs'] = []

    body['mpc_key'] = body['mnum'] if body['mnum'] else body['desig']

    # full_name
    if name:
        full_name = f'{mnum} {name}'
    elif mnum:
        full_name = f'({mnum}) {aliases[0]}'
    else:
        full_name = body['desig']
    body['full_name'] = full_name

    # aliases
    names = []              # All formal aliases
    lookups = {full_name}   # Alternative names to support identification
    if name:
        names.append(f'({mnum}) {name}')
        lookups.add(f'{mnum} ({name})')
        if name in _DISALLOWED_MINOR_PLANET_NAMES:
            lookups.add(name)
        else:
            names.append(name)
    if mnum:
        for desig in aliases:
            names.append(f'({mnum}) {desig}')
        names.append(f'({mnum})')
        lookups.add(mnum)
    names += aliases

    # Make the aliases unique; omit full_name
    aliases = []
    for name in names:
        if name not in aliases and name != full_name:
            aliases.append(name)
    names += aliases
    body['aliases'] = aliases

    # Lookups include aliases and names in uppercase
    lookups |= set(aliases)
    lookups |= {n.upper() for n in lookups}
    body['lookups'] = lookups

    body['ttype'] = TargetType.MINOR_PLANET
    body.update(elements)
    return body


__all__ = ['_mpc_body_dict', '_MPC_CACHE', '_MPC_CACHING', '_MPC_BY_NAME',
           '_MPC_BY_PROPERTIES']

##########################################################################################
