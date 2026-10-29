import geopandas as gpd, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
seg=gpd.read_file("data/boston/street_segments.geojson").to_crs(26986)
seg['cls']=seg.CFCC.map(lambda c: 'arterial/collector' if str(c)[:2] in ('A3',) else ('local' if str(c)[:2]=='A4' else None))
seg=seg[seg.cls.notna()].reset_index(drop=True); seg['len_m']=seg.length
seg=seg[seg.len_m.between(30,2000)].reset_index(drop=True)
s=pd.read_csv("data/boston/311_potholes.csv",low_memory=False)
s=s[s['type']=='Request for Pothole Repair'].drop_duplicates('case_enquiry_id')
s['year']=pd.to_datetime(s.open_dt,errors='coerce',format='mixed',utc=True).dt.year
s=s.dropna(subset=['latitude','longitude']); s=s[(s.latitude>42.2)&(s.latitude<42.45)]
g=gpd.GeoDataFrame(s[['case_enquiry_id','year']],geometry=gpd.points_from_xy(s.longitude,s.latitude),crs=4326).to_crs(26986).reset_index(drop=True)
j=gpd.sjoin_nearest(g,seg[['geometry','cls']],max_distance=30,distance_col='d'); j=j[~j.index.duplicated()]
print("requests",len(g),"matched",len(j),round(len(j)/len(g),3)); print(g.year.value_counts().sort_index().to_dict())
CT=j.groupby(['index_right','year']).size().unstack(fill_value=0).reindex(index=seg.index,columns=range(2012,2027),fill_value=0)
A=list(range(2015,2020)); B=list(range(2020,2026))
seg['yA']=(CT[A]>0).sum(axis=1); seg['nB']=CT[B].sum(axis=1)
for thr in [3,4,5]:
    seg['ch']=seg.yA>=thr
    t=seg.groupby(['cls','ch']).apply(lambda d: d.nB.sum()/(d.len_m.sum()/100)/len(B)).unstack()
    print("thr",thr,"of 5",(t[True]/t[False]).round(2).to_dict(),seg.groupby('cls').ch.sum().to_dict())
# longer A with 2012-13 + 2015-19 (7 yrs, chronic >=6)
A2=[2012,2013,2015,2016,2017,2018,2019]; seg['yA2']=(CT[A2]>0).sum(axis=1)
seg['ch']=seg.yA2>=6
t=seg.groupby(['cls','ch']).apply(lambda d: d.nB.sum()/(d.len_m.sum()/100)/len(B)).unstack()
print("7-yr A, >=6",(t[True]/t[False]).round(2).to_dict(),seg.groupby('cls').ch.sum().to_dict())
s2=seg.assign(rate=seg.nB/(seg.len_m/100)).sort_values('rate',ascending=False); cs=s2.nB.cumsum()/s2.nB.sum()
print("top10%",round(cs.iloc[int(len(s2)*.1)-1],3),"top20%",round(cs.iloc[int(len(s2)*.2)-1],3),"segments",len(seg))
seg.drop(columns="geometry").to_parquet("data/boston/panel.parquet")
CT.to_parquet("data/boston/counts.parquet")
