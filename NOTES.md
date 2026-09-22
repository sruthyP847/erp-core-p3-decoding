# P3 analysis notes — sub-001 to sub-010

Working log for the ERP CORE P3 pipeline. Last updated 2026-09-22.

## Dataset

`data/sub-001/eeg/sub-001_task-P3_eeg.set` (+ `.fdt`), BIDS-organised ERP CORE P3 task.
The table and most of the sections below describe **sub-001**, which the pipeline was
developed on; sub-002 to sub-010 were added on 2026-09-21 (see "Subjects" below).

| Property | Value |
|---|---|
| Manufacturer | BioSemi ActiveTwo |
| Sampling rate | 1024 Hz |
| Channels | 33 (30 EEG + 3 EOG) |
| Duration | 467.00 s (478,208 samples) |
| On-file filters | none (highpass 0.0, lowpass 512 Hz) |
| Reference as recorded | **CMS** (see `sub-001_task-P3_eeg.json`) |

Active visual oddball: letters A–E shown in random order, p = .2 each. One letter is
the designated target for a block, the other four are non-targets, so target
probability is .2 while the same physical stimulus serves as target in some blocks
and non-target in others. Participants respond target / non-target on every trial.

Scalp montage is the standard ERP CORE 30-channel set; the three ocular channels are
`HEOG_left`, `HEOG_right`, `VEOG_lower`.

## Subjects — sub-002 to sub-010 added 2026-09-21

Downloaded with `osf_download.py` through the OSF API: P3 component (node `etdkz`, a
child of the ERP CORE project `thsqg`), folder "P3 Raw Data BIDS-Compatible". Every
file's size and MD5 were checked against the API; 63 files, 0 failures. Layout matches
sub-001: seven files per subject in `sub-XXX/eeg/`. Every `.fdt` is exactly
channels x samples x 4 bytes against its `.set` header; all are 33 channels at 1024 Hz.

| Subject | `.fdt` | Duration | Stimulus / response events |
|---|---|---|---|
| sub-001 | 63.1 MB | 467 s | 200 / 202 |
| sub-002 | 54.7 MB | 405 s | 200 / 202 |
| sub-003 | 51.0 MB | 377 s | 200 / 201 |
| sub-004 | 73.5 MB | 544 s | 200 / 202 |
| sub-005 | 51.6 MB | 382 s | 200 / 201 |
| sub-006 | 44.3 MB | 328 s | 200 / 199 |
| sub-007 | 48.1 MB | 356 s | 200 / 202 |
| sub-008 | 62.2 MB | 460 s | 200 / 185 |
| sub-009 | 47.7 MB | 353 s | 200 / 203 |
| sub-010 | 49.6 MB | 367 s | 200 / 201 |

All ten give 200 epochs, 40 target / 160 standard. sub-008 has only 185 responses, so
it missed some trials. OSF's top level also has `participants.json`, `CHANGES` and
`LICENSE`, which were not downloaded. `python osf_download.py 11 40` fetches the rest.

The subject is a parameter everywhere: `prepare_epochs(subject="sub-001",
reference="mastoid")`, and `--subject` on `prepare_epochs.py`, `features.py` and
`plot_erp.py` (other subjects save to `erp_pz_<subject>.png`).

## Event coding

`sub-001_task-P3_events.tsv`, 402 rows: 200 stimulus + 202 response events.
`stim_file` is empty throughout.

Stimulus `value` is two digits, `XY`:

- `X` = the block's target letter (1–5 = A–E)
- `Y` = the letter actually presented

So **`X == Y` is a target** (codes 11/22/33/44/55, 8 each = **40 targets**) and `X != Y`
is a standard (**160 standards**) — a clean 20% oddball ratio.

Response codes: `201` = correct (195), `202` = incorrect (7), i.e. ~96.5% accuracy.

**Confirmed by the dataset** (2026-09-21). There is no subject-level `events.json`, but
the top-level sidecar `data/task-P3_events.json` applies to all subjects via BIDS
inheritance and documents every `value` level explicitly, e.g. `"21"` = "block target
B, trial stimulus A". That is exactly the `XY` scheme above — first digit block target,
second digit presented letter — for all 25 stimulus codes, and it also confirms
`201` = "Response - correct", `202` = "Response - error". The mapping is therefore
self-documented by the files, not just inferred from the ERP CORE convention.

