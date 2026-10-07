"""Conditional effects, post-review sensitivity, hindsight regret, and figures."""
import csv,json
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'revision'
TEXT={'group','setting','family','method'}
def read(path):
    with Path(path).open() as f:rows=list(csv.DictReader(f))
    for r in rows:
        for k,v in r.items():
            if k not in TEXT:
                if v in ('True','False'):r[k]=v=='True'
                else:r[k]=float(v)
    return rows
def boot(a):
    a=np.asarray(a,dtype=float)
    if not len(a):return [None,None,None]
    rng=np.random.default_rng(31415)
    means=a[rng.integers(len(a),size=(10000,len(a)))].mean(axis=1)
    return [float(a.mean()),*map(float,np.quantile(means,[.025,.975]))]
def avg(a):return float(np.mean(a)) if len(a) else None
def writecsv(name,rows):
    if not rows:return
    flat=[]
    for row in rows:
        out={}
        for key,value in row.items():
            if isinstance(value,list) and len(value)==3:
                for suffix,v in zip(('mean','ci95_low','ci95_high'),value):out[key+'_'+suffix]=v
            elif isinstance(value,list) and len(value)==2:
                for suffix,v in zip(('low','high'),value):out[key+'_'+suffix]=v
            else:out[key]=value
        flat.append(out)
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)

