from pathlib import Path
import argparse
from collections import Counter
import runpy, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, FancyArrowPatch, Polygon
from rdkit import Chem
from rdkit.Chem import Draw

PARSER = argparse.ArgumentParser(
    description="Rebuild the TCM-QM v1.1 manuscript figures from a frozen data release."
)
PARSER.add_argument("release_dir", type=Path, help="Path to the data_release directory")
PARSER.add_argument("output_dir", type=Path, help="Directory for 400-dpi PNG figures")
PARSER.add_argument(
    "--vector-output-dir",
    type=Path,
    default=None,
    help="Optional directory for PDF and SVG figures; defaults to output_dir",
)
ARGS = PARSER.parse_args()

ROOT=Path(__file__).resolve().parent
BASE={}
DATA=ARGS.release_dir.resolve(); TABLES=DATA/'tables'; ML=DATA/'machine_learning'
OUT=ARGS.output_dir.resolve(); VEC=(ARGS.vector_output_dir or OUT).resolve()
OUT.mkdir(parents=True,exist_ok=True); VEC.mkdir(parents=True,exist_ok=True)
NAVY='#173B57'; TEAL='#23858C'; CORAL='#D0644C'; GOLD='#D8A63B'; SAGE='#79A89B'; LILAC='#8065A8'; INK='#17242D'; GRAY='#61717B'; LINE='#DCE4E7'; PALE='#F5F8F8'; PAPER='#FFFFFF'
GREEN=NAVY
plt.rcParams.update({'font.family':'Arial','font.size':8.2,'axes.titlesize':9.4,'axes.titleweight':'bold','axes.labelsize':8.2,'axes.linewidth':.75,'axes.edgecolor':'#9AA8AF','axes.labelcolor':INK,'xtick.color':GRAY,'ytick.color':GRAY,'xtick.labelsize':7.1,'ytick.labelsize':7.1,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white','legend.fontsize':7.2,'lines.solid_capstyle':'round'})
df=pd.read_csv(TABLES/'tcm_qm_master.csv',encoding='utf-8-sig',low_memory=False,dtype={'cid':str})

def save(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=400,bbox_inches='tight',pad_inches=.045,facecolor='white')
    fig.savefig(VEC/f'{name}.pdf',bbox_inches='tight',pad_inches=.045,facecolor='white')
    fig.savefig(VEC/f'{name}.svg',bbox_inches='tight',pad_inches=.045,facecolor='white'); plt.close(fig)
def panel(ax,lbl,title):
    ax.text(-.11,1.075,lbl,transform=ax.transAxes,color=INK,fontsize=10.2,weight='bold',va='top')
    ax.set_title(title,loc='left',pad=6,color=INK)
def formula_counts():
    c=Counter()
    for f in df.molecular_formula.fillna(''):
        for e in set(re.findall(r'[A-Z][a-z]?',f)): c[e]+=1
    return c
def smooth_density(x,bins=100):
    x=np.asarray(pd.to_numeric(pd.Series(x),errors='coerce').dropna()); hist,edges=np.histogram(x,bins=bins,density=True); k=np.exp(-.5*(np.arange(-6,7)/2.2)**2); k/=k.sum(); return (edges[:-1]+edges[1:])/2,np.convolve(hist,k,mode='same')

def fig1():
    flow=pd.read_csv(TABLES/'selection_flow_summary.csv',encoding='utf-8-sig')
    f=dict(zip(flow.step_id,flow.record_count))
    fig=plt.figure(figsize=(7.15,5.1)); gs=fig.add_gridspec(2,2,hspace=.48,wspace=.40)
    stage_labels=['Candidate','Normalized','Qualified','Released']
    values=np.array([f['F0'],f['F0b'],f['F4'],f['F6']],dtype=float)
    x=np.arange(4)
    stage_colors=[LILAC,'#9D87BC',TEAL,'#69A9A8']

    ax=fig.add_subplot(gs[0,0])
    bars=ax.bar(x,values,color=stage_colors,width=.62,edgecolor='white',lw=.7)
    ax.set_xticks(x,stage_labels,rotation=18,ha='right'); ax.set_ylabel('Records')
    ax.set_ylim(0,7700); panel(ax,'a','Records at each selection stage')
    for b,v in zip(bars,values):
        ax.text(b.get_x()+b.get_width()/2,v+145,f'{int(v):,}',ha='center',va='bottom',
                fontsize=8.0,weight='bold',color=INK)
    ax.grid(axis='y',color=LINE,lw=.6); ax.set_axisbelow(True)

    ax=fig.add_subplot(gs[0,1])
    retained=values/values[0]*100
    ax.plot(x,retained,color=TEAL,lw=1.9,marker='o',ms=5.8,mfc='white',mec=TEAL,mew=1.5)
    ax.set_xticks(x,stage_labels,rotation=18,ha='right'); ax.set_ylabel('Candidate records retained (%)')
    ax.set_ylim(38,104); panel(ax,'b','Cumulative retention')
    for xx,pct in zip(x,retained):
        ax.text(xx,pct+3.0,f'{pct:.1f}%',ha='center',fontsize=7.8,weight='bold',color=INK)
    ax.grid(axis='y',color=LINE,lw=.6); ax.set_axisbelow(True)

    ax=fig.add_subplot(gs[1,0])
    item_labels=['Incomplete opt./frequency','Qualified duplicate','Imaginary modes','Not converged']
    counts=np.array([f['F1'],f['F5'],f['F2'],f['F3']],dtype=float)
    y=np.arange(len(counts)); cols=[CORAL,GOLD,'#B77C78','#87969C']
    ax.barh(y,counts,color=cols,height=.56,edgecolor='white',lw=.6)
    ax.set_yticks(y,item_labels); ax.invert_yaxis(); ax.set_xscale('log'); ax.set_xlim(8,5200)
    ax.set_xlabel('Records (log scale)'); panel(ax,'c','Exclusion and non-selection counts')
    for yy,v in zip(y,counts):
        ax.annotate(f'{int(v):,}',(v,yy),xytext=(5,0),textcoords='offset points',va='center',
                    fontsize=7.8,weight='bold',color=INK)
    ax.grid(axis='x',color=LINE,lw=.6); ax.set_axisbelow(True)
    ax.spines['left'].set_visible(False); ax.tick_params(axis='y',length=0)

    ax=fig.add_subplot(gs[1,1])
    losses=np.maximum(values[:-1]-values[1:],0)
    loss_labels=['CID\nnormalization','Quality\nadjudication','Final CID\nselection']
    bars=ax.bar(np.arange(3),losses,color=['#B9A9CC',CORAL,GOLD],width=.58,edgecolor='white',lw=.7)
    ax.set_xticks(np.arange(3),loss_labels); ax.set_ylabel('Reduction in records')
    ax.set_ylim(0,max(losses)*1.23); panel(ax,'d','Stage-to-stage reduction')
    for b,v in zip(bars,losses):
        ax.text(b.get_x()+b.get_width()/2,v+55,f'−{int(v):,}',ha='center',va='bottom',
                fontsize=8.0,weight='bold',color=INK)
    ax.grid(axis='y',color=LINE,lw=.6); ax.set_axisbelow(True)
    save(fig,'Fig1_evidence_chain')

def fig2():
    split=pd.read_csv(ML/'split_assignments.csv',encoding='utf-8-sig',dtype={'cid':str})
    sc=split[split.repeat==1].drop_duplicates('cid').scaffold.fillna('ACYCLIC').value_counts()
    fig=plt.figure(figsize=(7.15,5.55)); gs=fig.add_gridspec(2,2,hspace=.43,wspace=.34)
    ax=fig.add_subplot(gs[0,0]); ax.axis('off'); panel(ax,'a','Ten most frequent Bemis–Murcko scaffolds')
    top=sc.head(10)
    for i,(smi,count) in enumerate(top.items()):
        rr,cc=divmod(i,5); ia=ax.inset_axes([cc*.2+.008,.53-rr*.48,.184,.39]); ia.axis('off'); ia.set_facecolor(PALE)
        mol=Chem.MolFromSmiles(smi); img=Draw.MolToImage(mol,size=(300,220),kekulize=True) if mol else None
        if img is not None: ia.imshow(img)
        ia.add_patch(Rectangle((0,0),1,1,transform=ia.transAxes,fill=False,ec='#E5EAEC',lw=.55))
        ia.text(.5,-.02,f'{count:,}',transform=ia.transAxes,ha='center',va='top',fontsize=7.8,weight='bold',color=INK)
    ax=fig.add_subplot(gs[0,1]); rank=np.arange(1,len(sc)+1); ax.plot(rank,sc.values,color=GREEN,lw=1.8); ax.fill_between(rank,sc.values,color=TEAL,alpha=.16); ax.set_yscale('log'); ax.set_xlabel('Scaffold rank'); ax.set_ylabel('Molecules'); panel(ax,'b','Scaffold-frequency distribution'); ax.grid(color=LINE,lw=.6)
    singleton=(sc==1).sum(); ax.text(.97,.94,f'{len(sc):,} unique scaffolds\n{singleton:,} singletons ({singleton/len(sc):.1%})',transform=ax.transAxes,ha='right',va='top',color=INK,fontsize=9,weight='bold')
    ax=fig.add_subplot(gs[1,0]); x,y=smooth_density(df.molecular_mass_amu,80); ax.fill_between(x,y,color=LILAC,alpha=.45); ax.plot(x,y,color='#7D5A99',lw=1.8); med=pd.to_numeric(df.molecular_mass_amu).median(); ax.axvline(med,color=CORAL,ls='--'); ax.set_xlabel('Molecular mass (u)'); ax.set_ylabel('Density'); panel(ax,'c','Molecular-mass distribution'); ax.text(.98,.9,f'median = {med:.1f} u',transform=ax.transAxes,ha='right',color=GRAY); ax.grid(axis='y',color=LINE,lw=.6)
    ax=fig.add_subplot(gs[1,1]); xlog=pd.to_numeric(df.pubchem_XLogP,errors='coerce'); tpsa=pd.to_numeric(df.pubchem_TPSA,errors='coerce'); m=xlog.notna()&tpsa.notna(); h=ax.hexbin(xlog[m],tpsa[m],gridsize=42,mincnt=1,cmap='YlGnBu',linewidths=0); ax.set_xlabel('PubChem XLogP'); ax.set_ylabel('Topological polar surface area (Å²)'); panel(ax,'d','Lipophilicity–polarity distribution'); cb=fig.colorbar(h,ax=ax,pad=.015); cb.set_label('Molecules per hexagon'); ax.text(.98,.96,f'n = {m.sum():,}',transform=ax.transAxes,ha='right',va='top',color=GRAY)
    save(fig,'Fig2_chemical_space')

def fig3():
    panels=[('homo_lumo_gap_ev','HOMO-LUMO gap','eV',TEAL),('dipole_magnitude_debye','Dipole magnitude','Debye',CORAL),('zpe_eh','Zero-point energy','Eh',GOLD),('final_entropy_term_eh','Entropy term T·S','Eh',GREEN),('lowest_positive_frequency_cm1','Lowest positive frequency','cm$^{-1}$',SAGE),('highest_frequency_cm1','Highest frequency','cm$^{-1}$','#B98269')]
    fig,axs=plt.subplots(2,3,figsize=(7.15,4.55),constrained_layout=True)
    for i,(ax,(col,title,unit,color)) in enumerate(zip(axs.flat,panels)):
        vals=pd.to_numeric(df[col],errors='coerce').dropna(); x,y=smooth_density(vals,110); ax.fill_between(x,y,color=color,alpha=.18); ax.plot(x,y,color=color,lw=1.75); q1,med,q3=np.quantile(vals,[.25,.5,.75]); ax.axvspan(q1,q3,color=color,alpha=.08); ax.axvline(med,color=INK,ls=(0,(3,2)),lw=.8); ax.set_xlabel(unit); ax.set_ylabel('Density'); panel(ax,chr(97+i),title)
        tx,ha=(.04,'left') if i==5 else (.96,'right')
        ax.text(tx,.91,f'n={len(vals):,}\nmedian {med:.3g}\nIQR {q1:.3g}–{q3:.3g}',transform=ax.transAxes,ha=ha,va='top',fontsize=6.3,color=GRAY)
        ax.grid(axis='y',color=LINE,lw=.5); ax.set_axisbelow(True)
    save(fig,'Fig3_quantum_property_atlas')

def fig4():
    geo=pd.read_csv(DATA/'audits'/'initial_geometry_pubchem3d_full_results_frozen.csv',encoding='utf-8-sig',dtype={'cid':str})
    fig,axs=plt.subplots(2,2,figsize=(7.15,5.15),constrained_layout=True)
    ax=axs[0,0]; labels=['Normal termination','Optimization converged','Frequency analysis','Zero imaginary']; vals=np.array([3196,3196,3196,3191]); pct=vals/3196*100; y=np.arange(4)
    ax.hlines(y,99.6,pct,color='#D9E8E8',lw=4); ax.scatter(pct,y,s=68,c=[TEAL,TEAL,TEAL,GOLD],edgecolor='white',lw=.8,zorder=3)
    ax.set_xlim(99.6,100.04); ax.set_yticks(y,labels); ax.invert_yaxis(); ax.set_xlabel('Records passing (%)'); panel(ax,'a','Calculation completeness')
    for yi,p,v in zip(y,pct,vals): ax.text(p-.012,yi,f'{v:,}',ha='right',va='center',fontsize=8.5,weight='bold'); ax.grid(axis='x',color=LINE,lw=.6)
    ax=axs[0,1]; labels=['Coordinate identity','Minor relaxation','Similar conformer','Stereo repair']; vals=[3158,35,2,1]
    bars=ax.barh(np.arange(4),vals,color=[TEAL,GOLD,CORAL,LILAC],height=.62); ax.set_xscale('log'); ax.set_xlim(.7,5000); ax.set_yticks(np.arange(4),labels); ax.invert_yaxis(); ax.set_xlabel('Records'); panel(ax,'b','Starting-geometry provenance')
    for b,v in zip(bars,vals): ax.text(v*1.08,b.get_y()+b.get_height()/2,f'{v:,}',va='center',weight='bold',fontsize=9); ax.grid(axis='x',color=LINE,lw=.6)
    ax=axs[1,0]; rms=pd.to_numeric(geo.loc[geo.comparison_status=='direct_atom_order','heavy_atom_rmsd_angstrom'],errors='coerce').dropna(); nz=np.sort(rms[rms>.02]); ecdf=np.arange(1,len(nz)+1)/len(nz)
    ax.step(nz,ecdf,where='post',color=TEAL,lw=2); ax.fill_between(nz,ecdf,step='post',color=TEAL,alpha=.16); ax.scatter(nz,ecdf,s=16,color=TEAL,alpha=.55); ax.set_xlim(.02,.45); ax.set_ylim(0,1.04); ax.set_xlabel('Heavy-atom RMSD (Å)'); ax.set_ylabel('Empirical cumulative fraction'); panel(ax,'c','Non-identity RMSD'); ax.grid(color=LINE,lw=.6)
    ax=axs[1,1]; imag=df[pd.to_numeric(df.imaginary_frequency_count,errors='coerce')==1].sort_values('lowest_frequency_cm1'); yy=pd.to_numeric(imag.lowest_frequency_cm1).to_numpy(); xx=np.arange(len(yy))
    ax.vlines(xx,0,yy,color='#DEA391',lw=2.2); ax.scatter(xx,yy,s=58,color=CORAL,edgecolor='white',lw=.8,zorder=3); ax.axhline(0,color=INK,lw=.8); ax.set_xticks(xx,imag.cid); ax.set_ylabel('Lowest frequency (cm$^{-1}$)'); panel(ax,'d','Minor negative modes')
    for xi,v in zip(xx,yy): ax.text(xi,v-.12,f'{v:.2f}',ha='center',va='top',fontsize=8.5); ax.grid(axis='y',color=LINE,lw=.6)
    save(fig,'Fig4_quality_control')

def rain(ax,groups,labels,title,unit,letter):
    rng=np.random.default_rng(20260905)
    vp=ax.violinplot(groups,positions=[1,2],showextrema=False,widths=.78)
    for body,c in zip(vp['bodies'],[GREEN,TEAL]): body.set_facecolor(c); body.set_alpha(.68); body.set_edgecolor('none')
    bp=ax.boxplot(groups,positions=[1,2],widths=.16,patch_artist=True,showfliers=False,medianprops={'color':CORAL,'lw':1.5},boxprops={'facecolor':'white','edgecolor':INK},whiskerprops={'color':INK},capprops={'color':INK})
    for i,g in enumerate(groups,1):
        take=np.asarray(g)[rng.choice(len(g),min(180,len(g)),replace=False)]; ax.scatter(i+rng.normal(0,.035,len(take)),take,s=3,color=INK,alpha=.16,zorder=0)
    ax.set_xticks([1,2],labels); ax.set_ylabel(unit); panel(ax,letter,title); ax.grid(axis='y',color=LINE,lw=.6)

def fig5():
    vers=['6.0.1','6.1.1']; fig=plt.figure(figsize=(7.15,3.15)); gs=fig.add_gridspec(1,3,width_ratios=[.72,1.18,1.18],wspace=.42)
    ax=fig.add_subplot(gs[0]); cnt=df.orca_version.value_counts(); vals=np.array([cnt[v] for v in vers]); bars=ax.bar(vers,vals,color=['#8F6DB2','#C2ADD8'],width=.58,edgecolor='white',lw=.8); ax.set_ylabel('Records'); panel(ax,'a','ORCA version counts'); ax.grid(axis='y',color=LINE,lw=.6)
    for b,v in zip(bars,vals): ax.text(b.get_x()+b.get_width()/2,v+45,f'{v:,}',ha='center',weight='bold',fontsize=9)
    for j,(col,title,unit) in enumerate([('homo_lumo_gap_ev','HOMO-LUMO gap','eV'),('dipole_magnitude_debye','Dipole magnitude','Debye')],1):
        bx=fig.add_subplot(gs[j])
        for v,c in zip(vers,['#765394',TEAL]):
            a=pd.to_numeric(df.loc[df.orca_version==v,col],errors='coerce').dropna(); xx,yy=smooth_density(a,90); bx.fill_between(xx,yy,color=c,alpha=.13); bx.plot(xx,yy,color=c,lw=1.8,label=v)
        bx.set_xlabel(unit); bx.set_ylabel('Density'); panel(bx,chr(97+j),title); bx.grid(axis='y',color=LINE,lw=.6); bx.legend(frameon=False,fontsize=8)
    save(fig,'Fig5_software_provenance')

def fig6():
    g=pd.read_csv(ML/'metrics_summary.csv',encoding='utf-8-sig'); g=g[(g.split_type=='random_grouped')&(g.model=='extra_trees_morgan2_2d')]; s=pd.read_csv(ML/'scaffold_uncertainty'/'scaffold_split_uncertainty_summary.csv',encoding='utf-8-sig'); s=s[s.model=='extra_trees_morgan2_2d']
    gr=pd.read_csv(ML/'metrics_all_runs.csv',encoding='utf-8-sig'); gr=gr[(gr.split_type=='random_grouped')&(gr.model=='extra_trees_morgan2_2d')]
    sr=pd.read_csv(ML/'scaffold_uncertainty'/'scaffold_split_uncertainty_runs.csv',encoding='utf-8-sig'); sr=sr[sr.model=='extra_trees_morgan2_2d']
    order=['homo_lumo_gap_ev','dipole_magnitude_debye','gibbs_correction_eh','highest_frequency_cm1']; labels=['HOMO-LUMO gap','Dipole magnitude','Gibbs correction','Highest frequency']; gm=[];gsd=[];sm=[];ssd=[]
    for t in order:
        a=g[g.target==t].iloc[0]; b=s[s.target==t].iloc[0]; gm.append(a.r2_mean);gsd.append(a.r2_sd);sm.append(b.r2_mean);ssd.append(b.r2_sd)
    fig,axs=plt.subplots(2,2,figsize=(7.15,5.0),constrained_layout=True)
    rng=np.random.default_rng(20260907)
    for i,(ax,target,label) in enumerate(zip(axs.flat,order,labels)):
        a=gr.loc[gr.target==target,'r2'].to_numpy(); b=sr.loc[sr.target==target,'r2'].to_numpy(); groups=[a,b]
        vp=ax.violinplot(groups,positions=[0,1],showextrema=False,widths=.72)
        for body,c in zip(vp['bodies'],['#8F6DB2',TEAL]): body.set_facecolor(c); body.set_alpha(.28); body.set_edgecolor(c); body.set_linewidth(1)
        ax.boxplot(groups,positions=[0,1],widths=.18,patch_artist=True,showfliers=False,medianprops={'color':CORAL,'lw':1.4},boxprops={'facecolor':'white','edgecolor':INK},whiskerprops={'color':INK},capprops={'color':INK})
        for j,z in enumerate(groups): ax.scatter(j+rng.normal(0,.035,len(z)),z,s=11,color=['#765394',TEAL][j],alpha=.55,zorder=2)
        ax.set_xticks([0,1],['Connectivity-grouped','Scaffold-held-out']); ax.set_ylim(max(-.05,min(a.min(),b.min())-.05),1.03); ax.set_ylabel('Test R$^2$'); panel(ax,chr(97+i),label); ax.grid(axis='y',color=LINE,lw=.6)
    save(fig,'Fig6_ml_readiness')

def fig7():
    edges=pd.read_csv(TABLES/'tcm_source_edges.csv',encoding='utf-8-sig',dtype={'cid':str})
    prov=pd.read_csv(TABLES/'tcm_source_provenance.csv',encoding='utf-8-sig',dtype={'cid':str})
    herb_degree=edges.groupby('herb_id').cid.nunique().sort_values(ascending=False)
    cid_degree=edges.groupby('cid').herb_id.nunique().sort_values(ascending=False)
    fig=plt.figure(figsize=(7.15,5.05)); gs=fig.add_gridspec(2,2,hspace=.48,wspace=.38)

    ax=fig.add_subplot(gs[0,0]); top=herb_degree.head(12).sort_values(); names=list(top.index)
    bar_cols=[SAGE]*len(top); bar_cols[-3:]=[TEAL,TEAL,NAVY]
    ax.barh(np.arange(len(top)),top.values,color=bar_cols,height=.62,edgecolor='white',lw=.4); ax.set_yticks(np.arange(len(top)),names); ax.set_xlabel('Unique linked CIDs'); panel(ax,'a','Highest-degree herbs'); ax.grid(axis='x',color=LINE,lw=.6)

    ax=fig.add_subplot(gs[0,1]); bins=np.arange(1,cid_degree.max()+2)-.5
    ax.hist(cid_degree.values,bins=bins,color=TEAL,alpha=.82,edgecolor='white',lw=.5); ax.set_yscale('log'); ax.set_xlim(.5,min(cid_degree.max()+.5,90.5)); ax.set_xlabel('Herbs linked per CID'); ax.set_ylabel('CIDs'); panel(ax,'b','CID-degree distribution'); ax.grid(axis='y',color=LINE,lw=.6)

    ax=fig.add_subplot(gs[1,0]); x=np.sort(herb_degree.values); cum=np.cumsum(x)/x.sum(); pop=np.arange(1,len(x)+1)/len(x)
    ax.plot([0,*pop],[0,*cum],color=CORAL,lw=2.2); ax.plot([0,1],[0,1],ls='--',color='#91A0A6',lw=1.2); ax.fill_between([0,*pop],[0,*cum],[0,*pop],color=CORAL,alpha=.12)
    ax.set_xlabel('Cumulative share of herbs'); ax.set_ylabel('Cumulative share of herb–CID edges'); ax.set_xlim(0,1); ax.set_ylim(0,1); panel(ax,'c','Edge concentration'); ax.grid(color=LINE,lw=.6)
    gini=(2*np.sum(np.arange(1,len(x)+1)*x)/(len(x)*np.sum(x)))-(len(x)+1)/len(x)
    ax.text(.05,.91,f'Gini = {gini:.3f}',transform=ax.transAxes,weight='bold',fontsize=10,color=INK)

    ax=fig.add_subplot(gs[1,1]); rank=np.arange(1,len(herb_degree)+1)
    ax.plot(rank,herb_degree.values,color=NAVY,lw=1.9); ax.fill_between(rank,herb_degree.values,color=TEAL,alpha=.14)
    ax.set_xlabel('Herb rank'); ax.set_ylabel('Unique linked CIDs'); ax.set_yscale('log'); panel(ax,'d','Rank-degree distribution'); ax.grid(color=LINE,lw=.6)
    save(fig,'Fig7_data_architecture')

if __name__=='__main__':
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7()
    print('visual-v3',sorted(p.name for p in OUT.glob('Fig*.png')))
