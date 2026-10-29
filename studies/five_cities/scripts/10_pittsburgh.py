import geopandas as gpd, pandas as pd, numpy as np, pyfixest as pf, warnings; warnings.filterwarnings('ignore')
D="data/pgh/"
seg=gpd.read_file(D+"centerlines.geojson").to_crs(2272)  # PA South ft
cm={'Local':'local','Collector':'collector','Minor Arterial':'arterial','Principal Arterial':'arterial'}
seg['cls']=seg.domi_class.map(cm); seg=seg[seg.cls.notna()].reset_index(drop=True)
seg['len_m']=seg.length*0.3048; seg=seg[seg.len_m.between(30,2000)].reset_index(drop=True)
n=pd.read_csv(D+"311_new.csv",usecols=['subject','created_date_et','latitude','longitude','case_number'])
n=n[n.subject=='Potholes'].dropna(subset=['latitude','longitude']).drop_duplicates('case_number')
n['year']=n.created_date_et.str[:4].astype(int)
g=gpd.GeoDataFrame(n[['year']],geometry=gpd.points_from_xy(n.longitude,n.latitude),crs=4326).to_crs(2272).reset_index(drop=True)
j=gpd.sjoin_nearest(g,seg[['geometry']],max_distance=100,distance_col='d'); j=j[~j.index.duplicated()]
print("requests",len(g),"matched",len(j),round(len(j)/len(g),3))
CT=j.groupby(['index_right','year']).size().unstack(fill_value=0).reindex(index=seg.index,columns=range(2015,2027),fill_value=0)
A=list(range(2015,2020)); B=list(range(2020,2026))
seg['yA']=(CT[A]>0).sum(axis=1); seg['nB']=CT[B].sum(axis=1)
for thr in [3,4,5]:
    seg['ch']=seg.yA>=thr
    t=seg.groupby(['cls','ch']).apply(lambda d: d.nB.sum()/(d.len_m.sum()/100)/len(B)).unstack()
    print("thr",thr,"of 5",(t[True]/t[False]).round(2).to_dict(),seg.groupby('cls').ch.sum().to_dict())
s2=seg.assign(rate=seg.nB/(seg.len_m/100)).sort_values('rate',ascending=False); cs=s2.nB.cumsum()/s2.nB.sum()
print("top10%",round(cs.iloc[int(len(s2)*.1)-1],3),"top20%",round(cs.iloc[int(len(s2)*.2)-1],3),"segments",len(seg))
# renewals: overlap of segment with 10 m buffer of completed paving lines
pv=gpd.read_file(D+"paving.geojson").to_crs(2272); pv=pv[pv.status=='Completed']
pv['year']=pd.to_datetime(pv.stop_date_actual,errors='coerce').dt.year.fillna(pd.to_numeric(pv.start_year,errors='coerce'))
pv=pv[~pv.activity.isin(['Mechanical Patching','Base Repair','PCC - Slab Replacement - Level 1','Profile Milling'])]
buf=pv[['year','geometry']].copy(); buf['geometry']=buf.buffer(33)
ov=gpd.overlay(seg[['geometry']].reset_index().rename(columns={'index':'sid'}),buf,how='intersection',keep_geom_type=True)
ov['ol']=ov.length*0.3048
ov=ov.groupby(['sid','year']).ol.sum().reset_index().merge(seg[['len_m']],left_on='sid',right_index=True)
ren=ov[ov.ol>=0.5*ov.len_m][['sid','year']].drop_duplicates()
print("renewal events",len(ren),ren.year.value_counts().sort_index().to_dict())
# relative rate
Y=list(range(2015,2026)); rate=CT[Y].div(seg.len_m/100,axis=0); cmn=rate.groupby(seg.cls).mean(); rel=rate/cmn.loc[seg.cls].values; rel.index=seg.index
yrs=ren.groupby('sid').year.apply(lambda s: sorted(set(int(x) for x in s)))
ev={s:[y for y in ys if 2013<=y<=2021][0] for s,ys in yrs.items() if len([y for y in ys if 2013<=y<=2021])==1 and 2017<=[y for y in ys if 2013<=y<=2021][0]<=2020}
ch=seg.yA>=3
rows=[(s,k,rel.at[s,y0+k],bool(ch[s])) for s,y0 in ev.items() for k in range(-4,6) if k!=0 and (y0+k) in Y]
es=pd.DataFrame(rows,columns=['sid','k','rel','chronic'])
print("clean events",len(ev),"chronic",int(sum(ch[s] for s in ev)))
print(es.groupby(['chronic','k']).rel.mean().unstack(0).round(2))
pre=es[(es.k<0)&es.chronic].rel.mean(); post=es[(es.k>0)&es.chronic].rel.mean(); print("chronic pre/post",round(pre,2),round(post,2),round(1-post/pre,3))
never=ch & ~seg.index.isin(ren[ren.year.between(2013,2021)].sid); print("never renewed chronic",int(never.sum()),"rel 2020-25",round(rel.loc[never,list(range(2020,2026))].mean().mean(),2))
seg.drop(columns='geometry').to_parquet(D+"panel.parquet"); ren.to_parquet(D+"renewals.parquet"); CT.to_parquet(D+"counts.parquet")
