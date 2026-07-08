#!/usr/bin/env python3
##########################################################################################
# support/reality_check_radec.py
##########################################################################################
"""Reality-check RA_TARG/DEC_TARG in tests/SPT_TESTS.py against a two-body
propagation of the orbital elements stored in the MT_LV1_* keywords.

For every entry whose MT_LV1_1 says TYPE = ASTEROID or TYPE = COMET:

  * assemble the full element string from the MT_LV1_* continuation fields,
  * parse A/Q, E, I, O, W, M/T, EPOCH and the T/Epoch time scales,
  * evaluate the sky position with orbital_radec at the mean of PSTRTIME and
    PSTPTIME (the observing midpoint, UTC),
  * compare to the header RA_TARG / DEC_TARG and report the angular offset.

Propagation uses perturb=False (pure two-body), matching HST's own planning
convention, so a correct entry should reproduce RA_TARG to ~arcsec.  Large
offsets flag suspect header values, mis-entered elements, or frame issues
(e.g. B1950 elements, which orbital_radec does not precess).

Run:  python support/reality_check_radec.py [--asteroids] [--comets] [-o FILE]
By default both asteroids and comets are checked; pass --asteroids or --comets to
restrict to one type.
"""

import argparse
import csv
import math
import os
import sys
from datetime import datetime, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "targets"))  # orbital_radec
sys.path.insert(0, os.path.join(_ROOT, "tests"))    # SPT_TESTS

from orbital_radec import asteroid_radec, comet_radec
from SPT_TESTS import SPT_TESTS

DEFAULT_SCALE = "UTC"      # assumed T/EPOCH time scale when none is given
# Header position to check the propagated sky position against: the nominal target
# position RA_TARG / DEC_TARG. (RA_REF/DEC_REF, the aperture reference, is no longer
# carried in SPT_TESTS.)
COORD = ("RA_TARG", "DEC_TARG")
DEFAULT_CSV_OUT = os.path.join(_HERE, "reality_check_offsets.csv")

_MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


# --------------------------------------------------------------------------
# parsing helpers
# --------------------------------------------------------------------------
def full_mt_lv1(entry):
    """Concatenate MT_LV1_1, MT_LV1_2, ... in numeric order."""
    parts = []
    i = 1
    while ("MT_LV1_%d" % i) in entry:
        parts.append(entry["MT_LV1_%d" % i])
        i += 1
    return "".join(parts)


def parse_elements(s):
    """'TYPE = ASTEROID, A = 2.5, ...' -> {'TYPE':'ASTEROID','A':'2.5',...}."""
    out = {}
    for field in s.split(","):
        if "=" in field:
            k, v = field.split("=", 1)
            out[k.strip().upper()] = v.strip()
    return out


def norm_date(s):
    """Normalise 'DD-MON-YY[YY][:hh:mm:ss][.]' -> 'DD-MON-YYYY:hh:mm:ss'."""
    s = s.strip().rstrip(".").strip()
    datep, _, timep = s.partition(":")
    dd, mon, yy = [p.strip() for p in datep.split("-")]
    yy = int(yy)
    if yy < 100:
        yy = 1900 + yy if yy >= 50 else 2000 + yy       # HST-era pivot
    tp = (timep.split(":") + ["0", "0", "0"])[:3]
    hh, mm, ss = int(tp[0] or 0), int(tp[1] or 0), int(float(tp[2] or 0))
    return "%02d-%s-%04d:%02d:%02d:%02d" % (int(dd), mon.upper(), yy, hh, mm, ss)


def hst_time(s):
    """Parse HST 'YYYY.DDD:hh:mm:ss' (day-of-year) into a datetime."""
    left, hh, mm, ss = s.strip().split(":")
    year, doy = left.split(".")
    return (datetime(int(year), 1, 1)
            + timedelta(days=int(doy) - 1, hours=int(hh),
                        minutes=int(mm), seconds=int(ss)))


def mean_obs_dt(entry):
    """Midpoint datetime of PSTRTIME / PSTPTIME (rounded to the second)."""
    t0 = hst_time(entry["PSTRTIME"])
    t1 = hst_time(entry["PSTPTIME"])
    mid = t0 + (t1 - t0) / 2
    return (mid + timedelta(seconds=0.5)).replace(microsecond=0)


def dt_to_str(dt):
    return "%02d-%s-%04d:%02d:%02d:%02d" % (
        dt.day, _MON[dt.month - 1], dt.year, dt.hour, dt.minute, dt.second)


def epoch_dt(norm):
    """Parse a normalised 'DD-MON-YYYY:hh:mm:ss' back into a datetime."""
    datep, _, timep = norm.partition(":")
    dd, mon, yy = datep.split("-")
    hh, mm, ss = timep.split(":")
    return datetime(int(yy), _MON.index(mon.upper()) + 1, int(dd),
                    int(hh), int(mm), int(ss))


