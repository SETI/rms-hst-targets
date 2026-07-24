##########################################################################################
# targets/target_xml_support.py
##########################################################################################

import anyascii

from targets.cometdb         import comet_lookup
from targets.roman           import int_to_roman
from targets.standard_bodies import STANDARD_BODY_LOOKUP
from targets.target_xml_cache_support import (_missing_aliases, _new_desc,
                                              _read_target_xml_dict,
                                              find_xml_dict, find_xml_path,
                                              new_target_xml_dict, update_target_xml_dict)
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
    * "description": A list of description lines (strings); an empty list means "none".

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

    # description (a list of strings, one per line; an empty list means "none")
    if 'description' not in target:
        desc = []
        if target['ttype'] == TargetType.SATELLITE:
            desc.append(f'{target["type_name"]} of: {parent["full_name"]};')
            desc.append(f'Type of primary: {TargetType.NAME[parent["ttype"]]};')
            desc.append(f'LID of primary: {_lid_tail(parent)};')
            if parent['naif_id']:
                desc.append(f'NAIF ID of primary: {parent["naif_id"]};')

        elif parent and target['ttype'] == TargetType.COMET:
            desc.append(f'Fragment of: {parent["full_name"]};')
            xml_dict = find_xml_dict(parent)
            if xml_dict:
                desc.append(f'LID of primary: {xml_dict["lid_tail"]};')
            else:
                desc.append(f'LID of primary: {_lid_tail(parent)};')
            if parent['naif_id']:
                desc.append(f'NAIF ID of primary: {parent["naif_id"]};')

        elif target.get('fragment_keys', ''):
            uncataloged = []
            frag_info = {}
            for frag_key in target['fragment_keys']:
                comet = comet_lookup()[frag_key]
                xml_dict = find_xml_dict(comet)
                if xml_dict:
                    frag_info[frag_key] = {}
                    frag_info[frag_key]['lid_tail'] = xml_dict['lid_tail']
                if comet.get('naif_id', 0):
                    if frag_key not in frag_info:
                        frag_info[frag_key] = {}
                    frag_info[frag_key]['naif_id'] = comet['naif_id']

                if frag_key in frag_info:
                    frag_info[frag_key]['fragment'] = comet['fragment']
                else:
                    uncataloged.append(comet['fragment'])

            if not frag_info:
                desc = ['Cometary fragments: ' + ', '.join(uncataloged)]
            else:
                desc = ['Cometary fragments:']
                for frag_key, info in frag_info.items():
                    parts = [info['fragment'], ': ']
                    if 'lid_tail' in info:
                        parts += ['LID = ', info['lid_tail']]
                        if 'naif_id' in info:
                            parts += ['; ']
                    if 'naif_id' in info:
                        parts += ['NAIF ID = ', str(info['naif_id'])]
                    desc.append(''.join(parts))
                if uncataloged:
                    desc.append('Additional fragments: ' + ', '.join(uncataloged))

        target['description'] = desc

    return target


def get_target_xml_path(target, logger=None):
    """The cached directory path containing the content of the given target dictionary.
    """

    xml_path = find_xml_path(target)
    if xml_path is None:
        return new_target_xml_dict(target, logger=logger)

    # Check for a conflict
    xml_dict = _read_target_xml_dict(xml_path)
    for field in ('lid_tail', 'title', 'ttype'):
        if xml_dict[field] != target[field]:
            logger and logger.warning(f'Target context XML mismatch at "{field}" in '
                                      f'{xml_dict["xml_path"].name}: '
                                      f'{target[field]!r}, {xml_dict[field]!r}')
            logger and logger.warning('Pre-existing target XML file used', xml_path)

    # Update the file only if this target adds aliases or a description it lacks;
    # otherwise the existing file already covers it.
    missing_aliases = _missing_aliases(target, xml_dict)
    needs_desc = _new_desc(target, xml_dict)
    if missing_aliases or needs_desc:
        return update_target_xml_dict(target, logger=logger)

    return xml_path


##########################################################################################