def analyze():
    rows=read(OUT/'runs.csv');items=read(OUT/'items.csv')
    rows+=read(OUT/'break_even_runs.csv');items+=read(OUT/'break_even_items.csv')
    groups=defaultdict(list)
    for r in rows:groups[(r['group'],r['setting'],r['family'],r['N'])].append(r)
    effects=[];decisions=[];summaries=[];decomp=[];headroom=[];penalties=[];perseed=[]
    for (group,setting,family,N),rs in groups.items():
        meta=dict(group=group,setting=setting,family=family,N=int(N))
        methods=sorted({r['method'] for r in rs});maps={m:{r['seed']:r for r in rs if r['method']==m} for m in methods}
        pas=maps['passive'];pro=maps['always_probe']
        for method in methods:
            a=list(maps[method].values());success=[r for r in a if r['success']]
            reached=[r for r in a if r['decision_reached']]
            covm=sum(int(r['mass_covered']) for r in a);covj=sum(int(r['inertia_covered']) for r in a)
            ci=binomtest(covm,len(a)).proportion_ci();cij=binomtest(covj,len(a)).proportion_ci()
            summaries.append(dict(**meta,method=method,n=len(a),success=len(success),reached=len(reached),
                probes=sum(int(r['probes']) for r in a),success_robot_mean_s=avg([r['robot_time_s'] for r in success]),
                J_mean_s=avg([r['J'] for r in a]),mass_coverage_count=covm,inertia_coverage_count=covj,
                mass_coverage_ci95=[ci.low,ci.high],inertia_coverage_ci95=[cij.low,cij.high],mean_planner_ms=avg([r['planning_s']*1000 for r in a]),
                cap_binding_count=sum(int(r['cap_count']) for r in a),schedules=sum(int(r['schedules']) for r in a),
                max_margin_s=max(r['max_margin_s'] for r in a),
                mean_rounding_residual_s=avg([r['mean_rounding_residual_s'] for r in success])))
            if method!='passive':
                pairs=[(r,pas[r['seed']]) for r in a]
                common=[(r,b) for r,b in pairs if r['success'] and b['success']]
                reachedpairs=[(r,b) for r,b in pairs if r['decision_reached'] and b['decision_reached']]
                effects.append(dict(**meta,method=method,common_success_n=len(common),decision_reached_n=len(reachedpairs),
                    conditional_robot_difference_mean_ci95_s=boot([r['robot_time_s']-b['robot_time_s'] for r,b in common]),
                    reached_robot_difference_mean_ci95_s=boot([r['robot_time_s']-b['robot_time_s'] for r,b in reachedpairs]),
                    method_only_failures=sum(int(not r['success'] and b['success']) for r,b in pairs),
                    passive_only_failures=sum(int(r['success'] and not b['success']) for r,b in pairs),
                    unconditional_J_difference_mean_ci95_s=boot([r['J']-b['J'] for r,b in pairs])))
                for r,b in pairs:
                    perseed.append(dict(**meta,method=method,seed=int(r['seed']),both_success=int(r['success'] and b['success']),
                        both_decision_reached=int(r['decision_reached'] and b['decision_reached']),robot_difference_s=r['robot_time_s']-b['robot_time_s']))
            if method!='oracle':
                valid=[r for r in a if r['decision_reached'] and pas[r['seed']]['decision_reached'] and pro[r['seed']]['decision_reached']]
                regret=[];correct=0;beneficial=0;sensitivity_num=0;negatives=0;specificity_num=0
                for r in valid:
                    p=pas[r['seed']];b=pro[r['seed']]
                    cp=p['robot_time_s']+10*(N-p['completed']);cb=b['robot_time_s']+10*(N-b['completed'])
                    chosen=r['robot_time_s']+10*(N-r['completed'])
                    regret.append(chosen-min(cp,cb))
                    if cb<cp-.002:
                        beneficial+=1;sensitivity_num+=int(r['probes']);correct+=int(r['probes'])
                    elif cp<cb-.002:
                        negatives+=1;specificity_num+=1-int(r['probes']);correct+=1-int(r['probes'])
                    else:correct+=1
                decisions.append(dict(**meta,method=method,decision_n=len(valid),beneficial_probe_n=beneficial,
                    harmful_probe_n=negatives,correct_n=correct,sensitivity_numerator=sensitivity_num,
                    specificity_numerator=specificity_num,mean_regret_ci95_s=boot(regret),max_regret_s=max(regret,default=None)))
            for penalty in (1,5,10,30):
                penalties.append(dict(**meta,method=method,penalty_per_unfinished_item_s=penalty,
                    mean_cost_s=avg([r['robot_time_s']+r['planning_s']+penalty*(N-r['completed']) for r in a])))
        common=[seed for seed in pas if pas[seed]['success'] and pro[seed]['success']]
        decomp.append(dict(**meta,common_success_n=len(common),
            probe_elapsed_mean_s=avg([pro[s]['probe_s'] for s in common]),
            downstream_saved_mean_s=avg([pas[s]['robot_time_s']-(pro[s]['robot_time_s']-pro[s]['probe_s']) for s in common]),
            net_extra_mean_ci95_s=boot([pro[s]['robot_time_s']-pas[s]['robot_time_s'] for s in common]),
            probe_max_acceleration_ratio=max((pro[s]['probe_acceleration_ratio'] for s in pro if pro[s]['probes']),default=None)))
        if 'oracle' in maps:
            o=maps['oracle'];com=[s for s in pas if pas[s]['success'] and o[s]['success']]
            headroom.append(dict(**meta,common_success_n=len(com),
                passive_minus_known_payload_mean_ci95_s=boot([pas[s]['robot_time_s']-o[s]['robot_time_s'] for s in com]),
                note='Empirical diagnostic gap, not a universal upper bound on achievable savings.'))
    forecast=[]
    for family in ('excited','low_yaw'):
        a=[r for r in items if r['group']=='extended' and r['N']==100 and r['method']=='passive' and r['family']==family]
        for parameter in ('mass','inertia'):
            for predicted in ('pred','rollout'):
                ratios=[r[f'{predicted}_sd_{parameter}']/r[f'sd_{parameter}'] for r in a]
                forecast.append(dict(family=family,parameter=parameter,prediction=predicted,item_observations=len(a),
                    median_predicted_over_realized_sd=float(np.median(ratios)),
                    mean_absolute_log_ratio=float(np.mean(np.abs(np.log(ratios)))),
                    note='Repeated items within 27 successful seeds; descriptive forecast diagnostics, not independent samples.'))
    report=dict(total_post_review_batches=len(rows),total_item_records=len(items),
        summaries=summaries,effects=effects,decomposition=decomp,headroom=headroom,
        decisions=decisions,forecast=forecast,penalties=penalties,
        reviewer_corrections=dict(prior_margin_s=.16*.5+.16*np.sqrt(.008/.020),
            noiseless_startup_mass_threshold_kg=(.8*9.81-.8*5)/(9.81+5),
            probe_mass_regressor='g times window duration even without vertical motion',
            noise_binomial='Deterministic response to random draws still induces a success probability under the stated sampling distribution; not industrial reliability.'))
    (OUT/'analysis.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    writecsv('conditional_effects.csv',effects);writecsv('decomposition.csv',decomp)
    writecsv('headroom.csv',headroom);writecsv('decision_quality.csv',decisions)
    writecsv('conditional_summary.csv',summaries);writecsv('per_seed_differences.csv',perseed)
    writecsv('penalty_sensitivity.csv',penalties);writecsv('forecast_diagnostics.csv',forecast)
    from .revision_legacy import run as legacy
    legacy()
    from .revision_tables import make
    make(report)
    figures(rows,items,report)
    print(f'Analyzed {len(rows)} post-review batches, {len(items)} per-item records.',flush=True)

def figures(rows,items,s):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    def save(fig,name):
        fig.savefig(OUT/f'{name}.png',bbox_inches='tight');fig.savefig(OUT/f'{name}.pdf',bbox_inches='tight');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(9,3.2),layout='constrained')
    for ax,fam in zip(axs,('excited','low_yaw')):
        a=[r for r in s['decomposition'] if r['group']=='extended' and r['family']==fam]
        ax.plot([r['N'] for r in a],[r['probe_elapsed_mean_s'] for r in a],'o-',label='Probe elapsed')
        ax.plot([r['N'] for r in a],[r['downstream_saved_mean_s'] for r in a],'s-',label='Downstream saved')
        ax.plot([r['N'] for r in a],[r['net_extra_mean_ci95_s'][0] for r in a],'^-',label='Net extra time')
        ax.axhline(0,c='gray',lw=.7);ax.set(xlabel='Items in batch',title=fam.replace('_',' '));ax.grid(alpha=.15)
    axs[0].set_ylabel('Seconds per jointly successful batch');axs[1].legend(fontsize=8)
    save(fig,'decomposition')
    fig,axs=plt.subplots(1,2,figsize=(9,3.3),layout='constrained')
    for ax,setting in zip(axs,('base','noise10')):
        for method,marker in [('passive','o'),('always_probe','s'),('batch_aware','^'),('ignore_passive','D')]:
            a=sorted([r for r in s['decisions'] if r['setting']==setting and r['family']=='low_yaw' and r['method']==method],key=lambda r:r['N'])
            ax.plot([r['N'] for r in a],[r['mean_regret_ci95_s'][0] for r in a],marker+'-',label=method.replace('_',' '),alpha=.8)
        ax.set(xlabel='Items in batch',title='Nominal low yaw' if setting=='base' else 'Noise ×10; low yaw');ax.grid(alpha=.15)
    axs[0].set_ylabel('Mean two-action hindsight regret (s)');axs[1].legend(fontsize=8)
    save(fig,'decision_regret')
    fig,axs=plt.subplots(1,2,figsize=(9,3.3),layout='constrained')
    a=sorted([r for r in s['decomposition'] if r['setting']=='noise10' and r['family']=='low_yaw'],key=lambda r:r['N'])
    xx=[r['N'] for r in a];yy=[r['net_extra_mean_ci95_s'][0] for r in a]
    lo=[r['net_extra_mean_ci95_s'][1] for r in a];hi=[r['net_extra_mean_ci95_s'][2] for r in a]
    axs[0].errorbar(xx,yy,yerr=[np.array(yy)-lo,np.array(hi)-yy],fmt='o-',capsize=3,label='Realized probe minus passive')
    pred=[avg([-r['gain_s'] for r in rows if r['setting']=='noise10' and r['family']=='low_yaw' and r['N']==N and r['method']=='batch_aware' and r['decision_reached']]) for N in xx]
    axs[0].plot(xx,pred,'s--',label='Fixed-mean predicted net cost')
    axs[0].axhline(0,c='gray',lw=.7);axs[0].set(xlabel='Items in batch',ylabel='Seconds per decision-reaching batch',title='Noise ×10; low yaw');axs[0].legend(fontsize=8)
    for method,marker in [('passive','o'),('always_probe','s'),('batch_aware','^'),('ignore_passive','D')]:
        d=sorted([r for r in s['decisions'] if r['setting']=='noise10' and r['family']=='low_yaw' and r['method']==method],key=lambda r:r['N'])
        axs[1].plot([r['N'] for r in d],[r['mean_regret_ci95_s'][0] for r in d],marker+'-',label=method.replace('_',' '),alpha=.8)
    axs[1].set(xlabel='Items in batch',ylabel='Mean two-action hindsight regret (s)',title='Decision quality');axs[1].legend(fontsize=8)
    for ax in axs:ax.grid(alpha=.15)
    save(fig,'break_even')
    fig,axs=plt.subplots(1,2,figsize=(9,3.4),layout='constrained')
    for ax,par in zip(axs,('mass','inertia')):
        for prediction,label,style in [('','Realized','-'),('rollout_','Fixed-mean rollout','--'),('pred_','One-transfer forecast',':')]:
            a=[r for r in items if r['group']=='extended' and r['N']==100 and r['method']=='passive' and r['family']=='low_yaw']
            xs=sorted({r['item'] for r in a});y=[np.median([r[f'{prediction}sd_{par}'] for r in a if r['item']==k]) for k in xs]
            ax.semilogy(xs,y,style,label=label)
        ax.set(xlabel='Loaded transfer index',ylabel=f'{par.capitalize()} uncertainty scale ('+('kg' if par=='mass' else 'kg m²')+')',title='Low-yaw task; median across surviving seeds')
        from matplotlib.ticker import LogLocator,LogFormatterSciNotation
        ax.yaxis.set_major_locator(LogLocator(base=10,subs=(1,2,5)))
        ax.yaxis.set_major_formatter(LogFormatterSciNotation(base=10,labelOnlyBase=False,minor_thresholds=(np.inf,np.inf)))
        ax.grid(alpha=.15,which='both')
    axs[1].legend(fontsize=8);save(fig,'forecast_check')
    fig,axs=plt.subplots(1,2,figsize=(9,4.2),layout='constrained')
    for ax,fam in zip(axs,('excited','low_yaw')):
        settings=[];values=[];labels=[]
        for setting in ['base','noise10','noise100','margin_half','margin2','margin4','inflation4','inflation64','probe_fast','probe_slow']:
            a=[r for r in s['decomposition'] if r['setting']==setting and r['family']==fam and r['N']==60]
            if not a:continue
            r=a[0]
            if setting=='base':
                baseline={x['seed']:x for x in rows if x['setting']=='base' and x['family']==fam and x['N']==60 and x['method']=='passive' and x['seed']<=1010}
                active=[x for x in rows if x['setting']=='base' and x['family']==fam and x['N']==60 and x['method']=='always_probe' and x['seed']<=1010]
                differences=[x['robot_time_s']-baseline[x['seed']]['robot_time_s'] for x in active if x['success'] and baseline[x['seed']]['success']]
                value=avg(differences);n=len(differences)
            else:value=r['net_extra_mean_ci95_s'][0];n=r['common_success_n']
            settings.append(setting);values.append(value);labels.append(f'{setting} (n={n})')
        for i,v in enumerate(values):
            if v is not None:ax.scatter(v,i,c='#147d92' if v>=0 else '#c24e33',s=35)
            else:ax.text(.02,i,'no joint success',fontsize=8)
        ax.axvline(0,c='gray',lw=.7);ax.set(yticks=range(len(labels)),yticklabels=labels,xlabel='Probe minus passive (s)',title=fam.replace('_',' '));ax.invert_yaxis()
    save(fig,'sensitivity')
    fig,ax=plt.subplots(figsize=(6.5,3.2),layout='constrained')
    for i,N in enumerate((1,5,20,40,60,100)):
        a=[r for r in rows if r['group']=='extended' and r['family']=='low_yaw' and r['N']==N and r['method']=='always_probe']
        b={r['seed']:r for r in rows if r['group']=='extended' and r['family']=='low_yaw' and r['N']==N and r['method']=='passive'}
        vals=[r['robot_time_s']-b[r['seed']]['robot_time_s'] for r in a if r['success'] and b[r['seed']]['success']]
        ax.scatter(i+np.linspace(-.16,.16,len(vals)),vals,s=16,alpha=.6,color='#147d92')
    ax.axhline(0,c='gray',lw=.7);ax.set(xticks=range(6),xticklabels=[1,5,20,40,60,100],xlabel='Items in batch',ylabel='Probe minus passive (s)',title='Low yaw: each point is one jointly successful scenario')
    save(fig,'per_seed_effects')

if __name__=='__main__':analyze()
