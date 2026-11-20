"""Compact dataset-and-results report with shared PDF/LaTeX Markdown content."""
from pathlib import Path
import html
import json

import matplotlib.font_manager as fm
import numpy as np
import pymupdf
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle,
)

from .report_math import MathEquation


def register_report_fonts():
    for name, prop in [
        ('Report', fm.FontProperties(family='DejaVu Sans')),
        ('ReportBold', fm.FontProperties(family='DejaVu Sans', weight='bold')),
    ]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, fm.findfont(prop)))


def build_report(c):
    """Build only the report; use the saved measurements without rerunning MD analysis."""
    out = Path('reports')
    out.mkdir(exist_ok=True)
    s = json.loads(Path('results/summary.json').read_text())
    m = json.loads(Path('results/metadata.json').read_text())
    data = np.genfromtxt('results/correlations.csv', delimiter=',', names=True)
    full, geometry = s['full'], m['geometry']
    at = lambda key, lag: float(np.interp(lag, data['lag_steps'], data[key]))
    P = lambda text: ('paragraph', text)
    H = lambda text: ('heading', text)
    M = lambda text: ('math', text.replace(r'\frac', r'\dfrac'))
    T = lambda head, rows, widths: ('table', head, rows, widths)
    F = lambda name, caption: ('figure', name, caption)

    pages = [
        ('Dataset and molecular geometry', [
            P('Collective versus single-molecule orientational relaxation | CB4103'),
            P('The trajectory contains nearly rigid, water-like molecular groups. '
              'Individual and collective orientation correlations are compared using a '
              'normalized molecular-bisector proxy. All saved frames are retained.'),
            T(['Dataset property', 'Verified information'], [
                ['Source', f'dumpr.lammpstrj ({m["source"]["size_bytes"]:,} bytes)'],
                ['Composition', f'{m["atoms"]:,} atoms; {m["molecules"]:,} molecular groups'],
                ['Molecular grouping', 'One type-2 center and two type-1 satellites per group'],
                ['Saved record', f'{m["frames"]:,} complete frames; steps {m["first_step"]:,}–{m["last_step"]:,}'],
                ['Saving interval', f'Every {m["cadence"]} simulation steps'],
                ['Simulation box', f'Periodic cube; side length {m["box_lengths_min"][0]:.8f} dump units'],
                ['Coordinates and audit', 'Wrapped Cartesian coordinates; all frames, membership and intervals checked'],
                ['Unavailable metadata', 'Force field, units, timestep, charges, temperature, ensemble and dump-group completeness'],
            ], [.28, .72]),
            F('01_geometry',
              'Figure 1. Molecular-bisector schematic and bond-length/angle histories. '
              'Shaded envelopes show the minimum and maximum over every molecule in each frame; '
              'solid lines show the means. Atom-type chemistry is inferred.'),
            T(['Geometry measure', 'Mean', 'Observed range'], [
                ['Bond length / dump units', f'{geometry["bond_mean"]:.8f}',
                 f'{geometry["bond_min"]:.8f}–{geometry["bond_max"]:.8f}'],
                ['Internal angle / degrees', f'{geometry["angle_mean_degrees"]:.6f}°',
                 f'{geometry["angle_min_degrees"]:.6f}°–{geometry["angle_max_degrees"]:.6f}°'],
            ], [.36, .23, .41]),
            P(f'Minimum-image reconstruction corrects intramolecular boundary crossings for '
              f'{100 * geometry["mean_mic_molecule_fraction"]:.2f}% of groups per frame on average. '
              'The stable geometry supports an orientation proxy; it does not determine a charge model.'),
        ]),
        ('Orientation definitions and main correlations', [
            P('Bond vectors use the shortest periodic displacement, applied component by component. '
              'O and H label the inferred central and satellite sites; a labels either satellite.'),
            M(r'\mathbf{b}_{ia}=\mathbf{r}_{\mathrm{H}_a}-\mathbf{r}_{\mathrm{O}}'
              r'-\mathbf{L}\,\operatorname{round}\!\left('
              r'\frac{\mathbf{r}_{\mathrm{H}_a}-\mathbf{r}_{\mathrm{O}}}{\mathbf{L}}\right)'),
            M(r'\mathbf{u}_i=\frac{\mathbf{b}_{i1}+\mathbf{b}_{i2}}'
              r'{|\mathbf{b}_{i1}+\mathbf{b}_{i2}|},\qquad \mathbf{U}=\sum_{i=1}^{N}\mathbf{u}_i'),
            M(r'\mathbf{v}_i=\mathbf{u}_i-\overline{\mathbf{u}_i},\qquad '
              r'\delta\mathbf{U}=\mathbf{U}-\overline{\mathbf{U}}=\sum_i\mathbf{v}_i'),
            M(r'C_{\mathrm{SMOR}}(k)=\frac{1}{N}\sum_{i=1}^{N}'
              r'\langle\mathbf{u}_i(n)\cdot\mathbf{u}_i(n+k)\rangle'),
            M(r'A(k)=\sum_i\langle\mathbf{v}_i(n)\cdot\mathbf{v}_i(n+k)\rangle,'
              r'\qquad C_{\mathrm{conn}}(k)=\frac{A(k)}{A(0)}'),
            M(r'B(k)=\langle\delta\mathbf{U}(n)\cdot\delta\mathbf{U}(n+k)\rangle,'
              r'\qquad C_{\mathrm{COR}}(k)=\frac{B(k)}{B(0)}'),
            P('Here N is the molecule count, n indexes saved frames and k is a frame lag. '
              f'Each lag interval corresponds to {m["cadence"]} simulation steps. Brackets average all valid '
              'starting frames. Overbars use the same full record. Ordinary SMOR retains molecular '
              'means; connected self and COR measure fluctuations about their means.'),
            F('04_smor_cor',
              'Figure 2. Ordinary SMOR, connected molecular self and centered COR. '
              'The right panel expands the early decay; all delays are in simulation steps.'),
            T(['Lag / steps', 'SMOR', 'Connected self', 'COR'], [
                [f'{lag:,}'] + [f'{at(key, lag):.5f}' for key in ['smor', 'connected_self', 'cor']]
                for lag in [2500, 10000]
            ], [.22, .23, .30, .25]),
            P('The full-record collective correlation exceeds ordinary SMOR at both listed lags. '
              'Both retain positive correlation at 10,000 steps.'),
        ]),
        ('Collective contributions and spatial profiles', [
            P('The collective signal separates exactly into same-molecule self terms and '
              'different-molecule cross terms. Both contributions use the total zero-lag variance.'),
            M(r'C_{\mathrm{self}}(k)=\frac{A(k)}{B(0)},\qquad '
              r'C_{\mathrm{cross}}(k)=\frac{B(k)-A(k)}{B(0)}'),
            M(r'C_{\mathrm{COR}}(k)=C_{\mathrm{self}}(k)+C_{\mathrm{cross}}(k),'
              r'\qquad G_{\mathrm{cell}}=\frac{B(0)}{A(0)}=' + f'{full["G_cell"]:.4f}'),
            F('05_decomposition',
              'Figure 3. Exact collective self/cross decomposition. At every lag, '
              'the two contributions sum to COR. Cross contributions may be negative.'),
            T(['Lag / steps', 'Collective self', 'Collective cross', 'Sum / COR'], [
                [f'{lag:,}'] + [f'{at(key, lag):.5f}' for key in ['collective_self', 'collective_cross', 'cor']]
                for lag in [0, 2500]
            ], [.19, .27, .29, .25]),
            P(f'Cross terms contribute {100 * (1 - 1 / full["G_cell"]):.2f}% of the normalized '
              'zero-lag collective signal. The finite-cell factor describes fluctuation amplitudes; '
              'it does not by itself determine relaxation-time ordering.'),
            F('02_spatial_profiles',
              'Figure 4. Molecular-center counts in 24 fractional-coordinate bins per axis, '
              'shown separately for each trajectory quarter. A value of one indicates uniform-bin counts.'),
            P('Maximum full-record deviations from uniform counts are '
              + ', '.join(f'{axis}: {100 * value:.2f}%' for axis, value in
                          zip('xyz', s['spatial_diagnostics']['max_abs_deviation_from_uniform_by_axis']))
              + '. These projected counts do not establish a bulk phase or thermal equilibration.'),
        ]),
        ('Running integrals and result limits', [
            P('Running integrals measure accumulated orientation correlation through a declared '
              'upper cutoff. Numerical integration uses the trapezoidal rule.'),
            M(r'I_C(T)=\int_0^T C(\tau)\,\mathrm{d}\tau'),
            F('06_running_integrals',
              'Figure 5. Finite-cutoff running integrals and their collective self/cross contributions. '
              'The curves continue to increase near the final cutoff; full relaxation times remain unresolved.'),
            T(['Cutoff / steps', 'SMOR integral', 'Connected integral', 'COR integral'], [
                [f'{cutoff:,}'] + [f'{full["truncated_integrals_steps"][str(cutoff)][key]:,.2f}'
                                  for key in ['smor', 'connected_self', 'cor']]
                for cutoff in [1000, 2500, 5000, 10000]
            ], [.22, .25, .28, .25]),
            P('All integral values are in simulation steps. During the final 2,000 steps of the '
              f'reporting window, the SMOR and COR integrals increase by '
              f'{full["tail_diagnostics"]["smor"]["last_20_percent_integral_drift_steps"]:.1f} and '
              f'{full["tail_diagnostics"]["cor"]["last_20_percent_integral_drift_steps"]:.1f} steps, respectively. '
              'The reported areas therefore remain dependent on the cutoff.'),
            H('Sampling and numerical checks'),
            P(f'Quarter-record estimates of the finite-cell factor range from '
              f'{s["quarter_G_range"][0]:.4f} to {s["quarter_G_range"][1]:.4f}, showing segment sensitivity. '
              'These blocks do not provide independent-run confidence intervals. '
              'Direct correlation and explicit pair-sum checks agree with the fast estimator '
              'within floating-point precision; the maximum full-record decomposition error is '
              f'{full["decomposition_max_abs_error"] / 1e-16:.2f} × 10⁻¹⁶.'),
            H('Interpretation'),
            P('The supplied record shows substantial intermolecular contributions and a larger '
              'collective correlation at the reported lags. Missing timestep and charge information '
              'restrict the results to simulation-step units and a geometric orientation proxy. '
              'Finite-record mean subtraction and segment variation limit the long-time '
              'interpretation; converged full relaxation times and dielectric response are not established.'),
            H('Method reference and result files'),
            P('Maurya, Metya, Singh and Saito (2021), Journal of Chemical Physics 154, 164704. '
              'DOI: 10.1063/5.0046817. Orientation-correlation definitions are adapted to the supplied dataset.'),
            P('Dataset audit: results/metadata.json. Measured curves: results/correlations.csv. '
              'Integrals and sensitivity results: results/summary.json. '
              'Numerical checks: results/numerical_checks.json.'),
        ]),
    ]

    register_report_fonts()
    styles = getSampleStyleSheet()
    for name, size, leading, color, extra in [
        ('BodyR', 9.1, 12.6, '#243449', {'spaceAfter': 7}),
        ('HeadR', 18, 22, '#12344a', {'spaceAfter': 12, 'fontName': 'ReportBold'}),
        ('SubR', 10.5, 14, '#007c91', {'spaceBefore': 5, 'spaceAfter': 5, 'fontName': 'ReportBold'}),
        ('CaptionR', 7.4, 10, '#59697a', {'spaceAfter': 8}),
        ('CellR', 8.1, 11, '#243449', {}),
    ]:
        options = dict(fontName='Report', fontSize=size, leading=leading, textColor=colors.HexColor(color))
        options.update(extra)
        styles.add(ParagraphStyle(name=name, **options))
    para = lambda text, style='BodyR': Paragraph(html.escape(str(text)), styles[style])
    story, markdown, figure_names, math_count = [], [
        '# Collective versus single-molecule orientational relaxation', '',
        'CB4103 | Concise dataset and results report', '',
    ], [], 0
    doc = SimpleDocTemplate(
        str(out / 'final_report.pdf'), pagesize=A4,
        rightMargin=47, leftMargin=47, topMargin=42, bottomMargin=48,
        title='Collective versus single-molecule orientational relaxation', author='CB4103 project team',
    )
    for index, (title, elements) in enumerate(pages):
        if index:
            story.append(PageBreak())
        story.append(para(title, 'HeadR'))
        markdown.extend(['## ' + title, ''])
        for element in elements:
            kind = element[0]
            if kind in ['paragraph', 'heading']:
                story.append(para(element[1], 'SubR' if kind == 'heading' else 'BodyR'))
                markdown.extend([('### ' if kind == 'heading' else '') + element[1], ''])
            elif kind == 'math':
                story.append(MathEquation(element[1]))
                markdown.extend(['$$', element[1], '$$', ''])
                math_count += 1
            elif kind == 'table':
                header, rows, widths = element[1:]
                table = Table(
                    [[para(cell, 'CellR') for cell in row] for row in [header] + rows],
                    colWidths=[width * doc.width for width in widths], repeatRows=1, hAlign='LEFT',
                )
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dceaf0')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f7f9')]),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LINEBELOW', (0, 0), (-1, 0), .6, colors.HexColor('#9cb5c2')),
                ]))
                story.extend([table, Spacer(1, 8)])
                markdown.extend(['| ' + ' | '.join(header) + ' |', '| ' + ' | '.join(['---'] * len(header)) + ' |'])
                markdown.extend(['| ' + ' | '.join(map(str, row)) + ' |' for row in rows] + [''])
            elif kind == 'figure':
                name, caption = element[1:]
                path = Path('figures') / (name + '.png')
                with PILImage.open(path) as picture:
                    width, height = picture.size
                display_width = doc.width - 12
                story.append(KeepTogether([
                    Image(str(path), width=display_width, height=display_width * height / width),
                    para(caption, 'CaptionR'),
                ]))
                markdown.extend([f'![{caption}](../figures/{name}.png)', '', caption, ''])
                figure_names.append(name)

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#c1d2dc'))
        canvas.line(47, 37, A4[0] - 47, 37)
        canvas.setFont('Report', 7)
        canvas.setFillColor(colors.HexColor('#647588'))
        canvas.drawString(47, 25, 'CB4103 | Geometric orientation analysis | Simulation-step units')
        canvas.drawRightString(A4[0] - 47, 25, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    (out / 'final_report.md').write_text('\n'.join(markdown), encoding='utf-8')
    preview_dir = out / 'previews'
    preview_dir.mkdir(exist_ok=True)
    with pymupdf.open(out / 'final_report.pdf') as pdf:
        # Remove only obsolete numbered report previews; preserve slide previews.
        for preview in preview_dir.glob('report_page_*.png'):
            preview.unlink()
        previews = []
        for index, page in enumerate(pdf):
            path = preview_dir / f'report_page_{index + 1:02}.png'
            page.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4)).save(path)
            previews.append(path.as_posix())
        report_info = dict(
            report_pages=len(pdf), planned_content_pages=len(pages),
            report_page_text_lengths=[len(page.get_text()) for page in pdf],
            representative_report_previews=previews,
            report_math_blocks=math_count, report_math_format='LaTeX-style vector text with embedded STIX fonts',
            report_figures=figure_names,
        )
    inspection_path = Path('results/document_inspection.json')
    inspection = json.loads(inspection_path.read_text()) if inspection_path.exists() else {}
    inspection.update(report_info)
    inspection_path.write_text(json.dumps(inspection, indent=2), encoding='utf-8')
    print('Report built:', json.dumps(report_info), flush=True)
    return report_info
