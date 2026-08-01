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

Underscores replace dashes in comets so the results don't get split apart on the second
pass (where the splitting is by dashes). The underscores are replaced at the end of the
process.
"""

_TARGET_STRING_REPAIRS = [
    (r'SOLAR SYSTEM',                           ''),
    (r'COMET[- ]B2([- ]NUCLEUS|)',              r'C/1996 B2 (HYAKUTAKE)|[C]'),
    (r'COMET SHOEMAKER-LEVY 1993E.*',           r'D/1993 F2 (SHOEMAKER_LEVY 9)|[C]'),
    (r'COMET[ -](?:SHOEMAKER[- ]LEVY|SL)[- ](199\D)([A-Z]1?)(-\W+|)',
                                                r'SHOEMAKER_LEVY|\1\2|[C]'),
    (r'SL',                                     r'SHOEMAKER_LEVY'),
    # The numbered forms accept a dash as well as a slash, and supply "/" and "[C]"
    # themselves. Otherwise the generic comet-number pattern in hst_repairs gets there
    # first and appends "|[C]", after which these patterns can no longer match: they are
    # anchored at the end of the string, and the string now ends with the type marker.
    (r'(\d+P)[-/]CH.RYUMOV-GER[A-Z]*',          r'\1/CHURYUMOV_GERASIMENKO|[C]'),
    (r'CH.RYUMOV-GER[A-Z]*',                    r'CHURYUMOV_GERASIMENKO'),
    (r'(\d+P)[-/]CG',                           r'\1/CHURYUMOV_GERASIMENKO|[C]'),
    (r'CG',                                     r'CHURYUMOV_GERASIMENKO'),
    (r'(?:29P[-/]?)?SW1',                       r'29P/SCHWASSMANN_WACHMANN 1|[C]'),
    # Split by fragment, because an empty fragment would otherwise leave a trailing "_",
    # and hence a trailing dash, on the repaired name.
    (r'(?:73P[-/]?)?SW3-?([A-Z])[AB]?',         r'73P/SCHWASSMANN_WACHMANN 3_\1|[C]'),
    (r'(?:73P[-/]?)?SW3[AB]?',                  r'73P/SCHWASSMANN_WACHMANN 3|[C]'),
    (r'(?:73P[-/]?)?SCHWASSMANW3-?([A-Z])[AB]?', r'73P/SCHWASSMANN_WACHMANN 3_\1|[C]'),
    (r'(?:73P[-/]?)?SCHWASSMANW3[AB]?',         r'73P/SCHWASSMANN_WACHMANN 3|[C]'),
    (r'SCHWASSMAN-WACHMAN-1',                   r'SCHWASSMANN_WACHMANN 1'),
    (r'(?:76P[-/]?)?WKI ?1?',                   r'76P/WEST_KOHOUTEK_IKEMURA|[C]'),
    (r'288P',                                   r'(300163) 2006 VW139|[A]'),
    (r'SANTA',                                  r'HAUMEA'),
    (r'(?:2I|I2)?-?BOROSOV',                    r'2I/BORISOV'),
    (r'(HARTLEY|TEMPEL|WILD|GEHRELS|REINMUTH)(\d)',
                                                r'\1 \2'),
    (r'FORBES2',                                r'FORBES'),
    (r'KAGARA',                                 r'qcKagara'),

    (r'MARS[- ]?DUST',                          r'MARS|[R]'),
    (r'IO[ -]?(WAKE|TORUS)',                    r'IO|[t]'),
    (r'IO[- ]N(EUTRAL)?[- ]?CLOUD.*',           r'IO|[t]'),
    (r'GANY(FOOT)?',                            r'GANYMEDE|[S]'),
    (r'EUROFOOT',                               r'EUROPA|[S]'),
    (r'PL(UTO)?-CH(AR(ON)?)?',                  r'PLUTO|CHARON|[D]|[S]'),
]


__all__ = ['_TARGET_STRING_REPAIRS']

##########################################################################################
