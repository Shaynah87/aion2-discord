import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent

def font(size, bold=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf', size)

def render(folder):
    data=json.loads((folder/'season_data.json').read_text(encoding='utf-8'))
    for mi, month in enumerate(data['months']):
        # Separate consecutive panels keep the inline Discord preview readable.
        chunks=[]; current=[]; height=100
        for name, lines in month['sections']:
            h=85+len(lines)*48+(340 if name=='Albtraum' else 0)
            if current and height+h>850:
                chunks.append(current); current=[]; height=100
            current.append((name,lines,h)); height+=h
        if current: chunks.append(current)
        for pi, sections in enumerate(chunks):
            im=Image.new('RGB',(1200,110+sum(s[2] for s in sections)),month['color']); d=ImageDraw.Draw(im)
            d.text((600,46),month['title']+(f' · {pi+1}/{len(chunks)}' if len(chunks)>1 else ''),font=font(40,True),anchor='mm',fill='#ffffff')
            y=100
            for name,lines,h in sections:
                d.rounded_rectangle((24,y,1176,y+h-12),radius=12,fill='#171e29')
                d.text((48,y+15),name,font=font(35,True),fill='#ffffff')
                for j,line in enumerate(lines):
                    d.text((48,y+64+j*48),line,font=font(29),fill='#e2e7ef')
                if name=='Albtraum':
                    top=y+115
                    left=['Torwächter Pinopi','Rasender Feruk','Fafnirs Giftblut','Geist Giselle']
                    for i,t in enumerate(left):
                        yy=top+i*65; d.rounded_rectangle((45,yy,405,yy+48),8,fill='#303945'); d.text((225,yy+24),t,font=font(25),anchor='mm',fill='white')
                        mid=top+32+(i//2)*130+24
                        d.line([(405,yy+24),(430,yy+24),(430,mid),(455,mid)],fill='#9aa8ba',width=3)
                    for i,t in enumerate(['Festenhüter Notun','Mutierter Gerod']):
                        yy=top+32+i*130; d.rounded_rectangle((455,yy,805,yy+48),8,fill='#203b2b'); d.text((630,yy+24),t,font=font(25),anchor='mm',fill='#77df89'); d.line([(805,yy+24),(830,yy+24),(830,top+121),(855,top+121)],fill='#9aa8ba',width=3)
                    d.rounded_rectangle((855,top+97,1155,top+145),8,fill='#183551'); d.text((1005,top+121),'Zikels Schemen',font=font(25,True),anchor='mm',fill='#70baff')
                y+=h
            path=folder/f'roadmap_{mi+1:02}_{pi+1:02}.png'; im.save(path); yield path


