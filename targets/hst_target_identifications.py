##########################################################################################
# target_identifications/__init__.py
##########################################################################################
#
# To import:
#   from target_identifications import hst_target_identifications
#
# To use:
#   hst_target_identifications(spt_hdulist[0].header)
# returns a list of Target_Identification tuples. Each tuple contains:
#   (name, alt_designations, body_type, description, lid)
# where:
#   name                the preferred name;
#   alt_designations    a list of strings indicating alternative names;
#   target_type           "Asteroid", "Centaur", etc.;
#   description         a list of strings, to be separated by newlines inside the
#                       description attribute of the XML Target_Identification object;
#   lid                 the LID of the object, omitting "urn:...:target:".
#
# The input argument is the first header of the SPT/SHM/SHF file, using the HDU list
# returned by astropy.io.fits.open.
##########################################################################################

import os
import re
import sys

import pdslogger
import translator

from . import lids
from .standard_bodies import standard_body_identifications
from .minor_planets   import minor_planet_identifications
from .comets          import comet_identifications

standard_body_identifications.IGNORE_EXTRA_NAMES = True
minor_planet_identifications.IGNORE_EXTRA_NAMES = True
comet_identifications.IGNORE_EXTRA_NAMES = True

DEBUG = False           # Set to True to see lots of useful debugging info
standard_body_identifications.DEBUG = DEBUG
minor_planet_identifications.DEBUG = DEBUG
comet_identifications.DEBUG = DEBUG
comet_identifications.DEBUG = DEBUG

##########################################################################################
# SPT_REPAIRS is a manually managed list of target identifications that cannot be inferred
# from targeting info in the SPT file. Key is TARG_ID or PROPOSID.
#
# If the returned item is a dictionary, use its values to override info found in the SPT
# lookup. This is an easy way to fix incorrect or missing info, while still ensuring that
# the info returned is up to date and standard checks are performed.
#
# If the returned item is a list, it should be the exact list of target identification
# tuples and will be returned as is.
##########################################################################################

# NOTE that {'MT_LV1_1': 'FILE='} suppresses the checking of orbital elements.

