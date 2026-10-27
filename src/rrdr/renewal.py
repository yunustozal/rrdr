"""Does renewal end chronic failure? Event study, robustness and difference-in-differences (Fig. 3, Table 3)."""
import numpy as np
import pandas as pd


class Panel:
    """Relative request rates: observed / expected at the class-wide rate that year."""

    def __init__(self, s, panel_requests, years):
        self.segs = s.seg.values
        L = s.set_index("seg").len100m
        cls = s.set_index("seg").cls
        P = (panel_requests.pivot_table(index="seg", columns="year", values="req", aggfunc="sum")
             .reindex(index=self.segs, columns=range(years[0], years[1] + 1)).fillna(0))
        rate = P.div(L, axis=0)
        exp = pd.DataFrame({y: L * rate[y].groupby(cls).transform("mean") for y in P.columns})
        self.P, self.REL = P, P / exp


def clean_events(ren, years, window, segs):
    """First renewal in `years` with no other renewal year inside `window`."""
    first = ren[ren.year.between(*years)].groupby("seg").year.min()
    o = ren.merge(first.rename("ey"), on="seg")
    bad = set(o[(o.year != o.ey) & o.year.between(*window)].seg)
    return first[~first.index.isin(bad) & first.index.isin(segs)]


def compare(pan, ev, chronic, ren_never, years, never_window):
    """Mean relative rate before (up to 3 yrs) and after (yrs 1-3) renewal, and for never-renewed chronic segments."""
    pre, post = {0: [], 1: []}, {0: [], 1: []}
    for sg, ey in ev.items():
        c = int(chronic[sg])
        b = [pan.REL.at[sg, y] for y in range(max(years[0], ey - 3), ey)]
        a = [pan.REL.at[sg, y] for y in range(ey + 1, min(years[1], ey + 3) + 1)]
        if b and a:
            pre[c].append(np.mean(b))
            post[c].append(np.mean(a))
    renewed = set(ren_never[ren_never.year.between(*never_window)].seg)
    never = [sg for sg in pan.segs if sg not in renewed and chronic[sg]]
    nv = pan.REL.loc[never, years[0]:years[1]].values.mean()
    return dict(events_chronic=len(pre[1]), events_other=len(pre[0]),
                chronic_pre=np.mean(pre[1]), chronic_post=np.mean(post[1]),
                other_pre=np.mean(pre[0]), other_post=np.mean(post[0]),
                never_mean=nv, never_n=len(never), reduction=1 - np.mean(post[1]) / nv)


def did(pan, ev, controls, chronic, cls, years, by_event_time=False):
    import pyfixest as pf
    keep = list(ev.index) + list(controls)
    d = pan.P.loc[keep, years[0]:years[1]].stack().reset_index()
    d.columns = ["seg", "year", "req"]
    d["ey"] = d.seg.map(ev).fillna(9999)
    d = d[d.year != d.ey]
    d["post"] = (d.year > d.ey).astype(int)
    d["post_chronic"] = d.post * d.seg.map(chronic).astype(int)
    d["cls"] = d.seg.map(cls)
    fit = pf.fepois("req ~ post + post_chronic | seg + cls^year", data=d, vcov={"CRV1": "seg"})
    t = fit.tidy()
    res = {"obs": int(fit._N)}
    for v in ("post", "post_chronic"):
        b, se = t.loc[v, "Estimate"], t.loc[v, "Std. Error"]
        res[v] = (np.exp(b), np.exp(b - 1.96 * se), np.exp(b + 1.96 * se))
    res["chronic_effect"] = np.exp(t.loc["post", "Estimate"] + t.loc["post_chronic", "Estimate"])
    if by_event_time:
        d["k"] = np.where(d.ey < 9999, (d.year - d.ey).clip(-3, 3), -99).astype(int)
        es = pf.fepois("req ~ i(k, ref=-1) | seg + cls^year", data=d, vcov={"CRV1": "seg"}).tidy()
        res["event_time"] = {i: float(np.exp(v)) for i, v in es.Estimate.items() if "k::" in i and "-99" not in i}
    return res


