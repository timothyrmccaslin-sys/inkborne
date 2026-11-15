"""Shared battle-board helpers (boards 06 and 06b)."""
from common import *
from b04_dialogue import zr
from b02_forest import forest_far
S=STAGE
def bg(p,knock=110,dark=False):
    forest_far(p)
    p.wash([(0,470),(1280,440),(1280,720),(0,720)],W3,110,10)
    p.stroke([(0,500),(1280,470)],4,W2,110,dry=0.6)
    p.wash([(0,0),(1280,0),(1280,720),(0,720)],PAPER,knock,1)
    if dark: p.wash([(0,0),(1280,0),(1280,720),(0,720)],W1,90,1)
def party(p,itsuki=True,ipos=None,ipose="idle",bpose="idle",gpose="idle",a_dim=False):
    fig_benika(p,*S["benika"],170,1,bpose)
    if itsuki: fig_itsuki(p,*(ipos or S["itsuki"]),200,1,ipose)
    fig_gonzo(p,*S["gonzo"],230,1,gpose)
def foes(p,ronin=True,lantern=False,blot=False,flame=0.5):
    if lantern: fig_lantern(p,*S["lantern"],1.0,flame)
    if ronin: fig_ronin(p,*S["ronin"],260 if not (lantern or blot) else 240,-1)
    if blot: fig_blotling(p,*S["blotling"],1.0)
def turn_order(p,order,cur=0):
    x,y,w,h=zr("battle","B1")
    for i,n in enumerate(order):
        cx=x+28+i*58; enemy=n[0].islower()
        p.ellipse(cx,y+h/2,20,20,2.5,W1 if enemy else INK,230,fill=((W3 if enemy else PAPER),230))
        p.text(n[:2].title(),cx,y+h/2,12,INK,"bold","mm")
        if i==cur: p.ellipse(cx,y+h/2,25,25,3,RED,240)
def hud(p,ink=(58,40,30),hp=(214,177,288),act=0,inkwing=None,pulse=False):
    x,y,w,h=zr("battle","B4"); names=["Itsuki","Benika","Gonzō"]; mx=[214,177,288]
    for i in range(3):
        cx=x+i*248; p.rect(cx,y,240,h,INK if i==act else W1,240,3 if i==act else 1,fill=(250,247,240,230))
        p.ellipse(cx+30,y+h/2,22,22,2.5,INK,230,fill=((W3 if i!=0 or inkwing is None else GALE),200))
        p.text(names[i],cx+62,y+18,15,INK,"serifb","lm")
        if inkwing is not None and i==0: p.text(f"{inkwing} turns",cx+232,y+18,10,GALE,"bold","rm")
        p.text(f"{hp[i]}",cx+232,y+18 if (inkwing is None or i) else y+40,12,W1,"bold","rm") if False else None
        p.bar(cx+62,y+38,166,14,hp[i]/mx[i],W1); p.text("HP",cx+58,y+45,9,W2,"bold","rm")
        p.bar(cx+62,y+64,166,14,ink[i]/100,RED); p.text("INK",cx+58,y+71,9,W2,"bold","rm")
        if pulse and ink[i]>=100: p.blob(cx+145,y+71,100,18,RED,70,8)
def banner(p,txt,red=False,fs=24):
    x,y,w,h=zr("battle","B3"); p.stroke([(x+10,y+h/2),(x+w-10,y+h/2)],h*0.9,RED if red else INK,245,taper=(0.04,0.08),dry=0.0,jit=0.5)
    p.stroke([(x+w*0.2,y+h-4),(x+w*0.8,y+h-6)],3,PAPER,120,dry=0.6)
    p.text(txt,x+w/2,y+h/2,fs,PAPER,"serifb","mm")
def menu(p,items,sel=0,dim=(),title="Itsuki",lit=()):
    x,y,w,h=zr("battle","B5"); p.rect(x,y,w,h,INK,235,2,fill=(250,247,240,240))
    p.text(title,x+16,y+22,16,INK,"serifb","lm"); p.line([(x+12,y+40),(x+w-12,y+40)],1.5,W2)
    for i,t in enumerate(items):
        yy=y+44+i*40; c=W3 if t in dim else (RED if t in lit else INK)
        if i==sel: p.stroke([(x+14,yy+32),(x+w-20,yy+31)],5,RED,240,dry=0.2)
        p.text(t,x+24,yy+18,16,c,"serifb" if i==sel else "serif","lm")
def target_plate(p,name,frac):
    x,y,w,h=zr("battle","B2"); p.rect(x,y,w,h,INK,230,1,fill=(250,247,240,220))
    p.text(name,x+14,y+h/2,15,INK,"serifb","lm"); p.bar(x+200,y+16,184,14,frac,W1)
def ring(p,cx,cy,frac,clean=False,miss=False):
    """target circle r=48 at the hit point; outer ring closes from r=96 (frac 0) to r=48 (frac 1)"""
    p.ellipse(cx,cy,48,48,4,INK,230); p.ellipse(cx,cy,40,40,1.5,RED if clean else W2,200)
    r=96-48*frac
    if miss: p.ellipse(cx,cy,r,r,3,W3,200,arc=(0,300)); return
    if frac>0.5:
        for rr in (96,80,64): p.ellipse(cx,cy,rr,rr,1.5,W2,110,arc=(200,340))  # closing trail
    p.ellipse(cx,cy,r,r,5 if frac<1 else 8,RED if clean else INK,235)
    if clean:
        for k in range(10):
            t=k*0.628; p.line([(cx+math.cos(t)*58,cy+math.sin(t)*58),(cx+math.cos(t)*82,cy+math.sin(t)*82)],3,RED,220)
def pips(p,states,cx=None,y=None):
    x,y0,w,h=zr("battle","B7"); n=len(states); cx=cx or x+w/2; y=y or y0+h/2
    for i,s_ in enumerate(states):
        px=cx+(i-(n-1)/2)*44
        if s_=="clean": p.blob(px,y,13,13,RED,240,1,0.1)
        elif s_=="good": p.blob(px,y,13,13,W1,230,1,0.1)
        elif s_=="miss": p.ellipse(px,y,12,12,2,W2,200); p.line([(px-10,y-8),(px+10,y+8)],2,W1)
        else: p.ellipse(px,y,12,12,2,W2,200)
def dmg(p,x,y,txt,red=False,fs=24): p.text(txt,x,y,fs,RED if red else INK,"serifb","mm",bg=(250,247,240,150))
def std(p,order_cur=1,ink=(58,40,30),act=0,**k):
    turn_order(p,ORDER,order_cur); hud(p,ink,act=act,**k); reserved(p,False)
ORDER=["Benika","Itsuki","ronin","Gonzō"]  # spd order from data: 20, 17, 13, 10
