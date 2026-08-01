##########################################################################################
# targets/mpc_tools/_utils.py
##########################################################################################

import pathlib
import re

import anyascii

from targets._DISALLOWED_MINOR_PLANET_NAMES import _DISALLOWED_MINOR_PLANET_NAMES
from targets.cometdb import comet_dict
from targets.targettype import TargetType

_MPC_CACHE = pathlib.Path(__file__).parent.parent.parent / 'caches/MPC_CACHE'
_MPC_CACHING = True

# A Palomar-Leiden (e.g. "6317 P-L") or Trojan-survey (e.g. "3101 T-2") designation is the
# principal designation for those survey objects, per MPC/JPL, even though the MPC
# show_object page lists a later year-designation first. Prefer it as the primary desig.
_SURVEY_DESIG = re.compile(r'\d+ (?:P-L|T-[123])$')

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


def _mpc_body_dict(names, elements):
    """Get aliases and orbital elements for a body in the MPC database.

    Parameters:
        names (list[str]): The possible number, name, and designations of a body. The
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
    if names[0].isdigit():
        mnum = names[0]
        body['naif_id'] = 2000000 + int(names[0])
        names = names[1:]
    else:
        mnum = ''
    body['mnum'] = mnum

    # Name, if any
    if anyascii.anyascii(names[0].replace(' ', '').replace('-', '')).isalpha():
        name = names[0]
        names = names[1:]
    else:
        name = ''
    body['name'] = name
    body_name = name

    # Designations...
    if names:
        # Fix missing spaces
        for k, name in enumerate(names):
            if name[:4].isdigit() and name[4] != ' ':
                names[k] = name[:4] + ' ' + name[4:]
        desig = names[0]
        alt_desigs = names[1:]
    else:
        desig = ''
        alt_desigs = []
    body['desig'] = desig
    body['alt_desigs'] = alt_desigs
    desigs = names

    body['mpc_key'] = mnum if mnum else desig

    # full_name
    if body_name:
        full_name = f'{mnum} {body_name}'
    elif mnum:
        full_name = f'({mnum}) {desig}'
    else:
        full_name = desig
    body['full_name'] = full_name

    # aliases
    aliases = list(desigs)      # All formal aliases, full_name first
    lookups = set()             # Alternative names to support identification
    if body_name:
        if name in _DISALLOWED_MINOR_PLANET_NAMES:
            lookups.add(body_name)
        else:
            aliases.append(body_name)
    if mnum:
        for desig in desigs:
            lookups.add(f'({mnum}) {desig}')
        lookups.add(f'({mnum})')
        lookups.add(mnum)
        # The number combined with the name, e.g. "762 Pulcova" and "(762) Pulcova". This
        # is the most common way a TARGNAME identifies a numbered minor planet, and
        # `full_name` alone is not enough because it is excluded from `aliases` below.
        if body_name:
            lookups.add(f'{mnum} {body_name}')
            lookups.add(f'({mnum}) {body_name}')

    # Add ASCII versions of non-ASCII names
    for name in [full_name, body_name]:
        ascii_name = anyascii.anyascii(name)
        if name != ascii_name:
            aliases.append(ascii_name)

    # Make the aliases unique; omit full_name
    aliases2 = []
    for name in aliases:
        if name not in aliases2 and name != full_name:
            aliases2.append(name)
    aliases = aliases2
    body['aliases'] = aliases

    # Lookups include aliases and names in uppercase
    lookups |= set(aliases)
    lookups |= {n.upper() for n in lookups}
    body['lookups'] = lookups

    body['ttype'] = TargetType.MINOR_PLANET
    body.update(elements)

    # Handle bodies that were also comets
    for name in body['alt_desigs']:
        if name.endswith('P') and name[:-1].isdigit() and name in comet_dict():
            comet = comet_dict()[name]
            for alias in [comet['prefix'], comet['full_name']] + comet['aliases']:
                if alias not in body['aliases']:
                    body['aliases'].append(alias)
            for lookup in comet['lookups']:
                if lookup not in body['lookups']:
                    body['lookups'].add(lookup)

    return body


__all__ = [
    '_MPC_BY_NAME',
    '_MPC_BY_PROPERTIES',
    '_MPC_CACHE',
    '_MPC_CACHING',
    '_mpc_body_dict',
]

##########################################################################################
