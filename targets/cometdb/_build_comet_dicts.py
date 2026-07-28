##########################################################################################
# cometdb/_build_comet_dicts.py
##########################################################################################

import re
from logging import Logger

from targets.targettype import TargetType

from ._get_icq_comets import _get_icq_comets
from ._get_mpc_comets import _get_mpc_comets
from ._get_sbn_comets import _get_sbn_comets
from ._get_ssd_comets import _get_ssd_comets
from ._get_wiki_comets import _get_wiki_comets
from ._REPAIR_COMET import _repair_comet

_INT_MATCH = re.compile(r'(-?\d+)')
_FRAG_MATCH = re.compile(r'(.*)-[A-Z]\d?')


def _build_comet_dicts(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[dict[str, dict], dict[str, dict], dict[str, list[dict]]]:
    """A dictionary of comet parameters based on all the comet cache resources.

    Parameters:
        update: True to re-read the websites; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`comets`, `by_lookup`, `by_ambiguous`): Three dictionaries returning comet
        dictionaries based on a key:

        * `comets`: A dictionary in which every comet is unique, keyed by the numbered
          comet identifier (e.g., "1P" or "2I") or by the year-based designator (e.g.,
          "D/1993 F2"). If the comet is a fragment, an additional fragment identifier is
          appended, e.g., "79P-A" or "D/1993 F2-Q2").
        * `by_lookup`: A dictionary keyed by essentially any string that might be used to
          unambiguously identify a comet.
        * `by_ambiguous`: A dictionary keyed by potentially ambiguous comet names,
          returning the list of comets that might match (e.g., "Encke" or
          "Shoemaker-Levy").

        These are the optional fields of each comet dictionary:

        * `prefix` (str): The designation before the slash, either a single letter ("P",
          "C", etc.) or, for numbered comets, the digits followed by one letter.
        * `desig` (str): The designation of the form "[PCXAI]/<year> <letters><digits>".
          For named and numbered comets, this value is absent; any designation appears in
          the `alt_desigs` list instead. It never includes a comet number.
        * `name` (str): The discovery name of the object, if any. This excludes a
          discovery number (e.g., "Tempel" not "Tempel 2").
        * `cnum` (str): The comet number for the discovery name, if any and if known. If
          defined, the preferred full name of the comet includes this number.
        * `fragment` (str): The fragment identifier, if any, excluding any leading dash.
        * `alt_prefixes` (list[str]): A list of alternative prefixes, e.g., ["72D"] for a
          dead comet that is primarily referenced with prefix "72P".
        * `alt_frags` (list[str]): A list of alternative fragment identifiers, excluding
          any leading dash.
        * `alt_names` (list[str]): A list of alternative discover names and optional
          numbers, e.g., "Anderson" for 148P/Anderson-Linear. Unlike `name`, each name
          includes its `cnum` if any, e.g., "Tempel 2" for 10P/Tempel.
        * `alt_desigs` (list[str]): A list of alternative formal designations. Unlike
          the value of `desig`, these values include a fragment identifier (preceded by
          a dash) if needed.
        * `old_desigs` (list[str]): A list of old or non-standard designations, e.g.,
          "1993e" or "1994 X".
        * `mnum` (str): The minor planet number, if any.
        * `naif_id` (int): The NAIF ID, if any.
        * `ttype` (str): Always "C" for comets.
        * `A`, `Q`, `I`, `O`, `E`, `W`: Approximate orbital elements if known. "A" for
          semimajor axis in AU; "Q" for perihelion distance in AU; "I" for inclination in
          degrees; "O" for ascending node in degrees; "E" for eccentricity; "W" for
          argument of perihelion in degrees.
        * `year` (int): The most recent year that appears in a designation; -9999 if no
          year is found.
        * 'key' (str): The unique dictionary key for this object.
        * `parent_key` (str): The key for the "parent" object if this comet is a fragment.
        * `fragment_keys` (list[str]): The list of keys of the fragments if this is a
          parent.
        * `full_name` (str): The comet's name as it will be adapted to the LID, with
          standard capitalization.
        * `aliases` (list[str]): Standard aliases for this comet, to appear in the context
          product.
        * `lookups` (list[str]): Unique aliases for this comet, serving as the keys of
          the `by_lookup` dictionary.
        * `ambiguous` (list[str]): Ambiguous aliases, possibly referring to more than one
          comet.
    """

    # Get lists in decreasing order of authoritativeness
    comet_lists = [
        _get_wiki_comets(update, logger)[1],
        _get_mpc_comets(update, logger)[1],
        _get_sbn_comets(update, logger)[1],
        _get_ssd_comets(update, logger)[1],
        _get_icq_comets(update, logger)[1],
    ]

    comets = {}
    for comet_list in comet_lists:
        for comet in comet_list:

            # Handle known errors and inconsistencies
            _repair_comet(comet)

            # Construct a unique key
            prefix = comet.get('prefix', '')
            desig = comet.get('desig', '')
            fragment = comet.get('fragment', '')
            if len(prefix) > 1:  # if numbered
                key = prefix
            else:
                key = desig
            if fragment:
                key += '-' + fragment
            comet['key'] = key

            # Merge content into a single dictionary
            if key not in comets:
                comets[key] = _copy_comet(comet)
            else:
                _merge_comets(comets[key], comet, first_elements=False, logger=logger)

    # For named, numbered comets, move the designation to the alt list
    for comet in comets.values():
        if len(comet['prefix']) > 1 and comet.get('name', '') and comet.get('desig', ''):
            desig_frag = comet['desig'] + ('-' + comet.get('fragment', '')).rstrip('-')
            comet.setdefault('alt_desigs', []).append(desig_frag)
            comet['desig'] = ''

    # Identify prefix discrepancies among unnumbered comets, merge
    duplicate_pairs = []
    by_desig_tail = {}
    for key, comet in comets.items():
        desig = comet.get('desig', '')
        desig_frag = desig + ('-' + comet.get('fragment', '')).rstrip('-')
        desig_frags = ([desig_frag] if desig else []) + comet.get('alt_comets', [])
        for desig_frag in desig_frags:
            tail = desig_frag[2:]
            if tail in by_desig_tail:
                alt_key = by_desig_tail[tail]['key']
                if alt_key.startswith('C'):  # favor "C" if found
                    key, alt_key = alt_key, key
                    by_desig_tail[tail] = comets[alt_key]
                duplicate_pairs.append((key, alt_key))
            else:
                by_desig_tail[tail] = comet

    # Merge info from each duplicate, then delete it
    for key, alt_key in duplicate_pairs:
        logger and logger.info(f'Merging comets: "{key}", "{alt_key}"')
        _merge_comets(comets[key], comets[alt_key], first_elements=True, logger=logger)
        del comets[alt_key]

    # Identify duplicates of numbered comets
    duplicate_pairs = []
    for key, comet in comets.items():
        if '/' not in key:  # if numbered
            for desig_frag in comet.get('alt_desigs', []):
                tail = desig_frag[2:]
                if tail in by_desig_tail:
                    pair = (key, tail)
                    if pair not in duplicate_pairs:
                        duplicate_pairs.append(pair)

    # Merge info from each duplicate, then delete it
    for key, tail in duplicate_pairs:
        alt_key = by_desig_tail[tail]['key']
        logger and logger.info(f'Merging comets: "{key}", "{alt_key}"')
        _merge_comets(comets[key], comets[alt_key], first_elements=True, logger=logger)
        del comets[alt_key]

    # Remove duplicates from internal lists, handle other cleanup
    _complete_comets(comets, logger=logger)

    # Check ambiguous lists; a name that occurs for only one comet is not ambiguous after
    # all. Group case-insensitively so a name split across casings (e.g. "SHOEMAKER" vs
    # "Shoemaker" from different sources) counts as one comet, keeping the result
    # deterministic regardless of merge order.
    test_dict = {}
    for comet in comets.values():
        for amb in comet['ambiguous']:
            test_dict.setdefault(amb.upper(), []).append(comet)

    for amb_uc, comet_list in test_dict.items():
        unique_comets = {id(c): c for c in comet_list}
        if len(unique_comets) == 1:
            comet = next(iter(unique_comets.values()))
            # Move every casing of this name from ambiguous to the un-ambiguous lookups.
            for amb in [a for a in comet['ambiguous'] if a.upper() == amb_uc]:
                comet['lookups'].append(amb)
                comet['ambiguous'].remove(amb)

    # Warn about duplicated lookup keys
    test_dict = {}
    for key, comet in comets.items():
        for lookup in comet['lookups']:
            test = lookup.upper()
            # allow "P" vs. "C" vs. "D" ambiguity
            test = test[1:] if test[1] == '/' else test
            if test in test_dict and test_dict[test] is not comet:
                alt_key = test_dict[test]['key']
                logger and logger.warn(f'Duplicated lookup key "{lookup}" for keys: '
                                       f'"{key}", "{alt_key}"')
            else:
                test_dict[test] = comet

    # Assemble the lookup dictionaries
    by_lookup = {}
    for key, comet in comets.items():
        lookups = set(comet['lookups'])
        lookups |= set(_space_dash_permutations(lookups))
        lookups |= {key[1:] for key in lookups if key[1] == '/'}
        lookups |= {key.upper() for key in lookups}
        for lookup in lookups:
            by_lookup[lookup] = comet

    by_ambiguous = {}
    for key, comet in comets.items():
        lookups = set(comet['ambiguous'])
        lookups |= set(_space_dash_permutations(lookups))
        lookups |= {key[1:] for key in lookups if key[1] == '/'}
        lookups |= {key.upper() for key in lookups}
        for lookup in lookups:
            by_ambiguous.setdefault(lookup, []).append(comet)

    return comets, by_lookup, by_ambiguous


def _merge_comets(
    comet: dict,
    second: dict,
    first_elements: bool = True,
    logger: Logger | None = None
) -> None:
    """Merge the contents of two comet dictionaries, on the assumption that they refer to
    the same object.

    Parameters:
        comet: A comet dictionary, which is modified based on the contents of `second`.
        second: A second dictionary describing the same body.
        first elements: True to give priority to any orbital elements in `comet` over
            those in `second`.
        logger: Optional logger to use.
    """

    key = comet['key']

    # Handle name and cnum
    second_name = second.get('name', '')
    alt_names = comet.setdefault('alt_names', [])
    if second_name:
        name = comet.get('name', '')
        cnum = comet.get('cnum', '')
        name_num = (name + ' ' + cnum).rstrip()

        second_cnum = second.get('cnum', '')
        second_name_num = (second_name + ' ' + second_cnum).rstrip()

        if not name:
            comet['name'] = second_name
            comet['cnum'] = second_cnum
        elif name == second_name:
            comet['cnum'] = cnum or second_cnum
        elif second_name in name:   # e.g., "Anderson" in "Anderson-LINEAR"
            alt_names += [second_name, second_name_num]
            logger and logger.warn(f'Incomplete comet name for {key}: '
                                   f'"{second_name}" vs. "{name}"')
        elif name in second_name:
            alt_names += [name, name_num]
            comet['name'] = second_name
            comet['cnum'] = second_cnum
            logger and logger.warn(f'Incomplete comet name for {key}: '
                                   f'"{name}" vs. "{second_name}"')
        else:
            alt_names += [second_name, second_name_num]
            logger and logger.warn(f'Alternate comet name for {key}: '
                                   f'"{second_name}" vs. "{name}"')

    # Handle designation and fragment
    second_desig = second.get('desig', '')
    if second_desig:
        second_fragment = second.get('fragment', '')
        if comet.get('desig', ''):
            second_desig_frag = second_desig + ('-' + second_fragment).rstrip('-')
            comet.setdefault('alt_desigs', []).append(second_desig_frag)
        else:
            comet['desig'] = second_desig
            comet['fragment'] = second_fragment

    # Merge lists
    for field in ('alt_names', 'alt_desigs', 'alt_frags', 'alt_prefixes', 'old_desigs'):
        list_ = comet.setdefault(field, [])
        list_ += second.get(field, [])

    # Merge other fields
    for field in ('fragment', 'mnum', 'naif_id'):
        value = comet.get(field, '')
        second_value = second.get(field, '')
        if not second_value or value == second_value:
            continue
        elif second_value and not value:
            comet[field] = second_value
        elif second_value != value:
            logger and logger.warn(f'Comet {field} discrepancy for {key}: '
                                   f'"{second_value}" vs. "{value}"')

    for field in ('A', 'Q', 'I', 'O', 'E', 'W'):
        if field in second:
            if (not first_elements) or field not in comet:
                comet[field] = second[field]


def _complete_comets(
    comets: dict[str, dict],
    logger: Logger | None = None
) -> None:
    """Clean up the content of a comet dictionary and fill in missing values.

    Added fields include `year`, `naif_id`, `full_name` (for LID), `aliases`, `lookups`,
    and `ambiguous`.
    """

    # A parent comet inherits the comet number carried by its fragments. The SBDB rows
    # supply the cnum on the fragment entries (e.g. "9" for the pieces of D/1993 F2 =
    # Shoemaker-Levy 9), while the parent may come from a source that supplies no cnum.
    # Do this before _clean_comet so both the bare name and the numbered name survive into
    # the parent's full_name/aliases/lookups.
    for key, comet in comets.items():
        cnum = comet.get('cnum', '')
        if comet.get('fragment', '') and cnum:
            parent = comets.get(key.partition('-')[0])
            if parent is not None and not parent.get('cnum', ''):
                parent['cnum'] = cnum

    # Remove duplicates from lists
    for comet in comets.values():
        _clean_comet(comet, logger=logger)

    # Fill in parent_key
    missing_parents = []
    for key, comet in comets.items():
        fragment = comet.get('fragment', '')
        if fragment:
            parent_key = key.partition('-')[0]
            if parent_key in comets:
                comet['parent_key'] = parent_key
            else:
                missing_parents.append((key, parent_key))
                logger and logger.info(f'Parent comet is missing for {key}')

    # If parent is missing, construct it
    missing_parents.sort()
    for comet_key, parent_key in missing_parents:
        if parent_key in comets:
            continue
        comet = comets[comet_key]
        parent = {}
        for key in ('prefix', 'desig', 'name', 'year', 'ttype', 'cnum'):
            if comet.get(key):
                parent[key] = comet[key]
        for key in ('alt_names', 'alt_desigs'):
            parent[key] = []
            for value in comet[key]:
                match = _FRAG_MATCH.fullmatch(value)
                if match:
                    parent[key].append(match.group(1))

        parent['key'] = comet_key.rpartition('-')[0]
        comets[parent_key] = parent
        logger and logger.info(f'Parent comet {parent_key} constructed')

    # Fill in fragment_keys
    parent_keys = set()
    for key, comet in comets.items():
        parent_key = comet.get('parent_key', '')
        if parent_key:
            parent_keys.add(parent_key)
            parent = comets[parent_key]
            parent.setdefault('fragment_keys', []).append(key)

    for key in parent_keys:
        comets[key]['fragment_keys'].sort()

    # Make sure fragments have all the designations of their parent
    for comet in comets.values():
        parent_key = comet.get('parent_key', '')
        if parent_key:
            parent = comets[parent_key]
        elif comet.get('alt_frags', []):  # if a fragment is an alt name for primary
            parent = comet
        else:
            continue

        parent_desig = parent.get('desig', '')
        parent_desigs = ([parent_desig] if parent_desig else []
                         + [d for d in parent.get('alt_desigs', []) if '-' not in d])
        fragment = comet.get('fragment', '')
        fragments = ([fragment] if fragment else []) + comet.get('alt_frags', [])
        alt_desigs = comet.setdefault('alt_desigs', [])
        for fragment in fragments:
            alt_desigs += [d + '-' + fragment for d in parent_desigs]
        _clean_comet(comet)  # because this could create new duplicate alt_desigs

    # Fill in year
    for comet in comets.values():

        # Fill in year
        years = [-9999]  # if no year is found
        desigs = (comet.get('alt_desigs', []) + [comet.get('desig', '')]
                  + comet.get('old_desigs', []))
        for desig in desigs:
            after_slash = desig.rpartition('/')[-1]
            match = _INT_MATCH.match(after_slash)
            if match:
                years.append(int(match.group(1)))
            comet['year'] = max(years)

    # Fragments get the year of their parent if the year is missing
    for key, comet in comets.items():
        year = comet['year']
        if year == -9999:
            parent_key = comet.get('parent_key', '')
            if parent_key:
                year = comets[parent_key]['year']
                comet['year'] = year
        if year == -9999:
            logger and logger.warn(f'Comet year is unavailable for {key}')

    # Fill in NAIF IDs for minor planets
    for comet in comets.values():
        if 'mnum' in comet and 'naif_id' not in comet:
            comet['naif_id'] = 2000000 + int(comet['mnum'])

    # Fill in full names and aliases
    for comet in comets.values():
        _fill_comet_aliases(comet)


def _clean_comet(
    comet: dict,
    logger: Logger | None = None
) -> None:
    """Clean up the content of a single comet dictionary.

    Remove duplicates from lists, etc.
    """

    # Handle name, cnum, alt_names
    name = comet.get('name', '')
    cnum = comet.get('cnum', '')
    alt_names = comet.setdefault('alt_names', [])
    alt_names.append(name)  # a name without a cnum is always valid
    name_num = name + (' ' + cnum).rstrip(' ')
    comet['alt_names'] = _clean_list(alt_names, [name_num], casefold=True)

    # Handle fragment, alt_frags
    fragment = comet.get('fragment', '')
    alt_frags = comet.setdefault('alt_frags', [])
    if fragment:
        alt_frags.append(fragment)
    comet['alt_frags'] = _clean_list(alt_frags, [fragment])

    # For a named, numbered comet, move the desig to alt_desigs
    desig = comet.get('desig', '')
    desig_frag = desig + ('-' + fragment).rstrip('-')
    if len(comet['prefix']) > 1 and name and desig:
        comet.setdefault('alt_desigs', []).append(desig_frag)
        desig = ''
        desig_frag = ''
        comet['desig'] = ''

    # Handle desig, alt_desigs
    alt_desigs = comet.setdefault('alt_desigs', [])
    comet['alt_desigs'] = _clean_list(alt_desigs, [desig, desig_frag])

    # Check old_desigs
    comet['old_desigs'] = _clean_list(comet.get('old_desigs', []))

    # ttype
    comet['ttype'] = TargetType.COMET


def _clean_list(list_: list[str], extras: list[str] | None = None,
                casefold: bool = False) -> list[str]:
    """Strip duplicates and designation "extras" from a list.

    With `casefold`, duplicates are detected case-insensitively and the better-capitalized
    form is kept (e.g. "PanSTARRS 134" over "PANSTARRS 134"), so only one casing survives.
    """

    if extras is None:
        extras = []

    if casefold:
        extras_uc = {e.upper() for e in extras}
        cleaned_list = []
        index = {}      # uppercased item -> its position in cleaned_list
        for item in list_:
            item_uc = item.upper()
            if item_uc in extras_uc:
                continue
            if item_uc in index:
                pos = index[item_uc]
                if cleaned_list[pos].isupper() and not item.isupper():
                    cleaned_list[pos] = item     # prefer the better-capitalized form
                continue
            index[item_uc] = len(cleaned_list)
            cleaned_list.append(item)
        return cleaned_list

    cleaned_list = []
    for item in list_:
        if item in extras or item in cleaned_list:
            continue
        cleaned_list.append(item)

    return cleaned_list


def _fill_comet_aliases(
    comet: dict,
    logger: Logger | None = None
) -> None:
    """Fill in the comet's `full_name` (for LID), `aliases`, `lookups`, and `ambiguous`.
    """

    # Every prefix
    prefix = comet['prefix']
    prefixes = [prefix] + comet.get('alt_prefixes', [])

    # Every name + number
    name = comet.get('name', '')
    name_nums = []
    if name:
        name_num = name + (' ' + comet.get('cnum', '')).rstrip(' ')
        name_nums.append(name_num)
    name_nums += comet.get('alt_names', [])

    # Every dash + fragment
    fragments = [comet.get('fragment', '')] + comet.get('alt_frags', [])
    dash_frags = [('-' + f).rstrip('-') for f in fragments]

    desig = comet.get('desig', '')

    aliases = []

    # Handle a numbered comet
    if len(prefix) > 1:
        # Every number + prefix + name + number + fragment
        if name:
            for p in prefixes:
                for nn in name_nums:
                    for df in dash_frags:
                        aliases.append(p + '/' + nn + df)
        # Otherwise, every numbered prefix + primary designation + every fragment
        else:
            for p in prefixes:
                for df in dash_frags:
                    aliases.append(p + desig[1:] + df)

    # Handle an unnumbered comet
    else:
        # Every prefix + primary designation + fragment + (name)
        for p in prefixes:
            for nn in name_nums:
                for df in dash_frags:
                    aliases.append(p + '/' + desig[2:] + df + ' (' + nn + df + ')')
                    aliases.append(p + '/' + desig[2:] + df + ' (' + nn + ')')

        # Every prefix + primary designation + fragment
        for p in prefixes:
            for df in dash_frags:
                aliases.append(p + '/' + desig[2:] + df)

    # If a comet has a name and a cnum, that's enough for an alias
    if name and comet.get('cnum', ''):
        for df in dash_frags:
            aliases.append(name + ' ' + comet['cnum'] + df)

    # Append all remaining designations
    aliases += comet.get('alt_desigs', [])
    aliases += comet.get('old_desigs', [])

    aliases = _clean_list(aliases)
    comet['full_name'] = aliases[0]
    comet['aliases'] = aliases[1:]

    # Create the list of lookup keys
    lookups = [comet['key']] + list(aliases)
    ambiguous = []

    # Apostrophes in names are often overlooked
    for char in "'`":
        if char in name:
            extra_name_nums = [nn.replace(char, '') for nn in name_nums if char in nn]
            name_nums += extra_name_nums
            lookups += [key.replace(char, '') for key in lookups if char in key]

    # A name without a prefix might be unambiguous
    for nn in name_nums:
        if nn[-1].isdigit():
            for df in dash_frags:
                lookups.append(nn + df)
        else:
            for df in dash_frags:
                ambiguous.append(nn + df)

    # It's valid to include the number in front of any designation for a numbered comet
    if len(comet['prefix']) > 1:
        digits = comet['key'][:-1]
        extras = [digits + key for key in lookups if key[1] == '/']
        lookups += extras

    comet['lookups'] = _clean_list(lookups, casefold=True)
    comet['ambiguous'] = _clean_list(ambiguous)


def _space_dash_permutations(
    strings: list[str],
) -> list[str]:
    """A list containing every permutation of dashes and spaces, while also replacing
    underscores.
    """

    def _swapper(keys, locs):
        if not locs:
            return keys

        loc = locs[-1]
        options = _swapper(keys, locs[:-1])
        spaced = [key[:loc] + ' ' + key[loc+1:] for key in options]
        dashed = [key[:loc] + '-' + key[loc+1:] for key in options]
        return spaced + dashed

    results = []
    for string in strings:
        locs = [i for i, c in enumerate(string) if c in ' -_']
        results += _swapper([string], locs)

    return list(results)


def _copy_comet(comet: dict) -> dict:
    """Deep copy of a comet dictionary."""

    new_comet = comet.copy()
    for key, value in new_comet.items():
        if isinstance(value, list):
            new_comet[key] = list(value)

    return new_comet


__all__ = ['_build_comet_dicts']

##########################################################################################