SPT_REPAIRS = {
    '2442'      : {'TARGNAME': 'COMET-SL-1991A1'},  # was a random string
    '2569_'     : {'MT_LV1_1': 'STD=PLUTO'},        # missing TARG_ID, no MT_LV1
    '2771'      : {'MT_LV1_1': 'STD=SATURN'},       # HSP Saturn occ
    '2890_9'    : {'MT_LV1_1': 'STD=SATURN'},       # missing MT_LV1
    '2891_10'   : {'MT_LV1_1': 'STD=TITAN'},        # missing MT_LV1
    '3064_1'    : {'MT_LV1_1': 'FILE='},            # missing MT_LV1
    '3373'      : {'MT_LV1_1': 'STD=SATURN'},       # HSP Saturn occ
    '3375'      : {'MT_LV1_1': 'STD=SATURN'},       # HSP Saturn occ
    '4193'      : {'MT_LV1_1': 'STD=TITAN'},        # HSP Titan occ
    '4225'      : {'MT_LV1_1': 'STD=SATURN'},       # HSP Saturn occ
    '4257_13'   : {'MT_LV1_1': 'STD=MARS'},         # HSP Mars occ
    '4257_14'   : {'MT_LV1_1': 'STD=MARS'},
    '4257_22'   : {'MT_LV1_1': 'STD=MARS'},
    '4257_15'   : {'MT_LV1_1': 'STD=JUPITER'},      # HSP Jupiter occ
    '4257_16'   : {'MT_LV1_1': 'STD=JUPITER'},
    '4257_23'   : {'MT_LV1_1': 'STD=JUPITER'},
    '4257_17'   : {'MT_LV1_1': 'STD=URANUS'},       # HSP Uranus occ
    '4257_18'   : {'MT_LV1_1': 'STD=URANUS'},
    '4257_24'   : {'MT_LV1_1': 'STD=URANUS'},
    '5834_1'    : {'TARGNAME': 'C1984K1 SHOEMAKER'},# was "COMET-SHOEMAKER-1984K1"
    '5834_2'    : {'TARKEY1': 'COMET SHOEMAKER 87O-86XIV',
                                                    # was "SHOEMAKER 87O-85XIV"
                   'TARGNAME': 'C1987H1 SHOEMAKER'},# was "COMET-SHOEMAKER-1987H1"
    '6736'      : {'TARKEY1' : 'COMET C/1996 B2 (HYAKUTAKE)',
                   'TARGNAME': 'C/1996 B2'},        # was "COMET B2-NUCLEUS", "B2"
    '7489'      : {'MT_LV1_1': 'STD=TRITON'},       # FGS fixed, TARGNAME="TR\d+.*"
    '7490'      : {'MT_LV1_1': 'STD=TRITON'},       # FGS fixed, TARGNAME="TR\d+.*"
    '7594'      : {'TARKEY2' : 'COMET C/1997 BA6'}, # year was 1996
    '8105'      : {'MT_LV1_1': 'STD=PLUTO'},        # FGS fixed, TARGNAME="PLUTO-OS"
    '8699_2'    : {'TARGNAME': 'ASHBROOK-JACKSON',  # was "ASHBROOK"
                   'MT_LV1_1': 'FILE='},            # revised elements
    '8699_4'    : {'MT_LV1_1': 'FILE='},            # revised elements
    '8699_15'   : {'MT_LV1_1': 'FILE='},            # revised elements
    '8699_9'    : {'TARGNAME': 'SWIFT-GEHRELS'},    # was "SWIFT"
    '9110_28'   : {'TARGNAME': '50000 QUAOAR'},     # was "MINIXENA"
    '9386_150'  : {'MT_LV1_1': 'FILE='},            # revised elements
    '9678_1'    : {'TARGNAME': '50000 QUAOAR',      # was "OBJECTX"
                   'MT_LV1_1': 'FILE='},            # revised elements
    '9713_1'    : {'MT_LV1_1': 'FILE='},            # revised elements
    '9991_1'    : {'TARGNAME': '1999 RZ253'},       # was "ANY"
    '10268_3'   : {'MT_LV1_1': 'FILE='},            # changed elements
    '10514_1'   : {'TARGNAME': '80806'},            # sometimes "ANY"
    '10514_3'   : {'TARGNAME': '79360'},            # sometimes "ANY"
    '10514_4'   : {'TARGNAME': '99OJ4'},            # sometimes "ANY"
    '10514_5'   : {'TARGNAME': '82075'},            # sometimes "ANY"
    '10514_14'  : {'TARGNAME': '49036'},            # sometimes "ANY"
    '10514_16'  : {'TARGNAME': '98WG24'},           # sometimes "ANY"
    '10514_18'  : {'TARGNAME': '69990'},            # sometimes "ANY"
    '10514_33'  : {'TARGNAME': '99RB216'},          # sometimes "ANY"
    '10514_35'  : {'TARGNAME': '99RN215'},          # sometimes "ANY"
    '10514_55'  : {'TARGNAME': '00QC226'},          # sometimes "ANY"
    '10514_56'  : {'TARGNAME': '54598'},            # sometimes "ANY"
    '10514_58'  : {'TARGNAME': '00QN251'},          # sometimes "ANY"
    '10514_59'  : {'TARGNAME': '00WK183'},          # sometimes "ANY"
    '10514_85'  : {'TARGNAME': '88267'},            # sometimes "ANY"
    '10514_111' : {'TARGNAME': '01QP297'},          # sometimes "ANY"
    '10514_122' : {'TARGNAME': '01RX143'},          # sometimes "ANY"
    '10514_123' : {'TARGNAME': '01RZ143'},          # sometimes "ANY"
    '10514_129' : {'TARGNAME': '01YH140'},          # sometimes "ANY"
    '10514_174' : {'TARGNAME': '02PP149'},          # sometimes "ANY"
    '10514_191' : {'TARGNAME': '02VU130'},          # sometimes "ANY"
    '10514_197' : {'TARGNAME': '02XV93'},           # sometimes "ANY"
    '10514_249' : {'TARGNAME': 'COMET P/2004 PY42'},# was "04PY42", now a comet
    '10801_2'   : {'TARGNAME': '90482 ORCUS'},      # was "KBO90428ORCUS"
    '10860_2'   : {'TARKEY1': 'ASTEROID',           # was "PLANET"
                   'TARKEY2': ''},                  # was "the 10th planet"
    '11113_18'  : {'MT_LV1_1': 'FILE='},            # revised elements
    '11113_52'  : {'TARGNAME': '05SD278'},          # was TARGNAME": "05SD258",
    '11226_1'   : {'TARKEY2': 'Comet-8P-Tuttle'},   # was "Comet-8P-Tempel"
    '11518_1'   : {'MT_LV1_1': 'FILE='},            # missing MT_LV1_1. Weird.
    '11644_49'  : {'MT_LV1_1': 'FILE='},            # revised elements
    '11644_89'  : {'MT_LV1_1': 'FILE='},            # revised elements
    '12537_ANY' : {'MT_LV1_1': 'STD=EARTH',         # missing
                   'MT_LV2_1': 'STD=MOON'},
    '12792_1'   : {'TARKEY2': 'C/2011 W3 LOVEJOY'}, # was "New...comet"
    '14192_1'   : {'TARKEY1': 'COMET',              # was "ASTEROID"
                   'TARKEY2': ''},                  # was extraneous info
    '14474_1'   : {'TARKEY2': 'COMET P/2010 V1'},   # was "COMET 2010 V1"
    '14475_1'   : {'TARKEY1': 'COMET',              # was "ASTEROID"
                   'TARKEY2': ''},                  # was extraneous info
    '14498_1'   : {'TARGNAME': 'P2010-V1-C-OFFSET'},# was P2010-V-C-OFFSET"
    '14629_2'   : {'TARGNAME': '2014MU69'},         # was "2014MU69-A"
    '15003'     : {'TARKEY1' : 'KBO',
                   'TARGNAME': '2014MU69'},         # FGS occ campaign
#     '15108_1'   : {'TARGNAME': '2014 OS393'},       # was "K14OD3S"
    '16077_1'   : {'TARGNAME': 'P/2019 LD2',        # was "2019LD2"
                   'TARKEY2': 'P/2019 LD2',         # was "2019_LD2"
                   'MT_LV1_1': 'FILE='},            # revised elements
    '16183_6'   : {'MT_LV1_1': 'FILE='},            # revised elements

    # These targets cannot be identified based on any info currently available
    '10545_19'  : 'UNKNOWN_TNO',    # "TARGNAME": "OBJ-KBO30726D"
    '10545_20'  : 'UNKNOWN_TNO',    # "TARGNAME": "OBJ-KBO40804A"
    '10545_21'  : 'UNKNOWN_TNO',    # "TARGNAME": "OBJ-KBO41003B"
    '10545_22'  : 'UNKNOWN_TNO',    # "TARGNAME": "OBJ-KBO40506A"
    '12535'     : 'UNKNOWN_TNO',    # "TARGNAME": "VNH0007/08/10"
    '12887_1'   : 'UNKNOWN_TNO',    # "TARGNAME": "VNH0034"
    '13311_1'   : 'UNKNOWN_TNO',    # "TARGNAME": "A31006AP","TARKEY2": "NH-KBO"
    '13663_1'   : 'UNKNOWN_TNO',    # "TARGNAME": "KBO-G1", "TARKEY2": "NH-KBO"
    '13663_1'   : 'UNKNOWN_TNO',    # "TARGNAME": "KBO-G1", "TARKEY2": "NH-KBO"
    '16183_5'   : 'UNKNOWN_TNO',    # "TARGNAME": "P72X401", "TARKEY2": "KBO1"
    '16183_13'  : 'UNKNOWN_TNO',    # "TARGNAME": "P4856186", "TARKEY2": "KBO1"
    '16183_14'  : 'UNKNOWN_TNO',    # "TARGNAME": "B6600475", "TARKEY2": "KBO1"

    # These are KBO surveys with no specified target
    '6497'      : 'TNO_SURVEY',
    '13633'     : 'TNO_SURVEY',

    # This would otherwise fail because the body is no longer listed in the MPC
    '15344_30'  : [('2011 UH413', [], 'Trans-Neptunian Object',
                    ['This body was retracted in MPEC 2020-N22, July 7, 2020.'],
                    'trans-neptunian_object.2011_uh413')],

    # The abstract indicates these targets
    '15492_3'   : (minor_planet_identifications('2014 OS393') +
                   minor_planet_identifications('2014 PN70'))
}

