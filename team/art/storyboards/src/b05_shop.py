from common import *
from b04_dialogue import zr
ITEMS=[("Rice Cake",15,3),("Plum Tonic",60,1),("Pot of Pine Tea",120,0),("Festival Bento",280,0),("Inkstone Chip",40,2),("Pot of Fresh Ink",110,0),("Paper Firecracker",50,0),("Thunder Jar",150,0)]
def interior(p):
    p.wash([(0,0),(1280,0),(1280,720),(0,720)],SHADE,90,1)
    for x in range(0,1280,160): p.line([(x,0),(x,720)],2,W3,120)
    for y in (160,300,440): p.stroke([(0,y),(1280,y)],8,W2,110,dry=0.6)  # shelves
    for x in range(40,1280,90):
        for y in (160,300,440): p.blob(x,y-22,16,20,W2,90,3)  # jars
    p.wash([(0,0),(1280,0),(1280,720),(0,720)],PAPER,120,1)
def tsuru(p,rect):
    x,y,w,h=rect; cx=x+w/2
    p.wash([(x+w*0.1,y+h),(x+w*0.2,y+h*0.6),(x+w*0.8,y+h*0.6),(x+w*0.9,y+h)],W1,210,2)
    p.ellipse(cx,y+h*0.42,w*0.16,h*0.15,3,INK,235,fill=(PAPER,255))
    p.blob(cx,y+h*0.24,w*0.12,h*0.06,W3,240,1)  # grey bun
    p.line([(cx-w*0.08,y+h*0.42),(cx-w*0.02,y+h*0.43)],2,INK); p.line([(cx+w*0.03,y+h*0.43),(cx+w*0.09,y+h*0.42)],2,INK)
    for k in (0.36,0.48): p.line([(cx-w*0.1,y+h*k),(cx-w*0.13,y+h*(k+0.02))],1,W2)  # wrinkles
    p.line([(cx-w*0.04,y+h*0.5),(cx+w*0.05,y+h*0.5)],2,INK)
