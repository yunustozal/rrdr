"""Optional screen: LiDAR terrain/drainage indicators and soil drainage class per segment.

Output: terrain.csv with max_depth_in, log_acc, rel_elev_ft, slope_pct, poor_drain.
"""
import glob

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.merge import merge
from scipy.ndimage import uniform_filter

if not hasattr(np, "in1d"):          # pysheds with numpy >= 2
    np.in1d = np.isin


def _mosaic(cfg):
    files = sorted(glob.glob(str(cfg.data(cfg["terrain"]["dem_tiles"]))))
    if not files:
        raise FileNotFoundError("no DEM tiles found for the terrain screen")
    src = [rasterio.open(f) for f in files]
    mos, tr = merge(src, nodata=-9999)
    prof = src[0].profile
    prof.update(height=mos.shape[1], width=mos.shape[2], transform=tr, nodata=-9999, dtype="float32", compress="lzw")
    path = cfg.out("dem_mosaic.tif")
    with rasterio.open(path, "w", **prof) as d:
        d.write(mos[0].astype("float32"), 1)
    return path


def _hydrology(path, factor, cfg):
    """Depression depth (ft) and flow accumulation (acres) on an aggregated grid."""
    from pysheds.grid import Grid
    with rasterio.open(path) as d:
        shape = (d.height // factor, d.width // factor)
        z = d.read(1, out_shape=shape, resampling=Resampling.average)
        tr = d.transform * d.transform.scale(factor, factor)
        prof = d.profile.copy()
        cell = abs(tr.a)
    prof.update(height=shape[0], width=shape[1], transform=tr)
    agg = cfg.out("dem_hydrology.tif")
    with rasterio.open(agg, "w", **prof) as d:
        d.write(z, 1)
    grid = Grid.from_raster(str(agg))
    r = grid.read_raster(str(agg))
    f = grid.fill_depressions(grid.fill_pits(r))
    depth = (np.asarray(f) - np.asarray(r)).astype("float32")
    fdir = grid.flowdir(grid.resolve_flats(f))
    acc = (np.asarray(grid.accumulation(fdir)) * cell * cell / 43560).astype("float32")
    return depth, acc


def run(cfg, seg):
    t = cfg["terrain"]
    path = _mosaic(cfg)
    with rasterio.open(path) as d:
        dem, tr = d.read(1), d.transform
    valid = dem > -9000
    k = t.get("hydrology_cell_factor", 1)
    d30, a30 = _hydrology(path, k, cfg)
    up = lambda a: np.repeat(np.repeat(a, k, axis=0), k, axis=1)[: dem.shape[0], : dem.shape[1]]
    depth, acc = up(d30), up(a30)
    del d30, a30
    w = max(3, int(round(t["neighbourhood_window_ft"] / abs(tr.a))))
    z = np.where(valid, dem, 0).astype("float32")
    rel = z - uniform_filter(z, w) / np.maximum(uniform_filter(valid.astype("float32"), w), 1e-6)

    s = seg[seg.cls.isin(cfg["centerlines"]["classes_analysis"]) &
            (seg.len100m >= cfg["centerlines"]["min_length_m"] / 100)].copy()
    lab = rasterize(((g.buffer(t["pavement_buffer_ft"]), int(i)) for g, i in zip(s.geometry, s.seg)),
                    out_shape=dem.shape, transform=tr, fill=-1, dtype="int32")
    m = (lab >= 0) & valid
    df = pd.DataFrame({"seg": lab[m], "depth": depth[m], "acc": acc[m], "rel": rel[m]})
    st = df.groupby("seg").agg(max_depth_in=("depth", lambda x: x.max() * 12), acc_max=("acc", "max"),
                               rel_elev_ft=("rel", "mean"), ncell=("rel", "size"))
    st["log_acc"] = np.log10(st.acc_max + 0.01)

    def z_at(p):
        r_, c_ = rasterio.transform.rowcol(tr, p.x, p.y)
        ok = 0 <= r_ < dem.shape[0] and 0 <= c_ < dem.shape[1] and dem[r_, c_] > -9000
        return dem[r_, c_] if ok else np.nan
    z0 = np.array([z_at(g.interpolate(0.05, normalized=True)) for g in s.geometry])
    z1 = np.array([z_at(g.interpolate(0.95, normalized=True)) for g in s.geometry])
    s["slope_pct"] = np.abs(z0 - z1) / (s.geometry.length.values * 0.9) * 100
    out = s[["seg", "slope_pct"]].merge(st.reset_index(), on="seg")
    out = out[out.ncell >= 10]
    if cfg.has("soils"):
        soil = gpd.read_file(cfg.data(cfg["soils"]["file"])).to_crs(cfg["crs"])
        mid = gpd.GeoDataFrame(s[["seg"]], geometry=s.geometry.interpolate(0.5, normalized=True), crs=s.crs)
        sj = gpd.sjoin(mid, soil[["drclassdcd", "geometry"]], how="left", predicate="within")
        sj = sj[~sj.index.duplicated()]
        poor = sj.drclassdcd.isin(cfg["soils"]["poor_classes"]).astype(int)
        out = out.merge(pd.DataFrame({"seg": sj.seg.values, "poor_drain": poor.values,
                                      "soil_class": sj.drclassdcd.fillna("Unknown/urban").values}), on="seg", how="left")
    out.drop(columns=["ncell", "acc_max"]).to_csv(cfg.out("terrain.csv"), index=False)
    print(f"  terrain indicators for {len(out):,} segments")
    return out
