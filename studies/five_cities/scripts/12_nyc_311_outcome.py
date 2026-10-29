import pandas as pd, numpy as np, pyfixest as pf, warnings; warnings.filterwarnings('ignore')
D="data/nyc/"
b=pd.read_parquet(D+"panel_persist.parquet").set_index('OFT')
c=pd.read_parquet(D+"r311_counts.parquet")
S=c.pivot_table(index='OFT',columns='year',values='r311',aggfunc='sum',fill_value=0).reindex(b.index,fill_value=0)
S=S.reindex(columns=range(2010,2026),fill_value=0)
B=list(range(2018,2026)); A=list(range(2010,2018))
# 1) chronic from DOT work orders 2010-17 -> citizen 311 2018-25
nB=S[B].sum(axis=1)
for thr in [6,7]:
    ch=b.yearsA>=thr
    t=pd.DataFrame({'n':nB,'L':b.len_m,'cls':b.cls,'ch':ch}).groupby(['cls','ch']).apply(lambda g: g.n.sum()/(g.L.sum()/100)/8).unstack()
    print("WO-chronic(>=%d) -> 311 2018-25 ratio"%thr,(t[True]/t[False]).round(2).to_dict())
# 2) chronic from 311 2010-17 -> 311 2018-25
y311=(S[A]>0).sum(axis=1)
for thr in [6,7]:
    ch=y311>=thr
    t=pd.DataFrame({'n':nB,'L':b.len_m,'cls':b.cls,'ch':ch}).groupby(['cls','ch']).apply(lambda g: g.n.sum()/(g.L.sum()/100)/8).unstack()
    print("311-chronic(>=%d) -> 311 ratio"%thr,(t[True]/t[False]).round(2).to_dict(),"n",int(ch.sum()))
print("overlap WO-chronic & 311-chronic(>=6):", int(((b.yearsA>=7)&(y311>=6)).sum()), "of", int((b.yearsA>=7).sum()))
# 3) renewal DiD on 311 outcome
r=pd.read_parquet(D+"renewals.parquet"); r=r[r.OFT.isin(b.index)]
yrs=r.groupby('OFT').year.apply(lambda s: sorted(set(s)))
def pick(lo,hi,W):
    return {o:[y for y in ys if W[0]<=y<=W[1]][0] for o,ys in yrs.items() if len([y for y in ys if W[0]<=y<=W[1]])==1 and lo<=[y for y in ys if W[0]<=y<=W[1]][0]<=hi}
tr=pick(2017,2018,(2012,2025)); ctl=pick(2023,2024,(2012,2025))
rows=[(o,y,S.at[o,y],int(o in tr and y>tr[o]),int(b.yearsA[o]>=7),b.cls[o]) for o in list(tr)+list(ctl) for y in range(2012,2022) if not (o in tr and y==tr[o])]
d=pd.DataFrame(rows,columns=['OFT','year','y','post','chronic','cls']); d['cy']=d.cls+d.year.astype(str)
m=pf.fepois("y ~ post + post:chronic | OFT + cy",data=d,vcov={"CRV1":"OFT"}); e=m.coef()
print(m.tidy()[['Estimate','2.5%','97.5%']].round(3))
print("311 outcome: other",round(1-np.exp(e['post']),3),"chronic",round(1-np.exp(e['post']+e['post:chronic']),3))
