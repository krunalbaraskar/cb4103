"""Full-cache analysis, sampling diagnostics and machine-readable summaries."""
from pathlib import Path
import json, time, importlib.metadata
import numpy as np
from .trajectory import write_json,conversion_settings
from .correlation import correlations,running_integral,fit_decay,autocorrelation_direct

CURVES=['smor','connected_self','cor','collective_self','collective_cross','uncentered_collective']
LIMITATIONS=[
 'Force field, unit style, integration timestep, charges, temperature, ensemble and dump-group completeness are unavailable.',
 'Normalized bisectors are identical-dipole geometric proxies; nearly rigid geometry does not prove physical charge-site provenance.',
 'All lags, fitted scales and truncated integrals are in simulation steps; no ps conversion or dielectric constant is justified.',
 'Full relaxation integrals are not certified converged. Fits describe specified windows and correlated residuals have no IID confidence interval.',
 'Four temporal blocks give variation, not a calibrated confidence interval. Collective signal has one summed vector per frame.',
 'Molecular and collective finite-sample mean subtraction can bias long-lag correlations; alternative centering and segments are shown.',
 'Spatial profiles and orientation traces cannot establish temperature/energy equilibration without simulation logs.',
 'Finite-cell factor B(0)/A(0) uses molecular time-mean centering and is not automatically a macroscopic Kirkwood factor.',
 'Trajectory may be a selected atom group; no bulk-water, droplet, substrate or hydrate identity is established.'
]

def write_curves(path,r,cadence):
    lag=r['lag_index']*cadence
    data=np.column_stack([lag]+[r[k] for k in CURVES]+[r['origins']]+[running_integral(r[k],lag) for k in CURVES[:5]])
    header=','.join(['lag_steps']+CURVES+['origins']+['integral_'+k+'_steps' for k in CURVES[:5]])
    np.savetxt(path,data,delimiter=',',header=header,comments='',fmt='%.12g')

def record(r,cadence,c):
    lag=r['lag_index']*cadence
    cutoff={}
    for cutoff_step in c['cutoff_steps']:
        if cutoff_step <= lag[-1]:
            cutoff[str(cutoff_step)]={k:float(np.interp(cutoff_step,lag,running_integral(r[k],lag))) for k in CURVES[:5]}
    tail={}
    for k in ['smor','connected_self','cor']:
        arr=r[k];integral=running_integral(arr,lag)
        cross=np.flatnonzero(arr<=0)
        tail[k]=dict(last_value=float(arr[-1]),last_20_percent_mean=float(arr[int(.8*len(arr)):].mean()),
            last_20_percent_min=float(arr[int(.8*len(arr)):].min()),last_20_percent_max=float(arr[int(.8*len(arr)):].max()),
            last_20_percent_integral_drift_steps=float(integral[-1]-integral[int(.8*len(arr))]),
            first_zero_crossing_steps=int(lag[cross[0]]) if len(cross) else None)
    return dict(**r['stats'],max_lag_steps=int(lag[-1]),minimum_origins=int(r['origins'][-1]),
                truncated_integrals_steps=cutoff,tail_diagnostics=tail,
                fits={k:fit_decay(lag,r[k],c['fit_window_steps']) for k in ['smor','connected_self','cor']})