Epoch events are taken from the `sample` column of `events.tsv` rather than the `.set`
file's own annotations, because that is where the target labels are derived. The two
were checked against each other and agree to within 50 µs, so either source works.

## Preprocessing so far (`prepare_epochs.py`)

1. **EOG channel types.** `HEOG_left`, `HEOG_right`, `VEOG_lower` retyped from `eeg` to
   `eog` — MNE reads all 33 channels as EEG from the `.set` file. Result: 30 EEG + 3 EOG.
   Needed before any EOG-based artifact handling, and it keeps the ocular channels out
   of EEG-wide operations such as average referencing.
2. **Bandpass filter 0.1–30 Hz.** Zero-phase FIR (`firwin`), applied to EEG and EOG
   alike so the ocular traces stay comparable for artifact detection. Filter length is
   33,793 samples (33.0 s) against a 467 s recording — fine here, but worth revisiting
   if the record is ever cut into shorter segments.
3. **Target labels.** `target` column added to the events table: 1 where the two digits
   of the stimulus code match, 0 where they don't, `<NA>` for response rows. Offset by
   one into MNE event ids (`standard` = 1, `target` = 2) since MNE ids must be non-zero.
4. **Mastoid reference.** After filtering and before epoching, EEG is re-referenced to
   the average of P9/P10 (`set_eeg_reference(["P9", "P10"])`) and P9/P10 are then
   dropped, since they no longer carry independent data. EOG channels are untouched.
   `prepare_epochs(reference="none")` skips this and keeps the recorded CMS reference.
5. **Epochs −200 to +800 ms** around each stimulus event, baseline corrected to
   `(None, 0)`, no artifact rejection (`reject=None`).

Result: **200 epochs, 40 target / 160 standard, none dropped**; array shape
`(200, 31, 1025)` = (epochs, channels, samples), 28 EEG + 3 EOG. 1025 samples = 1.0 s x 1024 Hz + 1,
both endpoints inclusive.

## Reference finding — APPLIED 2026-09-21

The first Pz plot showed no P3: target and standard were nearly superimposed
(r = 0.71) with a difference of only ~2 µV.

Cause: the recording is still on BioSemi's **CMS** reference (`"EEGReference": "CMS"`
in the sidecar). CMS/DRL is not a usable EEG reference — the data is effectively
unreferenced, so every channel carries the same large common-mode signal, which
dominates both averages and swamps the condition difference. Event timing was checked
first and ruled out (agrees with the `.set` annotations to 50 µs).

Target − standard peak at Pz, 300–600 ms window:

| Reference | Peak difference | Latency | corr(target, standard) |
|---|---|---|---|
| CMS (as recorded) | 1.96 µV | 481 ms | 0.714 |
| **Average of P9/P10 (mastoids)** | **10.87 µV** | **451 ms** | 0.765 |
| Average reference | 5.08 µV | 375 ms | 0.672 |

**Decision: re-reference to the average of P9/P10.** This is the ERP CORE convention
for the P3 component and gives by far the cleanest result — a textbook parietal
oddball response, target peaking ~16 µV around 420 ms.

**Status: applied in `prepare_epochs.py`** (step 4 above), after filtering and before
epoching — re-referencing and filtering are both linear, so the order does not change
the result. P9/P10 are dropped afterwards. Re-run check: Pz target − standard peak is
still 10.87 µV at 451 ms (target peak 15.85 µV at 415 ms), identical to the table.
`plot_erp.py` no longer re-references itself; it passes `--reference` through to
`prepare_epochs()`, and now defaults to `mastoid`.

## Features (`features.py`) — added 2026-09-21

`extract_features(epochs, channels=None, window=(0.0, 0.8))` returns `X, y`.

- EEG channels only (the 3 EOG channels are left out), each channel averaged into
  **50 ms bins**, flattened to one row per epoch. `y` is 1 = target, 0 = standard.
