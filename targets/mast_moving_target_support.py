#!/usr/bin/env python3
##########################################################################################
# targets/mast_moving_target_support.py
##########################################################################################
"""Retrieve HST support files (SPT / SHM / SHF) for every moving-target observation.

Workflow
--------
1. Query MAST (CAOM) for every HST observation flagged as a moving target
   (``mtFlag = True``).  These span 845 programs across all instrument eras.
2. For those observations, list the data products and keep only the files whose
   name ends in ``_spt.fits``, ``_shm.fits`` or ``_shf.fits`` (the support /
   standard-header files that carry the MT_LVn ephemeris keywords).
3. Write a manifest CSV, then download the files into per-program subfolders::

       <outdir>/<proposal_id>/<rootname>_spt.fits

Downloads are resumable: a file already present with the expected byte size is
skipped, so re-running fills in only what is missing.

Requires:  astroquery, astropy, requests   (pip install astroquery requests)

Examples
--------
    # full run into the default cache
    python mast_moving_target_support.py

    # just build the manifest, download nothing
    python mast_moving_target_support.py --manifest-only

    # try a few programs first
    python mast_moving_target_support.py --limit-programs 3
"""

import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import requests
from astropy.table import Table, vstack
from astroquery.mast import Observations

SUFFIXES = ("_spt.fits", "_shm.fits", "_shf.fits")
DOWNLOAD_URL = "https://mast.stsci.edu/api/v0.1/Download/file"

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTDIR = os.path.join(os.path.dirname(_HERE), "caches", "SPT_CACHE")

_thread_local = threading.local()


def _session():
    """One requests.Session per worker thread."""
    s = getattr(_thread_local, "session", None)
    if s is None:
        s = requests.Session()
        _thread_local.session = s
    return s


# --------------------------------------------------------------------------
# MAST metadata
# --------------------------------------------------------------------------
def query_moving_target_observations():
    """Return the CAOM observation table for every HST moving-target obs."""
    print("Querying MAST for HST moving-target observations ...", flush=True)
    t0 = time.time()
    obs = Observations.query_criteria(obs_collection="HST", mtFlag=True)
    pids = np.unique(np.array(obs["proposal_id"]).astype(str))
    print("  %d observations across %d programs  (%.0fs)"
          % (len(obs), len(pids), time.time() - t0), flush=True)
    return obs


def build_manifest(obs, chunk=1000):
    """List products for the observations and keep SPT/SHM/SHF files.

    Returns an astropy Table with one row per file to fetch.
    """
    keep = []
    n = len(obs)
    print("Listing products in chunks of %d ..." % chunk, flush=True)
    for i in range(0, n, chunk):
        sub = obs[i:i + chunk]
        prod = Observations.get_product_list(sub)
        fn = np.char.lower(np.array(prod["productFilename"]).astype(str))
        mask = np.zeros(len(prod), bool)
        for suf in SUFFIXES:
            mask |= np.char.endswith(fn, suf)
        if mask.any():
            keep.append(prod[mask])
        done = min(i + chunk, n)
        got = sum(len(k) for k in keep)
        print("  %6d / %6d obs   support files so far: %d"
              % (done, n, got), flush=True)

    if not keep:
        return Table()
    man = vstack(keep, metadata_conflicts="silent")

    # De-duplicate on the archive URI (a support file can be listed under more
    # than one parent observation).
    _, uniq = np.unique(np.array(man["dataURI"]).astype(str), return_index=True)
    man = man[np.sort(uniq)]
    man["proposal_id"] = np.array(man["proposal_id"]).astype(str)
    return man


# --------------------------------------------------------------------------
# download
# --------------------------------------------------------------------------
def _target_path(outdir, row):
    return os.path.join(outdir, str(row["proposal_id"]), str(row["productFilename"]))


