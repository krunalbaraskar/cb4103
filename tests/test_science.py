import io
from pathlib import Path
import numpy as np
import pytest
from corsmor.trajectory import read_frame,molecule_mapping,reconstruct,TrajectoryError,load_config
from corsmor.correlation import correlations,autocorrelation_fft,autocorrelation_direct

CFG=load_config()

# Build a small byte string in LAMMPS dump format from supplied atom rows. Allow the timestep,
# box header, and columns to vary for parser tests.
def dump(rows,step=0,box='ITEM: BOX BOUNDS pp pp pp',columns='id mol type x y z'):
    return (f'ITEM: TIMESTEP\n{step}\nITEM: NUMBER OF ATOMS\n{len(rows)}\n{box}\n0 10\n0 10\n0 10\nITEM: ATOMS {columns}\n'+'\n'.join(rows)+'\n').encode()

# Create and parse a three-atom fixture with shuffled, nonconsecutive IDs and bonds split across
# periodic boundaries.
def frame():
    # Nonconsecutive atom/molecule IDs, shuffled rows, both bonds split over PBC.
    return read_frame(io.BytesIO(dump(['90 17 1 0.477350269 0.71649658 9.9',
      '3 17 2 9.9 9.9 9.9','55 17 1 0.477350269 9.08350342 9.9'])))

# Reconstruct the shuffled fixture and compare its molecule ID, direction, bond length, and
# angle with known values. Check that its center wraps into the fractional box.
def test_periodic_unsorted_geometry():
    f=frame(); membership,mols,groups=molecule_mapping(f)
    u,frac,g=reconstruct(f,groups,CFG)
    np.testing.assert_allclose(u,[[1,0,0]],atol=1e-8)
    np.testing.assert_array_equal(mols,[17])
    np.testing.assert_allclose(g[2],1,atol=1e-7)
    np.testing.assert_allclose(g[6],109.4712206,atol=1e-5)
    assert g[10]==1
    assert np.all((frac>=0)&(frac<1))

# Feed the parser each malformed or unsupported frame from the parametrized cases and require a
# trajectory error.
@pytest.mark.parametrize('blob',[
 b'ITEM: TIMESTEP\n0\n',
 dump(['1 1 2 1 1 1','1 1 1 2 1 1','3 1 1 1 2 1']),
 dump(['1 1 2 nan 1 1']),
 dump(['1.5 1 2 1 1 1']),
 dump(['1 1 2 1 1 1 extra']),
 dump(['1 1 2 1 1 1'],box='ITEM: BOX BOUNDS xy xz yz pp pp pp'),
 dump(['1 1 2 1 1 1'],columns='id mol type xs ys zs'),
 b'garbage\n',
 dump(['1 1 2 1 1 1']).replace(b'0 10',b'10 0'),
 dump(['1 1 2 1 1 1']).replace(b'1 1 2 1 1 1',b'1 1 2 x 1 1')])
def test_bad_frame_rejected(blob):
    with pytest.raises(TrajectoryError): read_frame(io.BytesIO(blob))

# Check that an empty stream signals a clean end of file and that molecule mapping rejects a
# group missing one of its required atoms.
def test_clean_eof_and_incomplete_membership():
    assert read_frame(io.BytesIO(b'')) is None
    f=read_frame(io.BytesIO(dump(['1 1 2 1 1 1','2 1 1 2 1 1'])))
    with pytest.raises(TrajectoryError): molecule_mapping(f)

# Place a satellite on top of its central atom and verify that reconstruction rejects the
# resulting zero-length bond.
def test_zero_bond_rejected():
    f=frame(); _,_,g=molecule_mapping(f)
    f['data'][g[0,1],3:]=f['data'][g[0,0],3:]
    with pytest.raises(TrajectoryError):reconstruct(f,g,CFG)

# Compare both correlation algorithms with hand-computed values at every lag in a four-sample
# trace, including the final lag with a single valid pair.
def test_fft_direct_known_origin_counts():
    # Analytic lag sums: 85/4, 42/3, 20/2, 8/1. Last lag tests zero-padding.
    x=np.array([1,2,4,8.])
    expected=[85/4,42/3,20/2,8]
    np.testing.assert_allclose(autocorrelation_fft(x,3),expected,rtol=1e-14)
    np.testing.assert_allclose(autocorrelation_direct(x,3),expected,rtol=1e-14)