##########################################################################################
# Needed to determine whether TORUS targeting is inside or outside the planet
##########################################################################################

PLANET_RADII = {
    'MARS'    :  3500.,
    'JUPITER' : 73000.,
    'SATURN'  : 62000.,
    'URANUS'  : 26000.,
    'NEPTUNE' : 26000.,
}

##########################################################################################
# translators for various small body notations
#
# If a pattern returns a tuple with "C" in front, it has been identified as a comet; "M",
# a minor planet. Otherwise, the category remains undetermined.
##########################################################################################

PREPROCESSOR1 = translator.TranslatorByRegex([
    (r'(.*)-(OFF|OFFSET|FIX)\d*',   r'\1'),     # common suffix for offsets
    (r'(.*)  +(.*)',                r'\1 \2'),  # convert multiple spaces to one
    (r'(.*)-V[1-9]\d*',             r'\1'),     # always a version number (so far)
    (r'(.*)',                       r'\1'),     # otherwise no change
])

PREPROCESSOR2 = translator.TranslatorByRegex([

    # Common suffixes
    (r'(.*)-(COPY|CLONE|NEW|REVISED)',      r'\1'),
    (r'(.*)-(POSITION\d+|TRACK\d*)',        r'\1'),
    (r'(.*)-VISIT\d+(|-\d+)',               r'\1'),
    (r'(.*)-EPOCH(-?\d+|-[A-Z])',           r'\1'),
    (r'(.*)-(UPDATE|UPDATED)',              r'\1'),
    (r'(.*)-(CORRECTED|CORRECTION)',        r'\1'),
    (r'(.*)-JPL\d\d',                       r'\1'),
    (r'(.*)-(JAN|FEB|MAR|APR|MAY|JUN)\d+',  r'\1'),
    (r'(.*)-(JUL|AUG|SEP|OCT|NOV|DEC)\d+',  r'\1'),
    (r'(.*)-20[0-2]\d[01]\d[0-3]\d',        r'\1'),
    (r'(.*)-V\d\d?(|-\d+\d?)',              r'\1'),
    (r'(.*)-HERITAGE',                      r'\1'),

    # Fix specific known cases
    (r'(.*) IMPROVED EPHEMERIS',            r'\1'),     # 10508 repair
    (r'(.*?) WHICH IS THE.*',               r'\1'),     # 13863 repair
    (r'(.*) AND ITS.*',                     r'\1'),     # 11971, 12004, 15207

    # Prefixes to ignore
    (r'CLONE OF *(.*)',                     r'\1'),
    (r'THE *(.*)',                          r'\1'),

    (r'(.*)',                               r'\1'),     # otherwise no change
])

