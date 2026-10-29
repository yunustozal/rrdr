import pandas as pd, numpy as np, geopandas as gpd, json, warnings; warnings.filterwarnings('ignore')
import os
CHI=os.environ.get("RRDR_CHICAGO_OUT","../../outputs/chicago")+"/"
os.makedirs("out",exist_ok=True)
import statsmodels.api as sm, statsmodels.formula.api as smf, pyfixest as pf
CITIES={}
# ---- Chicago
a=pd.read_csv(CHI+"analysis_segments.csv",usecols=['seg','cls','len100m'])
pr=pd.read_csv(CHI+"panel_requests.csv")
cnt=pr.pivot_table(index='seg',columns='year',values='req',aggfunc='sum',fill_value=0); cnt.columns=cnt.columns.astype(int)
rn=pd.read_csv(CHI+"renewals.csv"); rn=rn[rn.share>=0.5][['seg','year']]
CITIES['Chicago']=dict(units=a.rename(columns={'seg':'id'}).assign(len_m=a.len100m*100,cls=a.cls.astype(str))[['id','cls','len_m']],
  counts=cnt,ren=rn.rename(columns={'seg':'id'}),A=list(range(2011,2019)),B=list(range(2019,2026)),source='311 requests',
  es=(2020,2022,2016,2025),did=((2020,2021),(2024,2025),(2016,2025),(2019,2024)))
# ---- NYC
b=pd.read_parquet("data/nyc/panel_persist.parquet")
wc=pd.read_parquet("data/nyc/wo_counts.parquet"); cn=wc.pivot_table(index='OFT',columns='year',values='wo',aggfunc='sum',fill_value=0)
r=pd.read_parquet("data/nyc/renewals.parquet")
CITIES['New York']=dict(units=b.rename(columns={'OFT':'id'})[['id','cls','len_m']],counts=cn,ren=r.rename(columns={'OFT':'id'})[['id','year']],
  A=list(range(2010,2018)),B=list(range(2018,2026)),source='DOT pothole work orders',es=(2018,2021,2014,2025),did=((2017,2018),(2023,2024),(2012,2025),(2012,2022)))
c3=pd.read_parquet("data/nyc/r311_counts.parquet").pivot_table(index='OFT',columns='year',values='r311',aggfunc='sum',fill_value=0)
CITIES['New York (311)']=dict(CITIES['New York'],counts=c3,source='311 requests')
# ---- Boston
for nm,dd,src in [('Boston','boston','311 requests'),('Minneapolis','mpls','311 requests'),('Pittsburgh','pgh','311 requests')]:
    u=pd.read_parquet(f"data/{dd}/panel.parquet").reset_index(drop=True); u['id']=u.index
    ct=pd.read_parquet(f"data/{dd}/counts.parquet"); ct.columns=[int(c) for c in ct.columns]; ct.index=range(len(ct))
    CITIES[nm]=dict(units=u[['id','cls','len_m']],counts=ct,ren=None,A=list(range(2015,2020)),B=list(range(2020,2026)),source=src)
pr_=pd.read_parquet("data/pgh/renewals.parquet").rename(columns={'sid':'id'}); pr_['year']=pr_.year.astype(int)
CITIES['Pittsburgh'].update(ren=pr_,es=(2017,2020,2013,2021),did=((2016,2017),(2020,2021),(2012,2021),(2015,2020)))

def prep(c):
    u=c['units'].set_index('id'); u=u[u.len_m.between(50,2000)]
    ct=c['counts'].reindex(index=u.index,fill_value=0)
    yrs=sorted(set(c['A']+c['B'])); ct=ct.reindex(columns=yrs,fill_value=0)
    return u,ct
