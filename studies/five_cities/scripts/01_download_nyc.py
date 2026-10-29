import requests,os,sys,time
D="data/nyc"; os.makedirs(D,exist_ok=True)
def full(vid,name):
    p=f"{D}/{name}.csv"
    if os.path.exists(p) and os.path.getsize(p)>1000: return
    with requests.get(f"https://data.cityofnewyork.us/api/views/{vid}/rows.csv?accessType=DOWNLOAD",stream=True,timeout=600) as r:
        r.raise_for_status()
        with open(p,"wb") as f:
            for c in r.iter_content(1<<20): f.write(c)
    print(name,os.path.getsize(p),flush=True)
def soql(vid,name,where,select):
    p=f"{D}/{name}.csv"
    if os.path.exists(p) and os.path.getsize(p)>1000: return
    off=0;first=True
    with open(p,"w") as f:
        while True:
            for k in range(8):
                try:
                    r=requests.get(f"https://data.cityofnewyork.us/resource/{vid}.csv",params={"$select":select,"$where":where,"$order":"unique_key","$limit":50000,"$offset":off},timeout=900)
                    r.raise_for_status(); break
                except Exception as e:
                    print("retry",k,e,flush=True); time.sleep(20)
            t=r.text.splitlines(True)
            if first: f.writelines(t); first=False
            else: f.writelines(t[1:])
            n=len(t)-1; off+=n; print(name,off,flush=True)
            if n<50000: break
sel="unique_key,created_date,closed_date,complaint_type,descriptor,incident_address,street_name,cross_street_1,cross_street_2,borough,x_coordinate_state_plane,y_coordinate_state_plane,latitude,longitude,status,resolution_description"
full("x9wy-ing4","pothole_workorders")
full("ffaf-8mrv","resurfacing_projects")
full("inkn-q76z","cscl_centerline")
print("done")
