import json, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg')
import os; os.makedirs("out/figs",exist_ok=True)
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
H=json.load(open("out/harmonized.json"))
order=['Chicago','New York','New York (311)','Boston','Minneapolis','Pittsburgh']
lab={'Chicago':'Chicago (311)','New York':'New York (DOT work orders)','New York (311)':'New York (311)','Boston':'Boston (311)','Minneapolis':'Minneapolis (311)','Pittsburgh':'Pittsburgh (311)'}
# Fig 1 forest
fig,ax=plt.subplots(figsize=(6.5,3.6))
for i,c in enumerate(order[::-1]):
    e,lo,hi=H[c]['irr_80']; ax.plot([lo,hi],[i,i],color='k',lw=1.2); ax.plot(e,i,'o',color='k',ms=5)
    ax.plot(H[c]['irr_60'][0],i,marker='|',color='0.45',ms=9,mew=1.5); ax.plot(H[c]['irr_100'][0],i,marker='x',color='0.45',ms=5)
    ax.text(5.3,i,f"{e:.2f} ({lo:.2f}–{hi:.2f})  n={H[c]['n_chronic_80']:,}",va='center',fontsize=8)
ax.set_yticks(range(len(order))); ax.set_yticklabels([lab[c] for c in order[::-1]])
ax.axvline(1,color='0.6',lw=0.8,ls=':'); ax.set_xlim(0.8,5.2); ax.set_xlabel("Rate ratio, chronic vs. other segments of the same class (later period)")
ax.plot([],[],'o',color='k',label='Chronic: ≥80% of years (95% CI)'); ax.plot([],[],'|',color='0.45',ms=9,mew=1.5,label='≥60% of years'); ax.plot([],[],'x',color='0.45',label='100% of years')
fig.legend(loc='lower center',ncol=3,frameon=False,fontsize=7.5)
fig.tight_layout(rect=(0,0.07,0.78,1)); fig.savefig("out/figs/Fig1.png",dpi=300); fig.savefig("out/figs/Fig1.pdf"); fig.savefig("out/figs/Fig1.tif",dpi=600,pil_kwargs={'compression':'tiff_lzw'})
# Fig 2 event studies
fig,axs=plt.subplots(1,3,figsize=(7,2.6),sharey=True)
for ax,c in zip(axs,['Chicago','New York','Pittsburgh']):
    t=H[c]['es']['table']; ks=sorted(int(k) for k in t)
    for j,(nm,st) in enumerate([('Other renewed','0.55'),('Chronic renewed','k')]):
        xs=[k for k in ks if k<0]; ax.plot(xs,[t[str(k)][j] for k in xs],marker='o',ms=3,color=st,lw=1.2,label=nm)
        xs=[k for k in ks if k>0]; ax.plot(xs,[t[str(k)][j] for k in xs],marker='o',ms=3,color=st,lw=1.2)
    ax.axhline(H[c]['es']['never_rel'],color='k',ls='--',lw=0.9,label='Chronic never renewed')
    ax.axhline(1,color='0.7',lw=0.6,ls=':'); ax.axvline(0,color='0.7',lw=0.6)
    ax.set_title(lab[c],fontsize=9); ax.set_xlabel("Years since renewal")
axs[0].set_ylabel("Requests relative to class average"); axs[0].legend(frameon=False,fontsize=7,loc='upper left')
fig.tight_layout(); fig.savefig("out/figs/Fig2.png",dpi=300); fig.savefig("out/figs/Fig2.pdf"); fig.savefig("out/figs/Fig2.tif",dpi=600,pil_kwargs={'compression':'tiff_lzw'})
# Fig 3 Minneapolis PCI
t=pd.read_csv("out/mpls_pci_bins.csv",index_col=0)
fig,ax=plt.subplots(figsize=(4.5,2.6)); x=np.arange(len(t))
ax.bar(x-0.18,t['False'],0.36,color='0.7',label='Other segments'); ax.bar(x+0.18,t['True'],0.36,color='0.2',label='Chronic segments')
ax.set_xticks(x); ax.set_xticklabels(['Q1\n(PCI 3–64)','Q2\n(65–78)','Q3\n(79–94)','Q4\n(95–105)'])
ax.set_ylabel("Requests per 100 m per year,\n2020–2025"); ax.set_xlabel("Pavement condition index quartile (inspections 2010–2014)")
ax.legend(frameon=False,fontsize=7.5)
fig.tight_layout(); fig.savefig("out/figs/Fig3.png",dpi=300); fig.savefig("out/figs/Fig3.pdf"); fig.savefig("out/figs/Fig3.tif",dpi=600,pil_kwargs={'compression':'tiff_lzw'})
print("ok")