def run(cfg, s, panel_requests, ren):
    rc = cfg["renewal_effect"]
    p2 = cfg["requests"]["period2"]["years"]
    p1 = cfg["requests"]["period1"]["years"]
    segs = s.seg.values
    chronic = s.set_index("seg").chronic
    cls = s.set_index("seg").cls
    ren = ren[ren.seg.isin(segs)]
    pan = Panel(s, panel_requests, (p1[0], p2[1]))
    out = {}

    # main event study (Fig. 3)
    ev = clean_events(ren, rc["event_years"], rc["clean_window"], segs)
    out["main"] = compare(pan, ev, chronic, ren, p2, rc["never_renewed_window"])
    rows = []
    for sg, ey in ev.items():
        for y in range(p2[0], p2[1] + 1):
            k = y - ey
            if -3 <= k <= 5 and k != 0:
                rows.append((sg, k, pan.REL.at[sg, y], int(chronic[sg])))
    E = pd.DataFrame(rows, columns=["seg", "k", "rel", "chronic"])
    curve = E.groupby(["k", "chronic"]).rel.mean().unstack()
    curve.columns = ["other", "chronic"]
    curve.to_csv(cfg.out("fig3_event_study.csv"))
    out["main"]["chronic_post_1_5"] = E[(E.chronic == 1) & E.k.between(1, 5)].rel.mean()
    out["main"]["reduction_1_5"] = 1 - out["main"]["chronic_post_1_5"] / out["main"]["never_mean"]
    after = []
    for sg, ey in ev.items():
        hits = [y for y in range(ey + 1, p2[1] + 1) if pan.P.at[sg, y] > 0]
        after.append((int(chronic[sg]), bool(hits) and hits[0] - ey <= 2))
    A = pd.DataFrame(after, columns=["chronic", "within2"])
    out["main"]["new_request_within_2y"] = A.groupby("chronic").within2.mean().to_dict()
    out["main"]["reconstructions"] = int(sum(
        (ren[(ren.seg == sg) & (ren.year == ey)].type == "Street Construction").any() for sg, ey in ev.items()))
    renewed_never = set(ren[ren.year.between(*rc["never_renewed_window"])].seg)
    never = [sg for sg in segs if sg not in renewed_never and chronic[sg]]
    pan.REL.loc[never, p2[0]:p2[1]].mean().to_csv(cfg.out("never_renewed_by_year.csv"))

    # robustness (Table 3)
    rob = {}
    strict = ren[ren.share >= 0.5]
    rob["Baseline, renewals 2020-22"] = out["main"]
    rob["Address overlap >= 50%"] = compare(pan, clean_events(strict, rc["event_years"], rc["clean_window"], segs),
                                           chronic, strict, p2, rc["never_renewed_window"])
    rob["Renewals 2019-23"] = compare(pan, clean_events(ren, [2019, 2023], rc["clean_window"], segs),
                                      chronic, ren, p2, rc["never_renewed_window"])
    for th in cfg["chronic"].get("robustness_thresholds", []):
        ch = (s.set_index("seg").p1_yrs >= th).astype(int)
        rob[f"Chronic = {th} of 8 years"] = compare(pan, ev, ch, ren, p2, rc["never_renewed_window"])
    resurf = ren[ren.type == "Street Resurfacing"]
    rob["Resurfacing moratoria only"] = compare(pan, clean_events(resurf, rc["event_years"], rc["clean_window"], segs),
                                                chronic, ren, p2, rc["never_renewed_window"])
    h = rc["historical_replication"]
    ch_h = ((pan.P.loc[:, h["chronic_years"][0]:h["chronic_years"][1]] > 0).sum(axis=1)
            == h["chronic_years"][1] - h["chronic_years"][0] + 1).astype(int)
    rob["Historical system, renewals 2014-16"] = compare(
        pan, clean_events(ren, h["events"], h["window"], segs), ch_h, ren, p1, (p1[0] - 2, p1[1]))
    tab = pd.DataFrame(rob).T[["events_chronic", "chronic_pre", "chronic_post", "reduction", "never_mean"]]
    tab.to_csv(cfg.out("table3_robustness.csv"))
    out["robustness"] = tab

    # difference-in-differences
    never_all = [sg for sg in segs if sg not in set(ren[ren.year.between(*rc["clean_window"])].seg)]
    out["did_never"] = did(pan, ev, never_all, chronic, cls, p2)
    nyt = rc["not_yet_treated"]
    tr = clean_events(ren, nyt["treated"], rc["clean_window"], segs)
    ct = clean_events(ren, nyt["controls"], rc["clean_window"], segs)
    out["did_not_yet"] = did(pan, tr, list(ct.index), chronic, cls, nyt["years"], by_event_time=True)
    out["did_not_yet"]["treated"], out["did_not_yet"]["controls"] = len(tr), len(ct)
    return out
