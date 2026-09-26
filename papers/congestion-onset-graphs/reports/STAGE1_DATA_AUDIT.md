# Stage 1 data audit

Audit and downloads: September 22, 2026. Only the originating PEMS-BAY release,
its graph, and coordinates were downloaded as measurement inputs. All raw files
remain ignored by Git. The public release was usable for a bounded local research
pilot; no LargeST measurement download was necessary. No test measurements or
test outcomes were inspected, fitted, or scored.

## Sources, integrity, and terms

The [originating DCRNN repository](https://github.com/liyaguang/DCRNN) links the
Google Drive folder from which `pems-bay.h5` was retrieved. It describes speed
forecasting and requests research citation. Original file id:
`1wD-mHlqAb2mtHOe_68fZvDh1LpDegMMq`.

| Original file | Bytes | SHA-256 |
|---|---:|---|
| pems-bay.h5 | 135,930,936 | `65d69fb0a2323dba9867179eb7af47c8b814186bc459ff0a4937d21614153c8f` |
| adj_mx_bay.pkl | 1,681,480 | `116275f5704d0d492018e14c047f7ae5004385b450aa907f88424055a4a97370` |
| graph_sensor_locations_bay.csv | 9,750 | `276ee01059610774d4e59572507f7e32eaac21f1f5882fcd9e3d7d426a4b7a6c` |

Exact URLs, UTC retrieval times, content types, and statuses are in
`manifests/pems_download.json`; metadata evidence is in `source_access.json`.
The original graph pickle is read with a restricted NumPy-only unpickler after
retrieval; arbitrary pickle globals are rejected.

The code repository's MIT license is **not** taken as a raw-measurement license.
The [Zenodo mirror API](https://zenodo.org/api/records/5724362) explicitly records
`cc-by-4.0` for its derivative deposit by Semin Kwak. This clarifies the mirror's
declared license but does not prove that the depositor can grant every underlying
right. No mirror measurements were needed or redistributed.

The attempted PeMS User_Agreement URL returned an application error. Following
the site's own Conditions of Use link led to its login/welcome page without
retrievable dataset-specific terms; both attempts have hashes. General
[Caltrans Conditions of Use](https://dot.ca.gov/conditions-of-use) state a broad
public-information policy with exceptions for third-party material. Applicability
of that general policy to every field in this historical derivative remains
unverified. The bounded local use relies on the authors' public research release,
not a claim that an open measurement license was conclusively established.
Redistribution remains disabled. A collaborator who requires a conclusive
originating-data license should treat that as an unresolved release gate.

The prespecified LargeST fallback was inspected through its author repository,
paper, and Kaggle file-list API. The [paper's §4.3](https://arxiv.org/html/2306.08259v2)
distinguishes CC BY-NC 4.0 data from MIT code. The 2017 file is listed at
7,233,256,952 bytes; the API lists metadata and adjacency separately. No Kaggle
credentials were needed for this metadata query and no annual file was fetched.
Had a fallback been needed, the target would have been **throughput extremes**,
not low-speed congestion. This pilot retained the primary task.

## Actual content and graph alignment

The HDF group is `speed`; values have shape **52,116 x 325**. Axes and value-column
identifiers agree exactly. Timestamps run from **2017-01-01 00:00:00** through
**2017-06-30 23:55:00**. They are naive: no timezone is stored. There are no duplicate
timestamps. One jump occurs after March 12 at 01:55; the next timestamp is 03:00,
leaving 12 missing nominal frames. This is consistent with a daylight-saving
transition, but timezone metadata is absent, so the implementation does not assert
or reconstruct a timezone. March 12 is excluded as an incomplete calendar day.

Units are mph, supported by the PeMS speed legend and the originating speed task.
There is no flow-to-speed or unit conversion. Sensor IDs in source graph order
equal HDF column order, and coordinates are explicitly reindexed by sensor ID.
The ordering hash is in `manifests/data_audit.json`.

The graph has 2,694 positive source entries, including 325 diagonal entries.
Removing self loops leaves **2,369 directed nonself edges**. Twelve rows then
have no outgoing positive weight and receive an identity transition. Every row
is normalized. Under the fixed convention, row i aggregates neighbor states j;
it does not establish a causal traffic-flow direction. Coordinates alone define
the 16 deterministic balanced spatial blocks. No validation/test outcome enters
partition construction.

## Splits, embargo, masks, and development support

Of 181 calendar dates, 180 have complete five-minute grids. The first 108 complete
days are training, next 36 validation, last 36 test. Full 12-frame input histories
and six-frame outcomes must stay inside their split, avoid incomplete days, and
have no time gaps. Each boundary excludes observations in [boundary-90min,
boundary+90min); whole windows must avoid the excluded frames. This conservative
interpretation applies the embargo on both sides.

| Split | Dates | Complete days | Frames after embargo | Valid forecast origins |
|---|---|---:|---:|---:|
| Train | Jan 1–Apr 19, excluding Mar 12 | 108 | 31,086 | 31,052 |
| Validation | Apr 20–May 25 | 36 | 10,332 | 10,315 |
| Test, index only | May 26–Jun 30 | 36 | 10,350 | 10,333 |

The train/validation boundary is April 20 00:00 and validation/test boundary is
May 26 00:00. Exact date lists are saved. Test HDF values are never loaded by
the Stage 1 reader. Tests with deliberately poisoned test values verify that
development arrays leave those rows unavailable; asking to read `test` raises.

Training contains no zero, nonfinite, or negative values on retained frames.
Validation contains **304 zero values**, no negative or nonfinite values, and
99.99095% nonzero finite coverage. There are six duplicate **value vectors** in
training at distinct timestamps and none in validation. They remain records;
equal sensor vectors are not duplicate timestamps or evidence that they should
be dropped. Test value duplicates/zeros/missingness are intentionally unknown.

The released HDF contains no raw quality or imputation flags. DCRNN's metric
implementation masks designated missing values, but that does not establish
whether every zero in this file is a sentinel or stopped traffic. Accordingly,
zeros are treated as **unknown indicators**: lower event bounds count them as
non-events, upper bounds as events. This avoids asserting either convention.
Missing future observations are never filled into labels. At least 95% future
sensor-time coverage and agreement of lower/upper event labels are required.
Upstream imputation cannot be identified or undone without original flags; the
scientific target is the **released recorded-speed process**, not independently
verified raw detector truth.

Reference free speeds are training 85th percentiles. The state is
logit(clip(1-v/v_free, .001, .999)); the local event threshold is state >= 0.
The sustained event requires the count threshold for three consecutive future
frames within six future frames. The training 90th percentile, subject to the
10% floor and upward attainable-count rounding, fixes the threshold at
**48/325 = 0.1476923**. No validation threshold search was performed.

| Development support | Training | Validation |
|---|---:|---:|
| Unambiguous, coverage-eligible forecast origins | 31,052 | 10,309 |
| Positive target origins | 3,130 | 1,478 |
| Ambiguous event bounds | 0 | 0 |
| Onset-eligible origins, no conservatively active current event | 28,282 | 8,981 |
| Merged episode groups | 116 | 47 |
| Calendar days with positive targets | 73 | 26 |

Six validation origins fail coverage even though their event bounds agree.
Episode groups merge positive target periods with gaps strictly shorter than
30 minutes. These groups and overlapping forecast windows are **not assumed
statistically independent**. Whole days are the resampling clusters. The plan's
100-training/30-validation gate is met, so the single region alternative was not
invoked. A reusable metadata-connected-region alternative exists but was not used
to search for favorable labels.

## Frozen pilot and derived artifacts

The origin rule selects 128 uniformly spaced indices among the 10,315
split-contained validation origins **before consulting their outcomes**. Saved
indices are in `manifests/derived_data.json`. One fails future coverage, leaving
127 scored origins, 20 positive targets, and all 36 validation days. The onset
subset has 110 eligible origins and only five positives. These are preliminary
development scores, with no held-out test validation.

The CPU-only fit uses 2,588 training histories at a fixed 12-frame spacing,
rank-16 Gaussian factors with explicit diagonal floor 1e-6, six seasonal calendar
features, and one shared constrained dynamical model. Three complete training-day
folds produce 5,174 intact multivariate six-frame out-of-fold residual sequences.
Regimes are weekday/weekend crossed with hour//8. Fitting missing histories uses
training-only imputation; runtime constraints omit missing observations.

`data/processed/pilot_inputs.npz` is **46,322,954 bytes**, SHA-256
`65afcc26e5c3ca971557167f9de1252533c7f9acb20fe417671898dadc202ea3`.
It contains fitted arrays, residual sequences, and the 128 validation histories
and outcomes; it is **not committed**. The source/derived manifests record the
input hash, transformations, selection, dimensions, and date rules. Training
residuals are rounded to FP32 for storage as an explicit part of the fixed
empirical working law. No independent sensor shuffling is used.

Raw measurement downloads total **137,622,166 bytes**. Processed inputs occupy
about 46.3 MB. Small documentation downloads and dependency wheels add to these
totals; exact available installation evidence and final footprint are recorded
in the main handoff. These are far below the 12 GB acquisition and 20 GB processed
limits. No large archive, five-year download, or raw measurement redistribution
occurred.
