"""Match requests, permits, transit routes and renewal records to street segments.

Outputs (in output_dir):
  segments.gpkg / segments.csv   one row per centerline segment with period totals
  panel_requests.csv             requests per segment and year (both periods)
  renewals.csv                   renewal events per segment and year, with address overlap share
"""
import re

import geopandas as gpd
import numpy as np
import pandas as pd

STREET_TYPES = r"\s+(AVE|ST|BLVD|RD|DR|PL|PKWY|CT|TER|HWY|WAY|LN|SQ|PLZ|EXPY|ROW|CIR)$"


def street_name_from_address(addr: str) -> str:
    """'1234 N MILWAUKEE AVE' -> 'MILWAUKEE'."""
    a = re.sub(r"^\d+\s+", "", str(addr).upper().strip())
    a = re.sub(r"^(N|S|E|W)\s+", "", a)
    return re.sub(STREET_TYPES, "", a).strip()


def load_centerlines(cfg):
    c = cfg["centerlines"]
    cols = c["columns"]
    cl = gpd.read_file(cfg.data(c["file"])).to_crs(cfg["crs"]).reset_index(drop=True)
    cl["seg"] = cl.index
    cl["name"] = cl[cols["street_name"]].fillna("").astype(str).str.upper().str.strip()
    cl["pre"] = cl[cols["prefix"]].fillna("").astype(str).str.upper().str.strip()
    cl["cls"] = cl[cols["class"]].astype(str)
    cl["len100m"] = cl[cols["length_ft"]] * 0.3048 / 100
    addr = cl[cols["address_fields"]]
    cl["amin"] = addr.replace(0, np.nan).min(axis=1)
    cl["amax"] = addr.max(axis=1)
    return cl[["seg", "name", "pre", "cls", "len100m", "amin", "amax", "geometry"]]


def _points(df, lon, lat, crs):
    df = df.dropna(subset=[lat, lon])
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon], df[lat]), crs=4326).to_crs(crs)


def snap_by_name(points, cl, max_ft):
    """Nearest segment with the same street name within max_ft; returns points with 'seg'."""
    out = []
    for nm, grp in points.groupby("name"):
        cand = cl[cl.name == nm]
        if cand.empty:
            continue
        j = gpd.sjoin_nearest(grp, cand[["seg", "geometry"]], how="inner", max_distance=max_ft)
        out.append(j[~j.index.duplicated()].drop(columns="index_right"))
    return pd.concat(out) if out else points.iloc[0:0].assign(seg=[])


def load_requests(cfg, period):
    p = cfg["requests"][period]
    col = p["columns"]
    df = pd.read_csv(cfg.data(p["file"]), low_memory=False)
    df["year"] = pd.to_datetime(df[col["date"]], errors="coerce").dt.year
    df = df[df.year.between(*p["years"])]
    if "keep_status" in p:
        df = df[df[col["status"]].isin(p["keep_status"])]
    if "drop_status" in p:
        df = df[~df[col["status"]].isin(p["drop_status"])]
    if "keep_types" in p:
        df = df[df[col["type"]].isin(p["keep_types"])]
    if p.get("drop_duplicates"):
        df = df[~df[col["duplicate"]].astype(str).str.lower().eq("true")]
    if p.get("street_name_from") == "address":
        df["name"] = df[col["address"]].map(street_name_from_address)
    else:
        df["name"] = df[col["street_name"]].fillna("").astype(str).str.upper().str.strip()
    df["filled"] = df[col["filled"]] if "filled" in col else np.nan
    return _points(df, col["lon"], col["lat"], cfg["crs"])


def match_renewals(cfg, cl):
    r = cfg["renewals"]
    col = r["columns"]
    m = pd.read_csv(cfg.data(r["file"]))
    m = m[m[col["type"]].isin(r["keep_types"])].copy()
    m["year"] = pd.to_datetime(m[col["date"]], errors="coerce").dt.year
    m["name"] = m[col["street_name"]].fillna("").astype(str).str.upper().str.strip()
    m["pre"] = m[col["prefix"]].fillna("").astype(str).str.upper().str.strip()
    rows = []
    for (nm, pre), g in m.groupby(["name", "pre"]):
        cand = cl[(cl.name == nm) & (cl.pre == pre)]
        if cand.empty:
            continue
        for _, x in g.iterrows():
            lo, hi = x[col["addr_from"]], x[col["addr_to"]]
            hit = cand[(cand.amin < hi) & (cand.amax > lo)]
            for s, amin, amax in zip(hit.seg, hit.amin, hit.amax):
                ov = max(min(amax, hi) - max(amin, lo), 0) + 1
                rows.append((s, int(x.year), x[col["type"]], min(ov / (amax - amin + 1), 1.0)))
    ren = pd.DataFrame(rows, columns=["seg", "year", "type", "share"])
    return ren.groupby(["seg", "year", "type"], as_index=False).share.max()


def run(cfg):
    max_ft = cfg["matching"]["max_distance_ft"]
    cl = load_centerlines(cfg)
    panels, seg = [], cl.drop(columns="geometry").set_index("seg")
    for period, tag in (("period1", "p1"), ("period2", "p2")):
        pts = load_requests(cfg, period)
        j = snap_by_name(pts, cl, max_ft)
        print(f"  {period}: {len(j):,} of {len(pts):,} requests matched ({len(j) / len(pts):.1%})")
        panels.append(j.groupby(["seg", "year"]).size().rename("req").reset_index())
        g = j.groupby("seg")
        seg[f"{tag}_n"] = g.size()
        seg[f"{tag}_yrs"] = g.year.nunique()
        if j["filled"].notna().any():
            seg[f"{tag}_filled"] = g.filled.sum()
    pd.concat(panels).to_csv(cfg.out("panel_requests.csv"), index=False)
    if cfg.has("openings"):
        o = cfg["openings"]
        col = o["columns"]
        df = pd.read_csv(cfg.data(o["file"]), low_memory=False)
        df["year"] = pd.to_datetime(df[col["date"]], errors="coerce").dt.year
        df = df[df.year.between(*o["years"])]
        df["name"] = df[col["street_name"]].fillna("").astype(str).str.upper().str.strip()
        j = snap_by_name(_points(df, col["lon"], col["lat"], cfg["crs"]), cl, max_ft)
        print(f"  openings: {len(j):,} matched")
        n_years = o["years"][1] - o["years"][0] + 1
        seg["openings"] = j.groupby("seg").size()
        seg["open_rate"] = seg.openings.fillna(0) / seg.len100m / n_years
    if cfg.has("transit_routes"):
        t = cfg["transit_routes"]
        zone = gpd.read_file(cfg.data(t["file"])).to_crs(cfg["crs"]).buffer(t["buffer_ft"]).union_all()
        seg["bus"] = (cl.geometry.intersection(zone).length / cl.geometry.length >= t["min_share"]).astype(int).values
    if cfg.has("renewals"):
        ren = match_renewals(cfg, cl)
        ren.to_csv(cfg.out("renewals.csv"), index=False)
        print(f"  renewals: {len(ren):,} segment-events on {ren.seg.nunique():,} segments")
    fill = [c for c in seg.columns if c.startswith(("p1_", "p2_", "openings", "open_rate"))]
    seg[fill] = seg[fill].fillna(0)
    seg = seg.reset_index()
    seg.to_csv(cfg.out("segments.csv"), index=False)
    gpd.GeoDataFrame(seg, geometry=cl.geometry.values, crs=cl.crs).to_file(cfg.out("segments.gpkg"), driver="GPKG")
    return seg