CLASSIFIER = translator.TranslatorByRegex([
    (r'INTERSTELLAR ASTEROID ?(.*)',        ('C', r'\1')),
    (r'COMET[ -]?(.*) NUCLEUS.*',           ('C', r'\1')),
    (r'COMET[ -]?(.*)',                     ('C', r'\1')),
    (r'(.*) NUCLEUS.*',                     ('C', r'\1')),
    (r'(.*) ([A-Z]) FRAGMENT',              ('C', r'\1-\2')),
    (r'ACTIVE ASTEROID ?(.*)',              ('CM', r'\1')),

    (r'OBJ-KBO ?(.*)',                      ('M', r'\1')),
    (r'(.*) KBO',                           ('M', r'\1')),
    (r'[A-Z -]*OB[JK]ECTX? ?(.*)',          ('M', r'\1')),
    (r'[A-Z ]*KBO K(\d+)',                  ('T', r'\1')),
    (r'[A-Z ]*KBO\d (.*)',                  ('T', r'\1')),
    (r'[A-Z ]*KBO ?(.*)',                   ('T', r'\1')),
    (r'[A-Z -]*PLANET ?(.*)',               ('M', r'\1')),
    (r'[A-Z ]*TARGET ?(.*)',                ('M', r'\1')),
    (r'[A-Z ]*ASTEROID CENTAUR ?(.*)',      ('M', r'\1')),
    (r'[A-Z ]*ASTEROID ?(.*)',              ('M', r'\1')),
    (r'[A-Z ]*SYSTEM ?(.*)',                ('M', r'\1')),
    (r'[A-Z ]*CENTAUR\w? ?(.*)',            ('M', r'\1')),
    (r'[A-Z ]*DISK ?(.*)',                  ('M', r'\1')),
    (r'[A-Z ]*CANDIDATE ?(.*)',             ('M', r'\1')),
    (r'[A-Z ]*CLASSICAL ?(.*)',             ('M', r'\1')),
    (r'[A-Z ]*SCATEXTD ?(.*)',              ('M', r'\1')),
    (r'[A-Z ]*SCATNEAR ?(.*)',              ('M', r'\1')),
    (r'[A-Z ]*SATELLITE ?(.*)',             ('MS', r'\1')),
    (r'[A-Z ]*TN[OB] ?(.*)',                ('M', r'\1')),
    (r'[A-Z ]*BINARY ?(.*)',                ('MS', r'\1')),
    (r'[A-Z ]*TROJAN ?(.*)',                ('M', r'\1')),
    (r'[A-Z ]*D-TYPE ?(.*)',                ('M', r'\1')),
    (r'NEO ?(.*)',                          ('M', r'\1')),
    (r'TR(\d+)',                            ('M', r'\1')),
    (r'MP(\d\w+)',                          ('M', r'\1')),
    (r'BIN(\d.*)',                          ('M', r'\1')),
    (r'MBC[ -](.*)',                        ('CM', r'\1')),

    (r'(.*)',                               ('CM', r'\1')),
])

])

    # Re-classifications
    (r'288P.*',                             ('M', '(300163) 2006 VW139')),



COMET_REPAIRS = translator.TranslatorByRegex([

    (r'WKI1?',                      '76P/WEST-KOHOUTEK-IKEMURA'),
                                                        # 4549 repair
    (r'SHOEMAKER-LEVY 1993E.*',     'D/1993F2 SHOEMAKER-LEVY 9'),
    (r'SL-(COL|\d+)',               'D/1993F2 SHOEMAKER-LEVY 9'),
                                                        # 5590/.../5662 repairs
    (r'SHOEMAKER-1984K1',           'C/1987K1 SHOEMAKER'),
                                                        # 5834 repair
    (r'C-HYAKUTAKE',                'C/1996 B2 HYAKUTAKE'),
    (r'HYAKUTAKE',                  'C/1996 B2 HYAKUTAKE'),
                                                        # 6259/6591 repairs
    (r'([A-Z]+) 198\w+,C(.*)',      r'C/\2 \1'),        # 6447 repairs
    (r'([A-Z]+)-(\d\d)([A-Z]\d)',   r'C/19\2 \3 \1'),
    (r'P?/?WIRTANEN',               r'46P/WIRTANEN'),   # 7204 repair
    (r'COMET(\d{4}) ?(.*)',         r'C/\1 \2'),        # 7240 repair
    (r'MCNAUGHT',                   'C/1999 T1 MCNAUGHT-HARTLEY'),
    (r'SW3CB?',                     '73P/SCHWASSMANN-WACHMANN 3'),
    (r'HOLMES',                     '17P/HOLMES'),      # 8274 repair
    (r'FORBES',                     '37P/FORBES'),      # 8274 repair
    (r'SCHUSTER',                   '106P/SCHUSTER'),   # 8274 repair
    (r'LINEAR',                     'C/1999 S4 (LINEAR)'),
                                                        # 8276/8876 repair
    (r'SCHAUMASSE',                 '24P/SCHAUMASSE'),  # 8699 repair
    (r'BUS',                        '87P/BUS'),         # 8699 repair
    (r'WOLF',                       '14P/WOLF'),        # 8699 repair
    (r'KOJIMA',                     '70P/KOJIMA'),      # 8699 repair
    (r'WEST',                       '76P/WEST-KOHOUTEK-IKEMURA'),
    (R'SMIRNOVA2',                  '74P/SMIRNOVA-CHERNYKH'),
                                                        # 8699 repair
    (r'CHERYUMOV-GERASIMENKO',      '67P/CHURYUMOV-GERASIMENKO'),
                                                        # 9713 repair
    (r'73P-SW3(|-.*)',              r'73P/SCHWASSMANN-WACHMANN\1'),
                                                        # 10992 repair
    (r'(P2010-A2)-C18',             r'\1'),             # 12305, extraneous
    (r'(.*)-(DIXI|B|C)',            r'\1'),             # 12312, extraneous
    (r'(2013 ?P5)',                 r'P/2013 P5'),      # 13609 repair
    (r'(2\d\d\d) ?(\w\w)-(\w+)',    r'P/\1 \2 (\3)'),   # 13864/13866/14040 repair
    (r'P2010-V(|-.*)',              r'P2010-V1\1'),     # 14498 repair

    (r'SCHWASSMAN-WACHMAN-1',       '29P SCHWASSMANN-WACHMANN 1'),
                                                        # 15965 repair
    (r'C12019-Q4(|-.*)',            r'C2019-Q4\1'),     # 16009 repair
    (r'2IV\d',                      '2I/BORISOV'),      # 16040 repair
    (r'I2[-/]BOR[IO]SOV',           '2I/BORISOV'),      # 16043/9 repair

    (r'COMET(\d{4})(.*)',            r'\1/\2\3 \4'),

    # Abbreviations
    (r'(.*)-GERASIMENK',            '67P/CHURYUMOV-GERASIMENKO'),
    (r'(.*)-GER',                   '67P/CHURYUMOV-GERASIMENKO'),
    (r'C67P-CG',                    '67P/CHURYUMOV-GERASIMENKO'),
    (r'(|.*[^\w])S-?L(\d)',         r'\1SHOEMAKER-LEVY \2'),
    (r'(|.*[^\w])S-?W(\d)',         r'\1SCHWASSMANN-WACHMANN \2'),

    ('OUMUAMUA',                    "'OUMUAMUA"),
    ('SL[ -](.*)',                  r'SHOEMAKER-LEVY \1'),
    ('SHOEMAKER LEVY (.*)',         r'SHOEMAKER-LEVY \1'),

    # These are the most common comet names with required suffix numbers
    # Otherwise, suffixes of "-1", "-2", etc. are suppressed
    (r'(|.*[^\w])(BROOKS|'                  +
                r'GEHRELS|'                 +
                r'HARTLEY|'                 +
                r'HELIN-ROMAN-ALU|'         +
                r'KOWAL|'                   +
                r'LOVAS|'                   +
                r'MACHHOLZ|'                +
                r'MUELLER|'                 +
                r'NEUJMIN|'                 +
                r'REINMUTH|'                +
                r'RUSSELL|'                 +
                r'SCHWASSMANN-WACHMANN|'    +
                r'SHOEMAKER|'               +
                r'SHOEMAKER-HOLT|'          +
                r'SHOEMAKER-LEVY|'          +
                r'TEMPEL|'                  +
                r'TSUCHINSHAN|'             +
                r'VAISALA|'                 +
                r'WILD)[ -](\d)',           r'\1\2-\3'),

    # If not in the above list, a trailing single digit is a suffix
    (r'(.*)-\d',                    r'\1'),

    (r'(.*)',                       r'\1'),
])

