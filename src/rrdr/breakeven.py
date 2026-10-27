"""Break-even cost per pothole for renewing chronic segments that have not been renewed (Table 4).

    c*_i = C_r * B_i / (rho * F_i * A(H, r)),   A(H, r) = (1 - (1 + r)^-H) / r

C_r resurfacing cost per block, B_i length in blocks, F_i potholes filled per year
(period 1), rho the reduction in requests after renewal, H horizon, r discount rate.
"""
import numpy as np
import pandas as pd


def annuity(h, r):
    return (1 - (1 + r) ** -h) / r


def run(cfg, s, ren, rho):
    b = cfg["breakeven"]
    win = cfg["renewal_effect"]["never_renewed_window"]
    p1 = cfg["requests"]["period1"]["years"]
    n_years = p1[1] - p1[0] + 1
    renewed = set(ren[ren.year.between(*win)].seg)
    t = s[(s.chronic == 1) & ~s.seg.isin(renewed)].copy()
    t["blocks"] = t.len100m * 100 / b["block_length_m"]
    t["fills_per_year"] = t.p1_filled / n_years
    rows = []
    for h, r in b["scenarios"]:
        col = f"breakeven_{h}y_{int(r * 100)}pct"
        t[col] = b["resurfacing_cost_per_block"] * t.blocks / (rho * t.fills_per_year * annuity(h, r))
        row = {"horizon": h, "rate": r, "median": float(t[col].replace(np.inf, np.nan).median())}
        for c in b["patch_costs"]:
            row[f"pays_back_at_{c}"] = int((t[col] <= c).sum())
        rows.append(row)
    t.drop(columns="geometry", errors="ignore").to_csv(cfg.out("breakeven_targets.csv"), index=False)
    tab = pd.DataFrame(rows)
    tab.to_csv(cfg.out("table4_breakeven.csv"), index=False)
    summary = {"targets": len(t), "km": float(t.len100m.sum() / 10), "blocks": float(t.blocks.sum()),
               "median_fills_per_block_year": float((t.fills_per_year / t.blocks).median())}
    return t, tab, summary
