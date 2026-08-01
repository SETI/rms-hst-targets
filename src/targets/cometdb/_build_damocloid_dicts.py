##########################################################################################
# cometdb/_build_damocloid_dicts.py
##########################################################################################

from logging import Logger

from ._get_wiki_damocloids import _get_wiki_damocloids


def _build_damocloid_dicts(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[dict[str, dict], dict[str, dict], dict[str, list[dict]]]:
    """A dictionary of damocloid parameters based on all the damocloid cache resources.

    Parameters:
        update: True to re-read the websites; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`damocloids`, `by_lookup`, `by_ambiguous`): Three dictionaries returning
        damocloid dictionaries based on a key:

        * `damocloids`: A dictionary in which every damocloids is unique, keyed by the
          minor planet number if defined, or else by the MPC designation.
        * `by_lookup`: A dictionary keyed by essentially any string that might be used to
          unambiguously identify a damocloid.
        * `by_ambiguous`: Unused.

        These are the optional fields of each damocloid dictionary:

        * `desig` (str): The designation of the form "<year> <letters><digits>".
        * `name` (str): The name of the object, if any.
        * `mnum` (str): The minor planet number, if any.
        * `ttype` (str): TargetType code, one of "H" for Centaur, "T" for TNO, or "A" for
          asteroid.
        * 'key' (str): The unique dictionary key for this object.
        * `lookups` (list[str]): Unique aliases for this damocloid, serving as the keys of
          the `by_lookup` dictionary.
    """

    damocloid_list = _get_wiki_damocloids(update, logger)[1]

    damocloids = {}
    for damocloid in damocloid_list:

        # Construct a unique key
        mnum = damocloid.get('mnum', '')
        name = damocloid.get('name', '')
        desig = damocloid.get('desig', '')
        if mnum:
            key = mnum
        else:
            key = desig
        damocloid['key'] = key

        # lookups
        lookups = []
        if name:
            lookups.append(name)
        if desig:
            lookups.append(desig)
        if mnum:
            lookups.append(mnum)
            if name:
                lookups += [mnum + ' ' + name, '(' + mnum + ') ' + name]
            if desig:
                lookups.append('(' + mnum + ') ' + desig)
        damocloid['lookups'] = lookups
        damocloids[key] = damocloid

    # Assemble lookup dictionary
    by_lookup = {}
    for damocloid in damocloids.values():
        for lookup in damocloid['lookups']:
            by_lookup[lookup] = damocloid
            by_lookup[lookup.upper()] = damocloid

    return damocloids, by_lookup, {}


__all__ = ['_build_damocloid_dicts']

##########################################################################################