MINOR_PLANET_REPAIRS = translator.TranslatorByRegex([
    (r'(.*),.*',                    r'\1'),             # anything after a comma

    (r'(.*) = CHAOS',               r'\1'),             # 2432, extraneous
    (r'(.*) \(CENTAUR\)',           r'\1'),             # 7822 repair
    (r'VESTA-(0|\d\d\d?)',          '4 VESTA'),         # 7443 repair
    ('CHARIKLORING',                'CHARIKLO'),        # 13713 repair
    (r'(.*)PATROCLUS/MENOETIUS',    r'\1PATROCLUS'),    # 15141 repair
    (r'(486958)-[A-Z]',             r'\1'),             # 15158, 15450 repair

    (r'[ABY](\d+)',                 r'\1'),             # letter in front?
    (r'[ABY](\d{4}[A-Z].*)',        r'\1'),             # letter in front?

    (r'(.*)-\d',                    r'\1'),             # extraneous suffix

    ('(.*)LOGOS-ZOE(.*)',           r'\1LOGOS\2'),

    (r'(.*)',                       r'\1'),
])

# Regular expressions
NAME         = r"([A-Z`'][A-Z `'\.\|!-]*[A-Z])"
NNN          = r'([1-9]\d*)'
NAMENUM      = NAME[:-1] + '|' + NNN[1:]

YY19_XXNNN   = r'([7-9]\d)[ -]?([A-Z]{2}\d*)[A-D]?'
YY20_XXNNN   = r'([0-2]\d)[ -]?([A-Z]{2}\d*)[A-D]?'
YY_YY_XXNNN  = r'(19|20)(\d\d)[ -]?([A-Z]{2}\d*)[A-D]?'
YYYY         = r'(1\d{3})'

NAME_N       = NAME + r'[ _-]?(\d)'
NUMP         = r'(\d+[PCXDAI])'
YY_YY_XX     = r'(19|20)(\d\d)[ _-]?([A-Z]\w\d*)'
YY_YY_XX_F   = YY_YY_XX + r'(|-[A-G])'
P_YY_YY_XX   = r'([PCXDAI])[ /_-]?' + YY_YY_XX
P_YY_YY_XX_F = P_YY_YY_XX + r'(|-[A-G])'

SEP   = r'[ _-]?'
SEP1  = r'[ _-]?\(?'
SSEP1 = r'[ /_-]?\(?'
SEP2  = r'\)?'

ROMAN = r'((?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))'   # Roman numeral < 100
YYYY_ROMAN = r'(1\d{3})[ -]?' + ROMAN
YY19_ROMAN = r'([7-9]\d)[ -]?' + ROMAN

YYYYx = r'(1\d{3}[A-Za-z]1?)'
YY19x = r'([7-9]\d[A-Za-z]1?)'

# Below, the first letter is "M" for minor planet notation; "C" for comet
# notation or ambiguous notation.

