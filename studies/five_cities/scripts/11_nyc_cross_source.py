import pandas as pd, numpy as np, json, statsmodels.api as sm, statsmodels.formula.api as smf, warnings; warnings.filterwarnings('ignore')
import os; os.makedirs("out",exist_ok=True)
D="data/nyc/"
b=pd.read_parquet(D+"panel_persist.parquet").set_index('OFT'); b=b[b.len_m.between(50,2000)]
s=pd.read_parquet(D+"wo_counts_src.parquet")
def mat(df,val): 
    m=df.pivot_table(index='OFT',columns='year',values=val,aggfunc='sum',fill_value=0).reindex(b.index,fill_value=0); return m.reindex(columns=range(2010,2026),fill_value=0)
crew=mat(s[s.crew],'n'); cit=mat(s[~s.crew],'n')
r311=mat(pd.read_parquet(D+"r311_counts.parquet"),'r311')
wo=crew+cit
A=list(range(2010,2018)); B=list(range(2018,2026))
def irr(defm,outm,thr=7):
    ch=((defm[A]>0).sum(axis=1)>=thr).astype(int); n=outm[B].sum(axis=1)
    d=pd.DataFrame({'n':n,'ch':ch,'cls':b.cls,'lnL':np.log(b.len_m/100*8)})
    m=smf.glm("n ~ ch + C(cls)",data=d,family=sm.families.Poisson(),offset=d.lnL).fit(cov_type='HC1')
    ci=np.exp(m.conf_int().loc['ch']); return [round(float(np.exp(m.params['ch'])),2),round(float(ci[0]),2),round(float(ci[1]),2),int(ch.sum())]
R={'crew_def->citizen_out':irr(crew,cit,6),'citizen_def->crew_out':irr(cit,crew,6),'crew_def->citizen_out_7':irr(crew,cit),'citizen_def->crew_out_7':irr(cit,crew),
   'WO_def->311_out':irr(wo,r311),'311_def->WO_out':irr(r311,wo)}
ch_wo=(wo[A]>0).sum(axis=1)>=7; ch_311=(r311[A]>0).sum(axis=1)>=7
R['overlap']=[int((ch_wo&ch_311).sum()),int(ch_wo.sum()),int(ch_311.sum())]
R['crew_share']=round(float(crew.values.sum()/wo.values.sum()),3)
print(R); json.dump(R,open("out/nyc_cross.json","w"))