OUT={}
for nm,c in CITIES.items():
    u,ct=prep(c); A,B=c['A'],c['B']
    ya=(ct[A]>0).sum(axis=1); share=ya/len(A); nB=ct[B].sum(axis=1)
    res=dict(source=c['source'],units=int(len(u)),km=round(u.len_m.sum()/1000,0),requests=int(ct.values.sum()),A=f"{A[0]}-{A[-1]}",B=f"{B[0]}-{B[-1]}")
    for lab,thr in [('60',0.6),('80',0.8),('100',1.0)]:
        ch=share>=thr-1e-9
        d=pd.DataFrame({'n':nB,'ch':ch.astype(int),'cls':u.cls,'lnL':np.log(u.len_m/100*len(B))})
        m=smf.glm("n ~ ch + C(cls)",data=d,family=sm.families.Poisson(),offset=d.lnL).fit(cov_type='HC1')
        ci=np.exp(m.conf_int().loc['ch'])
        byc=d.groupby(['cls','ch']).apply(lambda g: g.n.sum()/np.exp(g.lnL).sum()).unstack()
        rr=(byc[1]/byc[0])
        res[f'irr_{lab}']=[round(float(np.exp(m.params['ch'])),2),round(float(ci[0]),2),round(float(ci[1]),2)]
        res[f'n_chronic_{lab}']=int(ch.sum()); res[f'class_ratio_{lab}']=[round(float(rr.min()),2),round(float(rr.max()),2)]
    rate=nB/(u.len_m/100); o=rate.sort_values(ascending=False).index; cs=nB[o].cumsum()/nB.sum()
    res['top10']=round(float(cs.iloc[int(len(o)*.1)-1]),3); res['top20']=round(float(cs.iloc[int(len(o)*.2)-1]),3)
    if c.get('ren') is not None:
        lo,hi,wlo,whi=c['es']; ren=c['ren'][c['ren'].id.isin(u.index)]
        ys=ren.groupby('id').year.apply(lambda s: sorted(set(int(x) for x in s)))
        ev={i:w[0] for i,yy in ys.items() for w in [[y for y in yy if wlo<=y<=whi]] if len(w)==1 and lo<=w[0]<=hi}
        Y=list(ct.columns); rt=ct.div(u.len_m/100,axis=0); cm=rt.groupby(u.cls).mean(); rel=rt/cm.loc[u.cls].values; rel.index=u.index
        ch=share>=0.8-1e-9
        rows=[(i,k,rel.at[i,y0+k],bool(ch[i])) for i,y0 in ev.items() for k in range(-4,6) if k!=0 and (y0+k) in Y]
        es=pd.DataFrame(rows,columns=['id','k','rel','chronic'])
        tab=es.groupby(['chronic','k']).rel.mean().unstack(0)
        never=ch & ~u.index.isin(ren[ren.year.between(wlo,whi)].id)
        pre=es[(es.k<0)&es.chronic].rel.mean(); post=es[(es.k>0)&es.chronic].rel.mean()
        res['es']=dict(events=len(ev),chronic_events=int(sum(ch[i] for i in ev)),pre=round(pre,2),post=round(post,2),reduction=round(1-post/pre,3),
                       never_n=int(never.sum()),never_rel=round(float(rel.loc[never,c['B']].mean().mean()),2),
                       table={str(k):[round(float(tab.at[k,False]),2),round(float(tab.at[k,True]),2)] for k in tab.index})
        (t1,t2),(c1,c2),W,(o1,o2)=c['did']
        def pick(a,b): return {i:w[0] for i,yy in ys.items() for w in [[y for y in yy if W[0]<=y<=W[1]]] if len(w)==1 and a<=w[0]<=b}
        tr=pick(t1,t2); ctl=pick(c1,c2)
        rows=[(i,y,ct.at[i,y],int(i in tr and y>tr[i]),int(ch[i]),u.cls[i]) for i in list(tr)+list(ctl) for y in range(o1,o2+1) if y in Y and not (i in tr and y==tr[i])]
        d=pd.DataFrame(rows,columns=['id','year','y','post','chronic','cls']); d['cy']=d.cls.astype(str)+d.year.astype(str)
        m=pf.fepois("y ~ post + post:chronic | id + cy",data=d,vcov={"CRV1":"id"}); e=m.coef(); V=m._vcov; names=list(e.index)
        g=np.array([1.0,1.0]); se=float(np.sqrt(g@V@g)); est=e['post']+e['post:chronic']
        res['did']=dict(treated=f"{t1}-{t2}",controls=f"{c1}-{c2}",obs=f"{o1}-{o2}",n_tr=len(tr),n_ctl=len(ctl),n_chronic_tr=int(sum(ch[i] for i in tr)),
            other=[round(1-float(np.exp(e['post'])),3)],chronic=[round(1-float(np.exp(est)),3),round(1-float(np.exp(est+1.96*se)),3),round(1-float(np.exp(est-1.96*se)),3)],nobs=len(d))
    OUT[nm]=res; print(nm,json.dumps({k:v for k,v in res.items() if k not in('es',)})[:600]); 
    if 'es' in res: print("   ES",{k:v for k,v in res['es'].items() if k!='table'})
json.dump(OUT,open("out/harmonized.json","w"),indent=1)
