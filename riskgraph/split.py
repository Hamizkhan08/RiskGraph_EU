"""Temporal split with scheme-start assignment.

Layout (day indices, [start, end)):  burn-in | train | validation | purge | test
  * burn-in: feature history only (30-day windows), never scored;
  * scheme-start rule: a positive case in block B whose scheme(s) ALL started before B's start is
    a *carry-over* case. The 'strict' view (primary) drops carry-over positives from evaluation and
    calibration; the 'all' view keeps them (sensitivity). Negatives are never dropped.
    Rationale: Tide schemes are long-lived (median ~13 d, p95 ~216 d), so a fixed purge cannot separate them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .config import BURN_IN_DAYS, PURGE_DAYS, TRAIN_END_FRACTION, VAL_END_FRACTION
from .features.build import CaseTable


@dataclass(frozen=True)
class Split:
    n_days: int
    burn_in: int
    train: tuple[int, int]
    val: tuple[int, int]
    purge: tuple[int, int]
    test: tuple[int, int]

    def block_range(self, name: str) -> tuple[int, int]:
        return getattr(self, name)

    def to_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(self).items()}


def make_split(
    n_days: int,
    burn_in: int = BURN_IN_DAYS,
    purge: int = PURGE_DAYS,
    train_end_frac: float = TRAIN_END_FRACTION,
    val_end_frac: float = VAL_END_FRACTION,
) -> Split:
    tr_end = int(round(train_end_frac * n_days))
    va_end = int(round(val_end_frac * n_days))
    if not (burn_in < tr_end < va_end and va_end + purge < n_days):
        raise ValueError(f"degenerate split for n_days={n_days}")
    return Split(
        n_days=n_days,
        burn_in=burn_in,
        train=(burn_in, tr_end),
        val=(tr_end, va_end),
        purge=(va_end, va_end + purge),
        test=(va_end + purge, n_days),
    )


def block_mask(ct: CaseTable, sp: Split, block: str) -> np.ndarray:
    a, b = sp.block_range(block)
    return (ct.day >= a) & (ct.day < b)


def carry_over(ct: CaseTable, block_start: int) -> np.ndarray:
    """Positive cases whose involved schemes all started before `block_start`."""
    return (ct.y == 1) & (ct.scheme_max_start >= 0) & (ct.scheme_max_start < block_start)


def eval_mask(ct: CaseTable, sp: Split, block: str, view: str = "strict") -> np.ndarray:
    """Cases usable for evaluation/calibration in `block`."""
    m = block_mask(ct, sp, block)
    if view == "strict":
        m &= ~carry_over(ct, sp.block_range(block)[0])
    elif view != "all":
        raise ValueError(view)
    return m


def window_mask(ct: CaseTable, start_day: int, end_day: int | None = None, view: str = "strict") -> np.ndarray:
    """Post-training window [start_day, end_day) with scheme-start rule relative to `start_day`."""
    m = (ct.day >= start_day) & (ct.day < (ct.day.max() + 1 if end_day is None else end_day))
    if view == "strict":
        m &= ~carry_over(ct, start_day)
    return m
