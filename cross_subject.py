"""Cross-subject classification of target vs standard epochs.

Pools every subject in data/ on the restricted feature set (centro-parietal
channels, ERP CORE P3 window) and runs the equal-prior StandardScaler +
shrinkage-LDA pipeline from classify.py in two ways:

1. leave-one-subject-out: train on nine subjects, test on the tenth, so the
   score is what a model trained on other people gets on a new person;
2. pooled stratified 5-fold that ignores subject, so every test epoch has
   training epochs from the same recording -- a deliberately leaky
   comparison, an upper bound rather than a generalisation estimate.

Leave-one-subject-out is run twice: on the raw pooled features, and after
per-subject standardisation (each subject's features z-scored with that
subject's own mean and SD over all of their epochs, labels unused). Each
held-out subject's two LOSO scores are printed next to its within-subject
score from classify.py's cross-validation.
"""

import mne
import numpy as np

from sklearn.dummy import DummyClassifier
from sklearn.model_selection import LeaveOneGroupOut, StratifiedKFold, cross_validate

from classify import N_SPLITS, SCORING, SEED, build_lda, evaluate
from features import BIN_WIDTH, P3_CHANNELS, P3_WINDOW, extract_features
from prepare_epochs import DATA_DIR, prepare_epochs

# The configuration adopted in classify.py; balanced accuracy is reported
# from it there, so it is the within-subject column here too.
LDA_NAME = "LDA, priors [0.5, 0.5]"
PRIORS = [0.5, 0.5]


def load_subjects(subjects):
    """Restricted features for each subject: {subject: (X, y)}."""
    data = {}
    for subject in subjects:
        epochs = prepare_epochs(subject)
        data[subject] = extract_features(epochs, channels=P3_CHANNELS, window=P3_WINDOW)
    return data


def standardise_per_subject(data):
    """Z-score each subject's features with that subject's own statistics.

    Mean and SD are taken over all of the subject's epochs, targets and
    standards together, so no labels are used. The held-out subject's
    unlabelled epochs are therefore used to set its scale, which is what a
    deployment could do too: record from a new person, standardise, classify.
    """
    return {
        subject: ((X - X.mean(axis=0)) / X.std(axis=0), y)
        for subject, (X, y) in data.items()
    }


def pool(data):
    """Stack the subjects' features; groups[i] is the subject index of row i."""
    X = np.concatenate([X for X, _ in data.values()])
    y = np.concatenate([y for _, y in data.values()])
    groups = np.concatenate(
        [np.full(len(y), k) for k, (_, y) in enumerate(data.values())]
    )
    return X, y, groups


def models():
    return {
        LDA_NAME: build_lda(priors=PRIORS),
        "Dummy (prior)": DummyClassifier(strategy="prior"),
    }


def leave_one_subject_out(X, y, groups):
    """One test fold per subject; fold k holds out the subject with index k.

    LeaveOneGroupOut yields the groups in sorted order, which is the order
    the subjects were pooled in.
    """
    cv = LeaveOneGroupOut()
    return {
        name: cross_validate(model, X, y, cv=cv, groups=groups, scoring=SCORING)
        for name, model in models().items()
    }


def pooled_kfold(X, y):
    """Stratified 5-fold over the pooled epochs, blind to subject."""
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    return {
        name: cross_validate(model, X, y, cv=cv, scoring=SCORING)
        for name, model in models().items()
    }


if __name__ == "__main__":
    mne.set_log_level("WARNING")
    subjects = sorted(p.name for p in DATA_DIR.glob("sub-*") if p.is_dir())
    data = load_subjects(subjects)
    X, y, groups = pool(data)

    # Within-subject scores, recomputed with classify.py's own folds so the
    # column matches what classify.py prints for [2].
    within = {s: evaluate(*data[s])[LDA_NAME] for s in subjects}
    loso = leave_one_subject_out(X, y, groups)
    Xz, yz, groups_z = pool(standardise_per_subject(data))
    assert (yz == y).all() and (groups_z == groups).all()
    loso_z = leave_one_subject_out(Xz, yz, groups_z)
    pooled = pooled_kfold(X, y)

    print(f"\n=== cross-subject, StandardScaler + LDA (lsqr, shrinkage=auto, "
          f"priors {PRIORS}) ===")
    print(f"  features: {', '.join(P3_CHANNELS)}, "
          f"{P3_WINDOW[0] * 1000:.0f}-{P3_WINDOW[1] * 1000:.0f} ms, "
          f"{BIN_WIDTH * 1000:.0f} ms bins ({X.shape[1]} per epoch)")
    print(f"  {len(subjects)} subjects pooled: {len(y)} epochs, "
          f"{y.sum()} target / {(y == 0).sum()} standard")

    print(f"\n--- [1] leave-one-subject-out vs within-subject "
          f"{N_SPLITS}-fold CV (classify.py) ---")
    print("  LOSO: trained on the other subjects, scored on the held-out one.")
    print("  LOSO z/subj: same, after z-scoring each subject's features with "
          "its own mean and SD (all epochs, no labels).")
    print("  within: mean +/- SD across that subject's own folds.")
    W = 17
    COLS = 3  # LOSO, LOSO z/subj, within
    print("\n  " + " " * 9 + "".join(f"{m:^{COLS * W}s}" for m in SCORING))
    print(f"  {'subject':9s}"
          + "".join(f"{'LOSO':>{W}s}{'LOSO z/subj':>{W}s}{'within':>{W}s}"
                    for _ in SCORING))
    for k, subject in enumerate(subjects):
        cells = ""
        for m in SCORING:
            w = within[subject][f"test_{m}"]
            cells += f"{loso[LDA_NAME][f'test_{m}'][k]:>{W}.3f}"
            cells += f"{loso_z[LDA_NAME][f'test_{m}'][k]:>{W}.3f}"
            cells += f"{f'{w.mean():.3f} +/- {w.std():.3f}':>{W}s}"
        print(f"  {subject:9s}{cells}")

    print(f"  {'-' * (9 + COLS * W * len(SCORING))}")
    cells = ""
    for m in SCORING:
        w = np.array([within[s][f"test_{m}"].mean() for s in subjects])
        for scores in (loso[LDA_NAME][f"test_{m}"],
                       loso_z[LDA_NAME][f"test_{m}"], w):
            cells += f"{f'{scores.mean():.3f} +/- {scores.std():.3f}':>{W}s}"
    print(f"  {'mean':9s}{cells}   (+/- SD across subjects)")
    cells = "".join(
        f"{loso['Dummy (prior)'][f'test_{m}'].mean():^{COLS * W}.3f}"
        for m in SCORING
    )
    print(f"  {'dummy':9s}{cells}   (LOSO, same folds)")

    print(f"\n--- [2] pooled stratified {N_SPLITS}-fold CV, ignoring subject "
          f"(leaky: same subjects in train and test) ---")
    print("  mean +/- SD across folds")
    print("\n  " + " " * 28 + "".join(f"{m:>{W + 2}s}" for m in SCORING))
    for name, scores in pooled.items():
        cells = ""
        for m in SCORING:
            s = scores[f"test_{m}"]
            cells += f"{f'{s.mean():.3f} +/- {s.std():.3f}':>{W + 2}s}"
        print(f"  {name:28s}{cells}")