def angsep_arcsec(ra1, dec1, ra2, dec2):
    """Great-circle separation between two (deg,deg) points, in arcsec."""
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    a = (math.sin((d2 - d1) / 2) ** 2
         + math.cos(d1) * math.cos(d2) * math.sin((r2 - r1) / 2) ** 2)
    return math.degrees(2 * math.asin(min(1.0, math.sqrt(a)))) * 3600.0


# --------------------------------------------------------------------------
# per-entry check
# --------------------------------------------------------------------------
def check(key, entry):
    """Return a result dict (with 'offset' or 'skip')."""
    for req in (COORD[0], COORD[1], "PSTRTIME", "PSTPTIME"):
        if req not in entry:
            return {"key": key, "skip": "missing %s" % req}

    el = parse_elements(full_mt_lv1(entry))
    typ = el.get("TYPE", "").upper()
    equinox = el.get("EQUINOX", "J2000").upper()
    obs_dt = mean_obs_dt(entry)
    obs = dt_to_str(obs_dt)
    ra_h, dec_h = float(entry[COORD[0]]), float(entry[COORD[1]])
    epoch_norm = norm_date(el["EPOCH"]) if "EPOCH" in el else None

    def run(perturb):
        if typ == "ASTEROID":
            a = float(el["A"]) if "A" in el else float(el["Q"]) / (1 - float(el["E"]))
            return asteroid_radec(
                a=a, e=float(el["E"]), incl=float(el["I"]),
                node=float(el["O"]), arg_peri=float(el["W"]),
                mean_anom=float(el["M"]), epoch=epoch_norm,
                time=obs, epoch_scale=el.get("EPOCHTIMESCALE", DEFAULT_SCALE),
                time_scale="UTC", perturb=perturb, equinox=equinox)
        if typ == "COMET":
            return comet_radec(
                q=float(el["Q"]), e=float(el["E"]), incl=float(el["I"]),
                node=float(el["O"]), arg_peri=float(el["W"]),
                peri_time=norm_date(el["T"]), epoch=epoch_norm,
                time=obs, peri_time_scale=el.get("TTIMESCALE", DEFAULT_SCALE),
                epoch_scale=el.get("EPOCHTIMESCALE", DEFAULT_SCALE),
                time_scale="UTC", perturb=perturb, equinox=equinox)
        return None

    if typ not in ("ASTEROID", "COMET"):
        return {"key": key, "skip": "TYPE=%r" % typ}
    try:
        # Propagate WITH major-planet perturbations so a stale osculation epoch
        # is not itself the source of the offset; fall back to two-body if the
        # perturbation integrator rejects the elements (e.g. extreme orbits).
        try:
            res = run(True)
        except Exception:                        # noqa: BLE001
            res = run(False)
    except KeyError as exc:
        return {"key": key, "skip": "missing element %s" % exc}
    except Exception as exc:                     # noqa: BLE001
        return {"key": key, "skip": "error: %s" % exc}

    gap_yr = abs((obs_dt - epoch_dt(epoch_norm)).days) / 365.25 if epoch_norm else 0.0
    tarkey = entry.get("TARKEY1", "").upper()
    return {"key": key, "targname": entry.get("TARGNAME", ""),
            "tarkey1": entry.get("TARKEY1", ""),
            "type": typ, "equinox": equinox, "obs": obs,
            "ra_h": ra_h, "dec_h": dec_h, "ra_c": res.ra, "dec_c": res.dec,
            "offset": angsep_arcsec(ra_h, dec_h, res.ra, res.dec),
            "gap_yr": gap_yr,
            "nongrav": any(k in el for k in ("A1", "A2", "A3")),
            "other": tarkey.startswith("OTHER") or "SLEW" in entry.get("TARGNAME", "").upper(),
            "has_lv2": any(k.startswith("MT_LV2") for k in entry)}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def fmt_off(arcsec):
    if arcsec < 60:
        return "%.2f\"" % arcsec
    if arcsec < 3600:
        return "%.2f'" % (arcsec / 60)
    return "%.3f deg" % (arcsec / 3600)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Reality-check RA_TARG/DEC_TARG in tests/SPT_TESTS.py against "
                    "two-body propagation of the MT_LV1_* orbital elements.")
    parser.add_argument("--asteroids", action="store_true",
                        help="include TYPE=ASTEROID entries (default: both types)")
    parser.add_argument("--comets", action="store_true",
                        help="include TYPE=COMET entries (default: both types)")
    parser.add_argument("--output", "-o", default=DEFAULT_CSV_OUT,
                        help="output CSV path (default: %(default)s)")
    args = parser.parse_args(argv)

    # With neither flag given, include both types; otherwise only those requested.
    include_asteroids = args.asteroids or not args.comets
    include_comets = args.comets or not args.asteroids
    csv_out = args.output

    results, skips = [], []
    for key, entry in SPT_TESTS:
        typ = entry.get("MT_LV1_1", "").replace(" ", "").upper()
        is_ast = typ.startswith("TYPE=ASTEROID")
        is_com = typ.startswith("TYPE=COMET")
        if not ((is_ast and include_asteroids) or (is_com and include_comets)):
            continue
        r = check(key, entry)
        (skips if "skip" in r else results).append(r)

    results.sort(key=lambda r: r["offset"], reverse=True)

    # full CSV
    with open(csv_out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "targname", "tarkey1", "type", "equinox", "obs_time",
                    COORD[0].lower(), COORD[1].lower(), "ra_calc", "dec_calc",
                    "offset_arcsec", "epoch_gap_yr", "nongrav", "other", "has_lv2"])
        for r in results:
            w.writerow([r["key"], r["targname"], r["tarkey1"], r["type"],
                        r["equinox"], r["obs"],
                        "%.6f" % r["ra_h"], "%.6f" % r["dec_h"],
                        "%.6f" % r["ra_c"], "%.6f" % r["dec_c"],
                        "%.3f" % r["offset"], "%.2f" % r["gap_yr"],
                        r["nongrav"], r["other"], r["has_lv2"]])

    # summary
    n = len(results)
    offs = [r["offset"] for r in results]
    print("=" * 78)
    print("REALITY CHECK: %s/%s vs propagation of MT_LV elements"
          % (COORD[0], COORD[1]))
    print("=" * 78)
    print("checked: %d   skipped: %d   (full table -> %s)"
          % (n, len(skips), os.path.basename(csv_out)))
    if n:
        srt = sorted(offs)
        pct = lambda p: srt[min(n - 1, int(p / 100 * n))]
        print("offset percentiles:  median %s   90%% %s   99%% %s   max %s"
              % (fmt_off(pct(50)), fmt_off(pct(90)), fmt_off(pct(99)),
                 fmt_off(max(offs))))
        bins = [("< 1\"", 0, 1), ("1-10\"", 1, 10), ("10-60\"", 10, 60),
                ("1'-10'", 60, 600), ("10'-1deg", 600, 3600),
                ("1-10deg", 3600, 36000), ("> 10deg", 36000, 9e9)]
        print("\ndistribution:")
        for label, lo, hi in bins:
            c = sum(1 for o in offs if lo <= o < hi)
            print("  %-9s %5d  %s" % (label, c, "#" * (c * 50 // max(1, n))))

    # excessive
    THRESH = 60.0    # arcsec
    bad = [r for r in results if r["offset"] >= THRESH]
    print("\n" + "-" * 78)
    print("HIGHLIGHTED: %d entries with offset >= %s" % (len(bad), fmt_off(THRESH)))
    print("-" * 78)
    clip = lambda s, n: (s if len(s) <= n else s[:n - 1] + "…")
    print("%-28s %-20s %-18s %-8s %10s  %s" %
          ("key", "targname", "tarkey1", "type", "offset", "note"))
    for r in bad[:60]:
        note = []
        if r["other"]:
            note.append("DUMMY/slew target")
        if r["equinox"] != "J2000":
            note.append("%s (rotated to J2000)" % r["equinox"])
        if r["nongrav"]:
            note.append("nongravitational (A1/A2/A3)")
        if r["gap_yr"] >= 1:
            note.append("epoch gap %.1f yr" % r["gap_yr"])
        if r["has_lv2"]:
            note.append("MT_LV2 offset")
        print("%-28s %-20s %-18s %-8s %10s  %s" %
              (r["key"], clip(r["targname"], 20), clip(r["tarkey1"], 18),
               r["type"], fmt_off(r["offset"]), "; ".join(note) or "-"))
    if len(bad) > 60:
        print("... %d more in %s" % (len(bad) - 60, os.path.basename(csv_out)))

    # Why are they off?  (categories are not exclusive; "unexplained" = none apply)
    def explained(r):
        return r["other"] or r["equinox"] != "J2000" or r["nongrav"] or r["gap_yr"] >= 1
    cats = [
        ("dummy/slew targets", lambda r: r["other"]),
        ("B1950 elements (rotated to J2000)", lambda r: r["equinox"] != "J2000"),
        ("nongravitational comets", lambda r: r["nongrav"]),
        ("epoch gap >= 1 yr", lambda r: r["gap_yr"] >= 1),
        ("UNEXPLAINED (clean, still off)", lambda r: not explained(r)),
    ]
    print("\nbreakdown of the %d highlighted:" % len(bad))
    for label, fn in cats:
        print("  %4d  %s" % (sum(1 for r in bad if fn(r)), label))

    if skips:
        print("\nskipped reasons (counts):")
        from collections import Counter
        for reason, c in Counter(s["skip"].split(":")[0] for s in skips).most_common():
            print("  %4d  %s" % (c, reason))


if __name__ == "__main__":
    main()
