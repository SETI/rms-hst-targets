##########################################################################################
# STANDARD_BODY_LIST.py
##########################################################################################
"""
==================
STANDARD_BODY_LIST
==================
This is a maintained list of information about Solar System bodies that are defined as
"standard" targets in APT. This list excludes small bodies unless they are in some way
exceptional.

Each standard body is represented by a tuple as follows::

    (name, number, naif_id, target_type, pname, aliases)

where:

* `name` (str): Name of the body, if any.
* `number` (int): For satellites, the satellite number; otherwise, the MPC number if it
  exists; otherwise, zero.
* `naif_id` (int): NAIF body ID.
* `target_type` (str): "P" for planet; "S" for satellite; "D" for dwarf planet; "T" for
  trans-neptunian object'; "A" for asteroid; "C" for comet; "*" for star.
* pname (str): Name of parent body if any.
* aliases (list[str]): Zero or more aliases for the body.
* alt_keys (list[str], optional): Any additional that might be used for lookup but are not
  really a valid alias.
"""

STANDARD_BODY_LIST = [
    ('Sun'        ,  0,    10, '*', '', []),

    ('Mars System'   , 0, 4, 'p', '', []),
    ('Jupiter System', 0, 5, 'p', '', []),
    ('Saturn System' , 0, 6, 'p', '', []),
    ('Uranus System' , 0, 7, 'p', '', []),
    ('Neptune System', 0, 8, 'p', '', []),

    ('Mercury'    ,  0,   199, 'P', '', []),
    ('Venus'      ,  0,   299, 'P', '', []),
    ('Earth'      ,  0,   399, 'P', '', []),
    ('Mars'       ,  0,   499, 'P', 'Mars System'   , []),
    ('Jupiter'    ,  0,   599, 'P', 'Jupiter System', []),
    ('Saturn'     ,  0,   699, 'P', 'Saturn System' , []),
    ('Uranus'     ,  0,   799, 'P', 'Uranus System' , []),
    ('Neptune'    ,  0,   899, 'P', 'Neptune System', []),

    ('Moon'       ,  1,   301, 'S', 'Earth', []),

    ('Phobos'     ,  1,   401, 'S', 'Mars', []),
    ('Deimos'     ,  2,   402, 'S', 'Mars', []),

    ('Io'         ,  1,   501, 'S', 'Jupiter', []),
    ('Europa'     ,  2,   502, 'S', 'Jupiter', []),
    ('Ganymede'   ,  3,   503, 'S', 'Jupiter', []),
    ('Callisto'   ,  4,   504, 'S', 'Jupiter', []),
    ('Amalthea'   ,  5,   505, 'S', 'Jupiter', []),
    ('Himalia'    ,  6,   506, 'S', 'Jupiter', []),
    ('Elara'      ,  7,   507, 'S', 'Jupiter', []),
    ('Pasiphae'   ,  8,   508, 'S', 'Jupiter', []),
    ('Sinope'     ,  9,   509, 'S', 'Jupiter', []),
    ('Lysithea'   , 10,   510, 'S', 'Jupiter', []),
    ('Carme'      , 11,   511, 'S', 'Jupiter', []),
    ('Ananke'     , 12,   512, 'S', 'Jupiter', []),
    ('Leda'       , 13,   513, 'S', 'Jupiter', []),
    ('Thebe'      , 14,   514, 'S', 'Jupiter', []),
    ('Adrastea'   , 15,   515, 'S', 'Jupiter', []),
    ('Metis'      , 16,   516, 'S', 'Jupiter', []),
    ('Callirrhoe' , 17,   517, 'S', 'Jupiter', ['S/1999 J 1']),
    ('Themisto'   , 18,   518, 'S', 'Jupiter', ['S/1975 J 1',
                                                'S/2000 J 1']),
    ('Magaclite'  , 19,   519, 'S', 'Jupiter', []),
    ('Taygete'    , 20,   520, 'S', 'Jupiter', ['S/2000 J 9' ]),
    ('Chaldene'   , 21,   521, 'S', 'Jupiter', ['S/2000 J 10']),
    ('Harpalyke'  , 22,   522, 'S', 'Jupiter', ['S/2000 J 5' ]),
    ('Kalyke'     , 23,   523, 'S', 'Jupiter', ['S/2000 J 2' ]),
    ('Iocaste'    , 24,   524, 'S', 'Jupiter', ['S/2000 J 3' ]),
    ('Erinome'    , 25,   525, 'S', 'Jupiter', ['S/2000 J 4' ]),
    ('Isonoe'     , 26,   526, 'S', 'Jupiter', ['S/2002 J 1' ]),
    ('Praxidike'  , 27,   527, 'S', 'Jupiter', ['S/2000 J 7' ]),
    ('Autonoe'    , 28,   528, 'S', 'Jupiter', ['S/2001 J 1' ]),
    ('Thyone'     , 29,   529, 'S', 'Jupiter', ['S/2001 J 2' ]),
    ('Hermippe'   , 30,   530, 'S', 'Jupiter', ['S/2001 J 3' ]),
    ('Aitne'      , 31,   531, 'S', 'Jupiter', ['S/2001 J 11']),
    ('Eurydome'   , 32,   532, 'S', 'Jupiter', ['S/2001 J 4' ]),
    ('Euanthe'    , 33,   533, 'S', 'Jupiter', ['S/2001 J 7' ]),
    ('Euporie'    , 34,   534, 'S', 'Jupiter', ['S/2001 J 10']),
    ('Orthosie'   , 35,   535, 'S', 'Jupiter', ['S/2001 J 9' ]),
    ('Sponde'     , 36,   536, 'S', 'Jupiter', ['S/2001 J 5' ]),
    ('Kale'       , 37,   537, 'S', 'Jupiter', ['S/2001 J 8' ]),
    ('Pasithee'   , 38,   538, 'S', 'Jupiter', ['S/2001 J 6' ]),
    ('Hegemone'   , 39,   539, 'S', 'Jupiter', ['S/2003 J 8' ]),
    ('Mneme'      , 40,   540, 'S', 'Jupiter', ['S/2003 J 21']),
    ('Aoede'      , 41,   541, 'S', 'Jupiter', ['S/2003 J 7' ]),
    ('Thelxinoe'  , 42,   542, 'S', 'Jupiter', ['S/2003 J 22']),
    ('Arche'      , 43,   543, 'S', 'Jupiter', ['S/2002 J 1' ]),
    ('Kallichore' , 44,   544, 'S', 'Jupiter', ['S/2003 J 11']),
    ('Helike'     , 45,   545, 'S', 'Jupiter', ['S/2003 J 6' ]),
    ('Carpo'      , 46,   546, 'S', 'Jupiter', ['S/2003 J 20']),
    ('Eukelade'   , 47,   547, 'S', 'Jupiter', ['S/2003 J 1' ]),
    ('Cyllene'    , 48,   548, 'S', 'Jupiter', ['S/2003 J 13']),
    ('Kore'       , 49,   549, 'S', 'Jupiter', ['S/2003 J 14']),
    (''           ,  0,   550, 'S', 'Jupiter', ['S/2003 J 17']),
    (''           ,  0,   551, 'S', 'Jupiter', ['S/2010 J 1' ]),
    (''           ,  0,   552, 'S', 'Jupiter', ['S/2010 J 2' ]),
    ('Dia'        , 53,   553, 'S', 'Jupiter', ['S/2000 J 11']),
    (''           ,  0,   554, 'S', 'Jupiter', ['S/2016 J 1' ]),
    (''           ,  0,   555, 'S', 'Jupiter', ['S/2003 J 18']),
    (''           ,  0,   556, 'S', 'Jupiter', ['S/2011 J 2' ]),
    (''           ,  0,   557, 'S', 'Jupiter', ['S/2003 J 5' ]),
    (''           ,  0,   558, 'S', 'Jupiter', ['S/2003 J 15']),
    (''           ,  0, 55060, 'S', 'Jupiter', ['S/2003 J 2' ]),
    (''           ,  0, 55061, 'S', 'Jupiter', ['S/2003 J 3' ]),
    (''           ,  0, 55062, 'S', 'Jupiter', ['S/2003 J 4' ]),
    (''           ,  0, 55064, 'S', 'Jupiter', ['S/2003 J 9' ]),
    (''           ,  0, 55065, 'S', 'Jupiter', ['S/2003 J 10']),
    (''           ,  0, 55066, 'S', 'Jupiter', ['S/2003 J 12']),
    (''           ,  0, 55068, 'S', 'Jupiter', ['S/2003 J 16']),
    (''           ,  0, 55070, 'S', 'Jupiter', ['S/2003 J 19']),
    (''           ,  0, 55071, 'S', 'Jupiter', ['S/2003 J 23']),
    (''           ,  0, 55074, 'S', 'Jupiter', ['S/2011 J 1' ]),

    ('Mimas'      ,  1,   601, 'S', 'Saturn', []),
    ('Enceladus'  ,  2,   602, 'S', 'Saturn', []),
    ('Tethys'     ,  3,   603, 'S', 'Saturn', []),
    ('Dione'      ,  4,   604, 'S', 'Saturn', []),
    ('Rhea'       ,  5,   605, 'S', 'Saturn', []),
    ('Titan'      ,  6,   606, 'S', 'Saturn', []),
    ('Hyperion'   ,  7,   607, 'S', 'Saturn', []),
    ('Iapetus'    ,  8,   608, 'S', 'Saturn', []),
    ('Phoebe'     ,  9,   609, 'S', 'Saturn', []),
    ('Janus'      , 10,   610, 'S', 'Saturn', []),
    ('Epimetheus' , 11,   611, 'S', 'Saturn', []),
    ('Helene'     , 12,   612, 'S', 'Saturn', ['S/1980 S 6' ]),
    ('Telesto'    , 13,   613, 'S', 'Saturn', ['S/1980 S 13']),
    ('Calypso'    , 14,   614, 'S', 'Saturn', ['S/1980 S 25']),
    ('Atlas'      , 15,   615, 'S', 'Saturn', ['S/1980 S 28']),
    ('Prometheus' , 16,   616, 'S', 'Saturn', ['S/1980 S 27']),
    ('Pandora'    , 17,   617, 'S', 'Saturn', ['S/1980 S 26']),
    ('Pan'        , 18,   618, 'S', 'Saturn', ['S/1981 S 13']),
    ('Ymir'       , 19,   619, 'S', 'Saturn', ['S/2000 S 1' ]),
    ('Paaliaq'    , 20,   620, 'S', 'Saturn', ['S/2000 S 2' ]),
    ('Tarvos'     , 21,   621, 'S', 'Saturn', ['S/2000 S 4' ]),
    ('Ijiraq'     , 22,   622, 'S', 'Saturn', ['S/2000 S 6' ]),
    ('Suttungr'   , 23,   623, 'S', 'Saturn', ['S/2000 S 12']),
    ('Kiviuq'     , 24,   624, 'S', 'Saturn', ['S/2000 S 5' ]),
    ('Mundilfari' , 25,   625, 'S', 'Saturn', ['S/2000 S 9' ]),
    ('Albiorix'   , 26,   626, 'S', 'Saturn', ['S/2000 S 11']),
    ('Skathi'     , 27,   627, 'S', 'Saturn', ['S/2000 S 8' ]),
    ('Erriapus'   , 28,   628, 'S', 'Saturn', ['S/2000 S 10']),
    ('Siarnaq'    , 29,   629, 'S', 'Saturn', ['S/2000 S 3' ]),
    ('Thrymr'     , 30,   630, 'S', 'Saturn', ['S/2000 S 7' ]),
    ('Narvi'      , 31,   631, 'S', 'Saturn', ['S/2003 S 1' ]),
    ('Methone'    , 32,   632, 'S', 'Saturn', ['S/2004 S 1' ]),
    ('Pallene'    , 33,   633, 'S', 'Saturn', ['S/2004 S 2' ]),
    ('Polydeuces' , 34,   634, 'S', 'Saturn', ['S/2004 S 5' ]),
    ('Daphnis'    , 35,   635, 'S', 'Saturn', ['S/2005 S 1' ]),
    ('Aegir'      , 36,   636, 'S', 'Saturn', ['S/2004 S 10']),
    ('Bebhionn'   , 37,   637, 'S', 'Saturn', ['S/2004 S 11']),
    ('Bergelmir'  , 38,   638, 'S', 'Saturn', ['S/2004 S 15']),
    ('Bestla'     , 39,   639, 'S', 'Saturn', ['S/2004 S 18']),
    ('Farbauti'   , 40,   640, 'S', 'Saturn', ['S/2004 S 9' ]),
    ('Fenrir'     , 41,   641, 'S', 'Saturn', ['S/2004 S 16']),
    ('Fornjot'    , 42,   642, 'S', 'Saturn', ['S/2004 S 8' ]),
    ('Hati'       , 43,   643, 'S', 'Saturn', ['S/2004 S 14']),
    ('Hyrrokkin'  , 44,   644, 'S', 'Saturn', []),
    ('Kari'       , 45,   645, 'S', 'Saturn', ['S/2006 S 2' ]),
    ('Loge'       , 46,   646, 'S', 'Saturn', ['S/2006 S 5' ]),
    ('Skoll'      , 47,   647, 'S', 'Saturn', ['S/2006 S 8' ]),
    ('Surtur'     , 48,   648, 'S', 'Saturn', ['S/2006 S 7' ]),
    ('Anthe'      , 49,   649, 'S', 'Saturn', ['S/2007 S 4' ]),
    ('Jarnsaxa'   , 50,   650, 'S', 'Saturn', ['S/2006 S 6' ]),
    ('Greip'      , 51,   651, 'S', 'Saturn', ['S/2006 S 4' ]),
    ('Tarqeq'     , 52,   652, 'S', 'Saturn', ['S/2007 S 1' ]),
    ('Aegaeon'    , 53,   653, 'S', 'Saturn', ['S/2008 S 1' ]),
    (''           ,  0, 65035, 'S', 'Saturn', ['S/2004 S 7' ]),
    (''           ,  0, 65040, 'S', 'Saturn', ['S/2004 S 12']),
    (''           ,  0, 65041, 'S', 'Saturn', ['S/2004 S 13']),
    (''           ,  0, 65045, 'S', 'Saturn', ['S/2004 S 17']),
    (''           ,  0, 65048, 'S', 'Saturn', ['S/2006 S 1' ]),
    (''           ,  0, 65050, 'S', 'Saturn', ['S/2006 S 3' ]),
    (''           ,  0, 65055, 'S', 'Saturn', ['S/2007 S 2' ]),
    (''           ,  0, 65056, 'S', 'Saturn', ['S/2007 S 3' ]),

    ('Ariel'      ,  1,   701, 'S', 'Uranus', []),
    ('Umbriel'    ,  2,   702, 'S', 'Uranus', []),
    ('Titania'    ,  3,   703, 'S', 'Uranus', []),
    ('Oberon'     ,  4,   704, 'S', 'Uranus', []),
    ('Miranda'    ,  5,   705, 'S', 'Uranus', []),
    ('Cordelia'   ,  6,   706, 'S', 'Uranus', ['S/1986 U 7']),
    ('Ophelia'    ,  7,   707, 'S', 'Uranus', ['S/1986 U 8']),
    ('Bianca'     ,  8,   708, 'S', 'Uranus', ['S/1986 U 9']),
    ('Cressida'   ,  9,   709, 'S', 'Uranus', ['S/1986 U 3']),
    ('Desdemona'  , 10,   710, 'S', 'Uranus', ['S/1986 U 6']),
    ('Juliet'     , 11,   711, 'S', 'Uranus', ['S/1986 U 2']),
    ('Portia'     , 12,   712, 'S', 'Uranus', ['S/1986 U 1']),
    ('Rosalind'   , 13,   713, 'S', 'Uranus', ['S/1986 U 4']),
    ('Belinda'    , 14,   714, 'S', 'Uranus', ['S/1986 U 5']),
    ('Puck'       , 15,   715, 'S', 'Uranus', ['S/1985 U 1']),
    ('Caliban'    , 16,   716, 'S', 'Uranus', ['S/1997 U 1']),
    ('Sycorax'    , 17,   717, 'S', 'Uranus', ['S/1997 U 2']),
    ('Prospero'   , 18,   718, 'S', 'Uranus', ['S/1999 U 3']),
    ('Setebos'    , 19,   719, 'S', 'Uranus', ['S/1999 U 1']),
    ('Stephano'   , 20,   720, 'S', 'Uranus', ['S/1999 U 2']),
    ('Trinculo'   , 21,   721, 'S', 'Uranus', ['S/2001 U 1']),
    ('Francisco'  , 22,   722, 'S', 'Uranus', ['S/2001 U 3']),
    ('Margaret'   , 23,   723, 'S', 'Uranus', ['S/2003 U 3']),
    ('Ferdinand'  , 24,   724, 'S', 'Uranus', []),
    ('Perdita'    , 25,   725, 'S', 'Uranus', ['S/1986 U 10']),
    ('Mab'        , 26,   726, 'S', 'Uranus', ['S/2003 U 1']),
    ('Cupid'      , 27,   727, 'S', 'Uranus', ['S/2003 U 2']),

    ('Triton'     ,  1,   801, 'S', 'Neptune', []),
    ('Nereid'     ,  2,   802, 'S', 'Neptune', []),
    ('Naiad'      ,  3,   803, 'S', 'Neptune', []),
    ('Thalassa'   ,  4,   804, 'S', 'Neptune', []),
    ('Despina'    ,  5,   805, 'S', 'Neptune', []),
    ('Galatea'    ,  6,   806, 'S', 'Neptune', []),
    ('Larissa'    ,  7,   807, 'S', 'Neptune', []),
    ('Proteus'    ,  8,   808, 'S', 'Neptune', []),
    ('Halimede'   ,  9,   809, 'S', 'Neptune', ['S/2002 N 1']),
    ('Psamathe'   , 10,   810, 'S', 'Neptune', ['S/2003 N 1']),
    ('Sao'        , 11,   811, 'S', 'Neptune', ['S/2002 N 2']),
    ('Laomedeia'  , 12,   812, 'S', 'Neptune', ['S/2002 N 3']),
    ('Neso'       , 13,   813, 'S', 'Neptune', ['S/2003 N 2']),
    ('Hippocamp'  , 14,   814, 'S', 'Neptune', ['S/2004 N 1']),

    # Dwarf planets
    # Below, "$" in a designation is a placeholder for the parent designation, e.g.,
    # "S/2005 $ 1" -> "S/2005 (136199) 1" or "S/2005 (2003 UB313) 1"
    ('Ceres'   ,  1, 2000001, 'D', '', ['1899 OF', '1943 XB']),

    ('Pluto System',  0,   9, 'p', ''            , []),
    ('Pluto'   , 134340, 999, 'D', 'Pluto System', []),
    ('Charon'  ,      1, 901, 'S', 'Pluto'       , ['S/1978 P 1']),
    ('Nix'     ,      2, 902, 'S', 'Pluto'       , ['S/2005 $ 2']),
    ('Hydra'   ,      3, 903, 'S', 'Pluto'       , ['S/2005 $ 1']),
    ('Kerberos',      4, 904, 'S', 'Pluto'       , ['S/2011 $ 1']),
    ('Styx'    ,      5, 905, 'S', 'Pluto'       , ['S/2012 $ 1']),

    ('Eris'    , 136199, 2136199, 'D', '', ['2003 UB313']),
    ('Dysnomia',      1,       0, 'S', 'Eris', ['S/2005 $ 1']),

    ('Haumea'  , 136108, 2136108, 'D', '', ['2003 EL61']),
    ("Hi'iaka" ,      1,       0, 'S', 'Haumea', ['S/2005 $ 1'], ['Hiiaka']),
    ('Namaka'  ,      2,       0, 'S', 'Haumea', ['S/2005 $ 2']),

    ('Makemake', 136472, 2136472, 'D', '', ['2005 FY9']),
    (''        ,      1,       0, 'S', 'Makemake', ['S/2015 $ 1']),

    # Other minor planet satellites
    ('Ida'     ,    243, 2000243, 'A', '', ['1910 CD', '1988 DB1']),
    ('Dactyl'  ,      1, 2431011, 'S', 'Ida', ['S/1993 $ 1']),

    ('Quaoar'  ,  50000, 2050000, 'T', '', ['2002 LM60']),
    ('Weywot'  ,      1,       0, 'S', 'Quaoar', ['S/2006 $ 1']),

    ('Gonggong', 225088, 2225088, 'T', '', ['2007 OR10']),
    ('Xiangliu',      1,       0, 'S', 'Gonggong', ['S/2010 $ 1']),

    ('Salacia' , 120347, 2120347, 'T', '', ['2004 SB60']),
    ('Actaea'  ,      1,       0, 'S', 'Salacia', ['S/2006 $ 1']),

    ('Orcus'   ,  90482, 2090482, 'T', '', ['2004 DW']),
    ('Vanth'   ,      1,       0, 'S', 'Orcus', ['S/2005 $ 1']),

    # Rings (real and imagined)
    ('Mars Rings'   , 0, 0, 'R', 'Mars'   , []),
    ('Jupiter Rings', 0, 0, 'R', 'Jupiter', []),
    ('Saturn Rings' , 0, 0, 'R', 'Saturn' , []),
    ('Uranus Rings' , 0, 0, 'R', 'Uranus' , []),
    ('Neptune Rings', 0, 0, 'R', 'Neptune', []),
    ('Pluto Rings'  , 0, 0, 'R', 'Pluto'  , []),

    # Io Torus
    ('Io Torus', 0, 0, 'Plasma Stream', 'Jupiter', []),
]

##########################################################################################
