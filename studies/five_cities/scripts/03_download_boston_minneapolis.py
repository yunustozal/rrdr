import requests,os,json,io
import pandas as pd
for d in ['data/boston','data/mpls']: os.makedirs(d,exist_ok=True)
# Boston
b="https://data.boston.gov/api/3/action/"
p=requests.get(b+"package_show",params={"id":"311-service-requests"},timeout=60).json()['result']
frames=[]
for r in ([] if os.path.exists('data/boston/311_potholes.csv') else p['resources']):
    nm=(r['name'] or '').upper()
    if not nm.startswith('311 SERVICE REQUESTS - 20') or not r.get('datastore_active'): continue
    y=nm[-4:]; rows=[]
    for t in ["Request for Pothole Repair","Pothole Repair (Internal)"]:
        off=0
        while True:
            j=requests.get(b+"datastore_search",params={"resource_id":r['id'],"filters":json.dumps({"type":t}),"limit":32000,"offset":off},timeout=600).json()['result']
            rows+=j['records']; off+=len(j['records'])
            if len(j['records'])<32000: break
    df=pd.DataFrame(rows); df['year_file']=y
    print('boston',y,len(df),flush=True); frames.append(df)
frames and pd.concat(frames).to_csv("data/boston/311_potholes.csv",index=False)
# Boston street segments (official SAM system layer)
if not os.path.exists("data/boston/street_segments.geojson"):
    q="https://gisportal.boston.gov/arcgis/rest/services/SAM/Live_SAM_Address/FeatureServer/3/query"; feats=[]; off=0
    while True:
        r=requests.get(q,params={"where":"1=1","outFields":"SEGMENT_ID,ST_NAME,ST_TYPE,CFCC,ownership,MUN_L,MUN_R","returnGeometry":"true","outSR":4326,"f":"geojson","resultOffset":off,"resultRecordCount":2000},timeout=300).json()
        fs=r.get('features',[]); feats+=fs; off+=len(fs)
        if len(fs)<2000: break
    json.dump({"type":"FeatureCollection","features":feats},open("data/boston/street_segments.geojson","w")); print("boston segments",len(feats))
# Minneapolis
base="https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/"
def pull(svc,where,out,geo=False):
    if os.path.exists(out): return
    feats=[];off=0
    while True:
        r=requests.get(base+svc+"/FeatureServer/0/query",params={"where":where,"outFields":"*","returnGeometry":str(geo).lower(),"outSR":4326,"f":"geojson","resultOffset":off,"resultRecordCount":1000},timeout=300).json()
        fs=r.get('features',[]); feats+=fs; off+=len(fs)
        if not fs or not (r.get('exceededTransferLimit') or r.get('properties',{}).get('exceededTransferLimit')): break
    json.dump({"type":"FeatureCollection","features":feats},open(out,'w'))
    print(svc,len(feats),flush=True)
for y in range(2015,2027):
    pull(f"Public_311_{y}","TYPENAME LIKE '%othole%'",f"data/mpls/311_{y}.geojson")
pull("PWStreetPavementMgmt","1=1","data/mpls/pavement_mgmt.geojson",True)
pull("PW_Street_Centerline","1=1","data/mpls/centerline.geojson",True)
print("done")
