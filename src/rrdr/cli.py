"""Command line entry point.

    python -m rrdr.cli download --config configs/chicago.yaml   # Chicago only
    python -m rrdr.cli run      --config configs/chicago.yaml   # full analysis
"""
import argparse
import json

import geopandas as gpd
import pandas as pd

from . import breakeven, config, figures, match, models, renewal


def _json(obj):
    if isinstance(obj, dict):
        return {str(k): _json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json(v) for v in obj]
    if isinstance(obj, pd.DataFrame):
        return json.loads(obj.to_json(orient="index"))
    try:
        return float(obj)
    except (TypeError, ValueError):
        return obj


def run(cfg, skip_terrain=False):
    print("[1/6] matching records to segments")
    match.run(cfg)
    seg = gpd.read_file(cfg.out("segments.gpkg"))
    seg["cls"] = seg.cls.astype(str)
    terrain_tab = None
    if cfg.has("terrain") and not skip_terrain:
        print("[2/6] terrain and soil screen")
        from . import terrain
        terrain_tab = terrain.run(cfg, seg)
    elif cfg.out("terrain.csv").exists():
        terrain_tab = pd.read_csv(cfg.out("terrain.csv"))
    print("[3/6] persistence and correlates")
    s, summary, _, _ = models.run(cfg, seg.drop(columns="geometry"), terrain_tab)
    results = {"persistence": summary}
    if cfg.has("renewals"):
        print("[4/6] renewal effect")
        ren = pd.read_csv(cfg.out("renewals.csv"))
        pr = pd.read_csv(cfg.out("panel_requests.csv"))
        rr = renewal.run(cfg, s, pr, ren)
        results["renewal"] = rr
        print("[5/6] break-even ranking")
        targets, _, bsum = breakeven.run(cfg, s, ren, rr["main"]["reduction_1_5"])
        results["breakeven"] = bsum
    print("[6/6] figures")
    p1, p2 = cfg["requests"]["period1"]["years"], cfg["requests"]["period2"]["years"]
    figures.fig1(cfg, p2)
    figures.fig2(cfg, s, p1, p2)
    if cfg.has("renewals"):
        figures.fig3(cfg, rr["main"], cfg["renewal_effect"]["event_years"])
        figures.fig4(cfg, targets)
    with open(cfg.out("results_summary.json"), "w") as fh:
        json.dump(_json(results), fh, indent=2)
    print(f"done -> {cfg['output_dir']}")
    return results


def main():
    ap = argparse.ArgumentParser(prog="rrdr")
    ap.add_argument("command", choices=["download", "run"])
    ap.add_argument("--config", required=True)
    ap.add_argument("--skip-terrain", action="store_true", help="skip the optional LiDAR/soil screen")
    a = ap.parse_args()
    cfg = config.load(a.config)
    if a.command == "download":
        from . import download
        if cfg.get("city", "").lower() != "chicago":
            raise SystemExit("automatic download is implemented for Chicago only; see docs/adapting.md")
        download.chicago(cfg)
    else:
        run(cfg, skip_terrain=a.skip_terrain)


if __name__ == "__main__":
    main()
