"""Render the link preview. Optional dependency: Pillow."""
from pathlib import Path
from math import sqrt
from PIL import Image, ImageDraw, ImageFont

image = Image.new('RGB', (1200, 630), '#f3f1e9')
draw = ImageDraw.Draw(image)
ink, muted, accent = '#26312b', '#697169', '#b84f2b'
# Pillow's built-in font has no "ő"; use Inter or DejaVu when the system has one.
FONTS = [Path('/usr/share/fonts/opentype/inter/Inter-Medium.otf'), Path('/Library/Fonts/Inter-Medium.otf'),
         Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
def font(size):
    for path in FONTS:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)
def text(x, y, value, size, color=ink):
    draw.text((x, y), value, font=font(size), fill=color)
text(60, 50, 'few-distance lab', 25)
text(60, 150, 'Place 20 points.', 64)
text(60, 232, 'Use only 17 distances.', 54, accent)
text(62, 346, 'A geometry puzzle from an Erdős problem.', 27)
text(62, 396, 'Every board has a proven minimum. Reach it.', 23, muted)
text(62, 550, 'By Dhiraj Khanal', 22, muted)
draw.rounded_rectangle((745, 40, 1150, 590), 22, fill='#252f2b')
spacing, left, top = 52, 791, 94
# A game in progress, not a solution: the preview should not spoil the board.
chosen = {(0, 0), (2, 0), (4, 0), (0, 1), (2, 1), (4, 1), (0, 2), (2, 2), (5, 4)}
for i in range(7):
    x, y = left + i * spacing, top + i * spacing * sqrt(2)
    draw.line((x, top, x, top + 6 * spacing * sqrt(2)), fill='#465047', width=1)
    draw.line((left, y, left + 6 * spacing, y), fill='#465047', width=1)
for y in range(7):
    for x in range(7):
        px, py = left + x * spacing, top + (6 - y) * spacing * sqrt(2)
        r = 9 if (x, y) in chosen else 4
        draw.ellipse((px - r, py - r, px + r, py + r), fill='#d2e4b7' if (x, y) in chosen else '#738075')
image.save(Path(__file__).resolve().parents[1] / 'web/social-card.png', optimize=True)