- 50 ms is 51.2 samples at 1024 Hz, so bins are cut on the time axis rather than by a
  fixed sample count: each bin is `[start, start + 50 ms)` and holds 51 or 52 samples.
  For the full window the first sample is at 0.00 ms and the last at 799.80 ms.
- Feature order is channel by channel: with 16 bins, channel `c`, bin `b` is column
  `c*16 + b`. When `channels` is given, columns follow the order of that list (checked).
- `X` is in volts, as MNE stores it, not µV. `classify.py` standardises, so it does not
  matter there.

Two feature sets:

| Set | Channels | Window | X shape |
|---|---|---|---|
| full (default) | all 28 EEG | 0–800 ms, 16 bins | `(200, 448)` |
| restricted (`--restricted`, or `channels=P3_CHANNELS, window=P3_WINDOW`) | Cz, CPz, Pz, P3, P4, PO3, PO4 | 300–600 ms, 6 bins | `(200, 42)` |

`y` is `(200,)`, 40 target / 160 standard, in both.

**Where the restricted parameters come from.** Kappenman et al. (2021), *NeuroImage*
225:117465 (the ERP CORE paper):

- **Window — theirs.** Table 2 gives **300–600 ms** as the recommended a priori P3
  measurement window for future studies using these tasks. (Their statistically
  significant window from the mass univariate analysis was 253.91–664.06 ms.)
- **Site — Pz only.** Table 1 quantifies the P3 at Pz; they note CPz and Pz had similar
  amplitudes and chose Pz as the most widely used site. The paper deliberately uses a
  single electrode, not a cluster.
- **The 7-channel centro-parietal cluster is our choice, not the paper's.** It is a
  cluster around the published site, not a published parameter.

Spot check: Pz, 400–450 ms bin averages 15.32 µV for targets vs 7.09 µV for standards,
so the P300 is present in the features.

## Classification, sub-001 only: full vs restricted features — 2026-09-21

`StandardScaler` + `LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")` in a
pipeline, so the scaler is fitted on training folds only. `StratifiedKFold(5,
shuffle=True, random_state=0)` — shuffled because epochs are stored block by block in
recording order. Scored by ROC-AUC and balanced accuracy. `DummyClassifier(strategy=
"prior")` goes through the same folds as the baseline. At this stage the script ran
both feature sets side by side on sub-001; it has since been changed to the ten-subject
loop in the next section, so **the tables here are no longer what `classify.py`
prints**.

Single 5-fold split, seed 0, mean ± SD across folds:

| | Full (448 features) | Restricted (42 features) |
|---|---|---|
| LDA ROC-AUC | 0.696 ± 0.109 | 0.716 ± 0.080 |
| LDA balanced accuracy | 0.609 ± 0.077 | 0.584 ± 0.056 |
| Dummy ROC-AUC | 0.500 ± 0.000 | 0.500 ± 0.000 |
| Dummy balanced accuracy | 0.500 ± 0.000 | 0.500 ± 0.000 |

Per-fold LDA scores:

| Metric | Set | Folds 1–5 |
|---|---|---|
| ROC-AUC | full | 0.855, 0.520, 0.656, 0.727, 0.723 |
| ROC-AUC | restricted | 0.707, 0.859, 0.656, 0.629, 0.727 |
| Balanced accuracy | full | 0.625, 0.562, 0.531, 0.578, 0.750 |
| Balanced accuracy | restricted | 0.562, 0.484, 0.609, 0.625, 0.641 |

Each test fold holds only 8 targets, so single folds swing widely (AUC 0.52 to 0.86)
and one split cannot separate the two feature sets.

**20-shuffle comparison.** LDA only, `RepeatedStratifiedKFold(n_splits=5, n_repeats=20,
random_state=1)`, mean of the 20 per-repeat means, with the range of per-repeat means.
Run as a one-off; it is **not in `classify.py`**.

| | Full | Restricted |
|---|---|---|
| ROC-AUC | 0.726 (0.682–0.774) | 0.722 (0.695–0.760) |
| Balanced accuracy | 0.645 (0.591–0.703) | 0.590 (0.562–0.659) |