COMET_TRANSLATOR = translator.TranslatorByRegex([
    (NAMENUM,                                   (r'\1',)),
    (NAME_N,                                    (r'\1 \2',)),

    (NAME + SEP + YYYYx,                        (r'\1', r'\2')),
    (NAME + SEP + YY19x,                        (r'\1', r'19\2')),
    (NAME + SEP + YYYYx + SEP + YYYY_ROMAN,     (r'\1', r'\2', r'\3 \4')),
    (NAME + SEP + YY19x + SEP + YY19_ROMAN,     (r'\1', r'19\2', r'19\3 \4')),
    (NAME + SEP + YYYY_ROMAN,                   (r'\1', r'\2 \3')),
    (NAME + SEP + YY19_ROMAN,                   (r'\1', r'19\2 \3')),

    (NUMP,                                      (r'\1',)),
    (NUMP + SSEP1 + NAMENUM + SEP2,             (r'\1', r'\2')),
    (NUMP + SSEP1 + NAME_N  + SEP2,             (r'\1', r'\2 \3')),
    (YY_YY_XX_F,                                (r'C/\1\2 \3\4',)),
    (YY_YY_XX + SEP1 + NAME   + SEP2,           (r'C/\1\2 \3', r'\4')),
    (YY_YY_XX + SEP1 + NAME_N + SEP2,           (r'C/\1\2 \3', r'\4 \5')),
    (P_YY_YY_XX_F,                              (r'\1/\2\3 \4\5',)),
    (P_YY_YY_XX + SEP1 + NAMENUM + SEP2,        (r'\1/\2\3 \4', r'\5')),
    (P_YY_YY_XX + SEP1 + NAME_N  + SEP2,        (r'\1/\2\3 \4', r'\5 \6')),
    (NAME   + SEP1 + YY_YY_XX + SEP2,           (r'C/\2\3 \4', r'\1')),
    (NAME_N + SEP1 + YY_YY_XX + SEP2,           (r'C/\3\4 \5', r'\1 \2')),
    (NAME   + SEP1 + P_YY_YY_XX + SEP2,         (r'\2/\3\4 \5', r'\1')),
    (NAME_N + SEP1 + P_YY_YY_XX + SEP2,         (r'\3/\4\5 \6', r'\1 \2')),

    # Unusual use of version number
    (P_YY_YY_XX + r'V\d',                       (r'\1/\2\3 \4',)),

    (r'.*',                                     ()),
])

MINOR_PLANET_TRANSLATOR = translator.TranslatorByRegex([
    (NAMENUM,                                   (r'\1',)),
    (NAME_N,                                    (r'\1 \2',)),

    (YY_YY_XXNNN,                               (r'\1\2 \3',)),
    (YY19_XXNNN,                                (r'19\1 \2',)),
    (YY20_XXNNN,                                (r'20\1 \2',)),
    (NNN,                                       (r'\1',)),
    (NNN + r'[ -]?' + NAME,                     (r'\1', r'\2')),

    (r'\(?' + NNN + r'\)?',                     (r'\1',)),
    (r'\(?' + NNN + r'\)?[ -]?' + NAME,         (r'\1', r'\2')),
    (r'\(?' + NNN + r'\)?[ -]?' + YY_YY_XXNNN,  (r'\1', r'\2\3 \4')),
    (NNN + r'[ -]?\(?' + NAME + r'\)?',         (r'\1', r'\2')),
    (NNN + r'[ -]?\(?' + YY_YY_XXNNN + r'\)?',  (r'\1', r'\2\3 \4')),
    (NNN + r'[ -]?' + NAME + r'[ -]?\(?' + YY_YY_XXNNN + r'\)?',
                                                (r'\1', r'\2', r'\3\4 \5')),
    (NAME + r'[ -]?\(?' + NNN + r'\)?',         (r'\2', r'\1')),
    (NAME + r'[ -]?\(?' + YY_YY_XXNNN + r'\)?', (r'\2\3 \4', r'\1')),

    (r'(J9\d[A-Z]\w\d[A-Z])',                   (r'\1',)),  # old KBO names
    (r'(K[0-2]\d[A-Z]\w\d[A-Z])',               (r'\1',)),  # old KBO names

    (r'.*',                                     ()),
])

STD_TRANSLATOR = translator.TranslatorByRegex([
    (r'244 \(OCEANA\)',         ('M', '224', 'OCEANA')),    # 4784 repair
    (r'1 \(VESTA\)',            ('M', '4', 'VESTA')),       # 5175 repair

    (NNN,                                       ('M', r'\1')),
    (NNN + r' ?\(' + NAME + r'\).*',            ('M', r'\1', r'\2')),
    (NAME + r' ?-?' + NNN,                      ('C', r'\1 \2')),
    (NAME,                                      ('S', r'\1')),
    (r'(.*)',                                   ('S', r'\1')),
])

UNIQUE_WARNINGS_LOGGED = set()

