"""Build a feature matrix from the P3 epochs.

Keeps the EEG channels only, averages each channel into 50 ms bins from
0 to 800 ms after the stimulus, and flattens to one row per epoch. With
--restricted (or channels=P3_CHANNELS, window=P3_WINDOW) the features are
limited to a centro-parietal cluster and the ERP CORE P3 window.
"""

import argparse

import numpy as np

from prepare_epochs import DEFAULT_SUBJECT, EVENT_ID, prepare_epochs

BIN_WIDTH = 0.05  # seconds
FULL_WINDOW = (0.0, 0.8)

# ERP CORE (Kappenman et al., 2021, NeuroImage 225:117465) measures the P3 at
# Pz (Table 1) in a recommended a priori window of 300-600 ms (Table 2). The
# window is theirs; the cluster around Pz is our choice, not the paper's.
P3_WINDOW = (0.3, 0.6)
P3_CHANNELS = ["Cz", "CPz", "Pz", "P3", "P4", "PO3", "PO4"]


def extract_features(epochs, channels=None, window=FULL_WINDOW):
    """Return X (epochs, channels * bins) and y (1 = target, 0 = standard).

    channels is a list of channel names, or None for every EEG channel;
    window is the (start, stop) in seconds that gets cut into 50 ms bins.
    Features are ordered channel by channel: all bins of the first channel,
    then all bins of the second, and so on.
    """
    # "eeg" drops the EOG channels
    data = epochs.get_data(picks="eeg" if channels is None else channels)
    start, stop = window

    # 50 ms is 51.2 samples at 1024 Hz, so bins are cut on the time axis
    # rather than by a fixed sample count. Each bin is [start, start + 50 ms).
    n_bins = int(round((stop - start) / BIN_WIDTH))
    edges = start + BIN_WIDTH * np.arange(n_bins + 1)
    # The small tolerance stops float error pushing a sample that sits on an
    # edge into the wrong bin.
    idx = np.searchsorted(epochs.times, edges - 1e-9)

    binned = np.stack(
        [data[:, :, a:b].mean(axis=2) for a, b in zip(idx[:-1], idx[1:])],
        axis=2,
    )  # (epochs, channels, bins)

    X = binned.reshape(len(binned), -1)
    y = (epochs.events[:, 2] == EVENT_ID["target"]).astype(int)
    return X, y


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default=DEFAULT_SUBJECT)
    parser.add_argument("--restricted", action="store_true",
                        help="centro-parietal channels, 300-600 ms only")
    args = parser.parse_args()

    epochs = prepare_epochs(args.subject)
    if args.restricted:
        X, y = extract_features(epochs, channels=P3_CHANNELS, window=P3_WINDOW)
        n_channels = len(P3_CHANNELS)
    else:
        X, y = extract_features(epochs)
        n_channels = len(epochs.copy().pick("eeg").ch_names)

    print(f"\n=== {args.subject}: features ===")
    print(f"  X shape    {X.shape}  (epochs, channels x bins = "
          f"{n_channels} x {X.shape[1] // n_channels})")
    print(f"  y shape    {y.shape}  ({y.sum()} target, {(y == 0).sum()} standard)")
