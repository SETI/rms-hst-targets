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
    'ANTISUN'   : {'reject': True},     # anti-solar pointings (e.g. programs 1431, 1478)
    'ASLAG'     : {'reject': True},     # anti-sun lag pointing (program 3069)
    '8800_*'    : {'reject': True},

    # New Horizons survey
    '6497_1'    : {'dict': _NH_SURVEY_DICT},
    '12535_*'   : {'dict': _NH_SURVEY_DICT},
    '12887_1'   : {'dict': _NH_SURVEY_DICT},
    '13311_1'   : {'dict': _NH_SURVEY_DICT},
    '13633_*'   : {'dict': _NH_SURVEY_DICT},
    '13663_1'   : {'dict': _NH_SURVEY_DICT},
    '16183_*'   : {'dict': _NH_SURVEY_DICT},

    # Unknown KBO
    '15344_30'  : {
        'dict': {'ttype': TT.TRANS_NEPTUNIAN_OBJECT,
                 'desig': '2011 UH413',
                 'full_name': '2011 UH413',
                 'description': 'Not found at in the Minor Planet Center database;\n'
                                'Discovery was retracted according to MPEC 2020-N22.'}
    },

    # FITS header overrides
    '6841_2'    : {'MT_LV1_3': ',Q=0.5320503'},         # header has Q=.05320503 (10x off)
    '9678_1'    : {'TARGNAME': '50000 QUAOAR'},         # was "OBJECTX"
    '10545_22'  : {'TARKEY2' : 'HAUMEA'},               # was "KBO-Santa"
    '10781_11'  : {'MT_LV1_4': ',Q=5.844212514611897'}, # header has Q=10.7296 but fixed
                                                        # in TARG_ID 10781_12, TARGNAME =
                                                        # "2000EC98-CORRECTION"
    '11113_14'  : {'TARGNAME': '05XU100'},              # was "05UX100" (transposed)
    '11113_52'  : {'TARGNAME': '05SD278'},              # was "05SD258"
    '11644_91'  : {'MT_LV1_1': 'TYPE=ASTEROID,A=39.57658392,E=0.1259586707,'
                               'I=14.5915709,O=10.656'},  # header I=34.59 (typo for
                                                          # 14.59); all other elements
                                                          # match 118228 1996 TQ66
    '15108_1'   : {'TARGNAME': 'K14Od3S'},              # was "K14OD3S" (capitalized)

    # Occultation studies
    '2771'      : {'MT_LV1_1': 'STD=SATURN'},           # HSP Saturn occ
    '3375'      : {'MT_LV1_1': 'STD=SATURN'},           # HSP Saturn occ
    '7489'      : {'MT_LV1_1': 'STD=TRITON'},           # FGS fixed, TARGNAME="TR\d+.*"
    '7490'      : {'MT_LV1_1': 'STD=TRITON'},           # FGS fixed, TARGNAME="TR\d+.*"
    '8105'      : {'MT_LV1_1': 'STD=PLUTO'},            # FGS fixed, TARGNAME="PLUTO-OS"
    '15003'     : {'TARKEY1' : 'KBO',
                   'TARGNAME': '2014MU69'},             # FGS occ campaign
}

__all__ = ['_HST_PROGRAM_OVERRIDES']

##########################################################################################
