from common import *
from b03_town import lantern
def zr(screen,code):
    for z in Z[screen]:
        if z[0]==code: return z[2:6]
def bust(p,who,rect,active=True,mirror=False):
    x,y,w,h=rect; cx=x+w/2; a=1.0 if active else 0.45; col=INK
    f=-1 if mirror else 1
    p.wash([(x+w*0.08,y+h),(x+w*0.18,y+h*0.62),(x+w*0.82,y+h*0.62),(x+w*0.92,y+h)],W2 if who=="itsuki" else PAPER,int(200*a),2)
    if who=="benika":
        p.stroke([(x+w*0.18,y+h*0.64),(x+w*0.5,y+h*0.75),(x+w*0.82,y+h*0.64)],5,W1,int(220*a))
        p.wash([(x+w*0.12,y+h*0.93),(x+w*0.88,y+h*0.93),(x+w*0.9,y+h),(x+w*0.1,y+h)],RED,int(220*a),1)
    p.ellipse(cx,y+h*0.4,w*0.17,h*0.17,3,col,int(235*a),fill=(PAPER,255))
    if who=="itsuki":
        p.stroke([(cx-w*0.18,y+h*0.32),(cx-w*0.05,y+h*0.2),(cx+w*0.18,y+h*0.3)],22,INK,int(240*a))
        p.stroke([(cx-f*w*0.16,y+h*0.3),(cx-f*w*0.3,y+h*0.6),(cx-f*w*0.36,y+h*0.9)],18,INK,int(230*a),dry=0.4)
        p.stroke([(cx-f*w*0.2,y+h*0.42),(cx-f*w*0.26,y+h*0.47)],7,RED,int(240*a),dry=0)
        p.line([(cx-w*0.06,y+h*0.4),(cx-w*0.01,y+h*0.4)],2,INK,int(230*a)); p.line([(cx+w*0.04,y+h*0.4),(cx+w*0.09,y+h*0.4)],2,INK,int(230*a))
        p.stroke([(cx-w*0.25,y+h*0.62),(cx,y+h*0.85),(cx+w*0.25,y+h*0.62)],6,INK,int(220*a))
    else:
        p.stroke([(cx-w*0.2,y+h*0.42),(cx-w*0.2,y+h*0.26),(cx,y+h*0.2),(cx+w*0.2,y+h*0.26),(cx+w*0.2,y+h*0.42)],20,INK,int(240*a))
        p.rect(cx+f*w*0.12,y+h*0.27,w*0.06,h*0.08,INK,int(255*a),1,fill=(250,250,245,int(255*a)))
        p.ellipse(cx-w*0.05,y+h*0.42,5,3,2,INK,int(230*a)); p.ellipse(cx+w*0.07,y+h*0.42,5,3,2,INK,int(230*a))
        p.arc_smile=None; p.line([(cx-w*0.03,y+h*0.5),(cx+w*0.04,y+h*0.51)],2,INK,int(220*a))
        p.stroke([(cx+f*w*0.32,y+h*0.1),(cx+f*w*0.38,y+h*0.6),(cx+f*w*0.3,y+h*0.98)],6,INK,int(220*a))  # bow
def backdrop(p):
    p.wash([(0,0),(1280,0),(1280,720),(0,720)],SHADE,80,1)
    p.stroke([(520,520),(520,170)],18,RED,120,dry=0.2); p.stroke([(780,520),(780,170)],18,RED,120,dry=0.2)
    p.stroke([(470,180),(650,160),(830,180)],22,RED,130,dry=0.3)
    p.wash([(0,520),(1280,500),(1280,720),(0,720)],W3,70,10); lantern(p,640,300,1.2)
    p.wash([(0,0),(1280,0),(1280,720),(0,720)],PAPER,90,1)  # knock back (action bg is blurred 6px, 60%)
