| PyPI Release | Test Status | Code Coverage |
| ------------- | ------------ | -------------- |
| [![PyPI version](https://badge.fury.io/py/rms-hst-pipeline.svg)](https://badge.fury.io/py/rms-hst-pipeline) | [![Build status](https://img.shields.io/github/actions/workflow/status/SETI/rms-hst-pipeline/run-app-tests.yml?branch=main)](https://github.com/SETI/rms-hst-pipeline/actions) | [![Code coverage](https://img.shields.io/codecov/c/github/SETI/rms-hst-pipeline/main?logo=codecov)](https://codecov.io/gh/SETI/rms-hst-pipeline) |

# 🚀 HST Pipeline

## 🧭 Overview

The **HST Pipeline** automates the end-to-end processing of Hubble Space Telescope (HST) data for the Planetary Data System (PDS).
It supports querying data from MAST, retrieving and labeling products, preparing browse products, and generating final PDS-compliant bundles.
This tool is designed for reproducible, efficient, and configurable data pipeline execution.

---

## ⚙️ Required Setup Before Running HST Pipeline Tasks

1. Set up a virtual environment at the root directory:
   ```bash
   python -m venv venv
   source venv/bin/activate   # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

2. Set the following environment variables:

   | Variable | Description |
   | --------- | ------------ |
   | `HST_STAGING` | Directory for downloaded files |
   | `HST_PIPELINE` | Directory for logs and program info |
   | `HST_BUNDLES` | Directory for final bundles |
   | `PDS_HST_PIPELINE` | Path to the `pds-hst-pipeline` repository (where shell commands for each task are executed) |

---

## 🧩 Example Commands

### ▶️ Run the Full Pipeline (All Tasks)

- Run with all proposal IDs (pre-fetched from MAST with the *True moving target* flag):
  ```bash
  python HST/pipeline/pipeline_run.py
  ```

- Query MAST with the *True moving target* flag to get the latest IDs, then run the pipeline:
  ```bash
  python HST/pipeline/pipeline_run.py --get-ids
  ```

- Run with a single proposal ID:
  ```bash
  python HST/pipeline/pipeline_run.py --proposal-ids 07885
  ```

- Run with multiple proposal IDs:
  ```bash
  python HST/pipeline/pipeline_run.py --proposal-ids 13736 05167 10341 14930 06679
  ```

- Run with a specific number of subprocesses and a maximum allowed runtime for each task (in seconds):
  ```bash
  python HST/pipeline/pipeline_run.py --proposal-ids 07885 13736 --max-subproc 30 --max-time 1860
  ```

---

### 🧠 Run Individual Tasks (Example: Proposal ID `7885`)

These are the commands executed internally when running `pipeline_run.py`:

```bash
python HST/pipeline/pipeline_query_hst_moving_targets.py --proposal-ids 7885
python HST/pipeline/pipeline_query_hst_products.py --proposal-id 7885
python HST/pipeline/pipeline_get_program_info.py --proposal-id 7885
python HST/pipeline/pipeline_retrieve_hst_visit.py --proposal-id 7885 --vi 01
python HST/pipeline/pipeline_retrieve_hst_visit.py --proposal-id 7885 --vi 02
python HST/pipeline/pipeline_retrieve_hst_visit.py --proposal-id 7885 --vi 03
python HST/pipeline/pipeline_label_hst_products.py --proposal-id 7885 --vi 01
python HST/pipeline/pipeline_label_hst_products.py --proposal-id 7885 --vi 02
python HST/pipeline/pipeline_label_hst_products.py --proposal-id 7885 --vi 03
python HST/pipeline/pipeline_prepare_browse_products.py --proposal-id 7885 --vi 01
python HST/pipeline/pipeline_prepare_browse_products.py --proposal-id 7885 --vi 02
python HST/pipeline/pipeline_prepare_browse_products.py --proposal-id 7885 --vi 03
python HST/pipeline/pipeline_finalize_hst_bundle.py --proposal-id 7885
```

---

✅ **Tip:**
Use `--help` with any script (e.g., `python HST/pipeline/pipeline_run.py --help`) to view all available options and arguments.

---
