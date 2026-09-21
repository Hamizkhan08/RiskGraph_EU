"""Model stack: logistic regression (interpretable baseline), LightGBM (transaction/behaviour
baseline) and graph-enhanced LightGBM. Same hyper-parameters for every feature set; no tuning.
Preprocessing (scaling) is fitted on TRAINING rows only. Calibration is fitted on VALIDATION only.
A GNN is intentionally not implemented (docs/METHODOLOGY.md, 'GNN decision')."""

from __future__ import annotations

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from .config import LGBM_PARAMS, NEG_TRAIN_FRACTION


def _slog(x: np.ndarray) -> np.ndarray:
    return np.sign(x) * np.log1p(np.abs(x))


class ScoreModel:
    """kind in {'logreg','lgbm'}; `cols` = feature names (defines the feature set)."""

    def __init__(self, kind: str, cols: list[str], seed: int = 0):
        self.kind, self.cols, self.seed = kind, list(cols), seed
        if kind == "logreg":
            self.est = Pipeline(
                [
                    ("slog", FunctionTransformer(_slog)),
                    ("scale", StandardScaler()),
                    ("lr", LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000)),
                ]
            )
        elif kind == "lgbm":
            self.est = LGBMClassifier(random_state=seed, **LGBM_PARAMS)
        else:
            raise ValueError(kind)

    def fit(self, X: pd.DataFrame, y: np.ndarray, neg_fraction: float = NEG_TRAIN_FRACTION) -> "ScoreModel":
        """Keep all positives and a random `neg_fraction` of negatives (training only)."""
        rng = np.random.default_rng(self.seed)
        keep = (y == 1) | (rng.random(len(y)) < neg_fraction)
        self.n_train_pos, self.n_train_rows = int(y[keep].sum()), int(keep.sum())
        self.est.fit(X[self.cols].to_numpy()[keep], y[keep])
        return self

    def score(self, X: pd.DataFrame) -> np.ndarray:
        return self.est.predict_proba(X[self.cols].to_numpy())[:, 1]

    @property
    def booster(self):
        return self.est.booster_ if self.kind == "lgbm" else None


class PlattCalibrator:
    """Sigmoid calibration on logit(raw score). Fitted on validation only (monotone -> ranking unchanged)."""

    def fit(self, score: np.ndarray, y: np.ndarray) -> "PlattCalibrator":
        z = self._logit(score).reshape(-1, 1)
        self.lr = LogisticRegression(C=1e6, max_iter=1000).fit(z, y)
        return self

    @staticmethod
    def _logit(s: np.ndarray) -> np.ndarray:
        s = np.clip(s, 1e-6, 1 - 1e-6)
        return np.log(s / (1 - s))

    def transform(self, score: np.ndarray) -> np.ndarray:
        return self.lr.predict_proba(self._logit(score).reshape(-1, 1))[:, 1]
