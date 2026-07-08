##########################################################################################
# targets/cometdb/repair_comet.py
##########################################################################################
"""
---------------
repair_comet.py
---------------

This function "repairs" any comet dictionary that contains out-of-date or incorrect
information about a comet, as extracted from one record in an online resource.

This file is to be actively maintained, such that known errors and inconsistencies in the
online source files are corrected before they become part of the database.
"""

import re

# (old designation, repaired designation)
_DESIG_REPAIRS = [('D/1977 C1', 'D/1977 DV3'),
                  ('C/1977 H1', 'C/1977 HG'),
                  ('P/1992 YF5', '173P'),
                  ('P/1999 J6', 'P/2010 H3'),
                  ('P/2004 V9', 'P/2010 H3')]


def repair_comet(comet: dict) -> None:
    """Update any out-of-date or incorrect information in a comet dictionary.

    Parameters:
        comet: Parameters describing a comet as extracted from one record in an online
            resource.
        logger: Optional Logger to use.

    Notes:
        These are the optional fields of the dictionary:

        * `prefix` (str): The designation before the slash, either a single letter ("P",
          "C", etc.) or, for numbered comets, the digits followed by one letter.
        * `desig` (str): The designation of the form "[PCXAI]/<year> <letters><digits>".
          For named and numbered comets, this value is absent; any designation appears in
          the `aliases` list instead. It never includes a comet number.
        * `name` (str): The discovery name of the object, if any. This excludes a
          discovery number (e.g., "Tempel" not "Tempel 2").
        * `cnum` (str): The comet number for the discovery name, if any and if known.
        * `fragment` (str): The fragment identifier, if any, excluding any leading dash.
        * `alt_prefixes` (list[str]): A list of alternative prefixes, e.g., ["72D"] for a
          dead comet that is primarily referenced with prefix "72P".
        * `alt_frags` (list[str]): A list of alternative fragment identifiers, excluding
          any leading dash.
        * `alt_names` (list[str]): A list of alternative discover names and optional
          numbers, e.g., "Anderson" for 148P/Anderson-Linear. Unlike `name`, each name
          includes the `cnum` if any, e.g., "Tempel 2" for 10P/Tempel.
        * `aliases` (list[str]): A list of old or non-standard designations, e.g., "1993e"
          or "1994 X".
        * `mnum` (str): The minor planet number, if any.
        * `naif_id` (int): The NAIF ID, if any.
        * `A`, `Q`, `I`, `O`, `E`, `W`: Approximate orbital elements if known. "A" for
          semimajor axis in AU; "Q" for perihelion distance in AU; "I" for inclination in
          degrees; "O" for ascending node in degrees; "E" for eccentricity; "W" for
          argument of perihelion in degrees.
    """

    # Fix inconsistencies
    name = comet.get('name', '')
    name = (name.replace('PANSTARRS', 'PanSTARRS')
                .replace('PanSTARR-', 'PanSTARRS-')  # error in SBN table
                .replace('CATALINA', 'Catalina')
                .replace('BATTERS', 'BATTeRS')
                .replace('duToit', 'du Toit')
                .replace('Groller', 'Groeller')
                .replace('XingMing', 'Xingming')
                .replace('Nevsky', 'Nevski')
                .replace('Tsuchinsahn', 'Tsuchinshan')
                .replace('CSS', 'Catalina')
                .replace(' comet', ' Comet'))
    comet['name'] = name

    prefix = comet['prefix']
    desig = comet.get('desig', '')

    # 141P/Machholz 2 == 141P/Machholz 2-A
    if prefix == '141P' and comet.get('fragment', '') == 'A':
        comet['alt_frags'] = ['A']
        comet['fragment'] = ''

    # 141P/Machholz 2-B == 141P/Machholz 2-H
    elif prefix == '141P' and comet.get('fragment', '') == 'H':
        comet['alt_frags'] = ['H']
        comet['fragment'] = 'B'

    # 69P/Taylor == 69P/Taylor-B
    elif prefix == '69P' and comet.get('fragment', '') == 'B':
        comet['alt_frags'] = ['B']
        comet['fragment'] = ''

    # 72D is more commonly referred to as 72P
    elif prefix == '72D':
        comet['alt_prefixes'] = ['72D']
        comet['prefix'] = '72P'

    # 85P is more commonly referred to as 85D
    elif prefix == '85P':
        comet['alt_prefixes'] = ['85P']
        comet['prefix'] = '85D'

    # "Fuls 2" is identified twice in the SBN file
    elif prefix == '407P' and 'Fuls 2' in comet.get('alt_names', []):
        comet['alt_names'].remove('Fuls 2')

    # This is a typo in the name of "C/2015 E61-B" in the Horizons file
    elif desig == 'C/2015 E61':
        comet['desig'] = 'C/2015 ER61'

    # Other designation repairs
    if desig:
        for old_desig, repair in _DESIG_REPAIRS:
            if desig == old_desig:
                alt_desigs = comet.setdefault('alt_desigs', [])
                if old_desig not in alt_desigs:
                    alt_desigs.append(old_desig)

                if repair[0].isdigit():
                    parts = repair.split('/')
                    comet['prefix'] = parts[0]
                    comet['desig'] = parts[0][-1] + '/' + parts[-1]
                else:
                    comet['prefix'] = repair[0]
                    comet['desig'] = repair

                break

##########################################################################################
