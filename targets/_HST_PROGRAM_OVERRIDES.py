##########################################################################################
# _HST_PROGRAM_OVERRIDES.py
##########################################################################################

SPT_REPAIRS = {
    '1431'      : 'ANTISOLAR_POINTING',             # TARGNAME "ANTISUN"; RA/DEC_TARG is
    '1478'      : 'ANTISOLAR_POINTING',             #   the anti-solar point (no body)
    'ANTISUN'   : 'ANTISOLAR_POINTING',             # ditto; these have TARG_ID="ANTISUN"
    'ASLAG'     : 'ANTISOLAR_POINTING',             # prog 3069; pointing is anti-solar
    '2442'      : {'TARGNAME': 'COMET-SL-1991A1'},  # was a random string
    '2569'      : {'MT_LV1_1': 'STD=PLUTO'},        # missing TARG_ID, no MT_LV1 in some
    '9991_1'    : {'TARGNAME': 'KBO1999RZ253'},     # was "ANY"; same as prev
    '10514_1'   : {'TARGNAME': '80806'},            # was "ANY"; (80806) 2000 CM105 by
                                                    #   elements + sky position
    '10514_3'   : {'TARGNAME': '79360'},            # was "ANY"; from APT file
    '10514_4'   : {'TARGNAME': '99OJ4'},            # was "ANY"; from APT file
    '10514_5'   : {'TARGNAME': '82075'},            # was "ANY"; from APT file
    '10514_14'  : {'TARGNAME': '49036'},            # was "ANY"; from APT file
    '10514_16'  : {'TARGNAME': '98WG24'},           # was "ANY"; from APT file
    '10514_18'  : {'TARGNAME': '69990'},            # was "ANY"; from APT file
    '10514_33'  : {'TARGNAME': '99RB216'},          # was "ANY"; from APT file
    '10514_35'  : {'TARGNAME': '99RN215'},          # was "ANY"; from APT file
    '10514_55'  : {'TARGNAME': '00QC226'},          # was "ANY"; from APT file
    '10514_56'  : {'TARGNAME': '54598'},            # was "ANY"; from APT file
    '10514_58'  : {'TARGNAME': '00QN251'},          # was "ANY"; from APT file
    '10514_59'  : {'TARGNAME': '00WK183'},          # was "ANY"; from APT file
    '10514_85'  : {'TARGNAME': '88267'},            # was "ANY"; from APT file
    '10514_111' : {'TARGNAME': '01QP297'},          # was "ANY"; from APT file
    '10514_122' : {'TARGNAME': '01RX143'},          # was "ANY"; from APT file
    '10514_123' : {'TARGNAME': '01RZ143'},          # was "ANY"; from APT file
    '10514_129' : {'TARGNAME': '01YH140'},          # was "ANY"; from APT file
    '10514_174' : {'TARGNAME': '02PP149'},          # was "ANY"; from APT file
    '10514_191' : {'TARGNAME': '02VU130'},          # was "ANY"; from APT file
    '10514_197' : {'TARGNAME': '02XV93'},           # was "ANY"; from APT file
    '5590_1'    : {'TARGNAME': 'D/1993 F2'},        # was "SL-COL": SL9 pre-impact
    '5834_1'    : {'MT_LV1_1': 'TYPE=COMET , Q = 2.6993596 , E = 0.9988181 , '
                               'I = 116.66543 , O =',
                   'MT_LV1_2': ' 49.69009 , W = 235.46970 , T = 06-SEP-85:08:03:14 '
                               ', EPOCH = 29'},
                                                    # header I/O/W were wrong in no
                                                    #   recognizable frame; Q, E, and T
                                                    #   match C/1984 K1 (Shoemaker), so
                                                    #   its catalog angles are used
    '6497_1'    : 'TNO_SURVEY',                     # "Kuiper belt field 1", blind search
    '6841_2'    : {'MT_LV1_1': 'TYPE=COMET,Q=.5320503,E=.8242432, I=4.24869,'
                               'O=89.15214,W=326.05'},  # header had Q=.05320503 (10x off)
    '8800_*'    : 'SLEW_TEST',                      # "Slew while exposing" dummy elements
    '9110_28'   : {'TARGNAME': '55565'},            # was "MINIXENA": (55565) Aya,
                                                    #   confirmed by sky position (1.7")
    '9678_1'    : {'TARGNAME': 'QUAOAR',            # was "OBJECTX": Quaoar before its
                   'MT_LV1_1': 'FILE='},            #   announcement, confirmed by sky
                                                    #   position (1.7"); the header
                                                    #   orbital elements are decoys
    '10545_19'  : {'TARGNAME': '120178'},           # was "OBJ-KBO30726D": 2003 OP32,
                                                    #   by elements + sky position
    '10545_20'  : {'TARGNAME': '136472'},           # was "OBJ-KBO40804A": Makemake,
                                                    #   by elements + sky position
    '10545_21'  : {'TARGNAME': '120348'},           # was "OBJ-KBO41003B": 2004 TY364,
                                                    #   by elements + sky position
    '10545_22'  : {'TARKEY2':  'HAUMEA'},           # was "KBO-Santa"
    '10781_11'  : {'MT_LV1_1': 'TYPE=COMET,Q=5.83260440906976,'
                               'E=0.4564002785487747,I=4.34413174'},
                                                    # header had Q=10.7296 (the semimajor
                                                    #   axis); the program itself re-flew
                                                    #   target "2000EC98-CORRECTION"
    '11113_14'  : {'TARGNAME': '05XU100'},          # was "05UX100" (letters transposed);
                                                    #   confirmed by elements + position
    '11113_18'  : {'MT_LV1_1': 'FILE='},
    '11113_52'  : {'TARGNAME': '05SD278'},          # was "05SD258"
    '12535_3'   : 'TNO_SURVEY',
    '12535_4'   : 'TNO_SURVEY',
    '12535_5'   : 'TNO_SURVEY',
    '12887_1'   : 'UNDESIGNATED_TNO',               # "VNH0034", a New Horizons candidate
                                                    #   KBO with no MPC designation
    '13311_1'   : 'UNDESIGNATED_TNO',               # "A31006AP", NH candidate KBO
    '13663_1'   : 'UNDESIGNATED_TNO',               # "KBO-G1", NH candidate KBO
    '12891_8'   : {'TARGNAME': '16974'},            # was "TROJAN13331", but the elements
                                                    #   and position are (16974) Iphthime
    '13633_*'   : 'TNO_SURVEY',
    '14498_1'   : {'TARGNAME': 'P/2010 V1-C'},      # was "P2010-V-C-OFFSET": fragment C
                                                    #   of 332P/Ikeya-Murakami (P/2010 V1)
    '15108_1'   : {'TARGNAME': '14OS393'},          # was "K14OD3S": packed "K14Od3S"
                                                    #   (2014 OS393) upcased in the header
    '15344_30'  : 'UNDESIGNATED_TNO',               # "2011UH413" is a survey-internal
                                                    #   designation (cycle 413 is not
                                                    #   possible); not in the MPC or JPL
    '16183_6'   : {'MT_LV1_1': 'FILE='},

    # Program 16183 recovered candidate KBOs from a May 2020 survey under internal
    # hexadecimal names. Those since designated by the MPC were identified by orbital
    # elements + sky position; the rest have no MPC designation.
    '16183_5'   : 'UNDESIGNATED_TNO',               # "P72X401"
    '16183_13'  : {'TARGNAME': '2020KH42'},         # was "P4856186"
    '16183_14'  : {'TARGNAME': '2020KK54'},         # was "B6600475"
    '16183_15'  : {'TARGNAME': '2020KD54'},         # was "P959EB2C"
    '16183_16'  : 'UNDESIGNATED_TNO',               # "P97C5C44"
    '16183_17'  : {'TARGNAME': '2020KG54'},         # was "P97D467E"
    '16183_18'  : {'TARGNAME': '2020KS55'},         # was "P6X78F"
    '16183_19'  : 'UNDESIGNATED_TNO',               # "P72X4B2"
    '16183_20'  : 'UNDESIGNATED_TNO',               # "P72X546"
    '16183_21'  : {'TARGNAME': '2020KO53'},         # was "A46D02CE"
    '16183_22'  : 'UNDESIGNATED_TNO',               # "P97E09E4"
    '16183_23'  : 'UNDESIGNATED_TNO',               # "P472E655"
    '16183_24'  : 'UNDESIGNATED_TNO',               # "P972BF5B"
    '16183_25'  : 'UNDESIGNATED_TNO',               # "P6X59B"
    '16183_26'  : 'UNDESIGNATED_TNO',               # "P6X5BC"
    '16183_27'  : 'UNDESIGNATED_TNO',               # "P72X638"
    '16183_28'  : 'UNDESIGNATED_TNO',               # "P72X665"
    '16183_29'  : 'UNDESIGNATED_TNO',               # "P953B127"
    '16183_30'  : {'TARGNAME': '2020KO55'},         # was "P6X6D2"
    '16183_31'  : 'UNDESIGNATED_TNO',               # "P6X6F8"
    '16183_32'  : {'TARGNAME': '2020KC53'},         # was "A1300EDC"
    '16183_33'  : 'UNDESIGNATED_TNO',               # "A4590CD3"
    '16183_34'  : 'UNDESIGNATED_TNO',               # "B10E0B9B"
    '16183_35'  : {'TARGNAME': '2013LU35'},         # was "P72X825"
    '16183_36'  : {'TARGNAME': '2020KF54'},         # was "P97D1F63"
    '16183_39'  : 'UNDESIGNATED_TNO',               # "P97B4AC8"
    '16183_40'  : {'TARGNAME': '2020KJ56'},         # was "P72X6DC"
    '16183_41'  : {'TARGNAME': '2020KL53'},         # was "P4811A01"
    '16183_42'  : {'TARGNAME': '2020KS53'},         # was "P48983C9"
    '16183_43'  : 'UNDESIGNATED_TNO',               # "P72X659"
    '16183_44'  : 'UNDESIGNATED_TNO',               # "P4730D64"

    '16192_2'   : {'TARGNAME': '300163'},           # was "288P2"; 288P = (300163), which
    '16192_3'   : {'TARGNAME': '300163'},           #   is not in the comet database
    '16687_2'   : {'TARGNAME': '300163'},           # was "288P-B" (binary component)
    '17707_1'   : {'TARGNAME': '469705'},           # was "KAGARA": (469705) ǂKá̦gára has
                                                    #   click letters the MPC can't match
    '18005_1'   : {'TARGNAME': '2014WC510'},        # was "WC510"

    # Occultation studies
    '2771'      : {'MT_LV1_1': 'STD=SATURN'},       # HSP Saturn occ
    '2890_9'    : {'MT_LV1_1': 'STD=SATURN'},       # missing MT_LV1
    '2891_10'   : {'MT_LV1_1': 'STD=TITAN'},        # missing MT_LV1
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
    '7489'      : {'MT_LV1_1': 'STD=TRITON'},       # FGS fixed, TARGNAME="TR\d+.*"
    '7490'      : {'MT_LV1_1': 'STD=TRITON'},       # FGS fixed, TARGNAME="TR\d+.*"
    '8105'      : {'MT_LV1_1': 'STD=PLUTO'},        # FGS fixed, TARGNAME="PLUTO-OS"
    '15003'     : {'TARKEY1' : 'KBO',
                   'TARGNAME': '2014MU69'},         # FGS occ campaign
}

__all__ = ['SPT_REPAIRS']

##########################################################################################
