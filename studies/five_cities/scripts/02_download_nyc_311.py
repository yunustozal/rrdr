import requests,time,os
D="data/nyc/"; os.makedirs(D,exist_ok=True)
sel="unique_key,created_date,closed_date,descriptor,incident_address,street_name,cross_street_1,cross_street_2,borough,latitude,longitude,status"
for vid,yrs in [("76ig-c548",range(2010,2020)),("erm2-nwe9",range(2020,2026))]:
    for y in yrs:
        p=f"{D}311_{y}.csv"
        if os.path.exists(p) and os.path.getsize(p)>1000: continue
        off=0; out=[]
        while True:
            for k in range(6):
                try:
                    r=requests.get(f"https://data.cityofnewyork.us/resource/{vid}.csv",params={"$select":sel,"$where":f"descriptor='Pothole' AND created_date>='{y}-01-01' AND created_date<'{y+1}-01-01'","$order":":id","$limit":50000,"$offset":off},timeout=600)
                    r.raise_for_status(); break
                except Exception as e: print("retry",y,k,str(e)[:80],flush=True); time.sleep(15)
            t=r.text.splitlines(True); out+= t if off==0 else t[1:]
            n=len(t)-1; off+=n
            if n<50000: break
        open(p,"w").writelines(out); print(y,off,flush=True)
print("done")
