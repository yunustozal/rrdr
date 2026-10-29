"""Download Pittsburgh inputs from the Western Pennsylvania Regional Data Center (WPRDC)."""
import os, requests
D="data/pgh/"; os.makedirs(D,exist_ok=True)
files={
 "311_new.csv":"https://data.wprdc.org/datastore/dump/5202679a-d243-402e-b82a-63189995a942",   # 311 data (new system; includes 2015- history)
 "paving.geojson":"https://data.wprdc.org/dataset/6d872b14-c9bb-4627-a475-de6a72050cb0/resource/c390f317-ee05-4d56-8450-6d00a1b02e39/download",
 "centerlines.geojson":"https://data.wprdc.org/dataset/9ebd073b-f637-4f33-a7c2-619d23dd085a/resource/8a38a51d-5000-4600-8114-3f9e92202a64/download",
}
for fn,u in files.items():
    p=D+fn
    if os.path.exists(p): continue
    with requests.get(u,stream=True,timeout=900) as r:
        r.raise_for_status()
        with open(p,"wb") as f:
            for c in r.iter_content(1<<20): f.write(c)
    print(fn,os.path.getsize(p))
print("done")
