"""Result-grounded Markdown/PDF report and editable PowerPoint with layout preview."""
from pathlib import Path
import json, html, textwrap
import numpy as np

ANCHOR='Maurya, Metya, Singh and Saito (2021), J. Chem. Phys. 154, 164704. https://doi.org/10.1063/5.0046817'

def build_documents(c):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import matplotlib.font_manager as fm
    import pymupdf
    from PIL import Image as PILImage
    out=Path('reports');out.mkdir(exist_ok=True)
    s=json.loads(Path('results/summary.json').read_text());m=json.loads(Path('results/metadata.json').read_text())
    n=json.loads(Path('results/numerical_checks.json').read_text())
    test=json.loads(Path('results/test_results.json').read_text()) if Path('results/test_results.json').exists() else {}
    f=s['full'];g=m['geometry'];data=np.genfromtxt('results/correlations.csv',delimiter=',',names=True)
    captions=json.loads(Path('figures/captions.json').read_text())
    fmt=lambda x:f'{x:.4g}'
    at=lambda key,t:float(np.interp(t,data['lag_steps'],data[key]))
    latest=f['truncated_integrals_steps']['10000']
    measured=(f'The complete record contains {m["frames"]:,} frames and {m["molecules"]:,} water-like molecular groups over '
        f'{m["first_step"]:,}-{m["last_step"]:,} simulation steps. The centered finite-cell factor is G_cell = {f["G_cell"]:.4f}; '
        f'quarter estimates range from {s["quarter_G_range"][0]:.4f} to {s["quarter_G_range"][1]:.4f}. '
        f'At lag 2,500 steps, ordinary SMOR is {at("smor",2500):.4f} and centered COR is {at("cor",2500):.4f}. '
        f'Integrals through 10,000 steps are {latest["smor"]:.2f} steps for SMOR and {latest["cor"]:.2f} steps for COR; these are finite-cutoff measures, not converged full relaxation times.')
    pages=[]
    def page(title,*elements):pages.append((title,elements))
    def P(text):return ('p',text)
    def H(text):return ('h',text)
    def T(head,rows,widths=None):return ('table',head,rows,widths)
    def F(name,width=174):return ('figure',name,width)
    def C(text):return ('code',text)
    published=[['Bulk reference','5.37','11.86','3.23'],['Graphene droplet, usual interaction','5.43','0.90','0.24'],['Droplet, strongest listed interaction','6.34','2.25','0.40']]
    page('Collective versus single-molecule orientational relaxation',
      P('CB4103 course project | Analysis of the supplied trajectory | 15 November 2026'),
      H('Abstract'),P('We compare individual molecular orientation memory with fluctuations of the summed molecular orientation. Molecule-resolved periodic reconstruction, a complete frame audit, and independent correlation checks precede interpretation. '+measured),
      H('Scientific question and literature'),
      P('Collective relaxation can differ from individual rotation because distinct molecules contribute cross correlations. Expanding the correlation of a sum gives an exact self/cross identity. A static correlation factor controls initial amplitudes but does not alone determine relaxation-time ordering.'),
      P('Maurya et al. (2021), Section III.C, Eqs. (2)-(11), Figs. 10-12 and Table IV, is the methodological anchor. Their TIP4P/2005 simulations use graphene droplets and a bulk reference, with known 300 K conditions and physical time. The supplied dataset has unknown provenance. We adapt the definitions rather than reproduce their numerical results.'),
      T(['Published system ONLY','SMOR / ps','COR / ps','Reported G_K'],published,[.46,.18,.18,.18]),
      P('Published benchmark values above are transcribed from Table IV; none are measurements from dumpr.lammpstrj. The paper retains a dynamic correction in its time-scale relation, so tau_COR = G_cell * tau_SMOR is not imposed here.'),
      P('Deliverables include reusable source/configuration, full-data caches and diagnostics, numerical validation, figures, this report, and an editable presentation.'))
    page('1. Dataset, provenance and reconstructed geometry',
      T(['Property','Verified value or limitation'],[
       ['Raw source','dumpr.lammpstrj; 7,817,235,449 bytes; original preserved'],
       ['Integrity scope',f'All {m["frames"]:,} complete frames; clean end of file'],
       ['Composition',f'{m["atoms"]:,} atoms; {m["molecules"]:,} stable groups; each type pattern (1,1,2)'],
       ['Step sequence',f'{m["first_step"]} to {m["last_step"]}; every interval {m["cadence"]} steps'],
       ['Coordinates / box','Wrapped x,y,z; fully periodic orthorhombic; box read every frame'],
       ['Side lengths',', '.join(f'{v:.8f}' for v in m['box_lengths_min'])+' dump units'],
       ['Unavailable','Model, units, timestep, charges, temperature, ensemble, full dump group'],
       ['Retained record','All frames; initial-10%-removed result supplied as sensitivity only']],[.25,.75]),
      F('01_geometry'),
      P(f'Across all frames and molecules, reconstructed bond lengths span {g["bond_min"]:.8f}-{g["bond_max"]:.8f} dump units; mean {g["bond_mean"]:.8f}. Angles span {g["angle_min_degrees"]:.6f}-{g["angle_max_degrees"]:.6f} degrees; mean {g["angle_mean_degrees"]:.6f}. On average {100*g["mean_mic_molecule_fraction"]:.2f}% of molecular groups require an intramolecular periodic correction.'),
      P(f'The unnormalized bond-sum magnitude spans {g["bisector_magnitude_min"]:.8f}-{g["bisector_magnitude_max"]:.8f} dump units. Near-constant geometry supports a constant-magnitude geometric proxy, conditional on equal symmetric charge sites. It does not identify the charge model. SPC and SPC/E share this geometry but differ in charge assignments; virtual sites and polarization would require model-specific treatment.'),
      P('Atom IDs, molecule IDs and types are validated in stable ID order in every frame. Frame hashes and explicit molecule ordering allow independent provenance checks. The trajectory may omit a substrate or other groups; water-like composition does not prove a homogeneous full-system simulation.'))
    equations='''b_ia = r_Ha - r_O - L round((r_Ha-r_O)/L)
u_i = (b_i1 + b_i2) / |b_i1 + b_i2|; U = sum_i u_i
v_i = u_i - mean_t(u_i); delta U = U - mean_t(U)
R(k) = sum_i <u_i(t) dot u_i(t+k)>; SMOR = R(k)/N
A(k) = sum_i <v_i(t) dot v_i(t+k)>; connected self = A(k)/A(0)
B(k) = <delta U(t) dot delta U(t+k)>; COR = B(k)/B(0)
collective self = A(k)/B(0)
collective cross = [B(k)-A(k)]/B(0)
G_cell = B(0)/A(0); self(0) = 1/G_cell
running integral(T) = trapezoidal integral from 0 to T of C(t) dt'''
    page('2. Estimators, centering and independent validation',
      C(equations),
      P('Angle brackets average all F-k valid origins at lag k. Each molecular mean and the total mean are estimated once over the same retained segment. This ensures delta U = sum_i v_i. Ordinary SMOR is computed separately; it retains persistent or finite-record molecular means. Both collective contributions share B(0), and cross values may be negative.'),
      P('The FFT estimator zero-pads to at least 2F-1, sums autocorrelation channel powers in float64, inverse transforms, and divides by F-k. Molecules are processed in batches of 64 from a float32 memory map. No all-pairs loop is needed for production cross terms. Direct time-domain and explicit ordered-pair sums are independent small-system checks.'),
      T(['Check','Actual result'],[
       ['Scientific pytest suite',test.get('summary','See results/pytest.log and results/test_results.json')],
       ['Actual-data FFT vs direct',f'Max error {max(n["fft_direct_max_abs_error"].values()):.3e}; 128 frames x 24 molecules'],
       ['Actual-data ordered-pair cross',f'Max error {n["explicit_ordered_cross_pair_max_abs_error"]:.3e}; 32 frames x 8 molecules'],
       ['Full-record decomposition',f'Max error {f["decomposition_max_abs_error"]:.3e}'],
       ['Cached unit-vector norms',f'Max absolute error {f["max_unit_norm_error"]:.3e}'],
       ['Frame/cadence audit',f'{m["frames"]:,} frames; all {m["frames"]-1:,} intervals validated']],[.35,.65]),
      P('Analytic tests include a rotating unit vector, a persistent orientation component, an exponential with known integral/scale, negative cross terms, and noncircular endpoint normalization. Reader tests include split molecules, unsorted and nonconsecutive IDs, multiple molecule orders, reordered columns, nonfinite data, malformed rows, changing membership, wrong cadence and truncation.'),
      P('Centering creates a finite-record constraint: F A(0) + 2 sum_(k>0) (F-k) A(k) = 0 when all lags are included. Long negative tails can therefore arise from mean estimation. Segment sensitivity is essential; an integral to the final saved lag is not a valid convergence certificate.'))
    page('3. Spatial and collective sampling diagnostics',
      F('02_spatial_profiles'),F('03_collective_stationarity'),
      P('Fractional-coordinate profiles use the inferred central sites and wrap only for binning. The maximum full-record deviation from the uniform-bin expectation is '+', '.join(f'{"xyz"[j]}: {100*v:.2f}%' for j,v in enumerate(s['spatial_diagnostics']['max_abs_deviation_from_uniform_by_axis']))+'. These are projected number profiles, not mass density or a structural phase identification.'),
      P('Collective traces and the prefix-centered factor show how much the estimate depends on the available record. Each prefix reestimates its means; early values use little information. The quarter means of U_y are '+', '.join(f'{b["mean_U"][1]:.2f}' for b in s['stationarity_blocks'])+'. Full-record component variances (x,y,z) are '+', '.join(f'{v:.2f}' for v in f['total_variance_components'])+'. This variation flags sampling of slow collective modes; it does not distinguish equilibration, persistent order or finite-record fluctuations. No thermal or energetic equilibration claim is possible without logs.'))
    page('4. Observed orientation correlations and cross terms',
      F('04_smor_cor'),F('05_decomposition'),
      P(f'At zero lag, A(0) = {f["A0"]:.5f} and B(0) = {f["B0"]:.5f}. Thus G_cell = {f["G_cell"]:.5f}, collective self(0) = {1/f["G_cell"]:.5f}, and collective cross(0) = {1-1/f["G_cell"]:.5f}. For comparison, B(0)/N = {f["G_centered_over_N"]:.5f}, while the uncentered raw factor is {f["G_raw"]:.5f}. These distinct conventions must not be interchanged.'),
      P(f'At lag 2,500 steps, ordinary SMOR = {at("smor",2500):.5f}, connected self = {at("connected_self",2500):.5f}, and COR = {at("cor",2500):.5f}. The collective self and cross contributions there are {at("collective_self",2500):.5f} and {at("collective_cross",2500):.5f}. At 10,000 steps, ordinary SMOR = {at("smor",10000):.5f} and COR = {at("cor",10000):.5f}.'),
      P('These comparisons describe this full-record estimator at declared lags. Intermolecular terms alter the collective signal, but the curves do not identify a unique microscopic hydrogen-bond mechanism. A static factor alone cannot establish a full-time relaxation ordering.'))
    rows=[]
    for cutoff,vals in f['truncated_integrals_steps'].items():rows.append([cutoff]+[f'{vals[k]:.3f}' for k in ['smor','connected_self','cor']])
    fitrows=[]
    for key in ['smor','connected_self','cor']:
        fit=f['fits'][key];fitrows.append([key,fmt(fit['tau_steps']) if 'tau_steps' in fit else 'unresolved',
          fmt(fit['rmse']) if 'rmse' in fit else '-', 'supported window' if fit['supported'] else 'rejected / unresolved'])
    page('5. Running integrals, fit scales and convergence limits',
      F('06_running_integrals'),
      T(['Cutoff / steps','Ordinary SMOR','Connected self','Centered COR'],rows,[.22,.26,.26,.26]),
      P('All table entries are truncated integrals in simulation steps. The cutoff dependence is part of the result. They are not full relaxation times, and their ratio is not reported as a converged time-scale ratio.'),
      T(['Fit curve','tau_fit / steps','RMSE','Adequacy'],fitrows,[.24,.23,.18,.35]),
      P('The secondary fit uses a * exp(-lag/tau_fit) over the fixed 100-2,500 step window. Adequacy requires positive data across the window, at least 0.05 decay span, RMSE below 0.03, R-squared above 0.95, and tau no larger than twice the window width. A supported window fit is descriptive; correlated residuals are not treated as IID errors and no confidence interval or full-time tail is inferred.'),
      P('In the final 20% of the reporting window, the SMOR running integral changes by '+fmt(f['tail_diagnostics']['smor']['last_20_percent_integral_drift_steps'])+' steps, and the COR integral changes by '+fmt(f['tail_diagnostics']['cor']['last_20_percent_integral_drift_steps'])+' steps. The first zero crossings are '+str(f['tail_diagnostics']['smor']['first_zero_crossing_steps'])+' and '+str(f['tail_diagnostics']['cor']['first_zero_crossing_steps'])+' steps respectively (None means absent in this window).'),
      P('The full integral times remain unresolved. Longer records with independent replicas, stable centering and stable late cutoffs are needed before a physical ordering or uncertainty interval can be claimed.'))
    page('6. Segment, centering and sampling sensitivity',
      F('07_block_variation'),F('08_sensitivity'),
      P(f'Quarter G_cell values range from {s["quarter_G_range"][0]:.5f} to {s["quarter_G_range"][1]:.5f}. Quarters contain roughly 2,500 frames each, so their lags stop near 2,500 steps. Halves stop near 5,000 steps. These records do not create four fully independent realizations; block variation is shown without confidence bands.'),
      P(f'The maximum ordinary-minus-connected self difference is {s["centering_sensitivity"]["max_abs_ordinary_minus_connected"]:.5f}; centered-versus-uncentered collective difference is {s["centering_sensitivity"]["max_abs_centered_minus_uncentered_collective"]:.5f}. The squared total mean divided by centered total variance is {s["centering_sensitivity"]["relative_total_mean_square"]:.5f}. Molecular mean-square orientation per molecule is {f["molecular_mean_square_per_molecule"]:.5f}.'),
      P(f'Every-second-frame analysis changes SMOR by at most {s["downsample_max_abs_difference"]["smor"]:.3e} and COR by at most {s["downsample_max_abs_difference"]["cor"]:.3e} at common lags. This tests cadence sensitivity but cannot recover unsaved motion faster than 10 steps. Removing the first 10% is a sensitivity analysis, not proof of an equilibration boundary.'))
    allocation=[['1','Question, literature, provenance','Opening, published benchmarks, unknown metadata'],['2','Reader and molecular reconstruction','Full integrity, MIC geometry, cache provenance'],['3','SMOR and connected self','Orientation choice, centering, running integrals'],['4','COR and intermolecular terms','Common denominator, factor, negative cross'],['5','Validation and sampling','FFT/direct, pair sums, blocks, convergence limits'],['6','Figures and reproducibility','Artifact navigation, commands, closing interpretation']]
    page('7. Interpretation, limitations and six-person delivery',
      P(measured),
      P('The defensible contribution is a fully audited orientation-proxy analysis and exact dynamic self/cross decomposition, accompanied by finite-record sensitivity diagnostics. The supplied data support numerical statements at specified lags and cutoffs. They do not by themselves establish a force field, physical dielectric response, temperature trend, or converged full relaxation ordering.'),
      H('Material limitations'),
      *[P(str(i+1)+'. '+text) for i,text in enumerate(s['limitations'])],
      H('Presentation ownership (organizational roles)'),
      T(['Person','Ownership','Speaking responsibility'],allocation,[.1,.38,.52]),
      P('Every student should explain the same central identity and the largest limitation. One implementation was completed for the project; these six roles allocate review and presentation responsibility, not separate claims of software authorship.'))
    refs=[
      '[1] '+ANCHOR+' Supplied full PDF: primary methods and Table IV.',
      '[2] LAMMPS dump documentation. https://docs.lammps.org/dump.html (accessed 15 November 2026). Coordinate semantics, grouping and box formats.',
      '[3] LAMMPS SPC/SPC/E documentation. https://docs.lammps.org/Howto_spc.html (accessed 15 November 2026). Shared geometry does not identify charges.',
      '[4] Liu et al. (2022), HTR. https://doi.org/10.1515/ntrev-2022-0044; Shi et al. (2024), HTR+. https://doi.org/10.1088/1361-648X/ad52df. Supplied structural-classification papers; optional future context.',
      '[5] Rodger, Forester and Smith (1996), Fluid Phase Equilibria 116, 326-332. Supplied hydrate-interface context, not a COR benchmark.',
      '[6] Du et al. (2019). https://doi.org/10.1016/j.ijheatmasstransfer.2018.11.044; Krachkovskiy et al. (2020). https://doi.org/10.1021/acs.jpcc.0c07383. General structure/transport context only.',
      '[7] Varnik, Baschnagel and Binder (2000). https://doi.org/10.1063/1.1288390. Supplied pressure-tensor background; filename year 2020 is incorrect.']
    viva=[
      ('Why can COR differ from SMOR?','The correlation of a sum includes distinct-molecule cross terms.'),
      ('Why is each contribution not normalized to one?','Both use B(0), so self(0)=1/G_cell and cross(0)=1-1/G_cell.'),
      ('Can a cross term be negative?','Yes. Anticorrelated orientations can cancel self contributions.'),
      ('Why no picoseconds or model name?','The integration timestep, units and charge model are unavailable; geometry is not provenance.'),
      ('Why subtract molecular means?','It gives an exact connected decomposition, but finite-record means can bias the long tail; ordinary SMOR is also shown.'),
      ('Why zero-pad and divide by F-k?','To avoid circular wraparound and account for fewer origins at larger lag.'),
      ('Does G_cell determine time ordering?','No. Dynamic cross terms and convergence are also needed.'),
      ('Why is full tau unresolved?','Finite cutoffs, mean estimation and segment variation do not establish a stable full-time integral or tail.'),
      ('Are 2,744 molecules independent COR samples?','No. COR has one summed vector per saved frame and temporally overlapping origins.')]
    page('References, viva preparation and reproducibility',
      *[P(ref) for ref in refs],H('Likely viva questions'),
      *[P(question+' '+answer) for question,answer in viva],
      H('Reproduce and inspect'),
      C('.venv/Scripts/python.exe -m pytest -q\n.venv/Scripts/python.exe -m corsmor.cli all --config config/analysis.json'),
      P('See README.md for clean environment setup and exact stage commands. results/metadata.json records source identity, complete audit and geometry; summary.json records estimators and limitations; validation.json separates numerical success from physical unknowns. All figures have PNG/SVG/PDF versions. submission/manifest.json lists artifacts without copying the raw trajectory.'))
    # One content model emits both readable Markdown and the typeset PDF.
    regular=fm.findfont('DejaVu Sans');bold=fm.findfont(fm.FontProperties(family='DejaVu Sans',weight='bold'))
    mono=fm.findfont('DejaVu Sans Mono')
    for name,path in [('Report',regular),('ReportBold',bold),('ReportMono',mono)]:
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,path))
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyR',fontName='Report',fontSize=9,leading=12.4,spaceAfter=6,textColor=colors.HexColor('#243449')))
    styles.add(ParagraphStyle(name='HeadR',fontName='ReportBold',fontSize=18,leading=22,spaceAfter=12,textColor=colors.HexColor('#12344a')))
    styles.add(ParagraphStyle(name='SubR',fontName='ReportBold',fontSize=11,leading=14,spaceBefore=6,spaceAfter=6,textColor=colors.HexColor('#007c91')))
    styles.add(ParagraphStyle(name='CaptionR',fontName='Report',fontSize=7.3,leading=9.5,spaceAfter=7,textColor=colors.HexColor('#59697a')))
    styles.add(ParagraphStyle(name='CellR',fontName='Report',fontSize=7.6,leading=10))
    styles.add(ParagraphStyle(name='CodeR',fontName='ReportMono',fontSize=7.1,leading=10.5,spaceAfter=8,backColor=colors.HexColor('#eef4f6'),borderPadding=5))
    def para(text,sty='BodyR'):return Paragraph(html.escape(text).replace('\n','<br/>'),styles[sty])
    story=[];md=[]
    for page_idx,(title,elements) in enumerate(pages):
        if page_idx:story.append(PageBreak())
        story.append(para(title,'HeadR'));md+=['# '+title,'']
        for el in elements:
            kind=el[0]
            if kind in ['p','h','code']:
                sty={'p':'BodyR','h':'SubR','code':'CodeR'}[kind]
                story.append(para(el[1],sty))
                md += ([('## ' if kind=='h' else '')+el[1],''] if kind!='code' else ['```text',el[1],'```',''])
            elif kind=='table':
                head,rows,widths=el[1:]
                widths=widths or [1/len(head)]*len(head)
                cells=[[para(str(cell),'CellR') for cell in row] for row in [head]+rows]
                t=Table(cells,colWidths=[v*493.2 for v in widths],repeatRows=1,hAlign='LEFT')
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceaf0')),('VALIGN',(0,0),(-1,-1),'TOP'),
                 ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f7f9')]),('LEFTPADDING',(0,0),(-1,-1),6),
                 ('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
                 ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#9cb5c2'))]))
                story.extend([t,Spacer(1,8)])
                md+=['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']
                md+=['| '+' | '.join(str(v) for v in row)+' |' for row in rows]+['']
            elif kind=='figure':
                name,width=el[1:];path=Path('figures')/(name+'.png');wpx,hpx=PILImage.open(path).size
                w=width*72/25.4;story.extend([Image(str(path),width=w,height=w*hpx/wpx),para(captions[name],'CaptionR')])
                md += [f'![{name}](../figures/{name}.png)',captions[name],'']
    (out/'final_report.md').write_text('\n'.join(md),encoding='utf-8')
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#c1d2dc'));canvas.line(51,37,544,37)
        canvas.setFont('Report',7);canvas.setFillColor(colors.HexColor('#647588'))
        canvas.drawString(51,25,'CB4103 | COR/SMOR | Geometric orientation proxy | Simulation-step units')
        canvas.drawRightString(544,25,str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(str(out/'final_report.pdf'),pagesize=A4,rightMargin=51,leftMargin=51,topMargin=45,bottomMargin=48,
                          title='Collective versus single-molecule orientational relaxation',author='CB4103 project team')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    (out/'previews').mkdir(exist_ok=True)
    presentation_info=build_presentation(s,m,n,test,allocation,viva)
    pdf=pymupdf.open(out/'final_report.pdf');renderdir=out/'previews';renderdir.mkdir(exist_ok=True)
    representative=sorted(set([0, min(2,len(pdf)-1), min(4,len(pdf)-1),min(5,len(pdf)-1),len(pdf)-1]))
    for i in representative:pdf[i].get_pixmap(matrix=pymupdf.Matrix(1.25,1.25)).save(renderdir/f'report_page_{i+1:02}.png')
    info=dict(report_pages=len(pdf),planned_content_pages=len(pages),report_page_text_lengths=[len(p.get_text()) for p in pdf],
      representative_report_previews=[str(renderdir/f'report_page_{i+1:02}.png') for i in representative],**presentation_info,
      native_powerpoint_render_available=False,presentation_preview_note='Companion PDF renders the same editable slide text/image geometry; it is a layout preview, not a native PowerPoint rendering.')
    Path('results/document_inspection.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print('Documents built:',json.dumps(info),flush=True)

def build_presentation(s,m,n,test,allocation,viva):
    """Editable text and vector elements with embedded result plots; 16:9 deck."""
    from pptx import Presentation
    from pptx.util import Inches,Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from PIL import Image
    import pymupdf
    prs=Presentation();prs.slide_width=Inches(13.333333);prs.slide_height=Inches(7.5)
    prs.core_properties.title='Collective versus single-molecule orientational relaxation'
    prs.core_properties.subject='CB4103: validated full-trajectory geometric orientation analysis'
    prs.core_properties.author='CB4103 project team'
    prs.core_properties.keywords='COR, SMOR, self/cross, simulation steps, finite sampling'
    preview=canvas.Canvas('reports/presentation_layout_preview.pdf',pagesize=(960,540))
    overflow=[];slide_text=[];slide_no=0
    ink='#173247';teal='#007c91';purple='#963b79';gray='#576d7e'
    def textbox(slide,text,x,y,w,h,size=22,color=ink,bold=False):
        box=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
        tf=box.text_frame;tf.clear();tf.word_wrap=True;tf.margin_left=0;tf.margin_right=0;tf.margin_top=0;tf.margin_bottom=0
        tf.vertical_anchor=MSO_ANCHOR.TOP
        for j,line in enumerate(text.split('\n')):
            p=tf.paragraphs[0] if j==0 else tf.add_paragraph();p.text=line;p.space_after=Pt(size*.28);p.line_spacing=1.1
            p.font.name='DejaVu Sans';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(color[1:])
        sty=ParagraphStyle('slide',fontName='ReportBold' if bold else 'Report',fontSize=size,leading=size*1.1,
                           textColor=colors.HexColor(color),spaceAfter=size*.28)
        top=540-y*72
        for line in text.split('\n'):
            par=Paragraph(html.escape(line) if line else '&#160;',sty);ww,hh=par.wrap(w*72,h*72+1000)
            par.drawOn(preview,x*72,top-hh);top-=hh+size*.28
        used=(540-y*72-top)/72
        if used>h+.08:overflow.append(dict(slide=slide_no,text=text[:80],used_height_inches=used,box_height_inches=h))
        return box
    def rect(slide,x,y,w,h,color):
        sh=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h));sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(color[1:]);sh.line.fill.background()
        preview.setFillColor(colors.HexColor(color));preview.rect(x*72,540-(y+h)*72,w*72,h*72,fill=1,stroke=0)
    def new(title,kicker,notes):
        nonlocal slide_no
        slide_no+=1;slide=prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid();slide.background.fill.fore_color.rgb=RGBColor(255,255,255)
        preview.setFillColor(colors.white);preview.rect(0,0,960,540,fill=1,stroke=0)
        rect(slide,0,0,13.333,.1,teal)
        textbox(slide,kicker.upper(),.55,.30,12.2,.35,11,teal,True)
        from reportlab.pdfbase import pdfmetrics
        title_size=min(29,840/max(pdfmetrics.stringWidth(title,'ReportBold',1),1))
        textbox(slide,title,.55,.76,12.2,.75,title_size,ink,True)
        textbox(slide,'CB4103  |  Supplied trajectory  |  Simulation-step units',.55,7.09,11.4,.22,9,gray)
        textbox(slide,f'{slide_no:02}',12.1,7.07,.65,.25,10,gray)
        slide.notes_slide.notes_text_frame.text=notes
        slide_text.append(dict(slide=slide_no,title=title,notes=notes))
        return slide
    def pic(slide,name,x=.55,y=1.7,w=12.2,h=4.6):
        path=Path('figures')/(name+'.png');px,py=Image.open(path).size
        ratio=min(w/px,h/py);iw,ih=px*ratio,py*ratio;xx=x+(w-iw)/2;yy=y+(h-ih)/2
        slide.shapes.add_picture(str(path),Inches(xx),Inches(yy),width=Inches(iw),height=Inches(ih))
        preview.drawImage(str(path),xx*72,540-(yy+ih)*72,iw*72,ih*72)
    def finish():preview.showPage()
    f=s['full'];cut=f['truncated_integrals_steps']['10000']
    slide=new('How does a molecular sum forget its orientation?','Collective versus single-molecule orientational relaxation',
       'Introduce the question. All results are from a geometric molecular-bisector proxy. The complete trajectory passed audit; metadata and full relaxation convergence remain separate limitations.')
    textbox(slide,'A complete-data analysis of 2,744 water-like molecular groups',.65,1.85,12,1.,29,teal,True)
    rect(slide,.65,3.1,5.85,2.0,'#eef5f7');rect(slide,6.8,3.1,5.85,2.0,'#f7eff5')
    textbox(slide,f'{m["frames"]:,} frames\n0-100,000 simulation steps',.9,3.35,5.35,1.3,25,ink)
    textbox(slide,f'G_cell = {f["G_cell"]:.4f}\nFull relaxation times unresolved',7.05,3.35,5.35,1.3,24,purple)
    textbox(slide,'Numerical validation passes; unknown physical metadata stays unknown.',.7,5.75,12, .8,21,gray)
    finish()
    slide=new('Individual rotation and collective memory ask different questions','1 | Motivation and published context',
       'Anchor: Maurya et al. 2021, Section III.C, equations 2-11, figures 10-12 and Table IV. TIP4P/2005 at graphene is a methodological reference, not the identity of this supplied dataset.')
    textbox(slide,'SMOR: orientation memory of each molecule.\nCOR: fluctuations of their summed orientation.\nDistinct-molecule cross terms connect the two.',.65,1.7,12,2.,25)
    textbox(slide,'Published Table IV only: SMOR / COR\nBulk: 5.37 / 11.86 ps\nUsual graphene droplet: 5.43 / 0.90 ps',.65,4.05,8.3,1.8,24,purple)
    textbox(slide,'The present trajectory has no verified ps conversion or force-field identity.',9.15,4.05,3.4,1.9,21,gray)
    finish()
    slide=new('Every saved frame was audited','2 | Dataset and provenance',
       'The original 7.817 GB source is preserved. Full streaming parser validates every frame, not sampled prefixes. IDs and molecule membership are stable even if atom row order changes. No original model, time step, units or temperature is supplied.')
    textbox(slide,f'{m["frames"]:,} complete frames; {m["atoms"]:,} atoms; {m["molecules"]:,} groups\nEvery group: one type-2 center + two type-1 satellites\nEvery saved interval: {m["cadence"]} steps; clean EOF\nPeriodic orthorhombic side length: {m["box_lengths_min"][0]:.6f} dump units',.65,1.75,12,2.7,25)
    rect(slide,.65,4.9,12,1.2,'#eef5f7')
    textbox(slide,'Unknown: original model, units, timestep, charges, temperature, ensemble, and whether the dump is the full system.',.9,5.10,11.5,.85,22,gray)
    finish()
    slide=new('Use one consistent centering and denominator','3 | Mathematical definitions',
       'Define u as the normalized sum of two minimum-image bond vectors. Means are per molecule over the same segment. Ordinary SMOR is uncentered; connected self is A/A0. COR is B/B0. Cross can be negative. The identity is exact at every lag.')
    textbox(slide,'u_i = normalized sum of two MIC bond vectors\nv_i = u_i - mean(u_i);   delta U = sum_i v_i\nA(t) = sum_i <v_i(0) dot v_i(t)>\nB(t) = <delta U(0) dot delta U(t)>',.65,1.7,12,2.55,24)
    textbox(slide,'COR = A(t)/B(0) + [B(t)-A(t)]/B(0)\nG_cell = B(0)/A(0)',.65,4.65,12,1.3,27,purple,True)
    finish()
    slide=new('Check the science independently of the fast estimator','4 | Numerical validation',
       'Describe analytic rotation and persistent-mean cases, explicit ordered cross-pair sums, zero-padding and F-k origin normalization, then full-data cadence and membership. Synthetic test fixtures are validation, not empirical findings.')
    textbox(slide,test.get('summary','Scientific tests: see results/pytest.log')+'\nPeriodic reconstruction, unsorted IDs, malformed frames, centering\nAnalytic lag sums, known rotation, known exponential\nActual-data FFT/direct error: '+f'{max(n["fft_direct_max_abs_error"].values()):.2e}'+'\nActual-data ordered cross-pair error: '+f'{n["explicit_ordered_cross_pair_max_abs_error"]:.2e}',.65,1.7,12,3.5,24)
    textbox(slide,'FFT: zero-pad >= 2F-1; divide each lag sum by F-k.\nProduction: streaming input, float32 cache, float64 accumulation.',.65,5.55,12,1.,21,teal)
    finish()
    slide=new('Geometry supports a proxy, not a force-field assignment','5 | Molecular and spatial diagnostics',
       'The geometry envelope includes every molecule in every frame. Spatial profiles are projections in fractional coordinates, compared across quarters. Matching SPC-like geometry does not prove SPC/E, charges, or omitted species.')
    pic(slide,'01_geometry',.55,1.7,12.2,2.3);pic(slide,'02_spatial_profiles',.55,4.05,12.2,2.25)
    textbox(slide,'Bond/angle rigidity is tested; physical dipole provenance remains unknown.',.65,6.5,12,.4,17,gray)
    finish()
    slide=new('Compare ordinary self, connected self and centered COR','6 | Full-record correlations',
       'All F-k origins are included. Ordinary and connected self differ because of finite-sample molecular means. Full curves extend to 10000 lag steps, one tenth of retained duration. Describe the observed curves without claiming a converged time ratio.')
    pic(slide,'04_smor_cor',.55,1.7,12.2,4.6)
    textbox(slide,'All horizontal axes are simulation steps. The three normalization conventions are distinct.',.65,6.5,12,.4,17,gray)
    finish()
    slide=new('Cross contributions change the collective signal','7 | Exact self/cross decomposition',
       f'G_cell={f["G_cell"]:.5f}; self zero-lag={1/f["G_cell"]:.5f}; cross zero-lag={1-1/f["G_cell"]:.5f}. Both terms use B0, so they are not separately unit-normalized. Negative dynamic values are allowed. Static amplitude alone does not establish relaxation ordering.')
    pic(slide,'05_decomposition',.55,1.7,12.2,4.4)
    textbox(slide,f'At lag zero: self = {1/f["G_cell"]:.4f}; cross = {1-1/f["G_cell"]:.4f}; sum = 1.',.65,6.35,12,.55,21,purple)
    finish()
    slide=new('Report finite-cutoff integrals, not full relaxation times','8 | Convergence assessment',
       'Running integrals use the trapezoidal rule. Discuss drift, sign changes and the cutoff table in the report. Fixed-window exponential fits are secondary descriptions with residual screens, not validation of the full tail.')
    pic(slide,'06_running_integrals',.55,1.7,12.2,4.35)
    textbox(slide,f'Through 10,000 steps: SMOR {cut["smor"]:.2f}; COR {cut["cor"]:.2f} steps. Full times unresolved.',.65,6.25,12,.65,20,purple)
    finish()
    slide=new('One trajectory gives block variation, not many independent replicas','9 | Sampling and stationarity',
       'Quarters are nonoverlapping and use means estimated within each segment. Their reporting lags are no more than one tenth of their durations. Halves provide integral comparisons. Do not call curves confidence intervals. Temperature and energy equilibration cannot be checked without logs.')
    pic(slide,'07_block_variation',.55,1.65,12.2,4.85)
    textbox(slide,f'Quarter G_cell range: {s["quarter_G_range"][0]:.4f}-{s["quarter_G_range"][1]:.4f}.',.65,6.6,12,.3,17,gray)
    finish()
    slide=new('Centering and saved cadence are part of the result','10 | Sensitivity checks',
       'Subtracting noisy molecular means changes connected self; total mean subtraction changes collective relaxation. Every-second-frame analysis tests saved-cadence sensitivity but does not recover fast unsaved motion. Initial 10% removal is not claimed to be a thermal equilibration cutoff.')
    pic(slide,'08_sensitivity',.55,1.7,12.2,4.5)
    textbox(slide,'Inspect centering, every-second-frame sampling, and initial-10% removal before interpreting the tail.',.65,6.35,12,.65,19,gray)
    finish()
    slide=new('What the supplied data establish','11 | Interpretation and next experiment',
       'Close with the strongest supported statements: complete audit, numerically validated geometric orientation correlations, exact cross decomposition, and quantified sensitivity. Missing metadata and independent longer sampling are concrete next steps, not presumed facts.')
    textbox(slide,'Established\nComplete-data integrity and stable molecular mapping\nValidated SMOR/COR and exact cross decomposition\nCutoff, block, centering and cadence diagnostics',.65,1.75,12,2.45,25,teal)
    textbox(slide,'Unresolved\nPhysical time, original force field and dielectric mapping\nConverged full relaxation times and their ordering\nNeed: original inputs/logs and longer independent records',.65,4.5,12,2.05,23,purple)
    finish()
    slide=new('Six-person speaking and review allocation','Appendix A | Team delivery',
       'These roles allocate presentation and review. Everyone should understand the exact decomposition and principal limitations. The complete reusable implementation is shared across the team.')
    for j,row in enumerate(allocation):
        y=1.70+j*.75;rect(slide,.65,y, .48,.48,teal)
        textbox(slide,row[0],.77,y+.03,.28,.4,17,'#ffffff',True)
        textbox(slide,row[1],1.35,y,4.25,.67,18,ink,True)
        textbox(slide,row[2],5.8,y,6.7,.6,18,gray)
    finish()
    slide=new('Prepare to defend definitions and limitations','Appendix B | Likely viva questions',
       '\n'.join(question+' '+answer for question,answer in viva))
    chosen=[viva[j] for j in [0,1,2,3,5,7]]
    for j,(question,answer) in enumerate(chosen):
        y=1.65+j*.79
        textbox(slide,question,.65,y,5.3,.65,19,ink,True)
        answer=answer.replace('Finite cutoffs, mean estimation and segment variation do not establish a stable full-time integral or tail.','Finite cutoffs and centering/block sensitivity leave the full integral unresolved.')
        textbox(slide,answer,6.15,y,6.45,.68,17,gray)
    finish()
    prs.save('reports/presentation.pptx');preview.save()
    pdf=pymupdf.open('reports/presentation_layout_preview.pdf')
    for i in [0,6,8,12,13]:pdf[i].get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(f'reports/previews/slide_{i+1:02}.png') if Path('reports/previews').exists() else None
    Path('reports/presentation_notes.md').write_text('\n\n'.join(f'# Slide {v["slide"]}: {v["title"]}\n\n{v["notes"]}' for v in slide_text),encoding='utf-8')
    return dict(slides=len(prs.slides),slide_text_overflows=overflow,editable_text_shapes=sum(1 for sl in prs.slides for sh in sl.shapes if sh.has_text_frame),
                slide_layout_preview_pages=len(pdf),slide_preview_file='reports/presentation_layout_preview.pdf')
