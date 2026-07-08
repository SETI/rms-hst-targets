##########################################################################################
# cometdb/query_centaur_by_name.py
##########################################################################################

from logging import Logger

from ._utils import centaur_dicts


def query_centaur_by_name(
    name: str, *,
    logger: Logger | None = None
) -> dict | None:
    """Get information about a comet in CometDB.

    Parameters:
        name: The name or designation of a comet.
        logger: An optional Logger for messages.

    Returns:
        A centaur dictionary.
    """

    _, by_lookup, _ = centaur_dicts()
    key = name.upper()

    if key in by_lookup:
        centaur = by_lookup[key]
        centaur_key = centaur['key']
        logger and logger.debug(f'Centaur {centaur_key} matches "{name}"')
        return centaur

    logger and logger.info(f'No centaur found matching "{name}"')
    return None

##########################################################################################
