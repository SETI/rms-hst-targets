##########################################################################################
# identify_standard_body.py
##########################################################################################
"""Identify the standard bodies (planets and satellites) named by an HST header.

A "standard body" is a planet or satellite carried in `STANDARD_BODY_LOOKUP`, as opposed
to a comet or minor planet. `identify_standard_body` recognizes such bodies from two
sources: the MT_LV* "STD" fields, where MT_LV2 names the body in the field of view and
MT_LV1 names the body HST tracked; and the repaired target description strings, which may
name additional standard bodies. An "STD" field that instead names a minor planet or
comet is resolved through the small-body identifiers.

To use::

    from targets.identify_standard_body import identify_standard_body

"""

import re
from logging import Logger

from targets import mpc_tools
from targets.errors import TargetIdentificationError
from targets.identify_small_body import identify_small_body
from targets.standard_bodies import STANDARD_BODY_LOOKUP

__all__ = ['identify_standard_body']

_STD_NUMBER_NAME = re.compile(r'\(?([1-9]\d*)\)?(?: *\((.+)\)| +(.+))?')


def _resolve_std(token: str, logger: Logger | None) -> tuple[dict | None, str, str]:
    """Resolve the value of an MT_LV* "STD" field.

    Parameters:
        token: The value of the "STD" field, e.g., "JUPITER", "2060", or "1 (CERES)".
        logger: An optional Logger for messages.

    Returns:
        A tuple `(body, name, number)`. If the token names a standard body, `body` is
        its dictionary and the strings are empty. Otherwise `body` is None, `name` is
        the small-body name or number to look up instead, and `number` is the minor
        planet number if the token supplied one.
    """

    token = ' '.join(str(token).split()).upper()
    if token in STANDARD_BODY_LOOKUP:
        return (STANDARD_BODY_LOOKUP[token], '', '')

    # "N", "N (NAME)", or "(N) NAME" identifies a minor planet by number. The name alone
    # can match a standard body that shares it (e.g., "9 (METIS)" is the asteroid, not
    # the satellite of Jupiter), so a standard body is accepted only if its own minor
    # planet number agrees.
    match = _STD_NUMBER_NAME.fullmatch(token)
    if match:
        number = match.group(1)
        name = match.group(2) or match.group(3) or ''
        if name and name in STANDARD_BODY_LOOKUP:
            body = STANDARD_BODY_LOOKUP[name]
            if str(body.get('mnum', '')) == number:
                return (body, '', '')
        return (None, name or number, number)

    return (None, token, '')


def identify_standard_body(
    kind1: str | None,
    payload1: dict | str | None,
    kind2: str | None,
    payload2: dict | str | None,
    answers: list[str],
    logger: Logger | None
) -> tuple[list[dict], list[dict], set[str]]:
    """Identify the standard bodies (planets and satellites) named by a header.

    Two sources are consulted: the MT_LV* "STD" fields, where MT_LV2 names the body in
    the field of view and MT_LV1 names the body HST tracked; and the repaired target
    description strings, which may name additional standard bodies. An "STD" field that
    names a minor planet or comet rather than a standard body is resolved through the
    small-body identifiers.

    Parameters:
        kind1: The MT_LV1 kind returned by `_parse_mt_lv`.
        payload1: The MT_LV1 payload returned by `_parse_mt_lv`.
        kind2: The MT_LV2 kind returned by `_parse_mt_lv`.
        payload2: The MT_LV2 payload returned by `_parse_mt_lv`.
        answers: The repaired identification strings from `hst_repairs`.
        logger: An optional Logger for messages.

    Returns:
        A tuple `(fov_bodies, tracked_bodies, consumed)`: the standard bodies in the
        field of view, the body HST tracked (per MT_LV1), and the set of `answers`
        strings consumed by a name match.

    Raises:
        TargetIdentificationError: If an "STD" field names a target that cannot be
            resolved.
    """

    fov_bodies = []         # bodies identified by name; the subject of the observation
    tracked_bodies = []     # the body HST tracked, per MT_LV1

    # Standard bodies named by the MT_LV* "STD" fields. MT_LV2 names the body in the
    # field of view; MT_LV1 names the body HST tracked.
    for kind, payload, level, target_list in [
            (kind2, payload2, 'MT_LV2', fov_bodies),
            (kind1, payload1, 'MT_LV1', tracked_bodies)]:
        if kind != 'STD':
            continue
        body, small_name, number = _resolve_std(payload, logger)
        if body is None:
            # The STD field names a minor planet or comet; identify it by name
            body, _, valid = identify_small_body([small_name], {}, logger=logger)
            if not valid:
                body = None
        if body is None and number and number != small_name:
            # The name did not resolve (e.g., it is reserved for a satellite), but the
            # minor planet number is authoritative
            try:
                body = mpc_tools.mpc_query_by_name(number, logger=logger)
            except RuntimeError:
                body = None
        if body is None:
            message = f'Unresolved standard target "STD={payload}" in {level}'
            logger and logger.error(message)
            raise TargetIdentificationError(message)
        logger and logger.info(f'{level} standard target: '
                               + (body.get('full_name') or body['name']))
        target_list.append(body)

    # Standard bodies identified by name from the target description
    consumed = set()
    for answer in answers:
        for part in answer.upper().split('-'):  # handle, e.g., "PANDORA-PROMETHEUS"
            body = STANDARD_BODY_LOOKUP.get(part)
            if body:
                consumed.add(answer)
                logger and logger.info(f'Standard body identified by name: {body["name"]} '
                                       f'(from "{part}")')
                fov_bodies.append(body)

    return fov_bodies, tracked_bodies, consumed

##########################################################################################