Reading: restricting to the published window and the cluster cuts features from 448 to
42 **without changing ROC-AUC**, but **balanced accuracy is lower** (0.590 vs 0.645).
Seed 0 came out slightly low for the full set on both metrics (0.696 / 0.609 vs 0.726 /
0.645). Why the two metrics diverge is untested; one possibility is that with 20%
targets the LDA's default decision threshold suits the restricted set less well, which
balanced class priors or a threshold tuned inside the CV would address. (Tested across
ten subjects in the next section: the threshold does depress balanced accuracy.)

All of this is sub-001, no artifact rejection, 40 targets.

## Classification, ten subjects (`classify.py`) — 2026-09-21

`classify.py` now finds every `sub-*` folder in `data/` and cross-validates each subject
**separately** (within-subject) on the **restricted** feature set: Cz, CPz, Pz, P3, P4,
PO3, PO4, 300–600 ms, 50 ms bins, 42 features per epoch. Same pipeline and folds as
above (`StandardScaler` + LDA `lsqr` / `shrinkage="auto"`, stratified 5-fold, shuffled,
seed 0); 40 target / 160 standard per subject; no artifact rejection.

Two LDA variants run through the same folds and are printed side by side:

- **[1] class-frequency priors** — sklearn's default (`priors=None`, about .8 / .2).
- **[2] priors `[0.5, 0.5]`** — the only change; nothing else differs.

Per subject: mean ± SD across folds. Mean row: mean ± SD of the ten per-subject means.

| Subject | ROC-AUC [1] | ROC-AUC [2] | Bal. acc. [1] | Bal. acc. [2] |
|---|---|---|---|---|
| sub-001 | 0.716 ± 0.080 | 0.714 ± 0.077 | 0.584 ± 0.056 | 0.634 ± 0.066 |
| sub-002 | 0.896 ± 0.085 | 0.896 ± 0.096 | 0.809 ± 0.123 | 0.797 ± 0.111 |
| sub-003 | 0.777 ± 0.067 | 0.780 ± 0.053 | 0.603 ± 0.047 | 0.684 ± 0.052 |
| sub-004 | 0.876 ± 0.081 | 0.866 ± 0.089 | 0.731 ± 0.099 | 0.797 ± 0.099 |
| sub-005 | 0.716 ± 0.049 | 0.719 ± 0.067 | 0.578 ± 0.047 | 0.634 ± 0.066 |
| sub-006 | 0.579 ± 0.061 | 0.562 ± 0.071 | 0.519 ± 0.050 | 0.550 ± 0.074 |
| sub-007 | 0.876 ± 0.045 | 0.874 ± 0.033 | 0.747 ± 0.108 | 0.838 ± 0.051 |
| sub-008 | 0.626 ± 0.137 | 0.645 ± 0.134 | 0.525 ± 0.027 | 0.559 ± 0.127 |
| sub-009 | 0.556 ± 0.087 | 0.569 ± 0.092 | 0.494 ± 0.008 | 0.588 ± 0.088 |
| sub-010 | 0.641 ± 0.079 | 0.660 ± 0.071 | 0.509 ± 0.061 | 0.625 ± 0.118 |
| **Mean** | **0.726 ± 0.120** | **0.728 ± 0.117** | **0.610 ± 0.107** | **0.671 ± 0.099** |
| Dummy (prior) | 0.500 | 0.500 | 0.500 | 0.500 |

sub-001's [1] column reproduces the earlier single-subject restricted run exactly
(0.716 / 0.584), so the refactor to a subject parameter changed nothing.

**Per-subject spread.** Subjects differ far more than folds do. With the default priors
ROC-AUC runs from 0.556 (sub-009) to 0.896 (sub-002), SD 0.120 across subjects; three
subjects sit near 0.88–0.90 (sub-002, sub-004, sub-007), and four are at or below 0.64
(sub-006, sub-008, sub-009, sub-010). sub-001, the development subject, happens to sit
at the group mean. Balanced accuracy [1] runs from 0.494 to 0.809, and four subjects
(sub-006, sub-008, sub-009, sub-010) were at 0.49–0.53, i.e. chance, even though their
ROC-AUC was above 0.5.

