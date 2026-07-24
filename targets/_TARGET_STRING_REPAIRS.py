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

Underscores replace dashes so the results don't get split apart on the second pass (where
the splitting is by dashes. The underscores are replaced at the end of the process.
"""

_TARGET_STRING_REPAIRS = [
    (r'SOLAR SYSTEM',                           ''),
    (r'COMET[- ]B2([- ]NUCLEUS|)',              r'C/1996 B2 (HYAKUTAKE)|[C]'),
    (r'COMET SHOEMAKER-LEVY 1993E.*',           r'D/1993 F2 (SHOEMAKER-LEVY 9)|[C]'),
    (r'COMET[ -](?:SHOEMAKER[- ]LEVY|SL)[- ](199\D)([A-Z]1?)(-\W+|)',
                                                r'SHOEMAKER_LEVY|\1\2|[C]'),
    (r'SL',                                     r'SHOEMAKER_LEVY'),
    (r'(\d+P/)?CH.RYUMOV-GER[A-Z]*',            r'\1CHURYUMOV_GERASIMENKO'),
    (r'(\d+P/)?CG',                             r'\1CHURYUMOV_GERASIMENKO'),
    (r'(?:29P/?-?)?SW1',                        r'29P/SCHWASSMANN_WACHMANN 1'),
    (r'(?:73P-)?SW3-?([A-Z]|)[AB]?',            r'73P/SCHWASSMANN_WACHMANN 3-\1'),
    (r'SCHWASSMANW3-?([A-Z]|)[AB]?',            r'\1SCHWASSMANN_WACHMANN 3-\2'),
    (r'SCHWASSMAN-WACHMAN-1',                   r'SCHWASSMANN_WACHMANN 1'),
    (r'WKI ?1?',                                r'76P/WEST_KOHOUTEK_IKEMURA|[C]'),
    (r'(MARS).*(SIDING SPRING).*',              r'[P]|MARS|[C]|SIDING SPRING|C/2013 A1'),
    (r'288P',                                   r'288P|[C]|(300163) 2006 VW139|[A]'),
    (r'SANTA',                                  r'HAUMEA'),
    (r'(?:2I|I2)?-?BOROSOV',                    r'2I/BORISOV'),
    (r'(HARTLEY|TEMPEL|WILD|GEHRELS|REINMUTH)(\d)',
                                                r'\1 \2'),
    (r'FORBES2',                                r'FORBES'),
    (r'MARS[- ]?DUST',                          r'MARS|[R]'),
    (r'IO[ -]?(WAKE|TORUS)',                    r'IO|[t]'),
    (r'IO[- ]N(EUTRAL)?[- ]?CLOUD.*',           r'IO|[t]'),
    (r'GANY(FOOT)?',                            r'GANYMEDE|[S]'),
    (r'EUROFOOT',                               r'EUROPA|[S]'),
    (r'PL(UTO)?-CH(AR(ON)?)?',                  r'PLUTO|CHARON|[D]|[S]'),
]


__all__ = ['_TARGET_STRING_REPAIRS']

##########################################################################################
