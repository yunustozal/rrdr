import pandas as pd, numpy as np, geopandas as gpd
from shapely import wkt
D="data/nyc/"
w=pd.read_csv(D+"pothole_workorders.csv",usecols=['the_geom','OFT','Source','InitBy','RptDate','Shape_Leng','Boro','OnPrimName'])
w['year']=pd.to_numeric(w.RptDate.str[:4],errors='coerce')
w=w[(w.year>=2010)&(w.year<=2025)]
w['OFT']=w.OFT.astype('int64')
# block geometry & length
g=w.drop_duplicates('OFT')[['OFT','the_geom','OnPrimName','Boro']].copy()
r=pd.read_csv(D+"resurfacing_projects.csv",usecols=['OFT Code','Project Type','Location Actual Paving End Date','Location WKT','Borough Code','Location On Street','Location Status','Project Status'])
r=r[(r['Project Type']=='Block')&r['OFT Code'].notna()].copy()
r['OFT']=r['OFT Code'].astype('int64')
r['pave']=pd.to_datetime(r['Location Actual Paving End Date'],format='%m/%d/%Y',errors='coerce')
r=r[r.pave.notna()]
r['year']=r.pave.dt.year
g2=r[~r.OFT.isin(g.OFT)].drop_duplicates('OFT')[['OFT','Location WKT','Location On Street','Borough Code']].rename(columns={'Location WKT':'the_geom','Location On Street':'OnPrimName','Borough Code':'Boro'})
blocks=pd.concat([g,g2]).dropna(subset=['the_geom'])
blocks['geometry']=blocks.the_geom.apply(lambda s: wkt.loads(s) if isinstance(s,str) and s[:5] in ('MULTI','LINES') else None)
blocks=gpd.GeoDataFrame(blocks.dropna(subset=['geometry']).drop(columns='the_geom'),geometry='geometry',crs=4326).to_crs(2263)
blocks['len_m']=blocks.length*0.3048
print('blocks',len(blocks))
# street attributes from CSCL by nearest midpoint
c=pd.read_csv(D+"cscl_centerline.csv",usecols=['the_geom','PHYSICALID','RW_TYPE','Snow Priority','Number Total Lane','Street Width','TRUCK ROUTE TYPE','Roadway Jurisdiction','STATUS'])
c=c[c.RW_TYPE.isin([1])]   # 1=street
c=gpd.GeoDataFrame(c,geometry=c.the_geom.apply(wkt.loads),crs=4326).drop(columns='the_geom').to_crs(2263)
mid=blocks.copy(); mid['geometry']=blocks.geometry.interpolate(0.5,normalized=True)
j=gpd.sjoin_nearest(mid[['OFT','geometry']],c,how='left',max_distance=150,distance_col='d').drop_duplicates('OFT')
blocks=blocks.merge(j[['OFT','Snow Priority','Number Total Lane','Street Width','TRUCK ROUTE TYPE','Roadway Jurisdiction','d']],on='OFT',how='left')
print(blocks['Snow Priority'].value_counts(dropna=False))
blocks.to_parquet(D+"blocks.parquet")
w.groupby(['OFT','year']).size().rename('wo').reset_index().to_parquet(D+"wo_counts.parquet")
w.assign(crew=w.Source.ne('CTZ')).groupby(['OFT','year','crew']).size().rename('n').reset_index().to_parquet(D+"wo_counts_src.parquet")
r[['OFT','pave','year']].to_parquet(D+"renewals.parquet")
print('renewals',len(r),r.OFT.nunique())