**Threshold test — hypothesis confirmed.** The hypothesis was that with 20% targets the
LDA's class-frequency priors put the decision threshold too far towards "standard",
depressing balanced accuracy without affecting the ranking. Setting the priors to
`[0.5, 0.5]`:

- balanced accuracy rises in **9 of 10 subjects**, mean **0.610 → 0.671**;
- ROC-AUC is essentially unchanged, mean 0.726 → 0.728, no subject moving by more than
  0.02 — as expected, since AUC ignores the threshold;
- the largest gains are among the subjects nearest chance: sub-010 0.509 → 0.625,
  sub-009 0.494 → 0.588 (its fold SD of 0.008 under [1] suggests nearly every epoch was
  being labelled "standard");
- the one exception is sub-002, 0.809 → 0.797, already the best-separated subject.

The small ROC-AUC movement is probably because sklearn's `lsqr` solver also weights the
pooled covariance by the priors, which would nudge the ranking; this was recalled, not
checked in the sklearn source.

**Decision: equal priors `[0.5, 0.5]` adopted** as the LDA configuration going forward;
balanced accuracy is reported from column [2]. `classify.py` still runs [1] alongside
it so the comparison stays reproducible.

**sub-006 and sub-008 are limited by separability, not threshold.** Equal priors barely
help them (balanced accuracy 0.550 and 0.559), and their ROC-AUC is low as well (0.562
and 0.645 under [2]), so there is little class separation in these features for any
threshold to exploit. Whatever helps them has to come from upstream: artifact
rejection, features, or the ERP itself (not yet looked at; sub-008 also missed trials,
185 responses). Contrast sub-009 and sub-010, whose ROC-AUC is similarly modest (0.569,
0.660) but whose balanced accuracy did respond to the threshold.

## ERP survey, all ten subjects (`plot_erp_all.py`) — 2026-09-22

`plot_erp_all.py` draws the Pz target − standard difference wave for every subject in
`data/` on one axis (`erp_pz_all.png`), mastoid referenced, same preprocessing as
`prepare_epochs.py`, and marks each subject's peak: the **largest positive value in
250–700 ms**, a window deliberately wider than the 300–600 ms feature window so a
shifted P3 is still found. A maximum sitting on either edge of that window is flagged,
because the wave is still rising or falling there and the real extremum is outside.

| Subject | Latency | Amplitude | Note |
|---|---|---|---|
| sub-001 | 451 ms | 10.87 µV | |
| sub-002 | 443 ms | 25.00 µV | largest P3 |
| sub-003 | 371 ms | 17.83 µV | |
| sub-004 | 699 ms | 13.80 µV | **window edge, not a peak** — P3 is late |
| sub-005 | 507 ms | 10.19 µV | |
| sub-006 | 250 ms | 2.96 µV | **window edge, not a peak** — no measurable P3 |
| sub-007 | 348 ms | 9.16 µV | followed by sustained negativity, see below |
| sub-008 | 571 ms | 10.35 µV | broad, late |
| sub-009 | 455 ms | 13.02 µV | |
| sub-010 | 278 ms | 7.55 µV | early and small |
| **Mean** | **437 ms** | **12.07 µV** | SD 128 ms, 5.69 µV |

sub-001's row reproduces the value in the reference table above (10.87 µV at 451 ms).

**The 128 ms latency SD is inflated by two values that are not true peaks.** sub-004's
699 ms and sub-006's 250 ms are the last and first samples of the search window, not
maxima of the waveform; the script marks both. With those two excluded the remaining
eight run 278–571 ms. The mean and SD in the table are computed over all ten as
printed and have not been recomputed without the edge values.

**sub-006 — no measurable P3.** The difference wave never rises above ~3 µV, the "peak"
at 250 ms is just the window start, and from roughly 350 ms onwards the wave is
negative (around −3 to −5 µV) through the end of the epoch. This is the ERP behind the
subject's chance-level classification (within-subject ROC-AUC 0.562): there is no P3
in the 300–600 ms features to separate the classes on.