def hst_target_identifications(spt_header0, filepath, logger=None):
    """Return a list of target identifications as tuples of the form:
          (name, alt_designations, type, description, lid)
    where:
          name                the preferred name
          alt_designations    a list of strings indicating alternative names.
          type                "Planet", "Satellite", etc.
          description         a list of strings, to be separated by newlines
                              inside the XML Target_Identification object.
          lid                 the LID of the object, omitting "urn:...:target:"
    """

    logger = logger or pdslogger.NullLogger()

    def merge(header, key):
        """Merge values spanning multiple FITS keyword lines"""

        value = header[key].rstrip()

        for k in range(2,10):
            key2 = key[:-1] + str(k)
            if key2 not in header:
                return value

            value += header[key2]

    # Get TARG_ID and PROPOSID
    TARG_ID = spt_header0['TARG_ID']
    PROPOSID = str(spt_header0['PROPOSID'])

    # Deal with SPT repairs
    repair = None
    for key in [TARG_ID, PROPOSID, PROPOSID + '_' + TARG_ID]:
        try:
            repair = SPT_REPAIRS[key]
            break
        except KeyError:
            pass

    if isinstance(repair, list):
        if DEBUG: print('target identified in SPT_REPAIRS')
        logger.debug('SPT repair ' + str([r[0] for r in repair]), filepath)
        return repair

    if isinstance(repair, str):
        if repair == 'UNKNOWN_TNO':
            return unknown_tno(spt_header0)
        if repair == 'TNO_SURVEY':
            return tno_survey(spt_header0)
        raise ValueError('Illegal SPT_REPAIR value', repair)

    if isinstance(repair, dict):
        messages = ['']
        if DEBUG: print('SPT repair found:')
        for key in repair:
            if key in spt_header0:
                message = f'  "{key}": "{repair[key]}" (was "{spt_header0[key]})"'
            else:
                message = f'  "{key}": "{repair[key]}" (was missing)'
            messages.append(message)
            if DEBUG: print(message)

        logger.debug('SPT repair ' + str(repair).replace('\n', ' '), filepath)

        temp_dict = {}
        for key in spt_header0:
            temp_dict[key] = spt_header0[key]

        for key in repair:
            temp_dict[key] = repair[key]

        spt_header0 = temp_dict

    # Get the MT_LV values
    MT_LVs = []
    try:
        for k in range(1,10):
            key = f'MT_LV{k}_1'
            value = merge(spt_header0, key).strip()
            if value.startswith(','):
                value = value[1:]
            MT_LVs.append(value)
    except KeyError:
        pass

    if DEBUG: print('MT_LVs =', MT_LVs)

    ######################################################################################
    # Handle STD values
    ######################################################################################

    STDs = []
    for value in MT_LVs:
        if value.startswith('STD'):
            parts = value.partition('=')
            name = parts[2].upper().split(',')[0].strip()
            STDs.append(name)

    if DEBUG: print('STDs =', STDs)

    if STDs:
        planet = STDs[0]
        target = STDs[-1]   # same as planet, except for satellites

        info = STD_TRANSLATOR.first(planet)
        body_type = info[0]
        names = list(info[1:])

        if DEBUG: print('STD translation =', info)

        # Handle small bodies
        if body_type == 'M':
            return minor_planet_identifications(names)

        if body_type == 'C':
            return comet_identifications(names)

        name = names[0]

        # Handle rings and the Io torus
        if len(MT_LVs) > 1 and MT_LVs[1].startswith('TYPE=TORUS'):

            match = re.fullmatch(r'.*, ?RAD ?= ?(.*?),.*', MT_LVs[1])
            if not match:
                return standard_body_identifications('Io Torus')

            rad = float(match.group(1))
            if DEBUG: print(f'TORUS, rad = {rad}, planet = {planet}')

            # Io torus is for planet Jupiter, POLE_LAT missing, and RAD > 150000
            if (planet == 'JUPITER' and 'POLE_LAT' not in MT_LVs[1] and
                                        rad > 150000.):
                if DEBUG: print('Io torus targeting identified')
                return standard_body_identifications('Io Torus')

            # Otherwise, a ring requires RAD greater than the planet radius
            if rad >= PLANET_RADII[planet]:
                if DEBUG: print('Rings targeting identified')
                return standard_body_identifications(planet + ' rings')
            else:
                if DEBUG: print('Planet targeting identified')
                return standard_body_identifications(planet)

        # Handle standard planets, dwarf planets, and satellites
        return standard_body_identifications(target)

    ######################################################################################
    # Handle small bodies
    ######################################################################################

    # Get the TARKEY values
    TARKEYs = []
    try:
        for k in range(1,10):
            key = f'TARKEY{k}'
            value = spt_header0[key].upper()
            TARKEYs.append(value)
    except KeyError:
        pass

    if DEBUG: print('TARKEYs =', TARKEYs)

    votes = ''
    if TARKEYs:
        if TARKEYs[0] == 'ASTEROID':
            votes = 'M'
            TARKEYs = TARKEYs[1:]
        elif TARKEYs[0] == 'COMET':
            votes = 'C'
            TARKEYs = TARKEYs[1:]

    if DEBUG: print('votes, TARKEYs =', votes, TARKEYs)

    # Get orbital elements if available
    if MT_LVs:
        parts = MT_LVs[0].split(',')
        parts = [p.split('=') for p in parts]

        get_elements = True
        left  = parts[0][0].strip()
        right = parts[0][1].strip()
        if left == 'TYPE':
            if right == 'ASTEROID':
                votes += 'M'
            elif right == 'COMET':
                votes += 'C'
            elif right == 'G_CIRCLE' and TARKEYs[0] == 'PLANET PLUTO':
                # Program 3843 is a special case, with no easy way to handle it
                return (standard_body_identifications('PLUTO') +
                        standard_body_identifications('CHARON'))
            else:
                raise ValueError('Unsupported target TYPE: ' + right)

        elif left == 'FILE':
            get_elements = False

        else:
            raise ValueError('Unsupported MT_LV value: ' + parts[0])
    else:
        get_elements = False

    if get_elements:
        found = False
        for part in parts:
            if part[0].strip() == 'E':
                e = float(part[1])
                found = True
                break

        if not found:
            raise ValueError('Missing eccentricity in MT_LV1')

        found = False
        for part in parts:
            if part[0].strip() == 'I':
                i = float(part[1])
                found = True
                break

        if not found:
            raise ValueError('Missing inclination in MT_LV1')

        found = False
        for part in parts:
            if part[0].strip() in ('A', 'Q'):
                if part[0].startswith('A'):
                    a = float(part[1])
                    q = 0.
                else:
                    a = 0.
                    q = float(part[1])
                found = True
                break

        if not found:
            raise ValueError('Missing semimajor axis/pericenter in MT_LV1')

        if DEBUG: print('a,q,e,i =', a, q, e, i)

    else:
        a = q = e = i = 0.
        if DEBUG: print('a,q,e,i ignored')

    # Interpret target info
    TARGNAME = spt_header0['TARGNAME']

    if DEBUG: print('Candidate identifiers =', TARKEYs + [TARGNAME])

    identifiers = []
    for text in TARKEYs + [TARGNAME]:
        if DEBUG: print('Initial:', text)

        text = PREPROCESSOR1.first(text)
        if DEBUG: print('PREPROCESSOR1:', text)

        text = PREPROCESSOR2.first(text)
        if DEBUG: print('PREPROCESSOR2:', text)

        (vote, text) = CLASSIFIER.first(text)
        if DEBUG: print('CLASSIFIER:', vote, text)

        votes += vote
        identifiers += [text]

    if DEBUG: print('votes, identifiers =', votes, identifiers)

    comet_ids = []
    if 'C' in votes:
        for identifier in identifiers:
            if DEBUG: print('Comet test for', identifier)

            identifier = COMET_REPAIRS.first(identifier)
            if DEBUG: print('COMET_REPAIRS', identifier)

            ids = list(COMET_TRANSLATOR.first(identifier))
            if DEBUG: print('COMET_TRANSLATOR', ids)

            comet_ids += [i for i in ids if i]

        if DEBUG: print('comet_ids', comet_ids)

    mp_ids = []
    if 'M' in votes:
        for identifier in identifiers:
            if DEBUG: print('Minor planet test for', identifier)

            identifier = MINOR_PLANET_REPAIRS.first(identifier)
            if DEBUG: print('MINOR_PLANET_REPAIRS', identifier)

            ids = list(MINOR_PLANET_TRANSLATOR.first(identifier))
            if DEBUG: print('MINOR_PLANET_TRANSLATOR', ids)

            mp_ids += [i for i in ids if i]

        if DEBUG: print('mp_ids', mp_ids)

    # Interpret as a comet
    comet_error = None
    comet_warnings = []
    if comet_ids:
        if DEBUG: print('Testing comet_ids', comet_ids)
        try:
            ids = comet_identifications(comet_ids, a=a, e=e, i=i, q=q,
                                        warnings=comet_warnings,
                                        ignore_suffix=True)
            if ids:
                for w in comet_warnings:
                    if w not in UNIQUE_WARNINGS_LOGGED:
                        logger.warn(w, filepath)
                        UNIQUE_WARNINGS_LOGGED.add(w)

                if DEBUG: print('Comet identified!')
                return ids

        except (ValueError, KeyError) as err:
            comet_error = err
            pass

    # Interpret as a minor planet
    mp_warnings = []
    if mp_ids:
        if DEBUG: print('Testing mp_ids', mp_ids)
        try:
            ids = minor_planet_identifications(mp_ids, a=a, e=e, i=i, q=q,
                                               warnings=mp_warnings)
            if ids:
                for w in mp_warnings:
                    if w not in UNIQUE_WARNINGS_LOGGED:
                        logger.warn(w, filepath)
                        UNIQUE_WARNINGS_LOGGED.add(w)

                if DEBUG: print('Minor planet identified!')
                return ids

        except (ValueError, KeyError):
            if not comet_error:     # raise the comet error instead, if any
                for w in mp_warnings:
                    logger.error(w, filepath)
                raise

    if comet_error:
        for w in comet_warnings:
            logger.error(w, filepath)
        raise comet_error

    raise ValueError(f'Unrecognized target "{TARGNAME}", proposal={PROPOSID}, '
                     + str(comet_ids + mp_ids))

