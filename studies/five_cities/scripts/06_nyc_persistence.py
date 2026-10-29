import pandas as pd, numpy as np
D="data/nyc/"
b=pd.read_parquet(D+"blocks.parquet",columns=['OFT','len_m','Snow Priority','Number Total Lane'])
b=b[b.len_m.between(50,2000)&b['Snow Priority'].isin(['C','S','H'])].rename(columns={'Snow Priority':'cls'})
wc=pd.read_parquet(D+"wo_counts.parquet")
P=wc.pivot_table(index='OFT',columns='year',values='wo',aggfunc='sum',fill_value=0).reindex(b.OFT,fill_value=0)
A=list(range(2010,2018)); B=list(range(2018,2026))
b=b.set_index('OFT')
b['yearsA']=(P[A]>0).sum(1); b['nB']=P[B].sum(1); b['nA']=P[A].sum(1)
b['rateB']=b.nB/(b.len_m/100)/len(B)
for thr in [6,7,8]:
    b['chronic']=b.yearsA>=thr
    t=b.groupby(['cls','chronic']).apply(lambda d: d.nB.sum()/(d.len_m.sum()/100)/len(B)).unstack()
    t['ratio']=t[True]/t[False]; t['n_chronic']=b.groupby('cls').chronic.sum()
    print("threshold",thr,"of 8"); print(t.round(2))
print("blocks",len(b),"chronic(7)",(b.yearsA>=7).sum())
s=b.sort_values('rateB',ascending=False); cs=s.nB.cumsum()/s.nB.sum()
for q in [.1,.2]: print("top",q,round(cs.iloc[int(len(s)*q)-1],3))
b.reset_index().to_parquet(D+"panel_persist.parquet")
