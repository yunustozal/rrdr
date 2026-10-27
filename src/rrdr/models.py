"""Concentration, persistence validation and correlates of persistence (Table 2)."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def analysis_set(cfg, seg, terrain=None):
    c = cfg["centerlines"]
    s = seg[seg.cls.isin(c["classes_analysis"]) & (seg.len100m >= c["min_length_m"] / 100)].copy()
    s["chronic"] = (s.p1_yrs >= cfg["chronic"]["min_years"]).astype(int)
    s["loglen"] = np.log(s.len100m)
    s["rate_p2"] = s.p2_n / s.len100m
    if "open_rate" in s:
        s["log_open"] = np.log1p(s.open_rate)
    if terrain is not None:
        s = s.merge(terrain, on="seg", how="left")
    return s


def concentration(cfg, seg):
    c = cfg["centerlines"]
    r = seg[seg.cls.isin(c["classes_all_roads"]) & (seg.len100m >= c["min_length_m"] / 100)].copy()
    r["rate"] = r.p2_n / r.len100m
    r = r.sort_values("rate", ascending=False)
    share = (r.p2_n.cumsum() / r.p2_n.sum()).values
    out = pd.DataFrame({"segment_share": np.arange(1, len(r) + 1) / len(r), "request_share": share})
    out.to_csv(cfg.out("concentration_curve.csv"), index=False)
    top = {p: float(share[int(len(r) * p) - 1]) for p in (0.10, 0.20)}
    return len(r), top


def validation(cfg, s):
    rows = []
    for th in [cfg["chronic"]["min_years"]] + cfg["chronic"].get("robustness_thresholds", []):
        ch = s.p1_yrs >= th
        for k in sorted(s.cls.unique()):
            m = s.cls == k
            a, b = s.rate_p2[m & ch].mean(), s.rate_p2[m & ~ch].mean()
            rows.append(dict(threshold=th, cls=k, n_chronic=int((m & ch).sum()), chronic=a, other=b, ratio=a / b))
    out = pd.DataFrame(rows)
    out.to_csv(cfg.out("table_validation.csv"), index=False)
    return out


def correlates(cfg, s):
    terrain_vars = [v for v in ["max_depth_in", "log_acc", "rel_elev_ft", "slope_pct"] if v in s]
    other = [v for v in ["log_open", "bus", "poor_drain"] if v in s]
    d = s.dropna(subset=terrain_vars + other).copy()
    for v in terrain_vars:
        d[v] = (d[v] - d[v].mean()) / d[v].std()
    rhs = " + ".join(other + terrain_vars + ["C(cls)"])
    logit = smf.logit(f"chronic ~ {rhs} + loglen", data=d).fit(disp=0)
    nb = smf.negativebinomial(f"p2_n ~ {rhs} + p1_yrs", data=d, offset=np.log(d.len100m)).fit(disp=0, maxiter=300)
    def tidy(m, name):
        ci = m.conf_int()
        return pd.DataFrame({f"{name}": np.exp(m.params), f"{name}_lo": np.exp(ci[0]),
                             f"{name}_hi": np.exp(ci[1]), f"{name}_p": m.pvalues})
    tab = tidy(logit, "OR").join(tidy(nb, "IRR"), how="outer")
    tab.to_csv(cfg.out("table2_correlates.csv"))
    extra = {"n": int(logit.nobs), "pseudo_r2": float(logit.prsquared)}
    if "open_rate" in d:
        med, p90 = d.open_rate.median(), d.open_rate.quantile(0.9)
        extra.update(open_median=float(med), open_p90=float(p90),
                     or_median_to_p90=float(np.exp(logit.params["log_open"] * (np.log1p(p90) - np.log1p(med)))))
    return tab, extra


def run(cfg, seg, terrain=None):
    s = analysis_set(cfg, seg, terrain)
    s.to_csv(cfg.out("analysis_segments.csv"), index=False)
    n_conc, top = concentration(cfg, seg)
    val = validation(cfg, s)
    tab, extra = correlates(cfg, s)
    summary = {
        "segments_analysis": len(s), "chronic": int(s.chronic.sum()),
        "rate_p2_chronic": float(s.rate_p2[s.chronic == 1].mean()), "rate_p2_other": float(s.rate_p2[s.chronic == 0].mean()),
        "concentration_n": n_conc, "top10_share": top[0.10], "top20_share": top[0.20], **extra,
    }
    return s, summary, val, tab
