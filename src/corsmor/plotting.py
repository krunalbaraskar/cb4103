"""Publication-style local diagnostic figures, PNG + SVG + PDF."""
from pathlib import Path
import json,os
os.environ.setdefault('MPLCONFIGDIR',str(Path('cache/matplotlib').resolve()))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from .correlation import running_integral

COLORS=dict(smor='#007c91',connected_self='#e69f00',cor='#963b79',collective_self='#007c91',collective_cross='#d35e35',uncentered_collective='#697887')
LABELS=dict(smor='Ordinary rank-one SMOR',connected_self='Connected molecular self',cor='Centered COR',collective_self='Collective self',collective_cross='Collective cross',uncentered_collective='Uncentered collective')

def load_csv(name):return np.genfromtxt(Path('results')/name,delimiter=',',names=True)

def make_figures(c):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':11,'axes.labelsize':10,
        'legend.fontsize':8,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':130,'savefig.dpi':200,
        'grid.alpha':.2,'axes.grid':True,'lines.linewidth':1.7,'pdf.fonttype':42,'svg.fonttype':'none'})
    out=Path('figures');out.mkdir(exist_ok=True)
    s=json.loads(Path('results/summary.json').read_text());meta=json.loads(Path('results/metadata.json').read_text())
    cache=Path(c['cache']);steps=np.load(cache/'steps.npy');geo=np.load(cache/'geometry.npy');sp=np.load(cache/'spatial_counts.npy')
    u=np.load(cache/'orientations.npy',mmap_mode='r');U=np.load('results/total_orientation.npy')
    full=load_csv('correlations.csv');lag=full['lag_steps']
    captions={}
    def save(fig,name,caption):
        fig.tight_layout(pad=1.4)
        for ext in ['png','svg','pdf']:fig.savefig(out/(name+'.'+ext),bbox_inches='tight')
        plt.close(fig);captions[name]=caption
    def xlag(ax):ax.set_xlabel('Lag (simulation steps)');ax.axhline(0,color='#9aa3ad',lw=.65)
    def curves(ax,rows,keys):
        for k in keys:ax.plot(rows['lag_steps'],rows[k],label=LABELS[k],color=COLORS[k])
        xlag(ax);ax.set_ylabel('Normalized correlation');ax.legend(frameon=False)
    fig,ax=plt.subplots(1,3,figsize=(11.4,3.4))
    ax[0].plot([-.8165,0,.8165],[.57735,0,.57735],'o-',color=COLORS['smor'],ms=10)
    ax[0].annotate('u: normalized bond sum',xy=(0,1.05),xytext=(-.85,1.28),fontsize=9)
    ax[0].arrow(0,0,0,.85,width=.013,color=COLORS['cor'],length_includes_head=True)
    ax[0].text(-.95,.52,'type 1',fontsize=9);ax[0].text(.65,.7,'type 1',fontsize=9);ax[0].text(.1,-.05,'type 2',fontsize=9)
    ax[0].set(xlim=(-1.2,1.2),ylim=(-.2,1.5),title='Geometric proxy (schematic)');ax[0].axis('off')
    ax[1].fill_between(steps,geo[:,0],geo[:,1],alpha=.28,color=COLORS['smor'],label='Per-frame min / max')
    ax[1].plot(steps,geo[:,2],color=COLORS['smor'],lw=.6,label='Mean');ax[1].set(xlabel='Saved step',ylabel='Bond length (dump units)',title='All reconstructed bonds');ax[1].ticklabel_format(axis='y',useOffset=False);ax[1].legend(frameon=False)
    ax[2].fill_between(steps,geo[:,4],geo[:,5],alpha=.28,color=COLORS['cor']);ax[2].plot(steps,geo[:,6],color=COLORS['cor'],lw=.6)
    ax[2].set(xlabel='Saved step',ylabel='Internal angle (degrees)',title='All molecular angles');ax[2].ticklabel_format(axis='y',useOffset=False)
    save(fig,'01_geometry','Every reconstructed molecule in every frame contributes to the geometry envelopes. The diagram defines the proxy and is schematic. Type labels are inferred chemistry, not verified force-field provenance.')
    fig,ax=plt.subplots(1,3,figsize=(11.4,3.3));bins=c['spatial_bins'];centers=(np.arange(bins)+.5)/bins
    edges=np.linspace(0,len(steps),5,dtype=int)
    for j in range(3):
        for q in range(4):
            a,b=edges[q:q+2];profile=sp[a:b,j].mean(axis=0)/(u.shape[1]/bins)
            ax[j].plot(centers,profile,label=f'Quarter {q+1}',alpha=.8,lw=1.2)
        ax[j].axhline(1,color='black',ls=':',lw=1);ax[j].set(xlabel=f'Fractional {"xyz"[j]} (periodic)',ylabel='Count / uniform expectation',title=f'Center profile: {"xyz"[j]}')
    ax[0].legend(ncol=2,frameon=False)
    save(fig,'02_spatial_profiles','Center number profiles use fractional periodic positions and 24 bins per axis. Quarter-to-quarter curves show variation; projection uniformity does not prove bulk phase or full-system provenance.')
    fig,ax=plt.subplots(2,1,figsize=(10,5.4))
    for j in range(3):ax[0].plot(steps[::5],U[::5,j],label=f'U{ "xyz"[j]}',lw=.65,alpha=.8)
    for edge in edges[1:-1]:ax[0].axvline(steps[edge],color='gray',lw=.8,ls=':')
    ax[0].set(xlabel='Saved step (every fifth frame shown)',ylabel='Summed unit orientation',title='Collective trace and quarter boundaries');ax[0].legend(ncol=3,frameon=False)
    # Prefix-mean centered finite-cell factor, accumulated in float64 batches.
    T=len(u);counts=np.arange(1,T+1,dtype=np.float64);a_prefix=np.zeros(T)
    for first in range(0,u.shape[1],c['molecule_batch']):
        x=np.asarray(u[:,first:first+c['molecule_batch']],dtype=np.float64)
        cs=np.cumsum(x,axis=0,dtype=np.float64)
        a_prefix+=np.cumsum(np.sum(x*x,axis=(1,2)))/counts-np.sum(cs*cs,axis=(1,2))/(counts*counts)
    b_prefix=np.cumsum(np.sum(U*U,axis=1))/counts-np.sum(np.cumsum(U,axis=0)**2,axis=1)/(counts*counts)
    good=(np.arange(T)>10)&(a_prefix>1e-12)
    g=b_prefix[good]/a_prefix[good];ax[1].plot(steps[good],g,color=COLORS['cor'],label='Prefix-centered G_cell')
    ax[1].axhline(s['full']['G_cell'],color='gray',ls=':',label='Full record');ax[1].set(xlabel='Last included simulation step',ylabel='Finite-cell B(0) / A(0)',title='Accumulated static factor (means reestimated at each prefix)');ax[1].legend(frameon=False)
    np.savetxt('results/prefix_factor.csv',np.column_stack([steps[good],g]),delimiter=',',header='last_step,G_cell_prefix',comments='')
    save(fig,'03_collective_stationarity','Collective components are sampled only for display. The finite-cell factor uses all available frames up to each endpoint with means reestimated; early-prefix changes and block differences diagnose finite sampling, not thermal equilibration.')
    fig,ax=plt.subplots(1,2,figsize=(10.8,3.8))
    for a in ax:curves(a,full,['smor','connected_self','cor'])
    ax[0].set_title('Primary reporting window');ax[1].set_xlim(0,2000);ax[1].set_title('Early-time detail at saved cadence')
    save(fig,'04_smor_cor','Ordinary rank-one SMOR, connected molecular self and centered collective COR use all F-k origins. Full-record reporting lag is at most one tenth of duration. Simulation-step axes cannot be converted to ps without the integration timestep.')
    fig,ax=plt.subplots(1,2,figsize=(10.8,3.8))
    for a in ax:curves(a,full,['cor','collective_self','collective_cross'])
    ax[0].set_title('Exact common-denominator decomposition');ax[1].set_xlim(0,2000);ax[1].set_title('Early-time cancellation / reinforcement')
    save(fig,'05_decomposition','Both self and cross use the same B(0) denominator. Their sum reconstructs centered COR at every lag. Negative cross contributions are retained. The zero-lag self amplitude is 1/G_cell, not one.')
    fig,ax=plt.subplots(1,2,figsize=(10.8,3.9))
    for k in ['smor','connected_self','cor']:
        ax[0].plot(lag,full['integral_'+k+'_steps'],label=LABELS[k],color=COLORS[k])
    for k in ['cor','collective_self','collective_cross']:
        ax[1].plot(lag,full['integral_'+k+'_steps'],label=LABELS[k],color=COLORS[k])
    for a in ax:
        a.set(xlabel='Integration cutoff (simulation steps)',ylabel='Truncated integral (simulation steps)');a.axhline(0,color='gray',lw=.7);a.legend(frameon=False)
        for v in c['cutoff_steps']:a.axvline(v,ls=':',color='gray',lw=.5)
    ax[0].set_title('Running integrals; full times unresolved');ax[1].set_title('Integral self/cross balance')
    save(fig,'06_running_integrals','Trapezoidal integrals depend on the declared upper cutoff. Vertical guides mark saved cutoff estimates. Curves are not certified converged full relaxation times; no tail is extrapolated.')
    fig,ax=plt.subplots(2,2,figsize=(10.8,6.0))
    for j,k in enumerate(['smor','cor']):
        for q in range(4):
            d=load_csv(f'quarter_{q+1}.csv');ax[0,j].plot(d['lag_steps'],d[k],label=f'Quarter {q+1}',lw=1.2)
        for h in range(2):
            d=load_csv(f'half_{h+1}.csv');ax[1,j].plot(d['lag_steps'],d['integral_'+k+'_steps'],label=f'Half {h+1}')
        ax[0,j].plot(lag,full[k],color='black',lw=1.2,ls=':',label='Full record');ax[0,j].set_xlim(0,2490)
        ax[0,j].set_title(LABELS[k]+': quarter variation');ax[0,j].set_ylabel('Normalized correlation');xlag(ax[0,j])
        ax[1,j].set(xlabel='Integration cutoff (simulation steps)',ylabel='Truncated integral (simulation steps)',title=LABELS[k]+': half-record integrals')
        for a in ax[:,j]:a.legend(frameon=False,ncol=2)
    save(fig,'07_block_variation','Nonoverlapping quarters use locally estimated means, with lags <= one tenth of each quarter duration; halves similarly restrict lags. These curves show block variation, not confidence bounds or independent molecular replicates.')
    fig,ax=plt.subplots(1,3,figsize=(11.4,3.5))
    curves(ax[0],full,['smor','connected_self']);ax[0].set_title('Molecular mean subtraction')
    curves(ax[1],full,['cor','uncentered_collective']);ax[1].set_title('Total mean subtraction')
    down=load_csv('downsample_2.csv');trim=load_csv('discard_first_10_percent.csv')
    ax[2].plot(lag,full['cor'],label='Full COR',color=COLORS['cor']);ax[2].plot(down['lag_steps'],down['cor'],label='Every second frame',ls='--',lw=1.1)
    ax[2].plot(trim['lag_steps'],trim['cor'],label='Discard initial 10%',ls=':',lw=1.3)
    xlag(ax[2]);ax[2].set(ylabel='Normalized correlation',title='Cadence and initial-cut sensitivity');ax[2].legend(frameon=False)
    save(fig,'08_sensitivity','Centering is a finite-record convention and can alter long-lag behavior. Downsampling tests sensitivity to saved cadence but cannot recover dynamics faster than ten steps. The initial 10% removal is a sensitivity calculation, not an asserted equilibration cutoff.')
    Path('figures/captions.json').write_text(json.dumps(captions,indent=2),encoding='utf-8')
    print('Created',len(captions),'figures in PNG, SVG, PDF',flush=True)
