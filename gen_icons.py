import io
from PIL import Image, ImageDraw

def make_icon(size):
    img = Image.new('RGB', (size, size), (7, 9, 14))
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / size
        d.line([(0,y),(size,y)], fill=(int(20+35*t), int(20+10*t), int(30+20*t)))
    mask = Image.new('L', (size,size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0,0,size-1,size-1], size//5, fill=100)
    overlay = Image.new('RGB', (size,size), (7,9,14))
    img = Image.composite(overlay, img, mask)
    d = ImageDraw.Draw(img)
    d.ellipse([size*0.06, size*0.06, size*0.94, size*0.94], outline=(245,158,11), width=max(2,size//40))
    pts = [(0.57,0.10),(0.29,0.56),(0.47,0.56),(0.42,0.90),(0.73,0.44),(0.54,0.44),(0.58,0.10)]
    d.polygon([(x*size, y*size) for x,y in pts], fill=(251,191,36))
    buf = io.BytesIO(); img.save(buf, 'PNG')
    return buf.getvalue()

import os
for dpi, px in [('mdpi',48),('hdpi',72),('xhdpi',96),('xxhdpi',144),('xxxhdpi',192)]:
    p = f'app/src/main/res/mipmap-{dpi}'
    os.makedirs(p, exist_ok=True)
    open(f'{p}/ic_launcher.png','wb').write(make_icon(px))
print('icons ok')
