"""Plot the Pz target-minus-standard difference wave for every subject.

One line per subject in data/ on a single axis, mastoid referenced, with each
subject's P3 peak (largest positive value in PEAK_WINDOW) marked. Prints the
peak latency and amplitude per subject.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import mne
import numpy as np

from plot_erp import CHANNEL
from prepare_epochs import DATA_DIR, prepare_epochs

OUT_FILE = "erp_pz_all.png"
# Wider than the 300-600 ms feature window so a shifted P3 is still found.
PEAK_WINDOW = (0.25, 0.7)  # seconds


def difference_wave(epochs, channel=CHANNEL):
    """Target minus standard average at one channel; returns (times_s, µV)."""
    target = epochs["target"].average().get_data(picks=channel)[0]
    standard = epochs["standard"].average().get_data(picks=channel)[0]
    return epochs.times, (target - standard) * 1e6


def find_peak(times, signal, window=PEAK_WINDOW):
    """Latency (s) and amplitude of the largest positive value in window."""
    mask = (times >= window[0]) & (times <= window[1])
    i = np.flatnonzero(mask)[np.argmax(signal[mask])]
    return times[i], signal[i]


if __name__ == "__main__":
    mne.set_log_level("WARNING")
    subjects = sorted(p.name for p in DATA_DIR.glob("sub-*") if p.is_dir())

    waves = {}
    for subject in subjects:
        times, diff = difference_wave(prepare_epochs(subject))
        waves[subject] = (diff, *find_peak(times, diff))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ms = times * 1000
    colors = plt.cm.tab10(np.arange(len(subjects)))
    for (subject, (diff, lat, amp)), color in zip(waves.items(), colors):
        ax.plot(ms, diff, color=color, lw=1.2,
                label=f"{subject}  {amp:5.1f} µV @ {lat * 1000:.0f} ms")
        ax.plot(lat * 1000, amp, "o", color=color, ms=4)

    ax.axvspan(PEAK_WINDOW[0] * 1000, PEAK_WINDOW[1] * 1000,
               color="gray", alpha=0.08, lw=0, label="peak window")
    ax.axvline(0, color="gray", lw=0.8)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Target − standard (µV)")
    ax.set_title(f"P3 difference wave at {CHANNEL}, all subjects\n"
                 "re-referenced to average of P9/P10; dots mark the peak in "
                 f"{PEAK_WINDOW[0] * 1000:.0f}–{PEAK_WINDOW[1] * 1000:.0f} ms",
                 fontsize=11)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT_FILE, dpi=150)
    print(f"saved {OUT_FILE}")

    print(f"\n=== {CHANNEL} target − standard peak, "
          f"{PEAK_WINDOW[0] * 1000:.0f}–{PEAK_WINDOW[1] * 1000:.0f} ms ===")
    print(f"  {'subject':9s}{'latency (ms)':>14s}{'amplitude (µV)':>16s}")
    in_window = (times >= PEAK_WINDOW[0]) & (times <= PEAK_WINDOW[1])
    for subject, (_, lat, amp) in waves.items():
        # A maximum on the window edge is not a peak: the wave is still
        # rising (or falling) there, so the real extremum lies outside.
        edge = lat in (times[in_window][0], times[in_window][-1])
        print(f"  {subject:9s}{lat * 1000:>14.0f}{amp:>16.2f}"
              + ("   (window edge, no peak inside)" if edge else ""))
    lats = np.array([lat for _, lat, _ in waves.values()]) * 1000
    amps = np.array([amp for _, _, amp in waves.values()])
    print(f"  {'-' * 39}")
    print(f"  {'mean':9s}{lats.mean():>14.0f}{amps.mean():>16.2f}   "
          f"(SD {lats.std():.0f} ms, {amps.std():.2f} µV)")
