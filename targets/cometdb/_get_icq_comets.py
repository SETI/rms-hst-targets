##########################################################################################
# cometdb/_get_icq_comets.py
##########################################################################################

from logging import Logger

import bs4

from ._utils import _compare_content, _fetch, _read_content

_ICQ_URL = 'http://www.icq.eps.harvard.edu/names1.html'
_ICQ_BASENAME = 'icq_names1.txt'

_COLUMN_TESTS = [(3, 'PCDX'), (4, '/ '), 9, 15, (16, '('), (45, ') '), 46, (47, '= '),
                 48, (49, '1 '), 56, (57, '= '), 58, (59, '1- ')]

def _get_icq_comets(
    update: bool = False,
    logger: Logger | None = None
) -> tuple[bool, list[dict]]:
    """Load the list of comets from the Minor Planet Center.

    Parameters:
        update: True to re-read the website; False to use the local cache.
        logger: Optional Logger to use.

    Returns:
        (`changed`, `comets`), where `changed` is True if the online content is new;
        `comets` is a list of dictionaries of comet information.
    """

    # Retrieve content
    if update:
        request = _fetch(_ICQ_URL, logger=logger)
        if request is None:
            update = False  # fall back to the cached copy
        else:
            soup = bs4.BeautifulSoup(request.content, 'html.parser')
            content = soup.find('pre').text
    if not update:
        content = _read_content(_ICQ_BASENAME, logger)

    recs = content.split('\n')
    recs = [rec.rstrip() for rec in recs if rec.rstrip()]

    # Extract comet info from table
    comets = []
    for k, rec in enumerate(recs):
        rec = rec.ljust(60)

        error_found = False
        for test in _COLUMN_TESTS:
            col, chars = test if isinstance(test, tuple) else (test, ' ')
            if rec[col] not in chars:
                logger and logger.error(f'Mis-aligned column at record[{k}][{col}]: '
                                        f'"{rec}"')
                error_found = True
                break
        if error_found:
            continue

        prefix = rec[:4].lstrip()
        year = rec[5:9].replace(' ', '')
        suffix = rec[9:15].rstrip()
        suffix, _, fragment = suffix.partition('-')
        name = rec[17:45].rstrip(' )')

        years = []
        if year:
            desig = prefix[-1] + '/' + year + suffix
            years.append(year)
        else:
            desig = ''

        # Handle old designations like "1992j"
        old_desigs = []
        old_desig = rec[49:57].rstrip()
        if old_desig:
            years.append(old_desig[:4])
        #     old_desigs.append(old_desig)

        # Handle old designations like "1993 XIII"
        old_desig = rec[59:].rstrip()
        if old_desig and old_desig[0] == '1':
            years.append(old_desig[:4].replace(' ', ''))
            if old_desig[4:]:
                old_desigs.append(years[-1] + old_desig[4:])

        # Update the name of a "Great" comet
        year = years[0]
        if ' comet' in name:
            name += ' of ' + year

        comet = {'prefix': prefix, 'desig': desig, 'name': name, 'old_desigs': old_desigs,
                 'fragment': fragment}
        comets.append(comet)

    # Separate numbered and unnumbered comets; key numbered comets by number + fragment
    unnumbered = []
    by_number = {}
    for comet in comets:
        if len(comet['prefix']) > 1:
            key = comet['prefix'] + ('-' + comet['fragment']).rstrip('-')
            by_number.setdefault(key, []).append(comet)
        else:
            unnumbered.append(comet)

    # For each numbered comet, merge the desigs and old_desigs of all apparitions
    for key, dict_list in by_number.items():
        comet = dict_list[-1].copy()
        desigs = []
        old_desigs = []
        for dict_ in dict_list:
            desig = dict_['desig']
            if desig:
                desig_frag = desig + ('-'  + dict_['fragment']).rstrip('-')
                desigs.append(desig_frag)
            old_desigs += dict_['old_desigs']

        comet['alt_desigs'] = desigs
        comet['old_desigs'] = old_desigs
        by_number[key] = comet

    comets = list(by_number.values()) + unnumbered
    if update:
        changed = _compare_content(content, _ICQ_BASENAME, logger=logger)
    else:
        changed = False

    return changed, comets


__all__ = ['_get_icq_comets']

##########################################################################################