**sub-004 — late P3.** The wave is still rising at 700 ms and, reading from the figure,
crests at roughly 15 µV just past 700 ms, then stays above 10 µV to the end of the
epoch at 800 ms. So the P3 exists and is large, but it lies almost entirely outside
the 300–600 ms feature window. Within-subject classification is nonetheless good
(ROC-AUC 0.866), presumably from the rising edge inside the window; the LOSO result
below is much worse.

**sub-007 — sustained negativity, unresolved.** There is a positive peak of 9.16 µV at
348 ms, on the early side, after which the difference wave turns negative around
400 ms and keeps falling to about −8 to −9 µV at 700–800 ms, still heading down at the
epoch end. It is the only subject with a large negative target − standard difference
in the P3 window. Two candidate explanations, not yet distinguished:

1. **A genuine component** — a sustained target-related negativity following the P3
   (target and standard averages differing in a slow late wave).
2. **Slow drift** — low-frequency activity surviving the 0.1 Hz highpass, or a
   baseline-period difference that the −200–0 ms baseline correction propagates into
   the epoch with opposite sign; with only 40 targets a few drifting trials could do it.

Things that would separate the two: single-trial inspection of the target epochs, a
stricter highpass or linear detrending per epoch, checking the standard average alone,
and whether the negativity is parietal-only or present at every channel (drift would
be broad). None done yet. Whichever it is, the classifier uses it: sub-007's
within-subject ROC-AUC is 0.874, second best, while its LOSO score is at chance (see
next section) because its sign is opposite to everyone else's.

## Cross-subject classification (`cross_subject.py`) — 2026-09-22

`cross_subject.py` pools all ten subjects on the restricted feature set (Cz, CPz, Pz,
P3, P4, PO3, PO4, 300–600 ms, 50 ms bins, 42 features) — **2000 epochs, 400 target /
1600 standard** — and runs the adopted pipeline (`StandardScaler` + LDA `lsqr` /
`shrinkage="auto"`, priors `[0.5, 0.5]`) two ways:

1. **Leave-one-subject-out (LOSO):** train on nine subjects, test on the tenth. This is
   what a model trained on other people gets on a new person.
2. **Pooled stratified 5-fold, ignoring subject:** every test epoch has training epochs
   from the same recording. Deliberately leaky, an upper bound, not a generalisation
   estimate.

The within-subject column below is recomputed inside the script with `classify.py`'s
own folds and matches column [2] of the ten-subject table exactly.

| Subject | ROC-AUC LOSO | ROC-AUC within | Bal. acc. LOSO | Bal. acc. within |
|---|---|---|---|---|
| sub-001 | 0.663 | 0.714 ± 0.077 | 0.622 | 0.634 ± 0.066 |
| sub-002 | 0.815 | 0.896 ± 0.096 | 0.644 | 0.797 ± 0.111 |
| sub-003 | 0.678 | 0.780 ± 0.053 | 0.616 | 0.684 ± 0.052 |
| sub-004 | 0.657 | 0.866 ± 0.089 | 0.569 | 0.797 ± 0.099 |
| sub-005 | 0.492 | 0.719 ± 0.067 | 0.488 | 0.634 ± 0.066 |
| sub-006 | 0.523 | 0.562 ± 0.071 | 0.522 | 0.550 ± 0.074 |
| sub-007 | 0.490 | 0.874 ± 0.033 | 0.487 | 0.838 ± 0.051 |
| sub-008 | 0.485 | 0.645 ± 0.134 | 0.450 | 0.559 ± 0.127 |
| sub-009 | 0.575 | 0.569 ± 0.092 | 0.600 | 0.588 ± 0.088 |
| sub-010 | 0.521 | 0.660 ± 0.071 | 0.509 | 0.625 ± 0.118 |
| **Mean** | **0.590 ± 0.104** | **0.728 ± 0.117** | **0.551 ± 0.064** | **0.671 ± 0.099** |
| Dummy (prior) | 0.500 | | 0.500 | |

Mean row: mean ± SD across the ten subjects. Within-subject cells are mean ± SD across
that subject's folds; LOSO has one score per subject, so no fold SD.

Pooled 5-fold, ignoring subject (mean ± SD across folds):