DESC={"Plum Tonic":["Sour enough to wake","the dead, nearly.","Restores 200 HP","to one ally."],"Rice Cake":["Sweet and filling.","Restores 50 HP","to one ally."]}
def shop_ui(p,tab="Buy",sel=1,qty=None,line="Plum Tonic? Wakes the dead. Nearly."):
    items=ITEMS if tab=="Buy" else [(n,pr//2,o) for (n,pr,o) in ITEMS if o>0]
    x,y,w,h=zr("shop","S1")
    for i,t in enumerate(["Buy","Sell"]):
        p.text(t,x+80+i*160,y+h/2,22,INK,"serifb","mm")
        if t==tab: p.stroke([(x+40+i*160,y+h-8),(x+120+i*160,y+h-10)],6,RED,240,dry=0.2)
    x,y,w,h=zr("shop","S2"); p.text("Kōbō Tsuru",x+w/2,y+h/2,26,INK,"serifb","mm")
    x,y,w,h=zr("shop","S3"); p.ellipse(x+14,y+h/2,12,12,3,INK); p.text("1,240 mon",x+w-8,y+h/2,20,INK,"serifb","rm")
    tsuru(p,zr("shop","S4"))
    x,y,w,h=zr("shop","S5"); p.rect(x,y,w,h,INK,255,1,fill=INK+(255,)); p.text("Grandmother Tsuru",x+w/2,y+h/2,12,PAPER,"serifb","mm")
    x,y,w,h=zr("shop","S6"); p.rect(x,y,w,h,INK,230,2,fill=(250,247,240,235))
    p.text("ITEM",x+70,y+16,11,W2,"bold","lm"); p.text("OWN",x+350,y+16,11,W2,"bold","mm"); p.text("PRICE",x+w-16,y+16,11,W2,"bold","rm")
    for i,(n,pr,own) in enumerate(items):
        yy=y+28+i*58
        if i==sel: p.wash([(x+4,yy),(x+w-4,yy),(x+w-4,yy+54),(x+4,yy+54)],W3,90,1); p.seal(x+w-6,yy+6,12,False)
        p.rect(x+12,yy+5,44,44,W2,200,1); p.text(n,x+70,yy+27,15,INK,"serif","lm"); p.text(str(own),x+350,yy+27,15,W1,"sans","mm")
        p.text(f"{pr}",x+w-16,yy+27,16,INK,"serifb","rm")
    x,y,w,h=zr("shop","S7"); p.rect(x,y,w,h,INK,230,2,fill=(250,247,240,235))
    p.rect(x+16,y+16,128,128,W2,220,2); p.blob(x+80,y+82,30,38,W1,200,2); p.text("icon-plum_tonic 128",x+80,y+156,10,W2,"sans","mm")
    nm=items[sel][0]; p.text(nm,x+160,y+30,18,INK,"serifb","lm")
    for i,l in enumerate(DESC[nm]): p.text(l,x+160,y+64+i*24,13,W1,"serif","lm")
    x,y,w,h=zr("shop","S8"); p.rect(x,y,w,h,INK,230,2,fill=(250,247,240,235))
    cmp_={"Plum Tonic":[("Itsuki","120","214 ▲"),("Benika","177","177 ="),("Gonzō","160","288 ▲")],"Rice Cake":[("Itsuki","120","170 ▲"),("Benika","177","177 ="),("Gonzō","160","210 ▲")]}[nm]
    for i,(n,a,b) in enumerate(cmp_):
        yy=y+24+i*40; p.ellipse(x+26,yy,13,13,2,INK); p.text(n,x+50,yy,15,INK,"serifb","lm"); p.text(f"HP {a} → {b}",x+w-16,yy,15,RED if "▲" in b else W1,"bold","rm")
    x,y,w,h=zr("shop","S9"); p.rect(x,y,w,h,W1,200,1,fill=(250,247,240,215))
    if qty: p.text(qty,x+w/2,y+h/2,18,INK,"serifb","mm")
    else: p.text("Tsuru: \""+line+"\"",x+20,y+h/2,15,INK,"serif","lm")
P=[]
p=Panel(PW,seed=51); interior(p); shop_ui(p); reserved(p,False)
P.append((p,"Buy: browsing the list","Shelves of jars behind, knocked back. Left: Grandmother Tsuru portrait (portrait-tsuru-calm). Centre: 8-row list, selected row = wash + seal tick. Right: description + party compare (who gains what, red ▲ for an improvement)."))
p=Panel(PW,seed=52); interior(p); shop_ui(p,qty="Buy  ◀  2  ▶   = 120 mon      [A] confirm   [B] back")
p.callout("qty stepper reuses the S9 bar",640,650,700,560,12); reserved(p,False)
P.append((p,"Buy: quantity + confirm","On A the bottom bar becomes the qty stepper (left/right or tap ◀ ▶). Confirm: 'coin' SFX, mon counter ticks down 20/s, Tsuru's portrait swaps to smile and she says a thank-you bark."))
p=Panel(PW,seed=53); interior(p); shop_ui(p,tab="Sell",sel=0,line="My own rice cakes? Half price, then.")
reserved(p,False)
P.append((p,"Sell tab","Same layout; list filters to owned items (Rice Cake, Plum Tonic, Inkstone Chip) and shows sell price (floor(price/2), SPEC s7). 'Equipment compare' is drawn as a party compare (HP / Ink now → after) since SPEC items have no gear: see LAYOUT_NOTES open question."))
p=wireframe("shop",54)
P.append((p,"Zone diagram (px @1280×720)","All panels end at y=612 except the bottom bar S9 (x 272–1008, between T1 and T2). Keeper portrait S4 bottom 422 + name plate S5 to 470, both above T1. mon counter S3 ends at x=1136, 16 px left of ☰."))
save(HEAD+"05 · Shop","Action view, mode: shop (Kōbō Tsuru) · "+SUB,P,2,"05_shop.png")
