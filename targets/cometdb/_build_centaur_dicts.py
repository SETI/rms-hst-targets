##########################################################################################
# cometdb/_build_centaur_dicts.py
##########################################################################################

from logging import Logger

from ._get_johnston_centaurs import _get_johnston_centaurs
# from ._get_wiki_centaurs import _get_wiki_centaurs  # not used
from targets.targettype import TargetType


def _build_centaur_dicts(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[dict[str, dict], dict[str, dict], dict[str, list[dict]]]:
    """A dictionary of centaur parameters based on all the centaur cache resources.

    Parameters:
        update: True to re-read the websites; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`centaurs`, `by_lookup`, `by_ambiguous`): Three dictionaries returning centaur
        dictionaries based on a key:

        * `centaurs`: A dictionary in which every centaur is unique, keyed by the
          minor planet number if defined, or else by the MPC designation.
        * `by_lookup`: A dictionary keyed by essentially any string that might be used to
          unambiguously identify a centaur.
        * `by_ambiguous`: A dictionary keyed by potentially ambiguous centaur names,
          returning the list of centaur that might match. Currently empty.

        These are the optional fields of each centaur dictionary:

        * `desig` (str): The designation of the form "<year> <letters><digits>".
        * `name` (str): The name of the object, if any.
        * `mnum` (str): The minor planet number, if any.
        * `naif_id` (int): The NAIF ID, if any.
        * `ttype` (str): Always "H" for centaurs.
        * `A`, `Q`, `I`, `O`, `E`, `W`: Approximate orbital elements if known. "A" for
          semimajor axis in AU; "Q" for perihelion distance in AU; "I" for inclination in
          degrees; "O" for ascending node in degrees; "E" for eccentricity; "W" for
          argument of perihelion in degrees.
        * 'key' (str): The unique dictionary key for this object.
        * `full_name (str): The centaur's name as it will be adapted to the LID.
        * `aliases` (list[str]): Standard aliases for this centaur, to appear in the
          context product.
        * `lookups` (list[str]): Unique aliases for this centaur, serving as the keys of
          the `by_lookup` dictionary.
        * `ambiguous` (list[str]): Ambiguous aliases, possibly referring to more than one
          centaur.
    """

    centaur_list = _get_johnston_centaurs(update, logger)[1]

    centaurs = {}
    for centaur in centaur_list:

        # Construct a unique key
        mnum = centaur.get('mnum', '')
        desig = centaur.get('desig', '')
        if mnum:
            key = mnum
        else:
            key = desig
        centaur['key'] = key

        # naif_id
        if mnum:
            centaur['naif_id'] = 2000000 + int(mnum)

        # ttype
        centaur['ttype'] = TargetType.CENTAUR

        # aliases, full_name
        name = centaur.get('name', '')
        aliases = []
        if mnum:
            if name:
                aliases.append(mnum + ' ' + name)
                aliases.append('(' + mnum + ') ' + name)
            aliases.append('(' + mnum + ') ' + desig)
        aliases.append(desig)

        centaur['full_name'] = aliases[0]
        centaur['aliases'] = aliases[1:]

        # lookups
        lookups = list(aliases)
        if name:
            lookups.append(name)
        if mnum:
            lookups += [mnum, '(' + mnum + ')']
        centaur['lookups'] = lookups

        centaur['ambiguous'] = []

        centaurs[key] = centaur

    # Assemble lookup dictionary; warn about duplicated lookup keys
    by_lookup = {}
    for key, centaur in centaurs.items():
        for lookup in centaur['lookups']:
            if lookup in by_lookup or lookup.upper() in by_lookup:
                alt_key = by_lookup[lookup]['key']
                logger and logger.warn(f'Duplicated lookup key "{lookup}" for keys: '
                                       f'"{key}", "{alt_key}"')
            else:
                by_lookup[lookup] = centaur
                by_lookup[lookup.upper()] = centaur

    by_ambiguous = {}

    return centaurs, by_lookup, by_ambiguous

##########################################################################################
