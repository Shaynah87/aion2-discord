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


def format_line(line, now):
    if isinstance(line, str):
        return line
    from datetime import datetime
    date = datetime.fromisoformat(line['date'])
    result = f"{line['text']} *({date:%d.%m.%Y})*"
    # Bei unbekannter Wartungsendzeit erst nach bestätigtem Release umstellen.
    release_at = line.get('release_at')
    released = line.get('released', False)
    if release_at:
        target = datetime.fromisoformat(release_at)
        if target.tzinfo is None:
            target = target.replace(tzinfo=now.tzinfo)
        released = released or now >= target
    return result if released else result + ' 🟠 **Kommend**'


def render(folder, now):
    data = json.loads((folder / 'season_data.json').read_text(encoding='utf-8'))
    for i, month in enumerate(data['months'], 1):
        sections = [(name, lines) for name, lines in month['sections'] if name != 'Weitere Inhalte' and lines]
        if not sections:
            continue
        prefix = f'month_{i:02}'
        yield prefix + '_banner', {'content': ''}, [banner(folder, month['title'], i)]
        blocks = []
        part = 0
        def flush():
            nonlocal part
            if blocks:
                part += 1
                body = '\n\n'.join(blocks)
                blocks.clear()
                return (f'{prefix}_part_{part:02}', {'content': body}, [])
        for name, lines in sections:
            heading = '**Schwer**' if name == 'Expedition – Schwer' and i == 1 else f'## {name}'
            block = heading + '\n' + '\n'.join(format_line(line, now) for line in lines)
            if len(block) > 1900:
                raise ValueError(f'Abschnitt zu lang: {name}')
            if len('\n\n'.join(blocks + [block])) > 1900:
                yield flush()
            blocks.append(block)
            if name == 'Albtraum':
                yield flush()
                yield prefix + '_albtraum', {'content': ''}, [nightmare(folder)]
        if blocks:
            yield flush()
