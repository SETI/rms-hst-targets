##########################################################################################
# _HST_PROGRAM_OVERRIDES.py
##########################################################################################

SPT_REPAIRS = {
    '2442'      : {'TARGNAME': 'COMET-SL-1991A1'},  # was a random string
    '2569'      : {'MT_LV1_1': 'STD=PLUTO'},        # missing TARG_ID, no MT_LV1 in some
    '9991_1'    : {'TARGNAME': 'KBO1999RZ253'},     # was "ANY"; same as prev
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
    '10545_22'  : {'TARKEY2':  'HAUMEA'},           # was "KBO-Santa"
    '11113_18'  : {'MT_LV1_1': 'FILE='},
    '11113_52'  : {'TARGNAME': '05SD278'},          # was "05SD258"
    '12535_3'   : 'TNO_SURVEY',
    '12535_4'   : 'TNO_SURVEY',
    '12535_5'   : 'TNO_SURVEY',
    '13633_*':  : 'TNO_SURVEY',
    '14498_1'   : {'TARGNAME': 'P2010-V1'},         # was "P2010-V-C-OFFSET"
    '16183_6'   : {'MT_LV1_1': 'FILE='},

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



#     '10860_2'   : {'TARKEY1': 'ASTEROID',           # was "PLANET"
#                    'TARKEY2': ''},                  # was "the 10th planet" SEE NOTES
#
#     '11644_49'  : {'MT_LV1_1': 'FILE='},            SHOULD BE OK
#     '11644_89'  : {'MT_LV1_1': 'FILE='},            SHOULD BE OK
#     '12537_ANY' : {'MT_LV1_1': 'STD=EARTH',         MAYBE HARD-WIRE EARTH to be ignored
#                    'MT_LV2_1': 'STD=MOON'}, WHY IS THIS NEEDED? MT_LV2 should be included!
#
#     # These targets cannot be identified based on any info currently available
#     '10545_19'  : 'UNKNOWN_TNO',    # "TARGNAME": "OBJ-KBO30726D"
#     '10545_20'  : 'UNKNOWN_TNO',    # "TARGNAME": "OBJ-KBO40804A"
#     '10545_21'  : 'UNKNOWN_TNO',    # "TARGNAME": "OBJ-KBO41003B"
#     '10545_22'  : 'UNKNOWN_TNO',    # "TARGNAME": "OBJ-KBO40506A"
#     '12535'     : 'UNKNOWN_TNO',    # "TARGNAME": "VNH0007/08/10"
#     '12887_1'   : 'UNKNOWN_TNO',    # "TARGNAME": "VNH0034"
#     '13311_1'   : 'UNKNOWN_TNO',    # "TARGNAME": "A31006AP", "TARKEY2": "NH-KBO"
#     '13663_1'   : 'UNKNOWN_TNO',    # "TARGNAME": "KBO-G1", "TARKEY2": "NH-KBO"
#     '13663_1'   : 'UNKNOWN_TNO',    # "TARGNAME": "KBO-G1", "TARKEY2": "NH-KBO"
#     '16183_5'   : 'UNKNOWN_TNO',    # "TARGNAME": "P72X401", "TARKEY2": "KBO1"
#     '16183_13'  : 'UNKNOWN_TNO',    # "TARGNAME": "P4856186", "TARKEY2": "KBO1"
#     '16183_14'  : 'UNKNOWN_TNO',    # "TARGNAME": "B6600475", "TARKEY2": "KBO1"
#
#     # These are KBO surveys with no specified target
#     '6497'      : 'TNO_SURVEY',
#     '13633'     : 'TNO_SURVEY',
#
#     # This would otherwise fail because the body is no longer listed in the MPC
#     '15344_30'  : [('2011 UH413', [], 'Trans-Neptunian Object',
#                     ['This body was retracted in MPEC 2020-N22, July 7, 2020.'],
#                     'trans-neptunian_object.2011_uh413')],


##########################################################################################
