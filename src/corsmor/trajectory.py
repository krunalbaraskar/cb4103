"""Strict orthorhombic LAMMPS parser and one-pass, resumable array conversion."""
from __future__ import annotations
import hashlib, json, os, platform, sys, time
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import psutil

class TrajectoryError(ValueError):
    pass

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(temp, path)

def load_config(path='config/analysis.json'):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def read_frame(stream):
    """Read exactly one frame; return None only at clean EOF. Check every row."""
    raw = []
    def line():
        b = stream.readline()
        if not b:
            raise TrajectoryError('Truncated frame at byte ' + str(stream.tell()))
        raw.append(b)
        return b.strip()
    first = stream.readline()
    if not first:
        return None
    raw.append(first)
    if first.strip() != b'ITEM: TIMESTEP':
        raise TrajectoryError('Expected TIMESTEP header')
    try:
        step = int(line())
        if line() != b'ITEM: NUMBER OF ATOMS':
            raise TrajectoryError('Expected NUMBER OF ATOMS')
        n = int(line())
        if n <= 0:
            raise TrajectoryError('Nonpositive atom count')
        if line() != b'ITEM: BOX BOUNDS pp pp pp':
            raise TrajectoryError('Only fully periodic orthorhombic BOX BOUNDS pp pp pp supported')
        bounds = np.array([list(map(float, line().split())) for _ in range(3)])
        if bounds.shape != (3, 2) or not np.isfinite(bounds).all() or np.any(bounds[:, 1] <= bounds[:, 0]):
            raise TrajectoryError('Invalid box bounds')
        header = line().decode('ascii').split()
        if header[:2] != ['ITEM:', 'ATOMS']:
            raise TrajectoryError('Expected ATOMS header')
        columns = header[2:]
        if len(set(columns)) != len(columns) or not set(['id','mol','type','x','y','z']) <= set(columns):
            raise TrajectoryError('Missing or duplicate required atom columns')
        rows = []
        for _ in range(n):
            row = line()
            if len(row.split()) != len(columns):
                raise TrajectoryError('Wrong atom row width')
            rows.append(row)
        with np.errstate(all='raise'):
            data = np.fromstring(b'\n'.join(rows), sep=' ', dtype=np.float64)
        if data.size != n * len(columns):
            raise TrajectoryError('Invalid numeric atom data')
        data = data.reshape(n, len(columns))
        if not np.isfinite(data).all():
            raise TrajectoryError('Nonfinite atom data')
        j = [columns.index(c) for c in ['id','mol','type']]
        integers = data[:, j]
        if np.any(integers != np.floor(integers)) or np.any(integers <= 0) or np.any(integers >= 2**53):
            raise TrajectoryError('Nonpositive, fractional or inexact integer ID/type')
        ids = integers[:, 0].astype(np.int64)
        if np.unique(ids).size != n:
            raise TrajectoryError('Duplicate atom IDs')
        order = np.argsort(ids)
        return dict(step=step, bounds=bounds, columns=columns, data=data[order],
                    digest=hashlib.sha256(b''.join(raw)).hexdigest(), offset=stream.tell())
    except (ValueError, OverflowError, FloatingPointError) as exc:
        if isinstance(exc, TrajectoryError):
            raise
        raise TrajectoryError(str(exc)) from exc

def molecule_mapping(frame, central_type=2, hydrogen_type=1):
    cols, data = frame['columns'], frame['data']
    membership = data[:, [cols.index(c) for c in ['id','mol','type']]].astype(np.int64)
    molecules = np.unique(membership[:, 1])
    groups = []
    # Called once, not once per frame.
    for m in molecules:
        ix = np.flatnonzero(membership[:, 1] == m)
        c = ix[membership[ix, 2] == central_type]
        h = ix[membership[ix, 2] == hydrogen_type]
        if len(ix) != 3 or len(c) != 1 or len(h) != 2:
            raise TrajectoryError('Molecule must have one center and two satellites: ' + str(m))
        groups.append([c[0], h[0], h[1]])
    return membership, molecules, np.array(groups, dtype=np.int64)

