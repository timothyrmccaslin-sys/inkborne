from ink import *
from common import OUT
import glob,os
files=sorted(f for f in glob.glob(OUT+"/0[1-6]*.png"))
TW=760; M=36; cols=3
thumbs=[]
for f in files:
    im=Image.open(f).convert("RGB"); h=int(im.height*TW/im.width); thumbs.append((os.path.basename(f),im.resize((TW,h),Image.LANCZOS)))
rows=[thumbs[i:i+cols] for i in range(0,len(thumbs),cols)]
rh=[max(t.height for _,t in r) for r in rows]
W=M+cols*(TW+M); H=150+sum(h+60 for h in rh)+40
B=paper(W,H,9); d=ImageDraw.Draw(B)
d.text((M,28),"INKBORNE demo · Storyboards · Contact sheet",font=font(46,"serifb"),fill=INK)
d.text((M,92),"01 world map · 02 Sumikage Wood · 03 Hanshi · 04 dialogue · 05 shop · 06 boss battle: Smudge Ronin + Unfurl · 06b standard battle",font=font(19,"serif"),fill=W1)
d.line([(M,135),(W-M,135)],fill=INK,width=3)
y=150
for r,hh in zip(rows,rh):
    for c,(n,t) in enumerate(r):
        x=M+c*(TW+M); B.paste(t,(x,y)); d.rectangle([x,y,x+TW-1,y+t.height-1],outline=INK,width=2)
        d.text((x,y+t.height+8),n,font=font(20,"serifb"),fill=INK)
    y+=hh+60
d.text((M,H-30),"Rough layout thumbnails by Helen (storyboard). Full boards and LAYOUT_NOTES.md alongside this file.",font=font(15,"sans"),fill=W2)
B.save(OUT+"/00_contact_sheet.png",optimize=True); print("wrote contact sheet",B.size)
