##########################################################################################
# _TARGNAME_PREFIX_SUFFIX_PATTERNS.py
##########################################################################################
"""A maintained list of grep patterns for words that might be appended to the end of an
HST TARGNAME without constraining the taget.

These are used by `hst_repairs()` _before_ all the more important patterns found in that
file are interpreted.
"""

_TARGNAME_PREFIX_PATTERNS = [
    r'BL',
    r'OBJ',
    r'RD',
    r'SKY-NEAR',
]

_TARGNAME_SUFFIX_PATTERNS = [
    r'ACQ',
    r'ACS(POL)?',
    r'ATMOS',
    r'AUR(ORA)?[NS]?',
    r'BCKSKY',
    r'BLANK',
    r'CALIB',
    r'CML',
    r'COPY',
    r'COS(|FUV|NUV)',
    r'CYC(|L|LE)',
    r'DAWN',
    r'DAY',
    r'DUSK',
    r'EGRESS',
    r'EPOCH',
    r'EUV',
    r'FINAL',
    r'FIX[AB]?',
    r'FOC',
    r'FOS[AB]?',
    r'FUV',
    r'FUV',
    r'GHRS',
    r'HILAT',
    r'HIRES',
    r'HRC',
    r'HRS',
    r'IM',
    r'INGRESS',
    r'JPL',
    r'LIMB',
    r'LONG?',
    r'LORES',
    r'MAPS?',
    r'NICMOS',
    r'NORTH',
    r'NOTRAN(|SIT)',
    r'NPR',
    r'NUV',
    r'OBS',
    r'OCC',
    r'OFF(SET)?',
    r'OFFIMPACTS?',
    r'OPP',
    r'ORB(IT)?',
    r'ORBCOV',
    r'OVAL[NS]?',
    r'PC',
    r'PJ',
    r'POS(ITION)?',
    r'QUAD',
    r'REP',
    r'ROT',
    r'SCAN',
    r'SLEW',
    r'SOUTH',
    r'SPEC(TRA)?',
    r'SPR',
    r'STIS(|NUV)',
    r'TOO',
    r'TRACK',
    r'TRANSIT[AB]?',
    r'UPDATE',
    r'UVI?S',
    r'VISIT',
    r'V',
    r'WF',
    r'WFC',
    r'WFC3',
    r'WFPC2',
]

_TARGNAME_SUFFIX_PATTERNS_NO_TAIL = [
    r'\d+LONG?',
    r'\d+-?[NSEW]',
    r'\dORBIT',
    r'[NSEW]',
    r'[NSEW]-?\d+[AB]?\d?',
    r'NS',
    r'EW',
    r'EQ',
    r'\d+DEG[NS]?',
    r'20[0-3]\d-?[01]\d-?[0-3]\d',  # "-yyyymmdd" suffix
]

##########################################################################################