def reconstruct(frame, groups, config):
    d, cols = frame['data'], frame['columns']
    xyz = d[:, [cols.index(c) for c in ['x','y','z']]]
    lengths = np.diff(frame['bounds'], axis=1)[:, 0]
    center = xyz[groups[:, 0]]
    raw = xyz[groups[:, 1:]] - center[:, None, :]
    bond = raw - lengths * np.rint(raw / lengths)
    norm = np.linalg.norm(bond, axis=2)
    if np.any(norm <= 0):
        raise TrajectoryError('Zero bond')
    angle = np.degrees(np.arccos(np.clip(np.sum(bond[:,0]*bond[:,1], axis=1) / np.prod(norm, axis=1), -1, 1)))
    total = bond.sum(axis=1)
    mag = np.linalg.norm(total, axis=1)
    if np.any(mag < 1e-10):
        raise TrajectoryError('Undefined bisector')
    if norm.min() < config['bond_range'][0] or norm.max() > config['bond_range'][1]:
        raise TrajectoryError('Bond outside configured proxy geometry range')
    if angle.min() < config['angle_range_degrees'][0] or angle.max() > config['angle_range_degrees'][1]:
        raise TrajectoryError('Angle outside configured proxy geometry range')
    diag = [norm.min(), norm.max(), norm.mean(), norm.std(), angle.min(), angle.max(), angle.mean(), angle.std(),
            mag.mean(), mag.std(), np.mean(np.any(np.abs(raw-bond)>1e-8, axis=(1,2))), mag.min(), mag.max()]
    frac = np.mod((center-frame['bounds'][:,0]) / lengths, 1.)
    return total / mag[:, None], frac, np.array(diag)

def conversion_settings(config):
    keys=['trajectory','cache','expected_frames','expected_atoms','expected_molecules',
          'expected_first_step','expected_last_step','expected_cadence','hydrogen_type',
          'central_type','bond_range','angle_range_degrees','spatial_bins','assumption']
    return {k:config[k] for k in keys}