| | ROC-AUC | Balanced accuracy |
|---|---|---|
| LDA, priors `[0.5, 0.5]` | 0.618 ± 0.032 | 0.586 ± 0.021 |
| Dummy (prior) | 0.500 ± 0.000 | 0.500 ± 0.000 |

**Reading.**

- **A model trained on other subjects does much worse than one trained on the
  subject.** Mean ROC-AUC falls 0.728 → 0.590 and balanced accuracy 0.671 → 0.551.
  LOSO is below within-subject for nine of ten subjects; the exception is sub-009
  (0.575 vs 0.569), which was near chance either way.
- **Five subjects are at chance under LOSO**: sub-005, sub-006, sub-007, sub-008 and
  sub-010, all with ROC-AUC ≤ 0.523. Only sub-002 (0.815) is clearly above 0.7.
- **The biggest drops are the subjects whose ERP departs from the group.** sub-007
  falls from 0.874 to 0.490: its sustained negativity has the opposite sign to the
  other subjects' P3 in the window, so a model trained on them ranks its targets
  backwards. sub-004 falls from 0.866 to 0.657: its P3 peaks after 700 ms, so the
  group model, tuned to a ~440 ms peak, finds little of it in 300–600 ms. sub-005's
  drop (0.719 → 0.492) has no such obvious cause in the survey; its P3 is ordinary
  (10.19 µV at 507 ms), so this is not explained yet.
- **Even the leaky pooled fold (0.618) is below the within-subject mean (0.728)**,
  despite seeing every subject in training. One set of LDA weights for everyone has to
  average over the between-subject differences in latency, amplitude and sign that the
  survey shows, and the per-subject standardisation that `StandardScaler` provides in
  the within-subject runs is lost when the scaler is fitted on the pooled data. That is
  an interpretation, not tested.
- Conclusion for now: with these features and this classifier, **the P3 decoder is
  subject-specific**. Cross-subject use would need either per-subject alignment
  (per-subject standardisation, latency alignment) or a model given a few labelled
  epochs from the new subject. Standardisation was tried next (below); latency
  alignment has not been.

### Per-subject standardisation — tested 2026-09-22, no average gain

`cross_subject.py` now also runs LOSO after **z-scoring each subject's 42 features
with that subject's own mean and SD over all 200 of their epochs**, targets and
standards together, so no labels are used. The held-out subject's own unlabelled
epochs set its scale, which a deployment could do too. This is done before pooling;
the pipeline's `StandardScaler` is unchanged and still fitted on the pooled training
rows. The raw LOSO column reproduces the table above exactly.

| Subject | ROC-AUC LOSO raw | ROC-AUC LOSO z/subj | Bal. acc. LOSO raw | Bal. acc. LOSO z/subj |
|---|---|---|---|---|
| sub-001 | 0.663 | 0.609 | 0.622 | 0.594 |
| sub-002 | 0.815 | 0.771 | 0.644 | 0.713 |
| sub-003 | 0.678 | 0.736 | 0.616 | 0.631 |
| sub-004 | 0.657 | 0.678 | 0.569 | 0.559 |
| sub-005 | 0.492 | 0.519 | 0.488 | 0.469 |
| sub-006 | 0.523 | 0.440 | 0.522 | 0.481 |
| sub-007 | 0.490 | 0.404 | 0.487 | 0.409 |
| sub-008 | 0.485 | 0.538 | 0.450 | 0.559 |
| sub-009 | 0.575 | 0.597 | 0.600 | 0.625 |
| sub-010 | 0.521 | 0.569 | 0.509 | 0.522 |
| **Mean** | **0.590 ± 0.104** | **0.586 ± 0.113** | **0.551 ± 0.064** | **0.556 ± 0.085** |

- **No average gain.** Mean ROC-AUC 0.590 → 0.586, balanced accuracy 0.551 → 0.556;
  the spread across subjects widens slightly. Six subjects go up, four go down. The
  largest gain is sub-003 (0.678 → 0.736); no subject that was near chance crosses
  0.75. The two best raw LOSO subjects get worse: sub-002 0.815 → 0.771, sub-001
  0.663 → 0.609, so their raw amplitude scale evidently matched the group and
  standardising discarded that.
