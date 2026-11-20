"""LaTeX-style mathematics drawn as embedded font glyphs in ReportLab PDFs."""
from functools import lru_cache
from pathlib import Path

from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import MathTextParser
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable


# Register a math font under a name based on its file and cache that name for reuse when laying
# out other glyphs.
@lru_cache(maxsize=None)
def _math_font(filename):
    name = 'ReportMath_' + Path(filename).stem
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, filename))
    return name


class MathEquation(Flowable):
    """Render a math expression as sharp, selectable vector text and rules."""

    # Parse a LaTeX-style expression with Matplotlib and build a ReportLab drawing from
    # positioned STIX glyphs and rules such as fraction bars.
    def __init__(self, expression, size=12):
        super().__init__()
        layout = MathTextParser('path').parse(
            '$' + expression + '$', dpi=72,
            prop=FontProperties(size=size, math_fontfamily='stix'),
        )
        self.drawing = Drawing(float(layout.width), float(layout.height) + 8)
        baseline = float(layout.depth) + 4
        ink = colors.HexColor('#173247')
        for glyph in layout.glyphs:
            # Matplotlib 3.11 includes a glyph index; earlier versions omit it.
            font, fontsize, code = glyph[:3]
            x, y = glyph[-2:]
            name = _math_font(font.fname)
            self.drawing.add(String(
                float(x), float(y) + baseline, chr(code),
                fontName=name, fontSize=float(fontsize), fillColor=ink,
            ))
        for x, y, width, height in layout.rects:
            self.drawing.add(Rect(
                float(x), float(y) + baseline, float(width), float(height),
                fillColor=ink, strokeColor=None,
            ))
        self.hAlign = 'CENTER'
        self.spaceAfter = 2
        self.scale = 1

    # Measure the equation at its current size and scale it down if it is wider than the
    # available layout space. Return the size ReportLab should reserve.
    def wrap(self, available_width, available_height):
        self.scale = min(1, available_width / max(self.drawing.width, 1))
        self.width = self.drawing.width * self.scale
        self.height = self.drawing.height * self.scale
        return self.width, self.height

    # Render the equation at the scale chosen during layout. Save and restore the canvas state
    # so the scale applies only to this equation.
    def draw(self):
        self.canv.saveState()
        self.canv.scale(self.scale, self.scale)
        renderPDF.draw(self.drawing, self.canv, 0, 0)
        self.canv.restoreState()
