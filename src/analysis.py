"""Paired scenario-level bootstrap, figures and machine-readable summaries."""
import csv,json
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .experiment import METHODS

LABELS={'fixed_nominal':'Fixed nominal','passive':'Passive learning','always_probe':'Always probe',
        'batch_aware':'Batch aware','ignore_passive':'Ignore passive learning','oracle':'Known payload'}

def read(path):
    with path.open(encoding='utf-8') as f: rows=list(csv.DictReader(f))
    for r in rows:
        for k in r:
            if k not in ('family','method'):r[k]=float(r[k])
    return rows

def bootstrap(x,seed=806):
    x=np.asarray(x);rng=np.random.default_rng(seed)
    means=x[rng.integers(0,len(x),size=(10000,len(x)))].mean(axis=1)
    return [float(np.mean(x)),*map(float,np.quantile(means,[.025,.975]))]

def analyze(outdir):
    outdir=Path(outdir); rows=read(outdir/'batches.csv');summary=[];comparisons=[]
    for family in ('excited','low_yaw'):
        for N in (1,5,20):
            cond=[r for r in rows if r['family']==family and r['N']==N]
            base={r['seed']:r for r in cond if r['method']=='passive'}
            for method in METHODS:
                a=[r for r in cond if r['method']==method];n=len(a)
                ok=sum(int(r['success']) for r in a);ci=binomtest(ok,n).proportion_ci()
                summary.append(dict(family=family,N=N,method=method,n=n,success=ok,
                    success_ci95=[ci.low,ci.high],mean_robot_time_s=float(np.mean([r['robot_time_s'] for r in a])),
                    mean_penalized_time_s=float(np.mean([r['penalized_time_s'] for r in a])),
                    mean_planning_ms=float(np.mean([r['planning_s']*1000 for r in a])),
                    probes=sum(int(r['probes']) for r in a),
                    mass_rmse_kg=float(np.sqrt(np.mean([(r['estimate_mass']-r['true_mass'])**2 for r in a]))),
                    inertia_rmse_kgm2=float(np.sqrt(np.mean([(r['estimate_inertia']-r['true_inertia'])**2 for r in a]))),
                    mass_coverage=float(np.mean([r['mass_covered'] for r in a])),
                    inertia_coverage=float(np.mean([r['inertia_covered'] for r in a]))))
                if method!='passive':
                    physical=[r['robot_time_s']-base[r['seed']]['robot_time_s'] for r in a]
                    primary=[r['penalized_time_s']-base[r['seed']]['penalized_time_s'] for r in a]
                    comparisons.append(dict(family=family,N=N,method=method,
                        robot_difference_mean_ci95_s=bootstrap(physical),
                        penalized_difference_mean_ci95_s=bootstrap(primary)))
    stress=[]
    if (outdir/'stress.csv').exists():
        sr=read(outdir/'stress.csv')
        for family in ('excited','low_yaw'):
            for method in METHODS:
                a=[r for r in sr if r['family']==family and r['method']==method]
                stress.append(dict(family=family,method=method,n=len(a),success=sum(int(r['success']) for r in a),
                    mass_coverage=float(np.mean([r['mass_covered'] for r in a])),
                    inertia_coverage=float(np.mean([r['inertia_covered'] for r in a])),
                    mean_time_s=float(np.mean([r['penalized_time_s'] for r in a]))))
    report=dict(total_batches=len(rows),total_completed_items=sum(int(r['completed']) for r in rows),
                summary=summary,paired_comparisons=comparisons,stress=stress,
                note='Condition-level intervals use 30 paired scenario seeds; same seeds recur across N/families. Hardware-dependent planning times are not bitwise reproducible.')
    (outdir/'summary.json').write_text(json.dumps(report,indent=2))
    with (outdir/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    fig,axs=plt.subplots(1,2,figsize=(8,3.2),sharey=True)
    colors=['#5c677d','#0077b6','#e76f51','#2a9d8f','#9b5de5','#343a40']
    for ax,family in zip(axs,('excited','low_yaw')):
        for method,color in zip(METHODS,colors):
            a=[s for s in summary if s['family']==family and s['method']==method]
            ax.plot([s['N'] for s in a],[s['mean_penalized_time_s']/s['N'] for s in a],
                    'o-',label=LABELS[method],color=color,markersize=4,alpha=.85)
        ax.set(title='Yaw-exciting task' if family=='excited' else 'Low-yaw task',xlabel='Items in batch',xticks=[1,5,20])
        ax.grid(alpha=.15)
    axs[0].set_ylabel('Penalized seconds per requested item')
    fig.legend(*axs[0].get_legend_handles_labels(),loc='lower center',ncol=3,bbox_to_anchor=(.5,-.01),fontsize=8)
    fig.tight_layout(rect=(0,.15,1,1));fig.savefig(outdir/'batch_cost.png');fig.savefig(outdir/'batch_cost.pdf');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(8,3.1))
    for ax,family in zip(axs,('excited','low_yaw')):
        for i,method in enumerate(('always_probe','batch_aware','ignore_passive')):
            a=[s for s in comparisons if s['family']==family and s['method']==method]
            v=np.array([s['robot_difference_mean_ci95_s'] for s in a]);x=np.arange(3)+(i-1)*.15
            ax.errorbar(x,v[:,0],yerr=np.maximum(np.array([v[:,0]-v[:,1],v[:,2]-v[:,0]]),0),
                        fmt='o',capsize=3,label=LABELS[method])
        ax.axhline(0,color='gray',lw=.8);ax.set(xticks=range(3),xticklabels=['1','5','20'],xlabel='Items in batch',title=family.replace('_',' '))
    axs[0].set_ylabel('Robot time minus passive (s / batch)')
    fig.legend(*axs[0].get_legend_handles_labels(),loc='lower center',ncol=3,fontsize=8)
    fig.tight_layout(rect=(0,.1,1,1));fig.savefig(outdir/'paired_differences.png');fig.savefig(outdir/'paired_differences.pdf');plt.close(fig)
    tr=json.loads((outdir/'batches_traces.json').read_text())
    fig,axs=plt.subplots(1,2,figsize=(8,3.1))
    for method in ('passive','always_probe','batch_aware'):
        a=np.array(tr[f'low_yaw_20_{method}'])
        if len(a):
            axs[0].plot(a[:,0],a[:,1],'o-',markersize=3,label=LABELS[method])
            axs[1].semilogy(a[:,0],a[:,5],'o-',markersize=3,label=LABELS[method])
    axs[0].set(xlabel='Completed loaded transfer',ylabel='Scheduled duration (s)')
    axs[1].set(xlabel='Completed loaded transfer',ylabel='Approximate inertia standard deviation')
    fig.legend(*axs[0].get_legend_handles_labels(),loc='lower center',ncol=3,fontsize=8)
    fig.tight_layout(rect=(0,.1,1,1));fig.savefig(outdir/'learning_trace.png');fig.savefig(outdir/'learning_trace.pdf');plt.close(fig)
    print(f'Analyzed {len(rows)} main batches; figures and summary saved in {outdir}')
