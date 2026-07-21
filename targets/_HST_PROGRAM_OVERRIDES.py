##########################################################################################
# _HST_PROGRAM_OVERRIDES.py
##########################################################################################

from targets.targettype import TargetType as TT

_NH_SURVEY_DICT = {
    'ttype'      : TT.TRANS_NEPTUNIAN_OBJECT,
    'name'       : 'New Horizons survey field',
    'description': 'KBO survey field from the search for a New Horizons flyby candidate.'
}

_HST_PROGRAM_OVERRIDES = {

    # Not a planetary observation
    'ANTISUN' : {'reject': True},       # anti-solar pointings (e.g. programs 1431, 1478)
    'ASLAG'   : {'reject': True},       # anti-sun lag pointing (program 3069)
    '8800_*'  : {'reject': True},

    # New Horizons survey
    '6497_1'  : {'dict': _NH_SURVEY_DICT, 'done': True},
    '12535_*' : {'dict': _NH_SURVEY_DICT, 'done': True},
    '12887_1' : {'dict': _NH_SURVEY_DICT, 'done': True},
    '13311_1' : {'dict': _NH_SURVEY_DICT, 'done': True},
    '13633_*' : {'dict': _NH_SURVEY_DICT, 'done': True},
    '13663_1' : {'dict': _NH_SURVEY_DICT, 'done': True},
    '16183_*' : {'dict': _NH_SURVEY_DICT, 'done': True},

    # Unknown KBO
    '15344_30': {
        'done': True,
        'dict': {'ttype': TT.TRANS_NEPTUNIAN_OBJECT,
                 'desig': '2011 UH413',
                 'full_name': '2011 UH413',
                 'description': 'Not found at in the Minor Planet Center database;\n'
                                'Discovery was retracted according to MPEC 2020-N22.'}
    },

    # FITS header overrides
    '6841_2'  : {'MT_LV1_3': ',Q=0.5320503'},           # header has Q=.05320503 (10x off)
    '9678_1'  : {'TARGNAME': '50000 QUAOAR'},           # was "OBJECTX"
    '10545_22': {'TARKEY2' : 'HAUMEA'},                 # was "KBO-Santa"
    '10781_11': {'MT_LV1_4': ',Q=5.844212514611897'},   # header has Q=10.7296 but fixed
                                                        # in TARG_ID 10781_12, TARGNAME =
                                                        # "2000EC98-CORRECTION"
    '11113_14': {'TARGNAME': '05XU100'},                # was "05UX100" (transposed)
    '11113_52': {'TARGNAME': '05SD278'},                # was "05SD258"
    '11644_91': {'MT_LV1_1': 'TYPE=ASTEROID,A=39.57658392,E=0.1259586707,'
                             'I=14.5915709,O=10.656'},  # header I=34.59 (typo for 14.59);
                                                        # all other elements match
                                                        # (118228) 1996 TQ66
    '15108_1'   : {'TARGNAME': 'K14Od3S'},              # was "K14OD3S" (capitalized)

    # Occultation studies. Each occultation records two targets: the occulting body (set
    # via MT_LV1_1='STD=...', or by name for the Arrokoth campaign) plus the occulted star,
    # supplied as an added 'dict'. Because the 'dict' has no 'done' flag, the mechanism
    # appends it to the identified bodies rather than replacing them. The occulted-star
    # identities come from Gaia DR3 cross-matches of the occulted-star pointings.
    '2771_*'  : {'MT_LV1_1': 'STD=SATURN RINGS',        # HSP Saturn-rings occultation
                 'dict': {'ttype'      : TT.STAR,
                          'name'       : 'GSC 06323-01466',
                          'full_name'  : 'GSC 06323-01466',
                          'aliases'    : ['2MASS J20131821-2027044', 'TIC 71355553',
                                          'Gaia DR3 6854313950930655104',
                                          'Gaia DR2 6854313950930655104'],
                          'description': 'Based on the SIMBAD Astronomical Database\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '20 hours 13 minutes 18.2363258 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-20 degrees 27 minutes 04.612233 seconds'}},

    '3373_*'  : {'MT_LV1_1': 'STD=SATURN RINGS',        # HSP Saturn-rings occultation
                 'dict': {'ttype'      : TT.STAR,
                          'name'       : 'GSC 05800-00460',
                          'full_name'  : 'GSC 05800-00460',
                          'aliases'    : ['2MASS J21470287-1458582', 'TIC 155841905',
                                          'Gaia DR3 6838627832714078336',
                                          'Gaia DR2 6838627832714078336'],
                          'description': 'Based on the SIMBAD Astronomical Database\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '21 hours 47 minutes 02.8797358 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-14 degrees 58 minutes 58.517862 seconds'}},

    '3375_*'  : {'MT_LV1_1': 'STD=SATURN RINGS',        # HSP Saturn-rings occultation
                 'dict': {'ttype'      : TT.STAR,       # GSC 6347-01433
                          'name'       : 'TYC 6347-1433-1',
                          'full_name'  : 'TYC 6347-1433-1',
                          'aliases'    : ['GSC 6347-01433', '2MASS J21190535-1639491',
                                          'TIC 288236294',
                                          'Gaia DR3 6835605588782360704',
                                          'Gaia DR2 6835605588782360704',
                                          'Gaia DR1 6835605584487000576'],
                          'description': 'Based on the SIMBAD Astronomical Database\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '21 hours 19 minutes 05.3612358528 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-16 degrees 39 minutes 49.155924132 seconds'}},

    '4193_*'  : {'MT_LV1_1': 'STD=TITAN',               # HSP Titan occ (header GSC6349-01493)
                 'dict': {'ttype'      : TT.STAR,
                          'name'       : '2MASS J20584686-1811327',
                          'full_name'  : '2MASS J20584686-1811327',
                          'aliases'    : ['Gaia DR3 6881831634595281408'],
                          'description': 'Based on the Gaia DR3 catalog\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '20 hours 58 minutes 46.8562381 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-18 degrees 11 minutes 33.056217 seconds'}},

    '4225_*'  : {'MT_LV1_1': 'STD=SATURN',              # HSP Saturn occultation
                 'dict': {'ttype'      : TT.STAR,
                          'name'       : 'GSC 06349-01499',
                          'full_name'  : 'GSC 06349-01499',
                          'aliases'    : ['2MASS J20593342-1809489', 'UCAC4 360-208929',
                                          'Gaia DR3 6881829912312797312',
                                          'Gaia DR2 6881829912312797312'],
                          'description': 'Based on the SIMBAD Astronomical Database\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '20 hours 59 minutes 33.4128641 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-18 degrees 09 minutes 49.067866 seconds'}},

    '4257_13' : {'MT_LV1_1': 'STD=MARS',                # HSP Mars occ (AGK+26D0765)
                 'dict': {'ttype'      : TT.STAR,
                          'name'       : 'HD 54126',
                          'full_name'  : 'HD 54126',
                          'aliases'    : ['HIP 34487', 'TYC 1904-316-1', 'SAO 79105',
                                          'BD+26 1463', 'GSC 01904-00316', 'PPM 97096',
                                          '2MASS J07084906+2637461',
                                          'Gaia DR3 883183509581729536',
                                          'Gaia DR2 883183509581729536',
                                          'Gaia DR1 883183505285058432'],
                          'description': 'Based on the SIMBAD Astronomical Database\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '07 hours 08 minutes 49.0772878 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '+26 degrees 37 minutes 45.361386 seconds'}},
    '4257_14' : {'MT_LV1_1': 'STD=MARS'},
    '4257_22' : {'MT_LV1_1': 'STD=MARS'},
    '4257_17' : {'MT_LV1_1': 'STD=URANUS',              # HSP Uranus occ (U111)
                 'dict': {'ttype'      : TT.STAR,
                          'name'       : '2MASS J19361883-2202544',
                          'full_name'  : '2MASS J19361883-2202544',
                          'aliases'    : ['Gaia DR3 6771955749711650304'],
                          'description': 'Based on the Gaia DR3 catalog\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '19 hours 36 minutes 18.8190995 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-22 degrees 02 minutes 54.695121 seconds'}},
    '4257_18' : {'MT_LV1_1': 'STD=URANUS'},

    # Triton occultations (FGS). STD=TRITON applies to every visit via '7489_*'; each
    # occulted-star visit adds its own star. 7489_9 (TR180-T) points at Triton itself
    # (JPL Horizons puts Triton 1.7" from its header position), not at a background star,
    # so it carries no star dict and resolves to Triton via '7489_*'.
    '7489_*'  : {'MT_LV1_1': 'STD=TRITON'},
    '7489_1'  : {'dict': {'ttype'      : TT.STAR,        # TR176
                          'name'       : '2MASS J20025129-2000571',
                          'full_name'  : '2MASS J20025129-2000571',
                          'aliases'    : ['TIC 74699322', 'Triton 176',
                                          'Gaia DR3 6866247122425234560',
                                          'Gaia DR2 6866247122425234560'],
                          'description': 'Based on the SIMBAD Astronomical Database\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '20 hours 02 minutes 51.3002486 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-20 degrees 00 minutes 57.275213 seconds'}},
    '7489_5'  : {'dict': {'ttype'      : TT.STAR,        # TR180
                          'name'       : 'TYC 6321-1030-1',
                          'full_name'  : 'TYC 6321-1030-1',
                          'aliases'    : ['GSC 06321-01030', 'BD-20 5772', 'CPD-20 7749',
                                          'PPM 270486', '2MASS J19573225-2018187',
                                          'TIC 242015278',
                                          'Gaia DR3 6866889546455545216',
                                          'Gaia DR2 6866889546454432768',
                                          'Gaia DR1 6866889542155142912'],
                          'description': 'Based on the SIMBAD Astronomical Database\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '19 hours 57 minutes 32.2577332 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-20 degrees 18 minutes 18.761489 seconds'}},

    '7490_*'  : {'MT_LV1_1': 'STD=TRITON',              # FGS; occulted star is a double
                 'dict': {'ttype'      : TT.STAR,       # TR148 (Tr148A/Tr148B)
                          'name'       : '2MASS J19410037-2051411',
                          'full_name'  : '2MASS J19410037-2051411',
                          'aliases'    : ['Gaia DR3 6868127596549168768'],
                          'description': 'Based on the Gaia DR3 catalog\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '19 hours 41 minutes 00.3716026 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-20 degrees 51 minutes 41.165583 seconds'}},

    '8105_*'  : {'MT_LV1_1': 'STD=PLUTO',               # FGS Pluto occultation
                 'dict': {'ttype'      : TT.STAR,       # PLUTO-OS
                          'name'       : '2MASS J16324364-1038237',
                          'full_name'  : '2MASS J16324364-1038237',
                          'aliases'    : ['TIC 40785288',
                                          'Gaia DR3 4332151374799793536',
                                          'Gaia DR2 4332151374799793536'],
                          'description': 'Based on the SIMBAD Astronomical Database\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '16 hours 32 minutes 43.6321929 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-10 degrees 38 minutes 23.650864 seconds'}},

    '15003_*' : {'TARKEY1' : 'KBO',                     # FGS 2014 MU69 (Arrokoth) occ
                 'TARGNAME': '2014MU69',
                 'dict': {'ttype'      : TT.STAR,       # STAR20170717
                          'name'       : '2MASS J19000829-2039378',
                          'full_name'  : '2MASS J19000829-2039378',
                          'aliases'    : ['Gaia DR3 4084968615275610752'],
                          'description': 'Based on the Gaia DR3 catalog\n'
                                         'Right Ascension, ICRS coord, ep=J2000: '
                                         '19 hours 00 minutes 08.2914738 seconds\n'
                                         'Declination, ICRS coord, ep=J2000: '
                                         '-20 degrees 39 minutes 37.975240 seconds'}},
}

__all__ = ['_HST_PROGRAM_OVERRIDES']

##########################################################################################
