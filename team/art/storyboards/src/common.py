import math
from ink import *
from zones import *
OUT="/workspace/inkborne/team/art/storyboards"
PW=768
def reserved(p,label=True,fs=11):
    for (c,n,x,y,w,h,_) in RESERVED:
        p.rect(x,y,w,h,W1,200,2,(3,3),fill=(163,156,140,60))
        if c=="M": p.text("☰",x+w/2,y+h/2+2,26,W1,"bold","mm")
        elif c=="T1":
            p.ellipse(x+w/2,y+h/2,58,58,2,W2,170); p.ellipse(x+w/2,y+h/2,22,22,2,W2,200)
        else:
            p.ellipse(x+130,y+70,34,34,2,W2,190); p.text("A",x+130,y+70,22,W1,"bold","mm")
            p.ellipse(x+58,y+128,28,28,2,W2,190); p.text("B",x+58,y+128,18,W1,"bold","mm")
        if label: p.tag(f"{c} {n}",x,y,w,h,W1,"bl" if c!="M" else "below",fs)
def zones(p,screen,codes=None,fs=11,red=()):
    for (c,n,x,y,w,h,_) in Z[screen]:
        if codes and c not in codes: continue
        if w==0 or x==0: continue
        p.zone(c,n,x,y,w,h,red=c in red,fs=fs)
def zone_at(p,screen,code,x,y,fs=11,red=False,centre=True):
    for (c,n,_,_,w,h,_) in Z[screen]:
        if c==code:
            X=x-w/2 if centre else x; p.zone(c,n,X,y,w,h,red=red,fs=fs); return
def wireframe(screen,seed=3,extra=None):
    p=Panel(PW,seed=seed)
    p.rect(64,36,1152,648,W2,160,1,(4,6)); p.text("safe 64 / 36",70,688,11,W2)
    if extra: extra(p)
    for (c,n,x,y,w,h,_) in Z[screen]:
        if x==0: continue
        p.zone(c,n,x,y,w,h,fs=12); p.text(f"{x},{y} {w}×{h}",x+4,y+h-4,10,W1,anchor="ld")
    reserved(p,True,12)
    for (c,n,x,y,w,h,_) in RESERVED: p.text(f"{x},{y} {w}×{h}",(x-150 if c=='M' else x+4),(y+70 if c=='M' else y+16),10,W1,anchor="la")
    return p
def save(title,sub,panels,cols,fname,**kw):
    path=f"{OUT}/{fname}"; board(title,sub,panels,cols,path,pw=PW,**kw); print("wrote",path); return path
HEAD="TABULA RASA demo · Storyboard "
SUB="logical 1280×720 (SPEC v1.1) · sumi-e ink, single vermilion accent · zones per src/zones.py"
