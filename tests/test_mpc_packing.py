##########################################################################################
# hst_targets/tests/test_mpc_packing.py
##########################################################################################

from mpc_packing import mpc_pack, mpc_unpack, mpc_is_valid_packed, mpc_is_valid_unpacked

# Examples defined here:
# https://minorplanetcenter.net/mpcops/documentation/provisional-designation-definition

_UNPACKED_VS_PACKED = [
    ("1995 XA"      , "J95X00A"),
    ("1995 XL1"     , "J95X01L"),
    ("1995 FB13"    , "J95F13B"),
    ("1998 SQ108"   , "J98SA8Q"),
    ("1998 SV127"   , "J98SC7V"),
    ("1998 SS162"   , "J98SG2S"),
    ("2099 AZ193"   , "K99AJ3Z"),
    ("2008 AA360"   , "K08Aa0A"),
    ("2007 TA418"   , "K07Tf8A"),
    ("A904 OA"      , "J04O00A"),
    ("A924 OA"      , "J24O00A"),
    ("1925 OA"      , "J25O00A"),

    ("2040 P-L"     , "PLS2040"),
    ("3138 T-1"     , "T1S3138"),
    ("1010 T-2"     , "T2S1010"),
    ("4101 T-3"     , "T3S4101"),

    ("2023 BA"      , "K23B00A"),
    ("2024 CZ3"     , "K24C03Z"),
    ("2025 DZ619"   , "K25Dz9Z"),
    ("2025 DA620"   , "_PD0000"),
    ("2026 DY620"   , "_QD000N"),
    ("2027 DZ6190"  , "_RD0aEM"),
    ("2028 EA339749", "_SEZZZZ"),
    ("2029 FL591673", "_TFzzzz"),
]


def test_mpc_packing():

    for unpacked, packed in _UNPACKED_VS_PACKED:
        test = mpc_pack(unpacked)
        assert packed == test, f'{unpacked} -> {packed} failed: {test}'

        test = mpc_unpack(packed)
        assert unpacked == test, f'{packed} -> {unpacked} failed: {test}'

        assert mpc_is_valid_unpacked(unpacked), unpacked
        assert not mpc_is_valid_packed(unpacked), unpacked

        assert mpc_is_valid_packed(packed, extended=True), packed
        assert mpc_is_valid_packed(packed, extended=False) ^ (packed[0] == '_'), \
            packed

##########################################################################################
