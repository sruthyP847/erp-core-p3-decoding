"""Plot the target and standard ERP averages at Pz.

prepare_epochs() re-references to the average of P9/P10 the way the ERP CORE
P3 pipeline does. Pass --reference none to plot the data as recorded on the
BioSemi CMS reference (see the EEGReference field in the sidecar) instead.
"""

import argparse

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from prepare_epochs import DEFAULT_SUBJECT, prepare_epochs

CHANNEL = "Pz"


def plot(epochs, out_file, subject, subtitle):
    evokeds = {name: epochs[name].average() for name in ("target", "standard")}

    fig, ax = plt.subplots(figsize=(8, 5))
    times = evokeds["target"].times * 1000  # ms

    for name, color in (("target", "crimson"), ("standard", "steelblue")):
        evoked = evokeds[name]
        signal = evoked.get_data(picks=CHANNEL)[0] * 1e6  # volts -> microvolts
        ax.plot(times, signal, color=color, label=f"{name} (n={evoked.nave})")

    ax.axvline(0, color="gray", lw=0.8)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude (µV)")
    ax.set_title(f"P3 ERP at {CHANNEL} — {subject}\n{subtitle}", fontsize=11)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_file, dpi=150)
    print(f"saved {out_file}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default=DEFAULT_SUBJECT)
    parser.add_argument("--reference", choices=["none", "mastoid"], default="mastoid")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    epochs = prepare_epochs(args.subject, reference=args.reference)

    # sub-001 keeps the plain file names; other subjects get theirs appended
    tag = "" if args.subject == DEFAULT_SUBJECT else f"_{args.subject}"

    if args.reference == "mastoid":
        subtitle = "re-referenced to average of P9/P10"
        out = args.out or f"erp_pz{tag}.png"
    else:
        subtitle = "as recorded (BioSemi CMS reference)"
        out = args.out or f"erp_pz_cms{tag}.png"

    plot(epochs, out, args.subject, subtitle)


if __name__ == "__main__":
    main()