# Generate a unit vector that rotates by a fixed angle per frame and check that ordinary SMOR
# matches the cosine of each angular lag.
def test_known_rotating_orientation():
    theta=np.arange(40)*0.2
    u=np.stack([np.cos(theta),np.sin(theta),np.zeros_like(theta)],axis=1)[:,None,:]
    r=correlations(u,12,batch=1)
    np.testing.assert_allclose(r['smor'],np.cos(np.arange(13)*0.2),atol=1e-14)

# Compare FFT and direct curves for deterministic random unit vectors. Sum ordered cross-
# molecule pairs independently and check the decomposition and zero-lag normalization.
def test_fft_direct_and_explicit_ordered_pairs():
    rng=np.random.default_rng(720)
    u=rng.normal(size=(29,5,3));u/=np.linalg.norm(u,axis=2,keepdims=True)
    f=correlations(u,15,batch=2);d=correlations(u,15,batch=3,method='direct')
    for key in ['smor','connected_self','cor','collective_self','collective_cross','uncentered_collective']:
        np.testing.assert_allclose(f[key],d[key],atol=2e-14)
    v=u-u.mean(axis=0)
    explicit=[]
    for k in range(16):
        value=0.
        for origin in range(len(u)-k):
            for i in range(5):
                for j in range(5):
                    if i!=j:value+=np.dot(v[origin,i],v[origin+k,j])
        explicit.append(value/(len(u)-k)/f['B'][0])
    np.testing.assert_allclose(f['collective_cross'],explicit,atol=2e-14)
    np.testing.assert_allclose(f['collective_self']+f['collective_cross'],f['cor'],atol=2e-14)
    assert abs(f['smor'][0]-1)<1e-14
    assert f['connected_self'][0]==f['cor'][0]==1
    np.testing.assert_allclose(f['collective_self'][0],1/f['stats']['G_cell'])

# Use two nearly opposing orientation histories to check that strong cancellation produces a
# negative cross contribution and preserves the collective sum.
def test_negative_cross_allowed():
    # Two strongly cancelling but unequal orientation histories.
    t=np.arange(71)*0.12
    a=np.stack([np.cos(t),np.sin(t),np.zeros_like(t)],axis=1)
    b=np.stack([-np.cos(t+0.1),-np.sin(t+0.1),np.zeros_like(t)],axis=1)
    r=correlations(np.stack([a,b],axis=1),10)
    assert r['stats']['G_cell']<0.01
    assert r['collective_cross'][0]<-100
    np.testing.assert_allclose(r['collective_cross']+r['collective_self'],r['cor'],atol=1e-12)

# Combine a rotating component with a fixed component and check the analytic curves. Centering
# removes the fixed contribution from connected self while ordinary SMOR retains it.
def test_centering_changes_connected_not_ordinary():
    t=np.arange(64)*2*np.pi/64
    u=np.stack([0.6*np.cos(t),0.6*np.sin(t),np.full_like(t,0.8)],axis=1)[:,None,:]
    r=correlations(u,31)
    np.testing.assert_allclose(r['smor'],0.64+0.36*np.cos(t[:32]),atol=1e-14)
    np.testing.assert_allclose(r['connected_self'],np.cos(t[:32]),atol=1e-14)
    assert abs(r['stats']['molecular_mean_square_per_molecule']-0.64)<1e-14

# Supply constant vectors throughout the trajectory and check that zero centered variance raises
# an error during normalization.
def test_constant_orientation_is_undefined_connected():
    with pytest.raises(ValueError): correlations(np.ones((10,2,3)),3)

# Check the frame count, endpoint steps, and every saved-frame interval in the real trajectory
# cache. Skip when the completed cache is absent.
def test_all_actual_cached_cadence():
    p=Path('cache/complete.json')
    if not p.exists():pytest.skip('Full-data check enabled after conversion')
    steps=np.load('cache/steps.npy',mmap_mode='r')
    assert len(steps)==10001 and steps[0]==0 and steps[-1]==100000
    np.testing.assert_array_equal(np.diff(steps),np.full(10000,10))

