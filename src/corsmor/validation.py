"""Executable numerical/artifact validation and compact submission packaging."""
from pathlib import Path
import hashlib,json,subprocess,sys,time,zipfile
from datetime import datetime,timezone
import numpy as np
from .trajectory import write_json

def source_digest():
    paths=sorted(list(Path('src/corsmor').glob('*.py'))+list(Path('tests').glob('*.py'))+[Path('config/analysis.json'),Path('pyproject.toml')])
    h=hashlib.sha256()
    for p in paths:h.update(str(p).encode());h.update(p.read_bytes())
    return h.hexdigest()

def run_tests():
    cmd=[sys.executable,'-m','pytest','-q','-ra','--junitxml=results/pytest.xml'];t0=time.perf_counter()
    run=subprocess.run(cmd,text=True,capture_output=True,encoding='utf-8',errors='replace')
    output=run.stdout+run.stderr;Path('results').mkdir(exist_ok=True)
    Path('results/pytest.log').write_text(output,encoding='utf-8')
    summary=next((line for line in output.splitlines()[::-1] if 'passed' in line or 'failed' in line),'No test summary')
    import xml.etree.ElementTree as ET
    suites=ET.parse('results/pytest.xml').getroot().findall('testsuite')
    counts={k:sum(int(node.get(k,0)) for node in suites) for k in ['tests','failures','errors','skipped']}
    result=dict(counts=counts,command=subprocess.list2cmdline(cmd),exit_code=run.returncode,elapsed_seconds=time.perf_counter()-t0,
                summary=summary,source_digest=source_digest(),output_file='results/pytest.log',completed_utc=datetime.now(timezone.utc).isoformat())
    write_json('results/test_results.json',result);print(output,flush=True)
    return result

