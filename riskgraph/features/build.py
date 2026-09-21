"""Time-respecting account-day feature engine.

Unit of analysis: case = (account, day d). Decision timestamp = END of day d.
Every feature at day d is a function of transactions with day <= d ONLY (enforced by construction:
all windows are trailing sums over a dense [account x day] tensor, and verified by the
future-perturbation test in tests/test_leakage.py).

Groups (used for ablations):
  T  own activity            B  behavioural history (deviation, novelty, reciprocity)
  G  generic graph context   M  typology/motif-aware (defined a priori from Tide's documented typologies)
Labels (y, scheme, family) are NEVER read by this module except to build the *target* table,
which is returned separately from the feature matrix.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import sparse

from ..config import BURN_IN_DAYS, FEATURE_VERSION
from ..data.schema import TxData

HUB_DEGREE = 20  # neighbour counts as a "hub" at >= 20 distinct counterparties in the window (assumption)
NEAR_LOW, NEAR_HIGH = 9000.0, 10000.0  # just-below the 10,000 reporting threshold (assumption, EU cash-limit style)

# name -> (group, definition). Single source of truth; builder asserts it produces exactly these.
FEATURES: dict[str, tuple[str, str]] = {
    # ---- T: own activity ----
    "t_n_out_1d": ("T", "count of outgoing transactions on day d"),
    "t_n_in_1d": ("T", "count of incoming transactions on day d"),
    "t_amt_out_1d": ("T", "sum of outgoing amounts on day d"),
    "t_amt_in_1d": ("T", "sum of incoming amounts on day d"),
    "t_max_out_1d": ("T", "largest outgoing amount on day d"),
    "t_max_in_1d": ("T", "largest incoming amount on day d"),
    "t_mean_out_1d": ("T", "mean outgoing amount on day d (0 if none)"),
    "t_std_out_1d": ("T", "std of outgoing amounts on day d (dispersion)"),
    "t_n_out_7d": ("T", "outgoing count, trailing 7 days incl. d"),
    "t_n_in_7d": ("T", "incoming count, trailing 7 days incl. d"),
    "t_amt_out_7d": ("T", "outgoing amount sum, trailing 7 days"),
    "t_amt_in_7d": ("T", "incoming amount sum, trailing 7 days"),
    "t_n_out_30d": ("T", "outgoing count, trailing 30 days"),
    "t_n_in_30d": ("T", "incoming count, trailing 30 days"),
    "t_amt_out_30d": ("T", "outgoing amount sum, trailing 30 days"),
    "t_amt_in_30d": ("T", "incoming amount sum, trailing 30 days"),
    "t_n_transfer_out_1d": ("T", "outgoing transactions of type transfer on day d"),
    "t_n_transfer_in_1d": ("T", "incoming transactions of type transfer on day d"),
    "t_n_deposit_1d": ("T", "transactions of type deposit (either direction) on day d"),
    "t_n_withdrawal_1d": ("T", "transactions of type withdrawal (either direction) on day d"),
    "t_n_payment_1d": ("T", "transactions of type payment (either direction) on day d"),
    "t_transfer_share_7d": ("T", "share of transfers among all transactions, trailing 7 days"),
    "t_night_share_1d": ("T", "share of day-d transactions between 00:00 and 05:59"),
    "t_n_ccy_7d": ("T", "distinct transaction currencies, trailing 7 days"),
    "t_out_in_ratio_1d": ("T", "log((1+out amount)/(1+in amount)) on day d"),
    # ---- B: behavioural history ----
    "b_new_cp_out_1d": ("B", "outgoing counterparties first seen on day d"),
    "b_new_cp_in_1d": ("B", "incoming counterparties first seen on day d"),
    "b_new_cp_share_1d": ("B", "new counterparties / transactions on day d"),
    "b_distinct_cp_30d": ("B", "distinct counterparties (either direction), trailing 30 days"),
    "b_repeat_share_30d": ("B", "1 - distinct counterparties / transactions, trailing 30 days"),
    "b_recip_cp_cum": ("B", "counterparties with transfers in both directions observed up to day d"),
    "b_z_out_amt": ("B", "z-score of day-d outgoing amount vs the previous 30 days"),
    "b_z_out_cnt": ("B", "z-score of day-d outgoing count vs the previous 30 days"),
    "b_velocity_ratio": ("B", "day-d transaction count / (mean daily count of previous 30 days + 0.1)"),
    "b_imbalance_7d": ("B", "(in - out)/(in + out) amount, trailing 7 days"),
    "b_top_cp_share_1d": ("B", "largest counterparty's share of day-d outgoing amount"),
    "b_active_days_30d": ("B", "days with any activity in trailing 30 days"),
    # ---- G: generic graph context (trailing-7-day window graph) ----
    "g_deg_out_7d": ("G", "distinct outgoing counterparties, trailing 7 days"),
    "g_deg_in_7d": ("G", "distinct incoming counterparties, trailing 7 days"),
    "g_deg_und_7d": ("G", "distinct counterparties (undirected), trailing 7 days"),
    "g_reach2_7d": ("G", "accounts within 2 hops in the 7-day undirected window graph"),
    "g_nbr_mean_deg_7d": ("G", "mean degree of neighbours in the 7-day window graph"),
    "g_nbr_hub_share_7d": ("G", f"share of neighbours with degree >= {HUB_DEGREE}"),
    "g_nbr_act_1d": ("G", "mean day-d transaction count of neighbours"),
    "g_triangles_7d": ("G", "undirected triangles through the account, 7-day window graph"),
    # ---- M: typology / motif aware ----
    "m_cycle2_7d": ("M", "directed 2-cycles (reciprocal pairs) through the account, 7-day graph"),
    "m_cycle3_7d": ("M", "directed 3-cycles through the account, 7-day graph"),
    "m_cycle4_7d": ("M", "directed 4-cycles (closed walks of length 4) through the account, 7-day graph"),
    "m_fanin_burst_3d": ("M", "max over last 3 days of distinct incoming counterparties in one day"),
    "m_fanout_burst_3d": ("M", "max over last 3 days of distinct outgoing counterparties in one day"),
    "m_passthrough_3d": ("M", "min(in,out)/max(in,out) amount over the last 3 days (rapid pass-through)"),
    "m_near10k_7d": ("M", f"transactions with amount in [{NEAR_LOW:.0f},{NEAR_HIGH:.0f}), trailing 7 days"),
    "m_near10k_1d": ("M", f"transactions with amount in [{NEAR_LOW:.0f},{NEAR_HIGH:.0f}) on day d"),
}
GROUPS = ("T", "B", "G", "M")


def feature_names(groups: tuple[str, ...] = GROUPS) -> list[str]:
    return [k for k, (g, _) in FEATURES.items() if g in groups]


@dataclass
class CaseTable:
    """Cases (account-days) + features + ground-truth targets (targets are NOT features)."""

    X: pd.DataFrame  # float32 features, index = case_idx
    acct: np.ndarray  # account index per case
    day: np.ndarray  # day index per case
    y: np.ndarray  # 1 if any positive transaction involves the account that day
    scheme_min_start: np.ndarray  # min start_day of involved positive schemes (-1 if none)
    scheme_max_start: np.ndarray  # max start_day of involved positive schemes (-1 if none)
    family_mask: np.ndarray  # bitmask of families of involved positive schemes
    scheme_first: np.ndarray  # scheme_idx of the (lowest-index) involved scheme (-1 if none)
    feature_version: str = FEATURE_VERSION


# ---------------------------------------------------------------------------------------------
def _win(ch: np.ndarray, w: int) -> np.ndarray:
    """Trailing-window sum over days [d-w+1, d] for a [A, D] channel."""
    c = np.concatenate([np.zeros((ch.shape[0], 1)), np.cumsum(ch, axis=1, dtype="float64")], axis=1)
    d = np.arange(ch.shape[1])
    return c[:, d + 1] - c[:, np.maximum(d + 1 - w, 0)]


def _win_prev(ch: np.ndarray, w: int) -> np.ndarray:
    """Sum over the PREVIOUS w days [d-w, d-1] (excludes d)."""
    c = np.concatenate([np.zeros((ch.shape[0], 1)), np.cumsum(ch, axis=1, dtype="float64")], axis=1)
    d = np.arange(ch.shape[1])
    return c[:, d] - c[:, np.maximum(d - w, 0)]


def _flat(a: np.ndarray, d: np.ndarray, n_d: int) -> np.ndarray:
    return a.astype("int64") * n_d + d.astype("int64")


def _bc(idx: np.ndarray, n: int, w: np.ndarray | None = None) -> np.ndarray:
    return np.bincount(idx, weights=w, minlength=n)


def _intervals(a: np.ndarray, key: np.ndarray, day: np.ndarray, w: int, n_d: int):
    """Per (a,key) pair: disjoint coverage intervals [start, end) of a trailing-w-day window.

    A pair is 'active' on day d iff it interacted on some day t with t <= d <= t+w-1.
    """
    order = np.lexsort((day, key, a))
    a, key, day = a[order], key[order], day[order]
    keep = np.r_[True, (a[1:] != a[:-1]) | (key[1:] != key[:-1]) | (day[1:] != day[:-1])]
    a, key, day = a[keep], key[keep], day[keep]
    same_next = np.r_[(a[1:] == a[:-1]) & (key[1:] == key[:-1]), False]
    nxt = np.r_[day[1:], 0]
    length = np.where(same_next, np.minimum(w, nxt - day), w)
    end = np.minimum(day + length, n_d)
    return a, key, day, end


def _window_distinct(a: np.ndarray, key: np.ndarray, day: np.ndarray, n_a: int, n_d: int, w: int) -> np.ndarray:
    ia, _, start, end = _intervals(a, key, day, w, n_d)
    m = n_d + 1
    diff = _bc(ia.astype("int64") * m + start, n_a * m) - _bc(ia.astype("int64") * m + end, n_a * m)
    return np.cumsum(diff.reshape(n_a, m), axis=1)[:, :n_d]


def _group_max(idx: np.ndarray, vals: np.ndarray, n: int) -> np.ndarray:
    out = np.zeros(n)
    if len(idx):
        s = pd.Series(vals).groupby(idx).max()
        out[s.index.to_numpy()] = s.to_numpy()
    return out


def build_cases(td: TxData, burn_in: int = BURN_IN_DAYS, max_day: int | None = None) -> CaseTable:
    """Build all cases with day in [burn_in, n_days) and their features.

    `max_day` (test hook) drops every transaction with day > max_day BEFORE building — used by the
    leakage test to prove features at day <= max_day do not depend on later data.
    """
    tx = td.tx[td.tx["in_period"]]
    n_d = td.n_days if max_day is None else min(td.n_days, max_day + 1)
    tx = tx[tx["day"] < n_d]
    n_a = len(td.accounts)
    day = tx["day"].to_numpy()
    amt = tx["amount"].to_numpy()
    s_i, d_i = tx["src_idx"].to_numpy(), tx["dst_idx"].to_numpy()
    hour = tx["ts"].dt.hour.to_numpy()
    typ = tx["tx_type"].astype(str).to_numpy()
    ccy = (
        tx["currency"].cat.codes.to_numpy().astype("int64")
        if hasattr(tx["currency"], "cat")
        else pd.factorize(tx["currency"])[0]
    )
    node, _ = pd.factorize(pd.concat([tx["src"], tx["dst"]]))
    s_node, d_node = node[: len(tx)], node[len(tx) :]
    N = n_a * n_d

    so, di = s_i >= 0, d_i >= 0  # out-endpoint / in-endpoint is an account
    fo, fi = _flat(s_i[so], day[so], n_d), _flat(d_i[di], day[di], n_d)
    night, near = hour < 6, (amt >= NEAR_LOW) & (amt < NEAR_HIGH)

    def ch(f: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
        return _bc(f, N, w).reshape(n_a, n_d)

    n_out, n_in = ch(fo), ch(fi)
    a_out, a_in = ch(fo, amt[so]), ch(fi, amt[di])
    sq_out = ch(fo, amt[so] ** 2)
    max_out = _group_max(fo, amt[so], N).reshape(n_a, n_d)
    max_in = _group_max(fi, amt[di], N).reshape(n_a, n_d)
    n_all = n_out + n_in
    types = {t: (typ == t) for t in ("transfer", "deposit", "withdrawal", "payment")}
    tr_out, tr_in = ch(fo, types["transfer"][so].astype(float)), ch(fi, types["transfer"][di].astype(float))
    dep = ch(fo, types["deposit"][so].astype(float)) + ch(fi, types["deposit"][di].astype(float))
    wdr = ch(fo, types["withdrawal"][so].astype(float)) + ch(fi, types["withdrawal"][di].astype(float))
    pay = ch(fo, types["payment"][so].astype(float)) + ch(fi, types["payment"][di].astype(float))
    ngt = ch(fo, night[so].astype(float)) + ch(fi, night[di].astype(float))
    nr1 = ch(fo, near[so].astype(float)) + ch(fi, near[di].astype(float))

    F: dict[str, np.ndarray] = {}
    F["t_n_out_1d"], F["t_n_in_1d"] = n_out, n_in
    F["t_amt_out_1d"], F["t_amt_in_1d"] = a_out, a_in
    F["t_max_out_1d"], F["t_max_in_1d"] = max_out, max_in
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_out = np.where(n_out > 0, a_out / np.maximum(n_out, 1), 0.0)
        var_out = np.where(n_out > 0, sq_out / np.maximum(n_out, 1) - mean_out**2, 0.0)
    F["t_mean_out_1d"], F["t_std_out_1d"] = mean_out, np.sqrt(np.maximum(var_out, 0.0))
    for w, sfx in ((7, "7d"), (30, "30d")):
        F[f"t_n_out_{sfx}"], F[f"t_n_in_{sfx}"] = _win(n_out, w), _win(n_in, w)
        F[f"t_amt_out_{sfx}"], F[f"t_amt_in_{sfx}"] = _win(a_out, w), _win(a_in, w)
    F["t_n_transfer_out_1d"], F["t_n_transfer_in_1d"] = tr_out, tr_in
    F["t_n_deposit_1d"], F["t_n_withdrawal_1d"], F["t_n_payment_1d"] = dep, wdr, pay
    F["t_transfer_share_7d"] = _win(tr_out + tr_in, 7) / np.maximum(_win(n_all, 7), 1)
    F["t_night_share_1d"] = ngt / np.maximum(n_all, 1)
    a_end = np.concatenate([s_i[so], d_i[di]])
    F["t_n_ccy_7d"] = _window_distinct(
        a_end, np.concatenate([ccy[so], ccy[di]]), np.concatenate([day[so], day[di]]), n_a, n_d, 7
    )
    F["t_out_in_ratio_1d"] = np.log1p(a_out) - np.log1p(a_in)

    # ---- B: behavioural history ---------------------------------------------------------------
    first_out = pd.DataFrame({"a": s_i[so], "k": d_node[so], "d": day[so]}).groupby(["a", "k"])["d"].min()
    first_in = pd.DataFrame({"a": d_i[di], "k": s_node[di], "d": day[di]}).groupby(["a", "k"])["d"].min()
    new_out = ch(_flat(first_out.index.get_level_values(0).to_numpy(), first_out.to_numpy(), n_d))
    new_in = ch(_flat(first_in.index.get_level_values(0).to_numpy(), first_in.to_numpy(), n_d))
    F["b_new_cp_out_1d"], F["b_new_cp_in_1d"] = new_out, new_in
    F["b_new_cp_share_1d"] = (new_out + new_in) / np.maximum(n_all, 1)
    ua = np.concatenate([s_i[so], d_i[di]])
    uk = np.concatenate([d_node[so], s_node[di]])
    ud = np.concatenate([day[so], day[di]])
    cp30 = _window_distinct(ua, uk, ud, n_a, n_d, 30)
    F["b_distinct_cp_30d"] = cp30
    F["b_repeat_share_30d"] = np.where(_win(n_all, 30) > 0, 1 - cp30 / np.maximum(_win(n_all, 30), 1), 0.0)
    # reciprocity: unordered account pairs seen in both directions
    pr = (
        pd.DataFrame({"u": s_i[so & di], "v": d_i[so & di], "d": day[so & di]})
        .groupby(["u", "v"])["d"]
        .min()
        .reset_index()
    )
    rev = pr.rename(columns={"u": "v", "v": "u", "d": "d2"})
    both = pr.merge(rev, on=["u", "v"])
    both = both[both["u"] < both["v"]]
    act_day = np.maximum(both["d"].to_numpy(), both["d2"].to_numpy())
    recip = np.zeros(n_a * n_d)
    for col in ("u", "v"):
        recip += _bc(_flat(both[col].to_numpy(), act_day, n_d), n_a * n_d)
    F["b_recip_cp_cum"] = np.cumsum(recip.reshape(n_a, n_d), axis=1)
    p_a, p_c = _win_prev(a_out, 30), _win_prev(n_out, 30)
    p_a2, p_c2 = _win_prev(sq_out, 30), _win_prev(n_out**2, 30)
    m_a, m_c = p_a / 30, p_c / 30
    sd_a = np.sqrt(np.maximum(p_a2 / 30 - m_a**2, 0) + (0.1 * m_a) ** 2 + 1.0)
    sd_c = np.sqrt(np.maximum(p_c2 / 30 - m_c**2, 0) + 0.25)
    F["b_z_out_amt"], F["b_z_out_cnt"] = (a_out - m_a) / sd_a, (n_out - m_c) / sd_c
    F["b_velocity_ratio"] = n_all / (_win_prev(n_all, 30) / 30 + 0.1)
    i7, o7 = _win(a_in, 7), _win(a_out, 7)
    F["b_imbalance_7d"] = np.where(i7 + o7 > 0, (i7 - o7) / np.maximum(i7 + o7, 1e-9), 0.0)
    pc = pd.DataFrame({"f": fo, "k": d_node[so], "w": amt[so]}).groupby(["f", "k"])["w"].sum().reset_index()
    tot = pc.groupby("f")["w"].sum()
    mx = pc.groupby("f")["w"].max()
    top = np.zeros(N)
    top[mx.index.to_numpy()] = (mx / tot.clip(lower=1e-9)).to_numpy()
    F["b_top_cp_share_1d"] = top.reshape(n_a, n_d)
    F["b_active_days_30d"] = _win((n_all > 0).astype(float), 30)

    # ---- G / M: window graphs ------------------------------------------------------------------
    per_day_in = np.zeros(N)
    per_day_out = np.zeros(N)
    u_in = pd.DataFrame({"f": fi, "k": s_node[di]}).drop_duplicates().groupby("f").size()
    u_out = pd.DataFrame({"f": fo, "k": d_node[so]}).drop_duplicates().groupby("f").size()
    per_day_in[u_in.index.to_numpy()] = u_in.to_numpy()
    per_day_out[u_out.index.to_numpy()] = u_out.to_numpy()
    pdi, pdo = per_day_in.reshape(n_a, n_d), per_day_out.reshape(n_a, n_d)
    burst_in, burst_out = pdi.copy(), pdo.copy()
    for s in (1, 2):
        burst_in[:, s:] = np.maximum(burst_in[:, s:], pdi[:, :-s])
        burst_out[:, s:] = np.maximum(burst_out[:, s:], pdo[:, :-s])
    F["m_fanin_burst_3d"], F["m_fanout_burst_3d"] = burst_in, burst_out
    i3, o3 = _win(a_in, 3), _win(a_out, 3)
    F["m_passthrough_3d"] = np.where(
        (i3 > 0) & (o3 > 0), np.minimum(i3, o3) / np.maximum(np.maximum(i3, o3), 1e-9), 0.0
    )
    F["m_near10k_7d"], F["m_near10k_1d"] = _win(nr1, 7), nr1

    ac = so & di & (s_i != d_i)
    ia, ib, st, en = _intervals(s_i[ac], d_i[ac], day[ac], 7, n_d)
    order = np.argsort(st, kind="stable")
    ia, ib, st, en = ia[order], ib[order], st[order], en[order]
    keys = [
        "g_deg_out_7d",
        "g_deg_in_7d",
        "g_deg_und_7d",
        "g_reach2_7d",
        "g_nbr_mean_deg_7d",
        "g_nbr_hub_share_7d",
        "g_nbr_act_1d",
        "g_triangles_7d",
        "m_cycle2_7d",
        "m_cycle3_7d",
        "m_cycle4_7d",
    ]
    G = {k: np.zeros((n_a, n_d), dtype="float32") for k in keys}
    act1 = n_all
    for d in range(max(burn_in, 0), n_d):
        m = (st <= d) & (en > d)
        if not m.any():
            continue
        A = sparse.csr_matrix((np.ones(m.sum()), (ia[m], ib[m])), shape=(n_a, n_a))
        Au = ((A + A.T) > 0).astype("float64").tocsr()
        deg_out, deg_in, deg = np.asarray(A.sum(1)).ravel(), np.asarray(A.sum(0)).ravel(), np.asarray(Au.sum(1)).ravel()
        A2u = Au @ Au
        R = (Au + A2u).tocsr()
        R.setdiag(0)
        R.eliminate_zeros()
        dv = np.maximum(deg, 1)
        G["g_deg_out_7d"][:, d], G["g_deg_in_7d"][:, d], G["g_deg_und_7d"][:, d] = deg_out, deg_in, deg
        G["g_reach2_7d"][:, d] = np.diff(R.indptr)
        G["g_nbr_mean_deg_7d"][:, d] = (Au @ deg) / dv
        G["g_nbr_hub_share_7d"][:, d] = (Au @ (deg >= HUB_DEGREE).astype(float)) / dv
        G["g_nbr_act_1d"][:, d] = (Au @ act1[:, d]) / dv
        G["g_triangles_7d"][:, d] = np.asarray(A2u.multiply(Au).sum(1)).ravel() / 2
        A2 = A @ A
        G["m_cycle2_7d"][:, d] = np.asarray(A.multiply(A.T).sum(1)).ravel()
        G["m_cycle3_7d"][:, d] = np.asarray(A2.multiply(A.T).sum(1)).ravel()
        G["m_cycle4_7d"][:, d] = np.asarray(A2.multiply(A2.T).sum(1)).ravel()
    F.update(G)
    # NOTE: g_deg_* and all graph features use account-to-account edges only (documented in DATA_CARD).

    if set(F) != set(FEATURES):
        raise RuntimeError(f"feature registry mismatch: {set(F) ^ set(FEATURES)}")

    # ---- cases: active account-days -----------------------------------------------------------
    act = n_all > 0
    act[:, :burn_in] = False
    ai, di_ = np.nonzero(act)
    X = pd.DataFrame({k: F[k][ai, di_].astype("float32") for k in FEATURES})
    y, smin, smax, fmask, sfirst = _targets(td, tx, ai, di_, n_d)
    return CaseTable(
        X=X,
        acct=ai.astype("int32"),
        day=di_.astype("int32"),
        y=y,
        scheme_min_start=smin,
        scheme_max_start=smax,
        family_mask=fmask,
        scheme_first=sfirst,
    )


def _targets(td: TxData, tx: pd.DataFrame, ai: np.ndarray, di: np.ndarray, n_d: int):
    """Ground-truth per case. Kept out of the feature builder's inputs by construction."""
    n = len(ai)
    y = np.zeros(n, dtype="int8")
    smin = np.full(n, -1, dtype="int32")
    smax = np.full(n, -1, dtype="int32")
    fm = np.zeros(n, dtype="int64")
    sf = np.full(n, -1, dtype="int32")
    pos = tx[tx["y"] == 1]
    if not len(pos):
        return y, smin, smax, fm, sf
    start_of = td.schemes.set_index("scheme_idx")["start_day"]
    rows = []
    for col in ("src_idx", "dst_idx"):
        sub = pos[pos[col] >= 0]
        rows.append(
            pd.DataFrame(
                {
                    "a": sub[col].to_numpy(),
                    "d": sub["day"].to_numpy(),
                    "s": sub["scheme_idx"].to_numpy(),
                    "f": sub["family_idx"].to_numpy(),
                }
            )
        )
    e = pd.concat(rows, ignore_index=True)
    e["start"] = e["s"].map(start_of).fillna(-1).astype("int32")
    e["bit"] = np.where(e["f"] >= 0, np.left_shift(1, e["f"].clip(lower=0).to_numpy().astype("int64")), 0)
    g = e.groupby(["a", "d"]).agg(smin=("start", "min"), smax=("start", "max"), fm=("bit", "max"), sf=("s", "min"))
    # OR-reduce bitmasks properly
    g["fm"] = e.groupby(["a", "d"])["bit"].apply(lambda s: int(np.bitwise_or.reduce(s.to_numpy()))).to_numpy()
    key = pd.MultiIndex.from_arrays([ai, di])
    hit = g.reindex(key)
    m = hit["smin"].notna().to_numpy()
    y[m] = 1
    smin[m], smax[m] = hit["smin"].to_numpy()[m].astype("int32"), hit["smax"].to_numpy()[m].astype("int32")
    fm[m], sf[m] = hit["fm"].to_numpy()[m].astype("int64"), hit["sf"].to_numpy()[m].astype("int32")
    return y, smin, smax, fm, sf


def save_cases(ct: CaseTable, path) -> None:
    """Cache a CaseTable without pickle (numpy .npz, allow_pickle never used)."""
    np.savez(
        path,
        X=ct.X.to_numpy(),
        cols=np.array(list(ct.X.columns)),
        acct=ct.acct,
        day=ct.day,
        y=ct.y,
        smin=ct.scheme_min_start,
        smax=ct.scheme_max_start,
        fm=ct.family_mask,
        sf=ct.scheme_first,
        fv=np.array(ct.feature_version),
    )


def load_cases(path) -> CaseTable:
    z = np.load(path, allow_pickle=False)
    return CaseTable(
        X=pd.DataFrame(z["X"], columns=[str(c) for c in z["cols"]]),
        acct=z["acct"],
        day=z["day"],
        y=z["y"],
        scheme_min_start=z["smin"],
        scheme_max_start=z["smax"],
        family_mask=z["fm"],
        scheme_first=z["sf"],
        feature_version=str(z["fv"]),
    )