# Convert a valid two-frame fixture and verify cache reuse when only an analysis setting
# changes. Then check that bad cadence, changed membership, and a missing frame each cause an
# error.
def test_converter_cadence_membership_and_truncation(tmp_path,monkeypatch):
    from corsmor.trajectory import convert
    monkeypatch.chdir(tmp_path)
    a=['1 1 2 5 5 5','2 1 1 5.577350269 5.81649658 5','3 1 1 5.577350269 4.18350342 5']
    c=CFG|dict(trajectory='input.dump',cache='smallcache',expected_frames=2,expected_atoms=3,
               expected_molecules=1,expected_first_step=0,expected_last_step=10)
    Path('input.dump').write_bytes(dump(a)+dump(a,step=10))
    m=convert(c);assert m['frames']==2 and m['complete_eof']
    assert convert(c|dict(molecule_batch=1))['source']==m['source']
    Path('input.dump').write_bytes(dump(a)+dump(a,step=11))
    with pytest.raises(TrajectoryError):convert(c|dict(cache='badcadence'))
    Path('input.dump').write_bytes(dump(a)+dump([x.replace(' 1 ',' 2 ',1) for x in a],step=10))
    with pytest.raises(TrajectoryError):convert(c|dict(cache='badmembership'))
    Path('input.dump').write_bytes(dump(a))
    with pytest.raises(TrajectoryError):convert(c|dict(cache='missingframe'))

# Reconstruct two molecules supplied out of order, then reorder the dump columns and confirm
# that both inputs give the same orientation vectors.
def test_multiple_unsorted_molecules_and_columns():
    # Molecule 99 appears before 4, atom IDs unrelated to molecule ordering.
    rows=['6 99 1 6.577350269 5.18350342 6','2 4 1 3.577350269 3.81649658 3',
          '90 99 2 6 6 6','70 4 2 3 3 3','4 99 1 6.577350269 6.81649658 6',
          '50 4 1 3.577350269 2.18350342 3']
    f=read_frame(io.BytesIO(dump(rows)));_,m,g=molecule_mapping(f)
    u,_,_=reconstruct(f,g,CFG)
    np.testing.assert_array_equal(m,[4,99]);np.testing.assert_allclose(u,[[1,0,0],[1,0,0]],atol=1e-8)
    # Reader resolves names rather than assuming id/mol/type/x/y/z positions.
    shuffled=[' '.join(np.array(r.split())[[4,0,2,5,1,3]]) for r in rows]
    other=read_frame(io.BytesIO(dump(shuffled,columns='y id type z mol x')))
    _,m2,g2=molecule_mapping(other);u2,_,_=reconstruct(other,g2,CFG)
    np.testing.assert_allclose(u,u2)

# Center a random vector trace and check that the autocorrelation sum vanishes when each lag is
# weighted by its valid frame-pair count.
def test_centered_finite_record_weighted_sum_constraint():
    x=np.random.default_rng(81).normal(size=(51,3));x-=x.mean(axis=0)
    ac=autocorrelation_fft(x,50)
    # Independently follows from |sum_t x_t|^2 = 0, explains centering tails.
    weighted=51*ac[0]+2*np.dot(np.arange(50,0,-1),ac[1:])
    assert abs(weighted)<1e-11

# Use a known exponential to check the running integral and recovered decay time. Also verify
# that a flat curve fails the decay screen.
def test_integral_and_fit_scale():
    from corsmor.correlation import running_integral,fit_decay
    lag=np.arange(0,5001,10);curve=np.exp(-lag/800)
    integral=running_integral(curve,lag)
    np.testing.assert_allclose(integral[-1],800*(1-np.exp(-5000/800)),rtol=2e-5)
    fit=fit_decay(lag,curve,[100,2500])
    assert fit['supported'];assert abs(fit['tau_steps']-800)<1e-6
    assert not fit_decay(lag,np.ones_like(lag),[100,2500])['supported']
