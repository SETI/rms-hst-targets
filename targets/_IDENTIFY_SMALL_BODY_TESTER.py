from targets.tests.SPT_TESTS import SPT_TESTS
from targets.hst_repairs import hst_repairs
from targets._HST_PROGRAM_OVERRIDES import SPT_REPAIRS
import pdslogger

logger = pdslogger.EasyLogger()


for filename, spt in SPT_TESTS:
    targ_id = spt['TARG_ID']
    if targ_id in SPT_REPAIRS:
        spt.update(SPT_REPAIRS[targ_id])

    strings = []
    for k in range(1, 7):
        key = 'TARKEY' + str(k)
        if key not in spt:
            break
        strings.append(spt[key])
    strings.append(spt['TARGNAME'])

    mt_lv1 = []
    for k in range(1, 7):
        key = 'MT_LV1_' + str(k)
        if key not in spt:
            break
        mt_lv1.append(spt[key])
    mt_lv1 = ''.join(mt_lv1)
    if 'COMET' in mt_lv1:
        keys = ('Q', 'I', 'O', 'E', 'W')
    elif 'ASTEROID' in mt_lv1:
        keys = ('A', 'I', 'O', 'E', 'W')
    else:
        keys = []

    elements = {}
    for part in mt_lv1.split(','):
        key, _, value = part.partition('=')
        key = key.strip()
        if key in keys:
            elements[key] = float(value)

    answers = hst_repairs(strings)
    if ('[M]' in answers or '[T]' in answers or '[H]' in answers or '[A]' in answers
            or ['D'] in answers or '[C]' in answers):
        print('=================', filename)
        body = identify_small_body(strings, elements, logger=logger)
        if body is None: print('*** FAILED! ***')

#         answers = {a for a in answers if a[0] != '['}
#         if answers:
#             (dicts, used, unused, found) = identify_minor_planet_by_strings(answers)
#             print(repr(filename), found, used, unused, [c['full_name'] for c in dicts])


#     if '[C]' in answers:
#         print('=================', filename)
#         answers = {a for a in answers if a[0] != '['}
#         if answers:
#             comet = identify_comet(answers, elements, logger=logger)