def convert(config):
    source, cache = Path(config['trajectory']), Path(config['cache'])
    cache.mkdir(exist_ok=True)
    stat = source.stat()
    identity = dict(path=str(source.resolve()), size_bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)
    resources = dict(disk_free_bytes=psutil.disk_usage(str(cache.resolve())).free,
                     ram_total_bytes=psutil.virtual_memory().total, ram_available_bytes=psutil.virtual_memory().available)
    if resources['disk_free_bytes'] < 1200*1024**2:
        raise RuntimeError('Need at least 1.2 GiB free for compact caches and artifacts')
    marker = cache/'checkpoint.json'
    done = cache/'complete.json'
    if done.exists():
        old = json.loads(done.read_text())
        if old['source'] != identity or conversion_settings(old['config']) != conversion_settings(config):
            raise RuntimeError('Completed cache provenance/config differs; use a separate cache path')
        print('Reusing completed validated cache', flush=True)
        return old
    F,N,bins = config['expected_frames'],config['expected_molecules'],config['spatial_bins']
    specs = {'orientations':((F,N,3),'float32'), 'steps':((F,),'int64'), 'box_lengths':((F,3),'float64'),
             'box_lower':((F,3),'float64'), 'geometry':((F,13),'float64'), 'spatial_counts':((F,3,bins),'int32'),
             'frame_sha256':((F,),'S64')}
    resume = json.loads(marker.read_text()) if marker.exists() else None
    if resume and (resume['source'] != identity or conversion_settings(resume['config']) != conversion_settings(config)):
        raise RuntimeError('Partial cache provenance/config differs; use a separate cache path')
    arrays = {k:np.lib.format.open_memmap(cache/(k+'.npy'), mode='r+' if resume else 'w+', shape=s, dtype=t)
              for k,(s,t) in specs.items()}
    start = resume['frames'] if resume else 0
    if resume:
        membership = np.load(cache/'atom_membership.npy')
        molecules = np.load(cache/'molecule_ids.npy')
        groups = np.load(cache/'groups.npy')
        columns = resume['columns']
    t0=time.perf_counter()
    with source.open('rb', buffering=8*1024**2) as stream:
        if resume:
            stream.seek(resume['offset'])
        f=start
        while True:
            frame = read_frame(stream)
            if frame is None:
                break
            if f >= F:
                raise TrajectoryError('More frames than configured; increase expected_frames in a fresh cache')
            if len(frame['data']) != config['expected_atoms']:
                raise TrajectoryError('Unexpected atom count')
            if f == 0:
                membership,molecules,groups=molecule_mapping(frame,config['central_type'],config['hydrogen_type'])
                columns=frame['columns']
                if len(molecules) != N:
                    raise TrajectoryError('Unexpected molecule count')
                for name,a in [('atom_membership',membership),('molecule_ids',molecules),('groups',groups)]:
                    np.save(cache/(name+'.npy'),a)
            current=frame['data'][:,[frame['columns'].index(c) for c in ['id','mol','type']]].astype(np.int64)
            if frame['columns'] != columns or not np.array_equal(current,membership):
                raise TrajectoryError('Changed columns, atom IDs, molecule membership or atom types')
            step=frame['step']
            if (f == 0 and step != config['expected_first_step']) or (f > 0 and step-arrays['steps'][f-1] != config['expected_cadence']):
                raise TrajectoryError('Nonuniform, repeated or unexpected timestep')
            orientation,frac,diag=reconstruct(frame,groups,config)
            arrays['orientations'][f]=orientation
            arrays['steps'][f]=step
            arrays['box_lengths'][f]=np.diff(frame['bounds'],axis=1)[:,0]
            arrays['box_lower'][f]=frame['bounds'][:,0]
            arrays['geometry'][f]=diag
            arrays['frame_sha256'][f]=frame['digest'].encode()
            for ax in range(3):
                arrays['spatial_counts'][f,ax]=np.bincount(np.minimum((frac[:,ax]*bins).astype(int),bins-1),minlength=bins)
            f+=1
            if f%250 == 0 or f == F:
                for a in arrays.values(): a.flush()
                write_json(marker,dict(source=identity,config=config,frames=f,offset=frame['offset'],columns=columns))
                print(f'Validated {f}/{F} frames; {stream.tell()/stat.st_size:.1%} bytes; {time.perf_counter()-t0:.1f}s this pass',flush=True)
    if f != F or arrays['steps'][f-1] != config['expected_last_step']:
        raise TrajectoryError('Incomplete expected step/frame range')
    if source.stat().st_size != stat.st_size or source.stat().st_mtime_ns != stat.st_mtime_ns:
        raise TrajectoryError('Source changed during conversion')
    for a in arrays.values(): a.flush()
    geo=arrays['geometry']
    result=dict(source=identity,config=config,frames=f,molecules=N,atoms=config['expected_atoms'],columns=columns,
        source_content_fingerprint=hashlib.sha256(arrays['frame_sha256'].tobytes()).hexdigest(),
        fingerprint_convention='SHA256 of concatenated 64-byte ASCII SHA256 hashes of each complete raw frame in order; frame_sha256.npy stores individual hashes',
        first_step=int(arrays['steps'][0]),last_step=int(arrays['steps'][-1]),cadence=int(config['expected_cadence']),
        complete_eof=True,all_frames_headers_membership_finite_geometry_cadence_validated=True,
        cache_dtype='float32',accumulation_dtype='float64',unit_of_lag='simulation steps',
        geometry_columns=['bond_min','bond_max','bond_mean','bond_std','angle_min_deg','angle_max_deg','angle_mean_deg','angle_std_deg','bisector_magnitude_mean','bisector_magnitude_std','mic_molecule_fraction','bisector_magnitude_min','bisector_magnitude_max'],
        geometry=dict(bond_min=float(geo[:,0].min()),bond_max=float(geo[:,1].max()),bond_mean=float(geo[:,2].mean()),
        angle_min_degrees=float(geo[:,4].min()),angle_max_degrees=float(geo[:,5].max()),angle_mean_degrees=float(geo[:,6].mean()),
        bisector_magnitude_min=float(geo[:,11].min()),bisector_magnitude_max=float(geo[:,12].max()),mean_mic_molecule_fraction=float(geo[:,10].mean())),
        box_lengths_min=arrays['box_lengths'].min(axis=0).tolist(),box_lengths_max=arrays['box_lengths'].max(axis=0).tolist(),
        assumptions=[config['assumption'],'Geometric orientation proxy, not proven physical dipoles or force-field provenance'],
        unknown_metadata={k:None for k in ['water_model','integration_timestep','unit_style','temperature','ensemble','charges','electrostatics','dump_group_is_full_system','equilibration_cutoff']},
        resources=resources,python=sys.version,platform=platform.platform(),completed_utc=datetime.now(timezone.utc).isoformat(),
        elapsed_conversion_this_pass_seconds=time.perf_counter()-t0)
    write_json(done,result)
    write_json('results/metadata.json',result)
    return result