##########################################################################################
# Functions for "special case" Target Identifications
##########################################################################################

def target_identification_details(spt_header0):

    details = ['', 'Targeting info:']
    for (key, value) in spt_header0.items():
        if (key.startswith('MT_LV') or
            key.startswith('TARKEY') or
            key == 'TARGNAME'):
                key = (key + '   ')[:8]         # extend key to 8 characters
                if isinstance(value, str):
                    value = '"' + value.replace('"','').replace("'",'') + '"'
                else:
                    value = str(value)
                details.append(f'    {key} = {value}')

    return details

def tno_survey(spt_header0):
    targ_id  = spt_header0['TARG_ID']
    proposid = spt_header0['PROPOSID']

    return [(f'TNO Survey Field HST-{targ_id}',
             [],
             'Trans-Neptunian Object',
             [f'Target {targ_id} was defined for a survey of Trans-Neptunian objects '
                + f'in HST Program {proposid}.'] +
             target_identification_details(spt_header0),
             lids.clean('trans-neptunian_object.survey.hst-' + targ_id)
            )]

def unknown_tno(spt_header0):
    targ_id  = spt_header0['TARG_ID']
    proposid = spt_header0['PROPOSID']

    return [(f'Unknown TNO HST-{targ_id}',
             [],
             'Trans-Neptunian Object',
             [f'Target {targ_id} was defined for a Trans-Neptunian object observed '
                + f'in HST Program {proposid}. The true identity of this TNO cannot '
                + 'be inferred from the information provided.'] +
              target_identification_details(spt_header0),
              lids.clean('trans-neptunian_object.unknown.hst-' + targ_id))]

##########################################################################################
