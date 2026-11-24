"""Season-Roadmap: native Discord-Texte, Monatsbanner und Albtraum-Diagramm."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype(name, size)


def banner(folder, title, index):
    path = folder / f'month_{index:02}_banner.png'
    im = Image.new('RGB', (1200, 110), '#292b30')
    d = ImageDraw.Draw(im)
    d.text((600, 55), title, font=font(46, True), fill='#f2f3f5', anchor='mm')
    im.save(path)
    return path


def nightmare(folder):
    path = folder / 'albtraum.png'
    im = Image.new('RGBA', (1200, 380), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x, y, end in [(360, 48, 94), (360, 140, 94), (360, 240, 286), (360, 332, 286)]:
        d.line([(x,y),(400,y),(400,end),(440,end)], fill='#92959d', width=3)
    for y in (94,286):
        d.line([(760,y),(800,y),(800,190),(840,190)], fill='#92959d', width=3)
    def node(x,y,w,label,bg,fg):
        d.rounded_rectangle((x,y-34,x+w,y+34), radius=9, fill=bg)
        d.text((x+w/2,y),label,font=font(27,True),fill=fg,anchor='mm')
    for y,label in zip((48,140,240,332),('Torwächter Pinopi','Rasender Feruk','Fafnirs Giftblut','Geist Giselle')):
        node(10,y,350,label,'#33353c','#eeeeee')
    node(440,94,320,'Festenhüter Notun','#24382d','#75c987')
    node(440,286,320,'Mutierter Gerod','#24382d','#75c987')
    node(840,190,350,'Zikels Schemen','#23394e','#78b5ed')
    im.save(path)
    return path


def media(path):
    return {'type':12,'items':[{'media':{'url':f'attachment://{path.name}'}}]}


def render(folder):
    data = json.loads((folder / 'season_data.json').read_text(encoding='utf-8'))
    for i, month in enumerate(data['months'], 1):
        sections = [(name, lines) for name, lines in month['sections'] if name != 'Weitere Inhalte' and lines]
        if not sections:
            continue
        files = [banner(folder, month['title'], i)]
        components = [media(files[0])]
        for name, lines in sections:
            if name != 'Expedition – Schwer':
                components.append({'type':14,'divider':True,'spacing':1})
            heading = '**Schwer**' if name == 'Expedition – Schwer' and month['title'].startswith('OKTOBER') else f'### {name}'
            body = '\n'.join(lines)
            components.append({'type':10,'content':f'{heading}\n{body}'})
            if name == 'Albtraum':
                files.append(nightmare(folder))
                components.append(media(files[-1]))
        yield f'month_{i:02}', {'flags':32768,'allowed_mentions':{'parse':[]},'components':[{'type':17,'components':components}]}, files
