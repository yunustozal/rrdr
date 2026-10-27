"""Figures 1-4 as PNG (300 dpi), TIFF (600 dpi) and vector PDF."""
import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, GREY, DARK = "#2a6fdb", "#9aa0a6", "#202124"
CLASS_NAMES = {"2": "Arterial (class 2)", "3": "Collector (class 3)", "4": "Local (class 4)"}


def _save(fig, cfg, name):
    for ext, kw in (("png", {"dpi": 300}), ("pdf", {}), ("tif", {"dpi": 600, "pil_kwargs": {"compression": "tiff_lzw"}})):
        fig.savefig(cfg.out(f"figures/{name}.{ext}"), **kw)
    plt.close(fig)


def fig1(cfg, p2_years):
    c = pd.read_csv(cfg.out("concentration_curve.csv"))
    x, y = c.segment_share.values * 100, c.request_share.values * 100
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(x, y, color=BLUE, lw=2)
    ax.plot([0, 100], [0, 100], color=GREY, lw=1, ls="--")
    for p in (10, 20):
        yy = y[int(len(y) * p / 100) - 1]
        ax.plot([p, p], [0, yy], color=GREY, lw=0.8, ls=":")
        ax.plot([0, p], [yy, yy], color=GREY, lw=0.8, ls=":")
        ax.plot([p], [yy], "o", color=DARK, ms=4)
        ax.text(p + 1.5, yy - 5, f"{p}% → {yy:.1f}%", fontsize=9, fontweight="bold", color=DARK)
    ax.text(66, 58, "equal distribution", color=GREY, fontsize=8, rotation=31)
    ax.set_xlabel("Road segments, ranked by requests per 100 m (%)")
    ax.set_ylabel(f"Cumulative share of requests, {p2_years[0]}–{p2_years[1]} (%)")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    fig.tight_layout()
    _save(fig, cfg, "Fig1")


def fig2(cfg, s, p1_years, p2_years):
    g = s.groupby(["cls", "chronic"]).apply(lambda d: (d.p2_n / d.len100m).mean()).unstack()
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    w, xi = 0.36, np.arange(len(g))
    b1 = ax.bar(xi - w / 2, g[0].values, w, color=GREY, label="Other segments")
    b2 = ax.bar(xi + w / 2, g[1].values, w, color=BLUE, label=f"Chronic in {p1_years[0]}–{p1_years[1]}")
    for b in list(b1) + list(b2):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.15, f"{b.get_height():.2f}", ha="center", fontsize=8.5)
    for i, k in enumerate(g.index):
        ax.text(i, g.loc[k].max() + 1.1, f"×{g.loc[k, 1] / g.loc[k, 0]:.2f}", ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(xi, [CLASS_NAMES.get(k, k) for k in g.index])
    ax.set_ylabel(f"Requests per 100 m, {p2_years[0]}–{p2_years[1]}")
    ax.set_ylim(0, g.values.max() * 1.25)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    _save(fig, cfg, "Fig2")


def fig3(cfg, main, ev_years):
    t = pd.read_csv(cfg.out("fig3_event_study.csv")).set_index("k")
    nv = main["never_mean"]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    for col, c, lab in (("other", GREY, f"Other segments, resurfaced (n = {main['events_other']:,})"),
                        ("chronic", BLUE, f"Chronic segments, resurfaced (n = {main['events_chronic']:,})")):
        for part in (t[t.index < 0], t[t.index > 0]):
            ax.plot(part.index, part[col], color=c, lw=2.2 if col == "chronic" else 1.8, marker="o", ms=4,
                    label=lab if part.index.min() < 0 else None)
    ax.axhline(nv, color=DARK, lw=1, ls="--")
    ax.text(5, nv + 0.08, f"Chronic, never renewed (mean): {nv:.2f}×", ha="right", fontsize=8)
    ax.axhline(1, color=GREY, lw=0.8)
    ax.text(-3, 1.05, "Street-class average", fontsize=8, color=GREY)
    ax.axvline(0, color=GREY, lw=0.8, ls=":")
    ax.text(0.1, t.values.max() + 0.15, "Resurfaced", ha="left", fontsize=8, color=DARK)
    before, after = t.loc[-1, "chronic"], t.loc[1, "chronic"]
    ax.annotate(f"{before:.2f}×", (-1, before), xytext=(-1.55, before + 0.09), fontsize=8.5, fontweight="bold")
    ax.annotate(f"{after:.2f}×", (1, after), xytext=(0.35, after - 0.28), fontsize=8.5, fontweight="bold")
    ax.set_xticks(range(-3, 6), ["−3", "−2", "−1", "0", "+1", "+2", "+3", "+4", "+5"])
    ax.set_xlabel(f"Years since resurfacing (renewals {ev_years[0]}–{ev_years[1]})")
    ax.set_ylabel("Requests relative to class average")
    ax.set_ylim(0, t.values.max() + 0.35)
    ax.legend(frameon=False, loc="center right", fontsize=8)
    fig.tight_layout()
    _save(fig, cfg, "Fig3")


def fig4(cfg, targets, h=10, r=3):
    segs = gpd.read_file(cfg.out("segments.gpkg"))
    base = segs[segs.cls.astype(str).isin(cfg["centerlines"]["classes_all_roads"])]
    col = f"breakeven_{h}y_{r}pct"
    tg = segs.merge(targets[["seg", col]], on="seg")
    bins = [(0, 150, "≤ $150", "#1a5fd0"), (150, 250, "$150–250", "#5b8fe6"),
            (250, 500, "$250–500", "#f0a04b"), (500, 1e12, "> $500", "#c9c9c9")]
    fig, ax = plt.subplots(figsize=(5.2, 7.2))
    base.plot(ax=ax, color="#e3e3e3", lw=0.25)
    for lo, hi, lab, c in bins[::-1]:
        sub = tg[(tg[col] > lo) & (tg[col] <= hi)]
        if len(sub):
            sub.plot(ax=ax, color=c, lw=1.6 if hi <= 250 else 1.1, label=f"{lab} ({len(sub)})")
    ax.set_axis_off()
    ax.legend(title=f"Break-even cost per pothole\n({h} yrs, {r}%)", frameon=False, loc="lower left", fontsize=8, title_fontsize=8.5)
    ax.set_title(f"{len(tg)} chronic segments not renewed", fontsize=10, loc="left")
    fig.tight_layout()
    _save(fig, cfg, "Fig4")
