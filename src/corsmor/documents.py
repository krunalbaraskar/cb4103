"""Build the concise report and the editable presentation with a layout preview."""
from pathlib import Path
import html
import json


def build_documents(c):
    from .report import build_report

    build_report(c)
    s = json.loads(Path('results/summary.json').read_text())
    m = json.loads(Path('results/metadata.json').read_text())
    n = json.loads(Path('results/numerical_checks.json').read_text())
    test_path = Path('results/test_results.json')
    test = json.loads(test_path.read_text()) if test_path.exists() else {}
    allocation=[['1','Question, literature, provenance','Opening, published benchmarks, unknown metadata'],['2','Reader and molecular reconstruction','Full integrity, MIC geometry, cache provenance'],['3','SMOR and connected self','Orientation choice, centering, running integrals'],['4','COR and intermolecular terms','Common denominator, factor, negative cross'],['5','Validation and sampling','FFT/direct, pair sums, blocks, convergence limits'],['6','Figures and reproducibility','Artifact navigation, commands, closing interpretation']]
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
    presentation_info = build_presentation(s, m, n, test, allocation, viva)
    inspection_path = Path('results/document_inspection.json')
    inspection = json.loads(inspection_path.read_text())
    inspection.update(presentation_info)
    inspection.update(
        native_powerpoint_render_available=False,
        presentation_preview_note='Companion PDF renders the same editable slide text/image geometry; '
                                  'it is a layout preview, not a native PowerPoint rendering.',
    )
    inspection_path.write_text(json.dumps(inspection, indent=2), encoding='utf-8')
    print('Documents built:', json.dumps(inspection), flush=True)


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
