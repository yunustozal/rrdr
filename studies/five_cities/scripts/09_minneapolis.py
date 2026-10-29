import geopandas as gpd, pandas as pd, numpy as np, glob
p=gpd.read_file("data/mpls/pavement_mgmt.geojson").to_crs(26915)
p['len_m']=p.length
p['cls']=p.NETWORK.map({'CSAH':'arterial','STH':'arterial','MSA':'collector','RES':'local','LOCAL':'local'})
p=p[p.cls.notna()&p.len_m.between(30,2000)].reset_index(drop=True)
fr=[]
for f in sorted(glob.glob("data/mpls/311_20*.geojson")):
    d=gpd.read_file(f); d=pd.DataFrame(d.drop(columns='geometry'))
    fr.append(d)
s=pd.concat(fr); s['year']=pd.to_datetime(s.OPENEDDATETIME,unit='ms').dt.year
s=s.drop_duplicates('CASEID').reset_index(drop=True)
s=gpd.GeoDataFrame(s,geometry=gpd.points_from_xy(s.XCOORD,s.YCOORD),crs=3857).to_crs(26915)
j=gpd.sjoin_nearest(s,p[['geometry','cls']],how='inner',max_distance=30,distance_col='d')
j=j[~j.index.duplicated()]
print("requests",len(s),"matched",len(j),round(len(j)/len(s),3)); print(s.year.value_counts().sort_index().to_dict())
CT=j.groupby(['index_right','year']).size().unstack(fill_value=0).reindex(p.index,fill_value=0)
A=[y for y in range(2015,2020)]; B=[y for y in range(2020,2026)]; CT=CT.reindex(columns=range(2015,2027),fill_value=0)
p['yA']=(CT[A]>0).sum(axis=1); p['nB']=CT[B].sum(axis=1)
for thr in [3,4,5]:
    p['ch']=p.yA>=thr
    t=p.groupby(['cls','ch']).apply(lambda g: g.nB.sum()/(g.len_m.sum()/100)/len(B)).unstack()
    print("thr",thr,"of 5",(t[True]/t[False]).round(2).to_dict(),p.groupby('cls').ch.sum().to_dict())
# PCI comparison
p['PCI']=pd.to_numeric(p.PCI,errors='coerce')
q=p[p.PCI.notna()].copy(); q['ch']=q.yA>=3
import statsmodels.formula.api as smf
q['lnL']=np.log(q.len_m)
m=smf.negativebinomial("nB ~ ch + PCI + C(cls)",data=q,offset=q.lnL).fit(disp=0)
print(m.params.round(3).to_dict()); print("IRR chronic",round(np.exp(m.params['ch[T.True]']),2),"IRR per -10 PCI",round(np.exp(-10*m.params['PCI']),2),"n",len(q))
print("corr chronic vs PCI", q.groupby('ch').PCI.mean().round(1).to_dict())
p.drop(columns='geometry').to_parquet("data/mpls/panel.parquet")
CT.to_parquet("data/mpls/counts.parquet")
