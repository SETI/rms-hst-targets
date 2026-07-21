##########################################################################################
# tests/test_targettype.py
##########################################################################################

from targets.targettype import TargetType


def test_lookup_inverts_name_in_both_cases() -> None:
    # Every type name maps back to its code, both in its given ("Dwarf Planet") form and
    # in the lowercase-underscored ("dwarf_planet") form used in LIDs.
    for code, name in TargetType.NAME.items():
        assert TargetType.LOOKUP[name] == code
        assert TargetType.LOOKUP[name.lower().replace(' ', '_')] == code


def test_lookup_representative_values() -> None:
    assert TargetType.LOOKUP['Planet'] == TargetType.PLANET
    assert TargetType.LOOKUP['planet'] == TargetType.PLANET
    assert TargetType.LOOKUP['Trans-Neptunian Object'] \
        == TargetType.TRANS_NEPTUNIAN_OBJECT
    assert TargetType.LOOKUP['trans-neptunian_object'] \
        == TargetType.TRANS_NEPTUNIAN_OBJECT
    assert TargetType.LOOKUP['Dwarf Planet'] == TargetType.DWARF_PLANET
    assert TargetType.LOOKUP['dwarf_planet'] == TargetType.DWARF_PLANET
    assert TargetType.LOOKUP['Galaxy'] == TargetType.GALAXY
    assert TargetType.LOOKUP['Star Cluster'] == TargetType.STAR_CLUSTER
    assert TargetType.LOOKUP['star_cluster'] == TargetType.STAR_CLUSTER

##########################################################################################
