import pandas as pd, numpy as np, geopandas as gpd, glob, re, warnings; warnings.filterwarnings('ignore')
D="data/nyc/"
b=gpd.read_parquet(D+"blocks.parquet"); 
pp=pd.read_parquet(D+"panel_persist.parquet")[['OFT','cls','len_m','yearsA']]
b=b[b.OFT.isin(pp.OFT)][['OFT','OnPrimName','geometry']]
s=pd.concat([pd.read_csv(f,low_memory=False) for f in sorted(glob.glob(D+"311_20*.csv"))])
s=s.dropna(subset=['latitude','longitude']).drop_duplicates('unique_key')
s['year']=pd.to_datetime(s.created_date).dt.year
g=gpd.GeoDataFrame(s,geometry=gpd.points_from_xy(s.longitude,s.latitude),crs=4326).to_crs(2263).reset_index(drop=True)
norm=lambda x: re.sub(r'[^A-Z0-9 ]','',str(x).upper()).replace('AVENUE','AV').replace('STREET','ST').replace('BOULEVARD','BLVD').replace('ROAD','RD').replace('PLACE','PL').strip()
b['nm']=b.OnPrimName.map(norm); g['nm']=g.street_name.map(norm)
# candidates within 100 ft; prefer name match, else nearest within 50 ft
j=gpd.sjoin_nearest(g[['unique_key','year','nm','geometry']],b[['OFT','nm','geometry']],max_distance=100,distance_col='d',lsuffix='s',rsuffix='b')
j['namehit']=j.nm_s==j.nm_b
j=j.sort_values(['unique_key','namehit','d'],ascending=[True,False,True]).drop_duplicates('unique_key')
j=j[j.namehit | (j.d<=50)]
print("311 requests",len(g),"matched",len(j),round(len(j)/len(g),3),"name-matched share",round(j.namehit.mean(),3))
c=j.groupby(['OFT','year']).size().rename('r311').reset_index(); c.to_parquet(D+"r311_counts.parquet")
print(g.year.value_counts().sort_index().to_dict())