def textbox(p,name_side,name,lines,adv=True):
    x,y,w,h=zr("dialogue","D3")
    p.rect(x,y,w,h,INK,230,3,fill=(250,247,240,235)); p.stroke([(x+10,y+h-6),(x+w-10,y+h-8)],5,W2,140,dry=0.6)
    nx,ny,nw,nh=zr("dialogue","D4" if name_side=="L" else "D5")
    p.rect(nx,ny,nw,nh,INK,255,2,fill=INK+(255,)); p.text(name,nx+nw/2,ny+nh/2+1,17,PAPER,"serifb","mm")
    p.seal(nx+(nw-14 if name_side=="L" else 14),ny+6,16,False)
    for i,l in enumerate(lines): p.text(l,x+28,y+44+i*40,17,INK,"serif")
    if adv:
        ax,ay,aw,ah=zr("dialogue","D6"); p.stroke([(ax,ay),(ax+aw/2,ay+ah),(ax+aw,ay)],6,RED,240,dry=0)
P=[]
p=Panel(PW,seed=41); backdrop(p)
bust(p,"itsuki",zr("dialogue","D1"),False); bust(p,"benika",zr("dialogue","D2"),True,mirror=True)
textbox(p,"R","Benika",["You walked out of Sumikage Wood with a blank","seal on your palm. Who painted you, stranger?"])
lx,ly,lw,lh=zr("dialogue","D8"); p.rect(lx,ly,lw,lh,W1,200,1,fill=(250,247,240,200)); p.text("LOG   AUTO",lx+lw/2,ly+lh/2,13,W1,"bold","mm")
reserved(p,False)
P.append((p,"Speaker: Benika (right)","Action-tier view over a blurred shrine plate. Active speaker full ink, listener knocked back to 45%. Name plate sits on the text box edge with a small red seal tick. Red chevron = advance (bobs when the line has finished typing)."))
p=Panel(PW,seed=42); backdrop(p)
bust(p,"itsuki",zr("dialogue","D1"),True); bust(p,"benika",zr("dialogue","D2"),False,mirror=True)
textbox(p,"L","Itsuki",["I was hoping someone here could tell me."],False)
p.callout("typing: 40 chars/s, 'text' blip every 2nd char",500,560,560,450,12)
p.callout("active portrait slides in 12 px + ink-in 150 ms",240,300,330,90,12)
reserved(p,False)
P.append((p,"Speaker swap: Itsuki (left)","Swap = 150 ms ink cross-fade, no hard cut. Advance indicator hidden while typing; tap A (or anywhere in D3) to finish the line, tap again to advance. Mood swaps use portrait-<id>-<mood> keys (calm/smile/angry/sad)."))
p=Panel(PW,seed=43); backdrop(p)
bust(p,"itsuki",zr("dialogue","D1"),True); bust(p,"benika",zr("dialogue","D2"),False,mirror=True)
textbox(p,"R","Benika",["Well? Are you going to answer me?"],False)
cx,cy,cw,ch=zr("dialogue","D7")
for i,t in enumerate(["Show her the blank seal.","\"I don't know. Truly.\"","Ask about the cracked seals."]):
    yy=cy+i*72; p.rect(cx,yy,cw,56,INK,230,2,fill=(250,247,240,240)); p.text(t,cx+28,yy+28,16,INK,"serif","lm")
    if i==0: p.stroke([(cx+20,yy+50),(cx+cw-20,yy+48)],5,RED,240,dry=0.2); p.seal(cx+cw-24,yy+16,14,False)
reserved(p,False)
P.append((p,"Choices","2–3 choice rows float between the portraits (above the text box, clear of T1/T2). Focus = red brush underline + small seal; up/down or tap selects, A confirms. Lines here are placeholders: Ollie owns dialogue text."))
p=wireframe("dialogue",44)
P.append((p,"Zone diagram (px @1280×720)","Portraits stop at y=484 so they never sit under T1/T2. The text box spans x 272–1008, exactly between T1 and T2. Log/Auto D8 sits left of ☰ with an 8 px gap."))
save(HEAD+"04 · Dialogue","Action view, mode: dialogue (shrine scene, Itsuki + Benika) · "+SUB,P,2,"04_dialogue.png")
