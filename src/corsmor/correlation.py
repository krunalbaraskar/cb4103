"""Origin-count-normalized autocorrelations; no circular FFT wraparound."""
import numpy as np
from scipy.fft import rfft, irfft, next_fast_len
from scipy.integrate import cumulative_trapezoid
from scipy.optimize import curve_fit

def autocorrelation_fft(x, max_lag):
    """Sum channel autocovariances (input already centered if desired)."""
    x=np.asarray(x,dtype=np.float64)
    if x.ndim == 1: x=x[:,None]
    F=len(x)
    if not 0 <= max_lag < F: raise ValueError('Lag outside trace')
    p=next_fast_len(2*F-1)
    z=rfft(x,n=p,axis=0,workers=1)
    power=(z.real*z.real+z.imag*z.imag).sum(axis=tuple(range(1,z.ndim)))
    return irfft(power,n=p)[:max_lag+1]/np.arange(F,F-max_lag-1,-1,dtype=np.float64)

def autocorrelation_direct(x,max_lag):
    x=np.asarray(x,dtype=np.float64)
    return np.array([np.sum(x[:len(x)-k]*x[k:],dtype=np.float64)/(len(x)-k) for k in range(max_lag+1)])

def correlations(u,max_lag,batch=64,method='fft'):
    """Global means over retained segment; all F-k origins at lag k.

    Ordinary self uses uncentered molecular unit vectors. Connected self uses
    each molecule's full segment mean. Collective always subtracts the total
    segment mean; B-A is exact with those same means/origins.
    """
    F,N,_=u.shape
    ac=autocorrelation_fft if method == 'fft' else autocorrelation_direct
    R=np.zeros(max_lag+1,dtype=np.float64)
    A=R.copy()
    U=np.zeros((F,3),dtype=np.float64)
    mean_square_sum=0.
    norm_error=0.
    for first in range(0,N,batch):
        x=np.asarray(u[:,first:first+batch],dtype=np.float64)
        norm_error=max(norm_error,float(np.max(np.abs(np.linalg.norm(x,axis=2)-1))))
        U+=x.sum(axis=1,dtype=np.float64)
        R+=ac(x,max_lag)
        mean=x.mean(axis=0,dtype=np.float64)
        mean_square_sum+=float(np.sum(mean*mean))
        A+=ac(x-mean,max_lag)
    Braw=ac(U,max_lag)
    delta=U-U.mean(axis=0)
    B=ac(delta,max_lag)
    if A[0] <= 1e-20 or B[0] <= 1e-20:
        raise ValueError('Connected self or collective variance is zero; normalized relaxation is undefined')
    G=B[0]/A[0]
    return dict(smor=R/N,connected_self=A/A[0],cor=B/B[0],collective_self=A/B[0],
                collective_cross=(B-A)/B[0],uncentered_collective=Braw/Braw[0],
                lag_index=np.arange(max_lag+1),origins=F-np.arange(max_lag+1),
                A=A,B=B,R=R,U=U,stats=dict(frames=F,molecules=N,G_cell=float(G),
                A0=float(A[0]),B0=float(B[0]),ordinary_A0=float(R[0]),
                molecular_mean_square_per_molecule=mean_square_sum/N,
                total_mean=U.mean(axis=0).tolist(),total_variance_components=np.mean(delta*delta,axis=0).tolist(),
                raw_collective_mean_square=float(Braw[0]),G_raw=float(Braw[0]/R[0]),
                G_centered_over_N=float(B[0]/N),max_unit_norm_error=norm_error,
                decomposition_max_abs_error=float(np.max(np.abs(B/B[0]-(A/B[0]+(B-A)/B[0]))))))

def running_integral(c,lag):
    return cumulative_trapezoid(c,lag,initial=0.)

def fit_decay(lag,c,window):
    """Descriptive unweighted exponential fit with explicit adequacy checks.

    Correlated residuals preclude usual IID confidence intervals. A fitted
    tau is never automatically accepted as a full relaxation time.
    """
    mask=(lag>=window[0])&(lag<=window[1])
    x,y=np.asarray(lag)[mask],np.asarray(c)[mask]
    output=dict(window_steps=list(window),model='a * exp(-lag/tau)',points=int(len(x)),
                interpretation='descriptive window fit; no IID uncertainty or full-time convergence implied')
    if len(x)<10 or np.min(y)<=0 or np.max(y)-np.min(y)<0.05:
        return output|dict(supported=False,reason='Window includes nonpositive values or insufficient resolved decay')
    try:
        par,_=curve_fit(lambda t,a,tau:a*np.exp(-t/tau),x,y,p0=(1.,max(float(x[-1])/2,1)),
                        bounds=([0.,float(np.min(np.diff(lag)))/10],[2.,100*float(lag[-1])]),maxfev=5000)
        pred=par[0]*np.exp(-x/par[1])
        rmse=float(np.sqrt(np.mean((y-pred)**2)))
        r2=float(1-np.sum((y-pred)**2)/np.sum((y-y.mean())**2))
        adequate=bool(rmse<0.03 and r2>0.95 and par[1] <= 2*(x[-1]-x[0]))
        return output|dict(supported=adequate,amplitude=float(par[0]),tau_steps=float(par[1]),rmse=rmse,r_squared=r2,
                           reason='Passes descriptive residual/span screen' if adequate else 'Residuals or extrapolation fail descriptive adequacy screen')
    except (ValueError,RuntimeError) as exc:
        return output|dict(supported=False,reason=str(exc))