- **Amplitude scaling is ruled out as the main cause of the LOSO drop.** If
  between-subject differences in amplitude or offset were what broke the group
  model, removing them per subject would have helped; it did not. The latency and
  sign differences seen in the ERP survey remain the likelier cause, and scaling
  cannot address either.
- **sub-007 falls further below chance, 0.490 → 0.404**, further evidence of the sign
  inversion: standardising cannot change the direction of a feature, it only makes
  the inverted signal cleaner, so a model trained on the other nine ranks sub-007's
  targets more consistently backwards. sub-006, with no P3, drops to 0.440 as well.

## Files

| File | Purpose |
|---|---|
| `osf_download.py` | Download subjects from OSF via the API with size/MD5 checks; skips intact files. `python osf_download.py 11 40` for a range (default 2–10). |
| `prepare_epochs.py` | Load, retype EOG, filter, mastoid re-reference (drops P9/P10), label targets, epoch. Importable as `prepare_epochs(subject)`; `--subject`. |
| `plot_erp.py` | Target vs standard average at Pz. `--subject`, `--reference mastoid\|none` (default `mastoid`). |
| `features.py` | `extract_features()`: 50 ms bin means per EEG channel → `X, y`. `--subject`; `--restricted` for the centro-parietal cluster, 300–600 ms. |
| `classify.py` | Within-subject stratified 5-fold CV for every subject in `data/`, restricted features: LDA with class-frequency priors vs priors `[0.5, 0.5]` vs a dummy baseline. |
| `cross_subject.py` | Pools all subjects on the restricted features: leave-one-subject-out, raw and after label-free per-subject z-scoring, vs within-subject CV per subject, plus a leaky pooled 5-fold; LDA with priors `[0.5, 0.5]`. |
| `plot_erp_all.py` | Pz target − standard difference wave for every subject on one axis, peak in 250–700 ms marked, window-edge maxima flagged. Prints the per-subject peak table. |
| `erp_pz.png` | Pz ERP, sub-001, **mastoid** referenced (P9/P10). |
| `erp_pz_cms.png` | Pz ERP, as recorded on CMS — kept for comparison. |
| `erp_pz_all.png` | Pz difference waves, all ten subjects, mastoid referenced, peaks marked. |

## Open items

- No artifact rejection or ICA yet; EOG channels are typed and ready for it. Current
  counts (40/160) are therefore the full trial set.
- Baseline correction to `(None, 0)` is applied by default in `prepare_epochs.py`.
- Classification: results are a single 5-fold split (seed 0) with 8 targets per test
  fold; repeated CV (`RepeatedStratifiedKFold`) is not in `classify.py`.
- The sub-001 full-vs-restricted balanced-accuracy gap (0.645 vs 0.590 over 20 shuffles)
  was measured with class-frequency priors and has not been re-run with equal priors;
  `classify.py` no longer runs the full feature set.
- sub-006 has no measurable P3 at Pz (survey, 2026-09-22), which accounts for its
  chance-level classification; nothing to recover with the current features. sub-008's
  P3 is broad and late (571 ms) and it missed trials; not looked at further.
- sub-007's sustained negativity after ~400 ms is unresolved: genuine component or slow
  drift. Single-trial inspection, detrending, and a cross-channel check would decide it.
- sub-004's P3 peaks after 700 ms, outside the 300–600 ms feature window; the window
  is fixed for all subjects and has not been adapted per subject.
- The survey's latency mean/SD (437 ± 128 ms) include the two window-edge values
  (sub-004, sub-006) and have not been recomputed without them.
- sub-005's LOSO score is at chance (0.492) although its within-subject ROC-AUC is
  0.719 and its P3 looks ordinary; cause not identified.
- Cross-subject: LOSO mean ROC-AUC 0.590. Per-subject standardisation tried
  (2026-09-22), no gain, so amplitude scaling is not the fix. Latency alignment
  (per-subject window or peak-aligned features) and sign handling for sub-007 are the
  untried options, as is adapting with a few labelled epochs from the new subject.
- 30 more subjects (sub-011 to sub-040) are on OSF, not downloaded.
