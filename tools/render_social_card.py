"""Render the challenge link preview. Optional dependency: Pillow."""
from pathlib import Path
from math import sqrt
from PIL import Image, ImageDraw, ImageFont

image = Image.new('RGB', (1200, 630), '#f3f1e9')
draw = ImageDraw.Draw(image)
ink, muted, accent = '#26312b', '#697169', '#b84f2b'
def text(x, y, value, size, color=ink):
    draw.text((x, y), value, font=ImageFont.load_default(size=size), fill=color)
text(60, 50, 'few-distance lab', 25)
text(60, 156, 'Place 8 dots.', 64)
text(60, 236, 'Use just 6 lengths.', 57, accent)
text(62, 350, 'A small geometry puzzle.', 28)
text(62, 400, 'Play. Find a pattern. Share your board.', 23, muted)
text(62, 550, 'By Dhiraj Khanal', 22, muted)
draw.rounded_rectangle((730, 45, 1150, 585), 22, fill='#252f2b')
spacing = 86
for i in range(4):
    x, y = 811+i*spacing, 130+i*spacing*sqrt(2)
    draw.line((x,130,x,130+3*spacing*sqrt(2)), fill='#465047', width=1)
    draw.line((811,y,811+3*spacing,y), fill='#465047', width=1)
for y in range(4):
    for x in range(4):
        px, py = 811+x*spacing, 130+y*spacing*sqrt(2)
        selected = (x,y) in {(0,0),(2,1),(1,3)}
        r = 10 if selected else 6
        draw.ellipse((px-r,py-r,px+r,py+r), fill='#d2e4b7' if selected else '#738075')
image.save(Path(__file__).resolve().parents[1] / 'web/social-card.png', optimize=True)
