##########################################################################################
# _TARGET_STRING_REPAIRS.py
##########################################################################################
"""A maintained list of grep patterns for words that do not contribute to the
identification of a target.

These are used by `hst_repairs()` _after_ all the more important patterns found in that
file are interpreted.

"|" in the replacement pattern splits the output string at this point.
"$" in the pattern splits the output string at this point and re-evaluates everything to
the right.

Include "[C]" in the returned string to indicate that this name refers to a comet.
Similarly, any TargetType character between square brackets "[]" indicates that this is a
target body of the specified type.
"""

_TARGET_STRING_REPAIRS = [
    (r'COMET[- ]B2([- ]NUCLEUS|)',              r'C/1996 B2 (Hyakutake)|[C]'),
    (r'COMET[ -](?:SHOEMAKER[- ]LEVY|SL)[- ](199\d)([A-Z]1?)(-\w+|)',
                                                r'Shoemaker-Levy|\1\2|[C]'),
    (r'SL',                                     'Shoemaker-Levy'),
    (r'(\d+P/)?CH.RYUMOV-GER[A-Z]*',            r'\1CHURYUMOV-GERASIMENKO'),
    (r'(\d+P/)?CG',                             r'\1CHURYUMOV-GERASIMENKO'),
    (r'(?:29P/?-?)?SW1',                        r'29P/Schwassmann-Wachmann 1'),
    (r'(?:73P-)?SW3-?([A-Z]|)[AB]?',            r'73P/Schwassmann-Wachmann 3-\1'),
    (r'SCHWASSMANW3-?([A-Z]|)[AB]?',            r'\1Schwassmann-Wachmann 3-\2'),
    (r'SCHWASSMAN-WACHMAN-1',                   r'Schwassmann-Wachmann 1'),
    (r'WKI ?1?',                                r'76P/West-Kohoutek-Ikemura|[C]'),
    (r'(MARS).*(SIDING SPRING).*',              r'[P]|Mars|[C]|Siding Spring|C/2013 A1'),
    (r'288P',                                   r'288P|[C]|(300163) 2006 VW139|[A]'),
    (r'SANTA',                                  r'Haumea'),
    (r'JOVIAN',                                 r'JUPITER'),
    (r'PL-?CH',                                 r'PLUTO|CHARON'),
    (r'(?:2I|I2)?-?BOROSOV',                    r'2I/Borisov'),
    (r'(HARTLEY|TEMPEL|WILD|GEHRELS|REINMUTH)(\d)',
                                                r'\1 \2'),
    (r'FORBES2',                                r'Forbes'),
]

##########################################################################################
