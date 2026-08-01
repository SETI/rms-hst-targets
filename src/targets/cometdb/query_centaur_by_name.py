##########################################################################################
# cometdb/query_centaur_by_name.py
##########################################################################################

from ._utils import centaur_lookup


def query_centaur_by_name(name, *, logger=None):
    """Get information about a comet in CometDB.

    Parameters:
        name (str): The name or designation of a comet.
        logger (PdsLogger, optional): Logger for messages.

    Returns:
        A centaur dictionary.
    """

    lookup = centaur_lookup()
    key = name.upper()

    if key in lookup:
        centaur = lookup[key]
        centaur_key = centaur['key']
        logger and logger.debug(f'Centaur {centaur_key} matches "{name}"')
        return centaur

    logger and logger.info(f'No centaur found matching "{name}"')
    return None


__all__ = ['query_centaur_by_name']

##########################################################################################
