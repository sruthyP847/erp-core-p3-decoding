"""Classify target vs standard epochs from the binned ERP features.

Stratified 5-fold cross-validation of a StandardScaler + shrinkage-LDA
pipeline, scored by ROC-AUC and balanced accuracy, with a DummyClassifier
run through the same folds as a baseline. Each subject in data/ is
cross-validated separately (within-subject) on the restricted feature set:
centro-parietal channels, ERP CORE P3 window.
"""

import mne
import numpy as np

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import BIN_WIDTH, P3_CHANNELS, P3_WINDOW, extract_features
from prepare_epochs import DATA_DIR, prepare_epochs

N_SPLITS = 5
SEED = 0
SCORING = {"ROC-AUC": "roc_auc", "balanced accuracy": "balanced_accuracy"}


def build_lda(priors=None):
    return make_pipeline(
        StandardScaler(),
        LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto", priors=priors),
    )


def build_models():
    return {
        # priors=None: sklearn uses the training class frequencies (~.8/.2)
        "LDA, class-frequency priors": build_lda(),
        # Equal priors move the decision threshold to midway between the classes.
        "LDA, priors [0.5, 0.5]": build_lda(priors=[0.5, 0.5]),
        # Always predicts the class prior: chance level for both metrics.
        "Dummy (prior)": DummyClassifier(strategy="prior"),
    }


def evaluate(X, y):
    """Cross-validate every model on the same folds; return the fold scores."""
    # Shuffled because the epochs are in recording order, block by block.
    # The scaler sits inside the pipeline, so it is fitted on training folds only.
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    return {
        name: cross_validate(model, X, y, cv=cv, scoring=SCORING)
        for name, model in build_models().items()
    }


if __name__ == "__main__":
    mne.set_log_level("WARNING")  # ten subjects of filter logs drown the table
    subjects = sorted(p.name for p in DATA_DIR.glob("sub-*") if p.is_dir())
    *ldas, dummy = build_models()

    rows = []
    for subject in subjects:
        epochs = prepare_epochs(subject)
        X, y = extract_features(epochs, channels=P3_CHANNELS, window=P3_WINDOW)
        scores = evaluate(X, y)
        rows.append({
            "subject": subject,
            **{(lda, m): scores[lda][f"test_{m}"] for lda in ldas for m in SCORING},
            **{(dummy, m): scores[dummy][f"test_{m}"] for m in SCORING},
        })

    print(f"\n=== within-subject stratified {N_SPLITS}-fold CV, "
          f"StandardScaler + LDA (lsqr, shrinkage=auto) ===")
    print(f"  features: {', '.join(P3_CHANNELS)}, "
          f"{P3_WINDOW[0] * 1000:.0f}-{P3_WINDOW[1] * 1000:.0f} ms, "
          f"{BIN_WIDTH * 1000:.0f} ms bins ({X.shape[1]} per epoch)")
    print(f"  {y.sum()} target / {(y == 0).sum()} standard epochs per subject; "
          f"per subject: mean +/- SD across folds")
    for k, lda in enumerate(ldas):
        print(f"  [{k + 1}] {lda}")

    columns = [(lda, m) for m in SCORING for lda in ldas]
    W = 17
    print("\n  " + " " * 9 + "".join(f"{m:^{W * len(ldas)}s}" for m in SCORING))
    print(f"  {'subject':9s}"
          + "".join(f"{f'[{ldas.index(lda) + 1}]':>{W}s}" for lda, _ in columns))
    for row in rows:
        cells = "".join(
            f"{f'{row[c].mean():.3f} +/- {row[c].std():.3f}':>{W}s}" for c in columns
        )
        print(f"  {row['subject']:9s}{cells}")

    # Mean and SD of the per-subject means, not of the pooled folds.
    print(f"  {'-' * (9 + W * len(columns))}")
    cells = ""
    for c in columns:
        per_subject = np.array([row[c].mean() for row in rows])
        cells += f"{f'{per_subject.mean():.3f} +/- {per_subject.std():.3f}':>{W}s}"
    print(f"  {'mean':9s}{cells}   (+/- SD across subjects)")

    cells = "".join(
        f"{np.mean([row[(dummy, m)].mean() for row in rows]):^{W * len(ldas)}.3f}"
        for m in SCORING
    )
    print(f"  {'dummy':9s}{cells}   ({dummy}, same folds)")
