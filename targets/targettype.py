##########################################################################################
# targettype.py
##########################################################################################

class TargetType:

    # Single-letter codes for all target classes
    ASTEROID = 'A'
    ASTROPHYSICAL = 'a'
    CALIBRATION_FIELD = 'F'
    CALIBRATOR = 'c'
    CENTAUR = 'H'               # for "Horse"
    COMET = 'C'
    DUST = 'd'
    DWARF_PLANET = 'D'
    EQUIPMENT = 'E'
    LABORATORY_ANALOG = 'L'
    MAGNETIC_FIELD = 'm'
    PLANET = 'P'
    PLANETARY_NEBULA = 'N'
    PLANETARY_SYSTEM = 'p'
    PLASMA_CLOUD = 't'          # for "Torus"
    PLASMA_STREAM = 'W'         # for "Wind"
    RING = 'R'
    SATELLITE = 'S'
    STAR = '*'
    TRANS_NEPTUNIAN_OBJECT = 'T'

    # Lookup table
    NAME = {
        'A': 'asteroid',
        'a': 'astrophysical',
        'F': 'calibration_field',
        'c': 'calibrator',
        'H': 'centaur',
        'C': 'comet',
        'd': 'dust',
        'D': 'dwarf_planet',
        'E': 'equipment',
        'L': 'laboratory_analog',
        'm': 'magnetic_field',
        'P': 'planet',
        'N': 'planetary_nebula',
        'p': 'planetary_system',
        't': 'plasma_cloud',
        'W': 'plasma_stream',
        'R': 'ring',
        'S': 'satellite',
        '*': 'star',
        'T': 'trans-neptunian_object',
    }

    # An extra
    MINOR_PLANET = 'M'
    MCODES = 'AHDT'

##########################################################################################
