##########################################################################################
# targets/cometdb/query_comet_by_name.py
##########################################################################################

from ._utils import comet_dicts


def query_comet_by_name(name, *, ambiguous=True, logger=None):
    """Get information about a comet in CometDB.

    Parameters:
        name (str): The name or designation of a comet.
        ambiguous (bool): True to return a list of matches when `name` is ambiguous.
        logger (Logger): Optional Logger for messages.

    Returns:
        dict or list[dict]: A comet dictionary or a list of comet dictionaries if multiple
        names match. If no match is found, an empty list is returned.
    """

    key = name.upper()
    _, by_lookup, by_ambiguous = comet_dicts()

    comet = None
    if key in by_lookup:
        comet = by_lookup[key]
    elif len(key) > 1 and key[1] == '/' and key[1:] in by_lookup:
        # works if leading letter is wrong
        comet = by_lookup[key[1:]]

    if comet:
        comet_key = comet['key']
        logger and logger.debug(f'Comet {comet_key} matches "{name}"')
        return comet

    if key in by_ambiguous:
        matches = by_ambiguous[key]
        count = len(matches)
        if ambiguous:
            logger and logger.debug(f'Comet name "{name}" has {count} matches')
            return matches

        logger and logger.info(f'Ambiguous comet name "{name}" has {count} matches')
        return matches

    logger and logger.info(f'No comet found matching "{name}"')
    return []

##########################################################################################
