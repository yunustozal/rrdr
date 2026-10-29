"""Minneapolis: later-period requests by pavement condition index (PCI) and chronic status."""
import pandas as pd, numpy as np, statsmodels.formula.api as smf, json, os
os.makedirs("out",exist_ok=True)
p=pd.read_parquet("data/mpls/panel.parquet").reset_index(drop=True)
ct=pd.read_parquet("data/mpls/counts.parquet"); ct.columns=[int(c) for c in ct.columns]; ct.index=range(len(ct))
p=p[p.len_m.between(50,2000)]
p['PCI']=pd.to_numeric(p.PCI,errors='coerce'); q=p[p.PCI.notna()].copy()
A=list(range(2015,2020)); B=list(range(2020,2026))
q['ch']=(ct.loc[q.index,A]>0).sum(axis=1)>=4; q['nB']=ct.loc[q.index,B].sum(axis=1)
q['pbin']=pd.qcut(q.PCI,4,labels=['Q1 (worst)','Q2','Q3','Q4 (best)'])
t=q.groupby(['pbin','ch']).apply(lambda g: g.nB.sum()/(g.len_m.sum()/100)/6).unstack(); t.to_csv("out/mpls_pci_bins.csv")
q['lnL']=np.log(q.len_m/100*6); q['chi']=q.ch.astype(int)
m=smf.negativebinomial("nB ~ chi + PCI + cls",data=q,offset=q.lnL).fit(disp=0); ci=np.exp(m.conf_int())
res={"n_sections":len(q),"n_chronic":int(q.ch.sum()),"irr_chronic":[round(float(np.exp(m.params.chi)),2)]+[round(float(x),2) for x in ci.loc['chi']],
     "irr_pci_minus10":[round(float(np.exp(-10*m.params.PCI)),3)]+[round(float(np.exp(-10*x)),3) for x in m.conf_int().loc['PCI'][::-1]],
     "mean_pci":{str(k):round(float(v),1) for k,v in q.groupby('ch').PCI.mean().items()}}
print(res); json.dump(res,open("out/mpls_pci.json","w"),indent=1)