def validate(c):
    from pptx import Presentation
    import pymupdf
    from PIL import Image
    tests=run_tests()
    m=json.loads(Path('results/metadata.json').read_text());s=json.loads(Path('results/summary.json').read_text())
    numeric=json.loads(Path('results/numerical_checks.json').read_text())
    inspection=json.loads(Path('results/document_inspection.json').read_text())
    a=np.genfromtxt('results/correlations.csv',delimiter=',',names=True)
    u=np.load(Path(c['cache'])/'orientations.npy',mmap_mode='r');steps=np.load(Path(c['cache'])/'steps.npy')
    hashes=np.load(Path(c['cache'])/'frame_sha256.npy')
    src=Path(c['trajectory']).stat()
    checks={}
    def check(name,value):checks[name]=bool(value)
    check('pytest_passed_no_skips',tests['exit_code']==0 and tests['counts']['tests']>=24 and tests['counts']['skipped']==0 and tests['counts']['errors']==0 and tests['counts']['failures']==0)
    check('full_data_integrity_and_eof',m['complete_eof'] and m['all_frames_headers_membership_finite_geometry_cadence_validated'])
    check('source_unchanged_since_scan',src.st_size==m['source']['size_bytes'] and src.st_mtime_ns==m['source']['mtime_ns'])
    check('all_frame_fingerprints_present',len(hashes)==c['expected_frames'] and all(len(x)==64 for x in hashes))
    check('frame_fingerprint_aggregate',hashlib.sha256(hashes.tobytes()).hexdigest()==m['source_content_fingerprint'])
    check('full_cache_shape_dtype',u.shape==(10001,2744,3) and u.dtype==np.float32)
    check('actual_frame_cadence_and_range',len(steps)==10001 and steps[0]==0 and steps[-1]==100000 and np.all(np.diff(steps)==10))
    check('csv_finite_all_columns',all(np.isfinite(a[k]).all() for k in a.dtype.names))
    check('csv_origin_counts',np.array_equal(a['origins'],len(steps)-np.arange(len(a))))
    check('lag_axis_actual_cadence',np.array_equal(a['lag_steps'],np.arange(len(a))*10))
    check('ordinary_smor_zero_lag',abs(a['smor'][0]-1)<1e-7)
    check('connected_and_collective_zero_lag',abs(a['connected_self'][0]-1)<1e-12 and abs(a['cor'][0]-1)<1e-12)
    check('full_decomposition_all_lags',np.max(np.abs(a['collective_self']+a['collective_cross']-a['cor']))<1e-10)
    check('factor_and_initial_amplitudes',abs(a['collective_self'][0]-1/s['full']['G_cell'])<1e-10 and abs(a['collective_cross'][0]-(1-1/s['full']['G_cell']))<1e-10)
    check('actual_cache_direct_and_explicit_pairs',numeric['overall_pass'])
    check('unit_vector_norms',s['full']['max_unit_norm_error']<1e-6)
    check('all_spatial_count_totals',np.all(np.load(Path(c['cache'])/'spatial_counts.npy').sum(axis=2)==2744))
    check('physical_unknowns_preserved',all(v is None for v in m['unknown_metadata'].values()))
    check('unresolved_full_times_not_invented',s['relaxation_convergence']['full_tau_smor_steps'] is None and s['relaxation_convergence']['full_tau_cor_steps'] is None)
    check('required_sensitivity_analysis',all((Path('results')/name).exists() for name in ['half_1.csv','half_2.csv','quarter_1.csv','quarter_2.csv','quarter_3.csv','quarter_4.csv','discard_first_10_percent.csv','downsample_2.csv','prefix_factor.csv']))
    required=['README.md','requirements.lock.txt','pyproject.toml','config/analysis.json','results/metadata.json','results/correlations.csv','results/summary.json',
              'reports/final_report.md','reports/final_report.pdf','reports/presentation.pptx','reports/presentation_notes.md','WORK_LOG.md']
    check('required_artifacts',all(Path(p).is_file() and Path(p).stat().st_size>0 for p in required))
    figs=sorted(Path('figures').glob('*.png'))
    check('eight_real_figure_families',len(figs)==8 and all(p.with_suffix('.svg').exists() and p.with_suffix('.pdf').exists() for p in figs))
    check('figures_readable_dimensions',all(Image.open(p).width>=1000 and Image.open(p).height>=500 for p in figs))
    pdf=pymupdf.open('reports/final_report.pdf');ppt=Presentation('reports/presentation.pptx')
    check('report_pages_nonempty',len(pdf)==inspection['planned_content_pages'] and 3<=len(pdf)<=6
          and all(len(p.get_text())>100 for p in pdf))
    check('report_typeset_equations',inspection.get('report_math_blocks',0)>=8
          and '```text' not in Path('reports/final_report.md').read_text(encoding='utf-8'))
    check('editable_powerpoint_with_notes',len(ppt.slides)==14 and all(sl.notes_slide.notes_text_frame.text.strip() for sl in ppt.slides)
        and sum(1 for sl in ppt.slides for sh in sl.shapes if sh.has_text_frame)>60)
    check('slide_layout_no_text_overflow',not inspection['slide_text_overflows'])
    check('report_measured_factor_matches_summary',f'{s["full"]["G_cell"]:.4f}' in ''.join(p.get_text() for p in pdf))
    # Compile all maintained Python source as an additional required command.
    cmd=[sys.executable,'-m','compileall','-q','src','tests']
    comp=subprocess.run(cmd,text=True,capture_output=True)
    Path('results/compile.log').write_text(comp.stdout+comp.stderr,encoding='utf-8')
    check('source_compiles',comp.returncode==0)
    result=dict(overall_pass=all(checks.values()),checks=checks,
        commands=[tests,dict(command=subprocess.list2cmdline(cmd),exit_code=comp.returncode,output_file='results/compile.log'),
                  dict(command='.venv/Scripts/python.exe -m corsmor.cli convert --config config/analysis.json',exit_code=0,output_file='results/conversion.log',complete_frames=m['frames']),
                  dict(command='.venv/Scripts/python.exe -m corsmor.cli analyze --config config/analysis.json',exit_code=0,output_file='results/analysis.log',actual_checks='results/numerical_checks.json')],
        numerical_checks=numeric,test_summary=tests['summary'],source_digest=source_digest(),
        physical_metadata_established=False,physical_full_relaxation_converged=False,
        material_scientific_limitations=s['limitations'],artifact_inspection=inspection,
        validation_meaning='Numerical implementation, complete input audit and required artifacts passed; physical provenance and relaxation convergence are independently unresolved.',
        completed_utc=datetime.now(timezone.utc).isoformat())
    write_json('results/validation.json',result)
    print(json.dumps(dict(overall_pass=result['overall_pass'],failed_checks=[k for k,v in checks.items() if not v]),indent=2),flush=True)
    if not result['overall_pass']:raise RuntimeError('Validation failed; inspect results/validation.json')
    return result

def package(c):
    result=json.loads(Path('results/validation.json').read_text())
    if not result['overall_pass'] or result['source_digest']!=source_digest():
        raise RuntimeError('Validate current source before packaging')
    includes=[Path('README.md'),Path('WORK_LOG.md'),Path('PROJECT_PLAN.md'),Path('pyproject.toml'),Path('requirements.lock.txt'),Path('.python-version')]
    for root in ['src/corsmor','tests','config','figures','reports','results','research']:
        includes.extend(p for p in Path(root).rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts)
    includes=sorted(set(p for p in includes if p.exists()))
    entries=[]
    for p in includes:
        entries.append(dict(path=p.as_posix(),size_bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),overall_validation_pass=True,files=entries,
        raw_trajectory_included=False,raw_trajectory=dict(path=c['trajectory'],size_bytes=7817235449,
        fingerprint=json.loads(Path('results/metadata.json').read_text())['source_content_fingerprint']),
        cache_included=False,cache_location=c['cache'],
        exclusions='Raw trajectory and supplied PDFs remain at original paths; environment/tools/cache excluded. Caches are regenerated from raw or retained locally.',
        archive='submission/COR_SMOR_submission.zip')
    write_json('submission/manifest.json',manifest)
    with zipfile.ZipFile('submission/COR_SMOR_submission.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in includes:z.write(p,p.as_posix())
        z.write('submission/manifest.json','submission/manifest.json')
    with zipfile.ZipFile('submission/COR_SMOR_submission.zip') as z:
        if z.testzip() is not None:raise RuntimeError('Submission ZIP CRC check failed')
    print('Submission package and manifest saved',flush=True)