def download_one(row, outdir):
    """Fetch a single product. Returns (status, nbytes).

    status in {'ok', 'skip', 'fail'}.
    """
    dest = _target_path(outdir, row)
    expected = int(row["size"]) if row["size"] not in (None, "", np.ma.masked) else -1
    if os.path.exists(dest) and (expected < 0 or os.path.getsize(dest) == expected):
        return "skip", os.path.getsize(dest)

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    try:
        r = _session().get(DOWNLOAD_URL, params={"uri": str(row["dataURI"])},
                           stream=True, timeout=180)
        r.raise_for_status()
        nbytes = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                if chunk:
                    f.write(chunk)
                    nbytes += len(chunk)
        os.replace(tmp, dest)
        return "ok", nbytes
    except Exception as exc:            # noqa: BLE001 - log and continue
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        sys.stderr.write("  FAIL %s : %s\n" % (row["productFilename"], exc))
        return "fail", 0


def download_all(man, outdir, workers=8):
    """Download every file in the manifest, resumably, with a thread pool."""
    total = len(man)
    print("Downloading %d files with %d workers -> %s" % (total, workers, outdir),
          flush=True)
    counts = {"ok": 0, "skip": 0, "fail": 0}
    nbytes = 0
    t0 = time.time()
    rows = [man[i] for i in range(total)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(download_one, row, outdir): row for row in rows}
        done = 0
        for fut in as_completed(futs):
            status, nb = fut.result()
            counts[status] += 1
            nbytes += nb
            done += 1
            if done % 250 == 0 or done == total:
                dt = time.time() - t0
                print("  %6d / %6d   ok=%d skip=%d fail=%d   %.2f GB   %.0fs"
                      % (done, total, counts["ok"], counts["skip"],
                         counts["fail"], nbytes / 1e9, dt), flush=True)
    return counts, nbytes


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--outdir", default=DEFAULT_OUTDIR,
                    help="download directory (default: %(default)s)")
    ap.add_argument("--manifest-only", action="store_true",
                    help="write the manifest CSV but download nothing")
    ap.add_argument("--workers", type=int, default=8,
                    help="parallel download workers (default: 8)")
    ap.add_argument("--chunk", type=int, default=1000,
                    help="observations per product-list query (default: 1000)")
    ap.add_argument("--limit-programs", type=int, default=0,
                    help="restrict to the first N programs (for testing)")
    args = ap.parse_args(argv)

    os.makedirs(args.outdir, exist_ok=True)

    obs = query_moving_target_observations()

    if args.limit_programs:
        pids = np.unique(np.array(obs["proposal_id"]).astype(str))
        keep_pids = set(sorted(pids)[:args.limit_programs])
        mask = np.array([str(p) in keep_pids for p in obs["proposal_id"]])
        obs = obs[mask]
        print("Restricted to %d programs -> %d observations"
              % (len(keep_pids), len(obs)), flush=True)

    man = build_manifest(obs, chunk=args.chunk)
    if len(man) == 0:
        print("No SPT/SHM/SHF products found.", flush=True)
        return

    # Save the manifest.
    cols = ["proposal_id", "obs_id", "productFilename",
            "productSubGroupDescription", "size", "dataURI"]
    cols = [c for c in cols if c in man.colnames]
    manifest_path = os.path.join(args.outdir, "manifest.csv")
    man[cols].write(manifest_path, format="csv", overwrite=True)

    sizes = np.array(man["size"]).astype(float)
    nprog = len(np.unique(np.array(man["proposal_id"]).astype(str)))
    print("\nManifest: %d files, %d programs, %.2f GB total"
          % (len(man), nprog, np.nansum(sizes) / 1e9), flush=True)
    print("  saved -> %s" % manifest_path, flush=True)

    if args.manifest_only:
        print("--manifest-only: not downloading.", flush=True)
        return

    counts, nbytes = download_all(man, args.outdir, workers=args.workers)
    print("\nDone. ok=%d skip=%d fail=%d   %.2f GB   into %s"
          % (counts["ok"], counts["skip"], counts["fail"],
             nbytes / 1e9, args.outdir), flush=True)
    if counts["fail"]:
        print("Re-run to retry the %d failed files (resumable)." % counts["fail"],
              flush=True)


if __name__ == "__main__":
    main()