def analyze(c):
    t0=time.perf_counter();cache=Path(c['cache']);out=Path('results');out.mkdir(exist_ok=True)
    meta=json.loads((cache/'complete.json').read_text())
    if conversion_settings(meta['config']) != conversion_settings(c):raise ValueError('Cache/config mismatch')
    write_json(out/'metadata.json',meta)
    if c['discard_frames'] != 0:
        raise ValueError('Primary analysis retains all frames; use the automatic initial-10%-removed sensitivity for equilibration sensitivity.')
    u=np.load(cache/'orientations.npy',mmap_mode='r')
    steps=np.load(cache/'steps.npy',mmap_mode='r')
    cadence=int(np.diff(steps)[0])
    if not np.all(np.diff(steps)==cadence):raise ValueError('Actual cache cadence is nonuniform')
    full=correlations(u[c['discard_frames']:],c['max_lag_frames'],c['molecule_batch'])
    write_curves(out/'correlations.csv',full,cadence)
    np.save(out/'total_orientation.npy',full['U'])
    np.savez_compressed(out/'correlation_arrays.npz',**{k:full[k] for k in CURVES+['A','B','R','lag_index','origins']})
    summary=dict(analysis_config=c,definitions=dict(G_cell='B(0)/A(0); A=sum_i <(u_i-mean_i)(0) dot (u_i-mean_i)(lag)>; B=<(U-mean_U)(0) dot (U-mean_U)(lag)>',
        origins='All F-k pairs in each analyzed segment, with means estimated once over that segment',
        ordinary_smor='sum_i <u_i(0) dot u_i(lag)> / N',connected_self='A(lag)/A(0)',
        cor='B(lag)/B(0)',collective_self='A(lag)/B(0)',collective_cross='[B(lag)-A(lag)]/B(0)',
        integral='Trapezoidal running integral in simulation steps; finite cutoff values only'),
        full=record(full,cadence,c),limitations=LIMITATIONS,retained_frames=len(u)-c['discard_frames'],
        discard_frames=c['discard_frames'],time_unit='simulation steps',
        fit_adequacy_screen='Unweighted a exp(-lag/tau); entire fixed window positive, span >=0.05, RMSE <0.03, R2>0.95, tau <=2*window width. Descriptive only.',
        block_uncertainty='Four nonoverlapping contiguous blocks. Range/variation only, no standard errors or confidence intervals.')
    segments={}
    F=len(u)
    definitions=[('half_1',0,F//2),('half_2',F//2,F)]
    edges=np.linspace(0,F,c['blocks']+1,dtype=int)
    definitions += [(f'quarter_{j+1}',int(edges[j]),int(edges[j+1])) for j in range(c['blocks'])]
    definitions += [('discard_first_10_percent',F//10,F)]
    for name,a,b in definitions:
        lagmax=min(c['max_lag_frames'],(b-a-1)//10)
        print('Analyzing',name,a,b,'maxlag',lagmax,flush=True)
        r=correlations(u[a:b],lagmax,c['molecule_batch'])
        write_curves(out/(name+'.csv'),r,cadence)
        segments[name]=record(r,cadence,c)|dict(first_frame=a,last_frame_exclusive=b,first_step=int(steps[a]),last_step=int(steps[b-1]))
    print('Analyzing every second saved frame',flush=True)
    down=correlations(u[::2],c['max_lag_frames']//2,c['molecule_batch'])
    write_curves(out/'downsample_2.csv',down,2*cadence)
    summary['segments']=segments
    summary['downsample_2']=record(down,2*cadence,c)
    summary['downsample_max_abs_difference']={k:float(np.max(np.abs(full[k][::2]-down[k]))) for k in CURVES}
    summary['centering_sensitivity']=dict(
        max_abs_ordinary_minus_connected=float(np.max(np.abs(full['smor']-full['connected_self']))),
        max_abs_centered_minus_uncentered_collective=float(np.max(np.abs(full['cor']-full['uncentered_collective']))),
        relative_total_mean_square=float(np.sum(np.mean(full['U'],axis=0)**2)/full['stats']['B0']))
    checks=empirical_checks(u,c)
    write_json(out/'numerical_checks.json',checks)
    geo=np.load(cache/'geometry.npy',mmap_mode='r');sp=np.load(cache/'spatial_counts.npy',mmap_mode='r')
    profiles=sp.mean(axis=0,dtype=np.float64)/(u.shape[1]/c['spatial_bins'])
    summary['spatial_diagnostics']=dict(normalization='Mean center count per fractional bin divided by N/bins; uniform expectation 1',
        profiles_relative_to_uniform=profiles.tolist(),max_abs_deviation_from_uniform_by_axis=np.max(np.abs(profiles-1),axis=1).tolist())
    blocks=[]
    for j in range(c['blocks']):
        a,b=edges[j:j+2];U=full['U'][a:b]
        p=sp[a:b].mean(axis=0,dtype=np.float64)/(u.shape[1]/c['spatial_bins'])
        blocks.append(dict(block=j+1,frames=int(b-a),first_step=int(steps[a]),last_step=int(steps[b-1]),
            mean_U=U.mean(axis=0).tolist(),variance_U=U.var(axis=0).tolist(),mean_bond=float(geo[a:b,2].mean()),
            mean_angle_degrees=float(geo[a:b,6].mean()),mean_mic_fraction=float(geo[a:b,10].mean()),
            spatial_max_abs_deviation_from_uniform=np.max(np.abs(p-1),axis=1).tolist()))
    summary['stationarity_blocks']=blocks
    # A full-time estimate requires evidence beyond a numerical plateau on one window.
    summary['relaxation_convergence']=dict(full_integral_resolved=False,full_tau_smor_steps=None,full_tau_cor_steps=None,
        ratio_tau_cor_to_smor=None,reason='Finite lag cutoff, temporally correlated origins, centering and segment sensitivity are explicitly inspected; no validated tail extrapolation or independent-run uncertainty establishes a converged full integral.',
        reported='Truncated integrals at declared cutoffs and screened descriptive fit scales only')
    summary['quarter_G_range']=[float(min(segments[f'quarter_{j+1}']['G_cell'] for j in range(c['blocks']))),
                                float(max(segments[f'quarter_{j+1}']['G_cell'] for j in range(c['blocks'])))]
    summary['versions']={p:importlib.metadata.version(p) for p in ['corsmor','numpy','scipy','matplotlib','pytest','reportlab','python-pptx','pymupdf','psutil']}
    summary['analysis_seconds']=time.perf_counter()-t0
    meta['software_versions']=summary['versions']
    write_json(out/'metadata.json',meta)
    write_json(out/'summary.json',summary)
    print('Analysis complete:',json.dumps(dict(G_cell=summary['full']['G_cell'],tail=summary['full']['tail_diagnostics'],checks=checks)),flush=True)
    return summary

def empirical_checks(u,c):
    tiny=np.asarray(u[:128,:24],dtype=np.float64)
    fft=correlations(tiny,35,batch=7)
    direct=correlations(tiny,35,batch=11,method='direct')
    errors={k:float(np.max(np.abs(fft[k]-direct[k]))) for k in CURVES}
    x=np.asarray(u[:32,:8],dtype=np.float64);v=x-x.mean(axis=0)
    r=correlations(x,12,batch=3)
    pair=[]
    for k in range(13):
        value=0.
        for t in range(len(x)-k):
            for i in range(8):
                for j in range(8):
                    if i!=j:value+=float(v[t,i]@v[t+k,j])
        pair.append(value/(len(x)-k)/r['B'][0])
    error=float(np.max(np.abs(np.array(pair)-r['collective_cross'])))
    return dict(actual_cache_subset_frames=128,actual_cache_subset_molecules=24,fft_direct_max_abs_error=errors,
                explicit_pair_subset_frames=32,explicit_pair_subset_molecules=8,explicit_ordered_cross_pair_max_abs_error=error,
                tolerance=1e-10,overall_pass=bool(max(errors.values())<1e-10 and error<1e-10))
