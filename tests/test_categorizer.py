##########################################################################################
# hst_targets/tests/test_translator.py
##########################################################################################

from xxx import _TRANSLATOR

TESTS = [
    ('(243) Ida I (Dactyl)',                'S', '(243) Ida I (Dactyl)'),
    ('(243) Ida I Dactyl',                  'S', '(243) Ida I (Dactyl)'),
    ('243 Ida I (Dactyl)',                  'S', '(243) Ida I (Dactyl)'),
    ('243 Ida I Dactyl',                    'S', '(243) Ida I (Dactyl)'),
    ('Ida I (Dactyl)',                      'S', 'Ida I (Dactyl)'),
    ('Ida I Dactyl',                        'S', 'Ida I (Dactyl)'),
    ('(243) Ida I',                         'S', '(243) Ida I'),
    ('243 Ida I',                           'S', '(243) Ida I'),
    ('Ida I',                               'S', 'Ida I'),
    ('S/2003 J 17 (Herse)',                 'S', 'S/2003 J 17 (Herse)'),
    ('S2003 J 17 (Herse)',                  'S', 'S/2003 J 17 (Herse)'),
    ('S/2003J 17 (Herse)',                  'S', 'S/2003 J 17 (Herse)'),
    ('S/2003 J17 (Herse)',                  'S', 'S/2003 J 17 (Herse)'),
    ('S/2003J17 (Herse)',                   'S', 'S/2003 J 17 (Herse)'),
    ('S2003J17 (Herse)',                    'S', 'S/2003 J 17 (Herse)'),
    ('S/2003 J 17 Herse',                   'S', 'S/2003 J 17 (Herse)'),
    ('S2003 J 17 Herse',                    'S', 'S/2003 J 17 (Herse)'),
    ('S/2003J 17 Herse',                    'S', 'S/2003 J 17 (Herse)'),
    ('S/2003 J17 Herse',                    'S', 'S/2003 J 17 (Herse)'),
    ('S/2003J17 Herse',                     'S', 'S/2003 J 17 (Herse)'),
    ('S2003J17 Herse',                      'S', 'S/2003 J 17 (Herse)'),
    ('S/2003 J 17',                         'S', 'S/2003 J 17'),
    ('S2003 J 17',                          'S', 'S/2003 J 17'),
    ('S/2003J 17',                          'S', 'S/2003 J 17'),
    ('S/2003 J17',                          'S', 'S/2003 J 17'),
    ('S/2003J17',                           'S', 'S/2003 J 17'),
    ('S2003J17',                            'S', 'S/2003 J 17'),
    ('J L',                                 'S', 'J L'),
    ('J-L',                                 'S', 'J L'),
    ('JL',                                  'S', 'J L'),
    ('J50',                                 'S', 'J50'),
    ('J 50',                                'S', 'J50'),
    ('J-50',                                'S', 'J50'),
    ('S/2018 (3548) 1',                     'S', '2018 (3548) 1'),
    ('S2018 (3548) 1',                      'S', '2018 (3548) 1'),
    ('(1) 1801 AA (Ceres)',                 'M', '(1) 1801 AA (Ceres)'),
    ('(1) 1801AA (Ceres)',                  'M', '(1) 1801 AA (Ceres)'),
    ('(1) 1801 AA Ceres',                   'M', '(1) 1801 AA (Ceres)'),
    ('(1) 1801AA Ceres',                    'M', '(1) 1801 AA (Ceres)'),
    ('(1) 1801 AA',                         'M', '(1) 1801 AA'),
    ('(1) 1801AA',                          'M', '(1) 1801 AA'),
    ('(1777) 4007 P-L (Gehrels)',           'M', '(1777) 4007 P-L (Gehrels)'),
    ('(1777) 4007 P-L Gehrels',             'M', '(1777) 4007 P-L (Gehrels)'),
    ('(1777) 4007 P-L',                     'M', '(1777) 4007 P-L'),
    ('(1) Ceres',                           'M', '1 Ceres'),
    ('1 Ceres',                             'M', '1 Ceres'),
    ('98 QP41',                             'M', '1998 QP41'),
    ('29 QP41',                             'M', '2029 QP41'),
    ('(1777)',                              'M', '(1777)'),
    ('D/1993 F2-P1 (Shoemaker-Levy 9-P1)',  'C', 'D/1993 F2-P1 (Shoemaker-Levy 9-P1)'),
    ('D/1993 F2 P1 (Shoemaker-Levy 9-P1)',  'C', 'D/1993 F2-P1 (Shoemaker-Levy 9-P1)'),
    ('D/1993 F2-P1 (Shoemaker-Levy 9 P1)',  'C', 'D/1993 F2-P1 (Shoemaker-Levy 9-P1)'),
    ('D/1993 F2-P1 (Shoemaker-Levy 9)',     'C', 'D/1993 F2-P1 (Shoemaker-Levy 9-P1)'),
    ('D/1993 F2 P1 (Shoemaker-Levy 9)',     'C', 'D/1993 F2-P1 (Shoemaker-Levy 9-P1)'),
    ('D/1993 F2 (Shoemaker-Levy 9-P1)',     'C', 'D/1993 F2-P1 (Shoemaker-Levy 9-P1)'),
    ('D/1993 F2 (Shoemaker-Levy 9 P1)',     'C', 'D/1993 F2-P1 (Shoemaker-Levy 9-P1)'),
    ('D/1993 F2 (Shoemaker-Levy 9)',        'C', 'D/1993 F2 (Shoemaker-Levy 9)'),
    ('D/1993 F2-A (Shoemaker-Levy A)',      'C', 'D/1993 F2-A (Shoemaker-Levy A)'),
    ('D/1993 F2 A (Shoemaker-Levy A)',      'C', 'D/1993 F2-A (Shoemaker-Levy A)'),
    ('D/1993 F2-A (Shoemaker-Levy)',        'C', 'D/1993 F2-A (Shoemaker-Levy A)'),
    ('D/1993 F2 A (Shoemaker-Levy)',        'C', 'D/1993 F2-A (Shoemaker-Levy A)'),
    ('D/1993 F2 (Shoemaker-Levy A)',        'C', 'D/1993 F2-A (Shoemaker-Levy A)'),
    ('D/1993 F2 (Shoemaker-Levy)',          'C', 'D/1993 F2 (Shoemaker-Levy)'),
    ('D/1993 F2-P1',                        'C', 'D/1993 F2-P1'),
    ('D/1993 F2 P1',                        'C', 'D/1993 F2-P1'),
    ('D/1993 F2',                           'C', 'D/1993 F2'),
    ('10P/Tempel 2-A',                      'C', '10P/Tempel 2-A'),
    ('10P/Tempel 2 A',                      'C', '10P/Tempel 2-A'),
    ('10P/Tempel 2',                        'C', '10P/Tempel 2'),
    ('10P/Tempel A',                        'C', '10P/Tempel A'),
    ('10P/Tempel',                          'C', '10P/Tempel'),
    ('(Shoemaker-Levy 9-A)',                'C', 'Shoemaker-Levy 9-A'),
    ('(Shoemaker-Levy 9 A)',                'C', 'Shoemaker-Levy 9-A'),
    ('(Shoemaker-Levy 9)',                  'C', 'Shoemaker-Levy 9'),
    ('(Shoemaker-Levy A)',                  'C', 'Shoemaker-Levy A'),
    ('Shoemaker-Levy 9-A',                  'C', 'Shoemaker-Levy 9-A'),
    ('Shoemaker-Levy 9 A',                  'C', 'Shoemaker-Levy 9-A'),
    ('Shoemaker-Levy 9',                    'C', 'Shoemaker-Levy 9'),
    ('Shoemaker-Levy A',                    'C', 'Shoemaker-Levy A'),
    ('(Ceres)',                             '', 'Ceres'),
]


def test_translator():
    for test, cat, answer in TESTS:
        for regex, category, replacement in _TRANSLATOR:
            match = regex.match(test)
            if match:
                break
        assert match, f'No match for "{test}"'
        expanded = match.expand(replacement)
        assert answer == expanded, f'Replacement failed, "{test}" -> "{expanded}"'
        assert cat == category, f'Category mismatch, "{test}" -> "{category}"'

##########################################################################################
