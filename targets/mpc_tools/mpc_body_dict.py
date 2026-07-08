##########################################################################################
# mpc_tools/mpc_body_dict.py
##########################################################################################

from targets.targettype import TargetType


def mpc_body_dict(
    aliases: list[str],
    elements: dict[str, float],
) -> dict:
    """Get aliases and orbital elements for a body in the MPC database.

    Parameters:
        aliases: A list of the possible number, name, and designations of a body.
        elements: A dictionary of orbital elements keyed by element name, as follows:

            * "A": semimajor axis in AU.
            * "Q": perihelion distance in AU.
            * "I": inclination in degrees.
            * "O": ascending node in degrees.
            * "E": eccentricity.
            * "W": argument of pericenter in degrees.

    Returns:
        A dictionary of minor planet parameters.

        Details TBD.
    """

    body = {}

    # Minor planet number, if any
    if aliases[0].isdigit():
        body['mnum'] = aliases[0]
        body['naif_id'] = 2000000 + int(aliases[0])
        aliases = aliases[1:]
    else:
        body['mnum'] = ''

    # Name, if any
    if aliases[0].replace(' ', '').isalpha():
        body['name'] = aliases[0]
        aliases = aliases[1:]
    else:
        body['name'] = ''

    # Designations...
    if aliases:
        aliases.sort()
        body['desig'] = aliases[0]
        body['alt_desigs'] = aliases[1:]
    else:
        body['desig'] = ''
        body['alt_desigs'] = []

    body['mpc_key'] = body['mnum'] if body['mnum'] else body['desig']

    if body['name']:
        body['full_name'] = body['mnum'] + ' ' + body['name']
    elif body['mnum']:
        body['full_name'] = '(' + body['mnum'] + ') ' + body['desig']
    else:
        body['full_name'] = body['desig']

    body.update(elements)

    # Determine the TargetType (TBD!!!)
    body['ttype'] = TargetType.MINOR_PLANET

    return body

##########################################################################################
