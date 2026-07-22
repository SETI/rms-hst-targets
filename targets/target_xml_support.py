##########################################################################################
# targets/target_xml_support.py
##########################################################################################

import anyascii

from targets.cometdb         import comet_lookup
from targets.roman           import int_to_roman
from targets.standard_bodies import STANDARD_BODY_LOOKUP
from targets.target_xml_cache_support import (new_target_xml_dict, target_xml_dict,
                                              target_xml_path, update_target_xml_dict)
from targets.targettype      import TargetType

_LID_PREFIX = 'urn:nasa:pds:context:target:'


def _lid_tail(target):
    """The LID of the target following the colon, depending on `full_name` and `ttype`."""

    name = anyascii.anyascii(target['full_name']).lower()

    # Slashes and spaces are handled inconsistently!
    if target['ttype'] == TargetType.SATELLITE:
        if name[1] == '/':
            name = name.replace('/', '').replace(' ', '')   # S/2003 J 5 -> S2003J5
    elif target['ttype'] == TargetType.COMET:
        if name[1] == '/':
            name = name.replace('/', '')                    # C/2007 N3 -> C2007 N3
        else:
            name = name.replace('/', ' ')                   # 1P/Halley -> 1P Halley

    if target['ttype'] in {TargetType.SATELLITE, TargetType.RING, TargetType.TORUS}:
        name = target['parent']['full_name'] + '.' + name

    tail = TargetType.NAME[target['ttype']] + '.' + name
    tail = tail.replace(' ', '_').lower()

    # Filter out disallowed characters
    tail = ''.join(c for c in tail if c in 'abcdefghijklmnopqrstuvwxyz0123456789_-.:')
    return tail


_TYPE_WORD = {
    TargetType.SATELLITE: 'Satellite',
    TargetType.COMET    : 'Fragment',
    TargetType.RING     : 'Ring',
}


def _complete_target(target):
    """Fill in any missing, required parameters in the given target dictionary.

    The target's `ttype` must already be its final category; the identification core
    (`identify_target_dicts`) categorizes minor planets, so this function does not.

    These items are required:

    * "title": The title (with preferred capitalization).
    * "lid_tail": The name as it will appear in the LID, following "target:".
    * "lid": The full LID, beginning with "urn:nasa:pds:context:target:".
    * "type_name": The full name of the target type, e.g., "Trans-Neptunian Object".
    * "parent": For satellites, rings, and tori, the target dictionary describing the
      primary. Ignored for other target types.
    * "alt_titles": A list of standard aliases for this target, using standard
      capitalization. Each of these will be used as an `alternate_title` in the context
      product.
    * "description": Descriptive text, if needed; otherwise, blank or "none".

    Parameters:
        target (dict): Body dictionary.

    Returns:
        dict: `target`, modified in place and returned.
    """

    target['type_name'] = TargetType.NAME[target['ttype']]

    # alt_titles
    if 'alt_titles' not in target:
        alt_titles = list(target.get('aliases', []))
        mnum = target.get('mnum')
        if mnum:
            alias = f'Minor Planet {mnum}'
            if alias not in alt_titles:
                alt_titles.append(alias)
        naif_id = target.get('naif_id')
        if naif_id:
            alias = f'NAIF ID {naif_id}'
            if alias not in alt_titles:
                alt_titles.append(alias)
        target['alt_titles'] = alt_titles

    # parent (could be None, but shouldn't be missing)
    parent_name = target.get('parent_key', '')
    if parent_name:
        parent = STANDARD_BODY_LOOKUP.get(parent_name) or comet_lookup().get(parent_name)
    else:
        parent = None
    target['parent'] = parent

    # title
    if (target['ttype'] == TargetType.SATELLITE and parent['ttype'] != TargetType.PLANET
            and target.get('satnum')):
        target['title'] = (parent['full_name'] + ' ' + int_to_roman(target['satnum'])
                           + ' (' + target['name'] + ')')
        if target['name'] not in target['alt_titles']:
            target['alt_titles'] = [target['name']] + target['alt_titles']
    else:
        target['title'] = target['full_name']

    # lid_tail and lid
    lid_tail = _lid_tail(target)
    target['lid_tail'] = lid_tail
    target['lid'] = _LID_PREFIX + lid_tail

    # description
    if 'description' not in target:
        desc = []
        if parent:
            type_word = _TYPE_WORD.get(target['ttype'], '')
            if type_word:
                desc.append(f'{type_word} of: {parent["full_name"]};')
            if parent['ttype'] != TargetType.COMET:
                desc.append(f'Type of primary: {TargetType.NAME[parent["ttype"]]};')
            desc.append(f'LID of primary: {_lid_tail(parent)};')
            if parent['naif_id']:
                desc.append(f'NAIF ID of primary: {parent["naif_id"]};')
        else:
            desc = ['none']

        target['description'] = '\n'.join(desc)

    return target


def get_target_xml_path(target, logger=None):
    """The cached directory path containing the content of the given target dictionary.
    """

    for key in [target['lid_tail'], target['title']] + target['alt_titles']:
        xml_path = target_xml_path(key)
        if xml_path is not None:
            break

    # If this target has no pre-existing context product
    if xml_path is None:
        return new_target_xml_dict(target, logger=logger)

    # Check for a conflict
    xml_dict = target_xml_dict(key)
    for key in ('lid_tail', 'title', 'ttype'):
        if xml_dict[key] != target[key]:
            logger and logger.warning(f'Target context XML mismatch at "{key}" in '
                                      f'{xml_dict["xml_path"].name}: '
                                      f'{target[key]!r}, {xml_dict[key]!r}')
            logger and logger.warning('Pre-existing target XML file used', xml_path)

    # Investigate alt_titles
    new_alts = set(target['alt_titles'])
    old_alts = set(xml_dict['alt_titles'])
    if new_alts == old_alts:
        return xml_path  # no conflict

    diff = old_alts - new_alts
    if diff:
        return update_target_xml_dict(target, logger=logger)


##########################################################################################
