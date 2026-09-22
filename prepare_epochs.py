"""Prepare P3 epochs for one subject (sub-001 by default).

Loads the EEGLAB recording, marks the ocular channels as EOG, bandpass
filters, re-references to the average of the mastoids (P9/P10), labels each
stimulus as target/standard, and cuts epochs around the stimulus events.
"""

import argparse
from pathlib import Path

import mne
import numpy as np
import pandas as pd

DATA_DIR = Path("data")
DEFAULT_SUBJECT = "sub-001"

EOG_CHANNELS = ["HEOG_left", "HEOG_right", "VEOG_lower"]
MASTOIDS = ["P9", "P10"]

L_FREQ, H_FREQ = 0.1, 30.0
TMIN, TMAX = -0.2, 0.8
BASELINE = (None, 0)

# MNE event ids must be non-zero, so the 0/1 target labels are offset by one.
EVENT_ID = {"standard": 1, "target": 2}


def subject_file(subject, suffix):
    """Path of one of a subject's BIDS files, e.g. suffix "eeg.set"."""
    return DATA_DIR / subject / "eeg" / f"{subject}_task-P3_{suffix}"


def load_raw(subject=DEFAULT_SUBJECT):
    """Read the raw recording, set EOG types, and bandpass filter."""
    raw = mne.io.read_raw_eeglab(subject_file(subject, "eeg.set"), preload=True)
    raw.set_channel_types({ch: "eog" for ch in EOG_CHANNELS})
    raw.filter(L_FREQ, H_FREQ, picks=["eeg", "eog"], fir_design="firwin")
    return raw


def load_events(subject=DEFAULT_SUBJECT):
    """Read events.tsv and add a target column (1 = target, 0 = standard).

    A stimulus code is two digits: the block's target letter followed by the
    letter shown, so the trial is a target when the digits match. Response
    events get <NA>.
    """
    events = pd.read_csv(subject_file(subject, "events.tsv"), sep="\t")
    is_stim = events["trial_type"] == "stimulus"
    code = events["value"].astype("Int64")

    events["target"] = pd.Series(pd.NA, index=events.index, dtype="Int64")
    events.loc[is_stim, "target"] = (
        (code[is_stim] // 10) == (code[is_stim] % 10)
    ).astype("Int64")
    return events


def build_event_array(events):
    """Turn the stimulus rows into an MNE events array."""
    stim = events[events["trial_type"] == "stimulus"]
    return np.column_stack(
        [
            stim["sample"].to_numpy(dtype=int),
            np.zeros(len(stim), dtype=int),
            stim["target"].to_numpy(dtype=int) + 1,
        ]
    )


def prepare_epochs(subject=DEFAULT_SUBJECT, reference="mastoid"):
    """Build one subject's epochs, e.g. subject="sub-004".

    reference="none" keeps the recorded CMS reference.
    """
    raw = load_raw(subject)
    if reference == "mastoid":
        # The recording is on BioSemi CMS, i.e. effectively unreferenced.
        # Once P9/P10 are the reference they carry no independent data.
        raw.set_eeg_reference(MASTOIDS)
        raw.drop_channels(MASTOIDS)
    events = load_events(subject)
    event_array = build_event_array(events)

    epochs = mne.Epochs(
        raw,
        event_array,
        event_id=EVENT_ID,
        tmin=TMIN,
        tmax=TMAX,
        baseline=BASELINE,
        preload=True,
        reject=None,  # no artifact rejection yet
    )
    return epochs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default=DEFAULT_SUBJECT)
    args = parser.parse_args()

    epochs = prepare_epochs(args.subject)

    print(f"\n=== {args.subject}: epoch counts per class ===")
    for name in EVENT_ID:
        print(f"  {name:9s} {len(epochs[name])}")
    print(f"  {'total':9s} {len(epochs)}")

    data = epochs.get_data()
    print("\n=== epoch array ===")
    print(f"  shape      {data.shape}  (epochs, channels, samples)")
    print(f"  times      {epochs.times[0]:.3f} to {epochs.times[-1]:.3f} s")
    print(f"  sfreq      {epochs.info['sfreq']} Hz")
    print(f"  channels   {len(epochs.ch_names)} "
          f"({len(mne.pick_types(epochs.info, eeg=True))} EEG, "
          f"{len(mne.pick_types(epochs.info, eog=True))} EOG)")
