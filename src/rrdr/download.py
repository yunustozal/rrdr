"""Download the public Chicago inputs.

Other cities: download your own files and point configs/<city>.yaml at them;
the rest of the workflow does not depend on this module.
"""
import io
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

PORTAL = "https://data.cityofchicago.org"
ISGS = "https://data.isgs.illinois.edu/arcgis/rest/services/elevation/IL_Cook_DTM_2022/ImageServer/exportImage"
SDA = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
HEADERS = {"User-Agent": "rrdr research workflow (open data)"}


def _get(url, params=None, timeout=600, tries=4):
    for k in range(tries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(5 * (k + 1))
    raise RuntimeError(f"download failed: {url}")


def socrata_csv(dataset, out, where=None, select="*", page=200_000):
    parts, offset = [], 0
    while True:
        params = {"$select": select, "$order": ":id", "$limit": page, "$offset": offset}
        if where:
            params["$where"] = where
        df = pd.read_csv(io.StringIO(_get(f"{PORTAL}/resource/{dataset}.csv", params).text), low_memory=False)
        parts.append(df)
        offset += page
        print(f"  {dataset}: {offset if len(df) == page else offset - page + len(df):,} rows", end="\r")
        if len(df) < page:
            break
    df = pd.concat(parts)
    df.to_csv(out, index=False)
    print(f"  {dataset}: {len(df):,} rows -> {out}")
    return df


def chicago(cfg):
    d = Path(cfg["data_dir"])
    d.mkdir(parents=True, exist_ok=True)
    print("311 pothole requests, historical (7as2-ds3y)")
    r = _get(f"{PORTAL}/api/views/7as2-ds3y/rows.csv", {"accessType": "DOWNLOAD"})
    (d / "311_potholes_historical.csv").write_bytes(r.content)
    print("311 pothole requests, current (v6vf-nfxy)")
    socrata_csv("v6vf-nfxy", d / "311_potholes_current.csv", where="sr_type like '%Pothole%'")
    print("Street centerlines (pr57-gg9e)")
    r = _get(f"{PORTAL}/api/geospatial/pr57-gg9e", {"method": "export", "format": "Shapefile"})
    (d / "centerlines").mkdir(exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for name in z.namelist():
            ext = Path(name).suffix.lower()
            (d / "centerlines" / f"cl{ext}").write_bytes(z.read(name))
    print("Roadway construction moratoriums (ndbz-vy4e)")
    socrata_csv("ndbz-vy4e", d / "moratoriums.csv",
                where="moratorium_type in('Street Resurfacing','Street Construction')")
    print("Openings in the public way (pubx-yq2d)")
    socrata_csv("pubx-yq2d", d / "openings.csv", where="worktype='GenOpening'",
                select="applicationnumber,applicationstartdate,streetname,latitude,longitude")
    print("CTA bus routes (6uva-a5ei)")
    r = _get(f"{PORTAL}/api/geospatial/6uva-a5ei", {"method": "export", "format": "GeoJSON"})
    (d / "cta_bus_routes.geojson").write_bytes(r.content)
    if cfg.get("terrain", {}).get("enabled", False):
        lidar(cfg)
    if cfg.get("soils"):
        ssurgo(cfg)


def lidar(cfg, res_ft=15, px=2000):
    """Bare-earth DTM 2022 tiles covering the city, from the ISGS image service."""
    out = Path(cfg["data_dir"]) / "lidar"
    out.mkdir(parents=True, exist_ok=True)
    step = res_ft * px
    for xa in range(1_090_000, 1_210_000, step):
        for ya in range(1_810_000, 1_960_000, step):
            f = out / f"dtm2022_{res_ft}ft_{xa}_{ya}.tif"
            if f.exists():
                continue
            p = dict(bbox=f"{xa},{ya},{xa + step},{ya + step}", bboxSR=3435, imageSR=3435,
                     size=f"{px},{px}", format="tiff", pixelType="F32", noData=-9999,
                     interpolation="RSP_BilinearInterpolation", f="image")
            r = _get(ISGS, p)
            if "image" in r.headers.get("Content-Type", ""):
                f.write_bytes(r.content)
    print(f"  LiDAR tiles -> {out}")


def ssurgo(cfg, bbox=(-87.95, 41.64, -87.52, 42.03), n=4):
    """SSURGO map units with drainage class, clipped to the city bounding box."""
    import geopandas as gpd
    from shapely import wkt
    w0, s0, e0, n0 = bbox
    rows = []
    for i in range(n):
        for j in range(n):
            w, e = w0 + (e0 - w0) * i / n, w0 + (e0 - w0) * (i + 1) / n
            s, nn = s0 + (n0 - s0) * j / n, s0 + (n0 - s0) * (j + 1) / n
            poly = f"POLYGON(({w} {s},{e} {s},{e} {nn},{w} {nn},{w} {s}))"
            q = (f"SELECT mp.mukey, ma.muname, ma.drclassdcd, ma.hydgrpdcd, "
                 f"mp.mupolygongeo.STIntersection(geometry::STGeomFromText('{poly}',4326)).STAsText() AS wkt "
                 f"FROM mupolygon mp JOIN muaggatt ma ON mp.mukey=ma.mukey "
                 f"WHERE mp.mupolygongeo.STIntersects(geometry::STGeomFromText('{poly}',4326))=1")
            t = requests.post(SDA, data={"query": q, "format": "JSON+COLUMNNAME"}, timeout=300).json().get("Table", [])
            rows += [dict(zip(t[0], x)) for x in t[1:]]
    df = pd.DataFrame(rows)
    g = gpd.GeoDataFrame(df.drop(columns="wkt"), geometry=df.wkt.map(wkt.loads), crs=4326).to_crs(cfg["crs"])
    g = g[g.geometry.notna() & ~g.geometry.is_empty]
    out = Path(cfg["data_dir"]) / "soil" / "ssurgo.gpkg"
    out.parent.mkdir(parents=True, exist_ok=True)
    g.to_file(out, driver="GPKG")
    print(f"  SSURGO -> {out}")
