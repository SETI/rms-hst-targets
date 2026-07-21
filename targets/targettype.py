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
    GALAXY = 'G'
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
    STAR_CLUSTER = 's'
    TRANS_NEPTUNIAN_OBJECT = 'T'

    # Lookup table
    NAME = {
        'A': 'Asteroid',
        'a': 'Astrophysical',
        'F': 'Calibration Field',
        'c': 'Calibrator',
        'H': 'Centaur',
        'C': 'Comet',
        'd': 'Dust',
        'D': 'Dwarf Planet',
        'E': 'Equipment',
        'G': 'Galaxy',
        'L': 'Laboratory Analog',
        'm': 'Magnetic Field',
        'P': 'Planet',
        'N': 'Planetary Nebula',
        'p': 'Planetary System',
        't': 'Plasma Cloud',
        'W': 'Plasma Stream',
        'R': 'Ring',
        'S': 'Satellite',
        '*': 'Star',
        's': 'Star Cluster',
        'T': 'Trans-Neptunian Object',
    }

    # Extras
    MINOR_PLANET = 'M'
    MCODES = 'AHDT'
    TORUS = PLASMA_CLOUD


TargetType.LOOKUP = {name: key for key, name in TargetType.NAME.items()}
TargetType.LOOKUP.update({name.lower().replace(' ', '_'): key
                          for key, name in TargetType.NAME.items()})

__all__ = ['TargetType']

##########################################################################################
