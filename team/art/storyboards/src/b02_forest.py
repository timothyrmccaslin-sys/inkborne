from common import *
def walker(p,x,y,h=128,face=1):  # field sprite stand-in (96x128 frame, anchor feet)
    fig_itsuki(p,x,y,h,face)
def forest_far(p,a=1.0):
    p.wash([(0,0),(1280,0),(1280,720),(0,720)],SHADE,60,1)
    for i,x in enumerate(range(-40,1320,90)):
        hh=260+(i*53)%120
        p.stroke([(x,560),(x+6,560-hh)],22,W3,int(150*a),dry=0.6)
    p.wash([(0,330),(1280,300),(1280,420),(0,450)],PAPER,170,30)
def forest_mid(p,a=1.0):
    for x in (120,420,860,1150):
        p.stroke([(x,620),(x+12,330),(x-6,120)],34,W1,int(210*a),dry=0.5)
        for k in range(3):
            yy=150+k*70; p.stroke([(x,yy),(x+110,yy-30),(x+200,yy-10)],18,W1,int(170*a),dry=0.6)
            p.stroke([(x,yy+10),(x-90,yy-20),(x-170,yy+5)],14,W1,int(150*a),dry=0.6)
    # path
    p.wash([(0,600),(400,560),(900,575),(1280,540),(1280,720),(0,720)],W3,110,8)
    p.stroke([(0,590),(420,555),(900,570),(1280,535)],5,W2,140,dry=0.6)
    # broken seal-stone
    p.wash([(690,560),(700,470),(740,465),(752,560)],W1,220,1.5); p.line([(712,470),(726,520),(716,560)],2,PAPER)
    p.seal(720,500,22,False,200,0.3)
def forest_near(p,a=1.0):
    for x in (30,1240):
        p.stroke([(x,740),(x+10,0)],60,INK,int(235*a),dry=0.4)
        for k in range(4): p.stroke([(x,120+k*140),(x+(1 if x<640 else -1)*140,90+k*140)],10,INK,int(200*a),dry=0.5)
    for x in range(200,1100,140): p.stroke([(x,720),(x+16,672),(x+30,660)],5,INK,int(170*a))  # grass
def leaves(p,pts):
    for (x,y) in pts: p.stroke([(x,y),(x+10,y+5),(x+18,y+2)],5,W1,200)
P=[]
# 1 layers
p=Panel(PW,seed=21); forest_far(p); p.text("FAR  poi-forest-far",70,240,16,W1,"bold",bg=(250,247,240,200))
p.text("0.2× camera · mist band 8 px/s",70,264,14,W1,bg=(250,247,240,200))
forest_mid(p,0.55); p.text("MID  poi-forest-mid  (alpha)",380,470,16,INK,"bold",bg=(250,247,240,210)); p.text("0.6× · pine boughs sway ±2° @0.3Hz",380,494,14,W1,bg=(250,247,240,210))
forest_near(p,0.6); p.text("NEAR  poi-forest-near (alpha) 1.15×, over the walker",150,64,16,INK,"bold",bg=(250,247,240,210))
P.append((p,"Parallax layers (2560×1440 each, SPEC s5)","Far: bamboo silhouettes + mist in wash 3. Mid: old pines, path, broken seal-stone (the only red: faded seal). Near: foreground trunks and grass framing the left/right edges, drawn over the walker. Camera scroll factors are suggestions."))
# 2 in play
p=Panel(PW,seed=22); forest_far(p); forest_mid(p); walker(p,470,590,128); forest_near(p)
leaves(p,[(560,200),(610,280),(990,160),(330,330)]); p.arrow((600,215),(620,300),W1,1.5,8,curve=0.2)
p.callout("falling leaves: 6 on screen, 30–50 px/s, sway",980,170,1050,240,12)
p.callout("mist band drift",640,360,760,420,12)
p.callout("seal-stone: faded red seal flickers 0.2Hz",722,495,800,560,12)
zones(p,"poi",["P1"]); p.text("Sumikage Wood",84,76,22,INK,"serifb")
reserved(p)
P.append((p,"In play: walking the path","Itsuki leads (field sheet walk-itsuki, 96×128). Area toast P1 fades in on entry. Path runs left→right along y≈560–600 so the walker never sits under T1/T2: keep the walkable band above y=496 near the screen edges, or let the camera lead."))
# 3 triggers & exits
p=Panel(PW,seed=23); forest_far(p); forest_mid(p)
fig_blotling(p,960,585,0.9); p.text("!",960,520,30,RED,"serifb","mm")
walker(p,720,600,128,1)
zone_at(p,"poi","P2",722,416,red=False); p.text("Read the seal-stone  [A]",722,438,15,INK,"serifb","mm")
p.callout("battle trigger: Blot puddle ripples, eye blinks; contact = ink wipe to battle",960,560,700,300,12)
zone_at(p,"poi","P3",310,330,centre=False); p.stroke([(340,350),(318,362),(340,374)],6,INK)
p.text("← to Shirofuda map",310,410,14,INK,"bold")
zone_at(p,"poi","P3",1150,330,centre=False); p.stroke([(1176,350),(1198,362),(1176,374)],6,INK)
p.text("Hanshi →",1150,410,14,INK,"bold")
forest_near(p,0.5); reserved(p)
P.append((p,"Triggers + exits","P2 prompt floats 96 px above the target, clamped out of T1/T2/☰. Battle trigger is a visible Blot puddle (no random encounters in the demo). Exit chevrons P3 sit at mid-height on the screen edges, never in the lower corners."))
# 4 zones
def ex(p):
    p.wash([(0,600),(400,560),(900,575),(1280,540),(1280,720),(0,720)],W3,90,8)
    p.rect(0,520,1280,110,GALE,160,2,(10,6)); p.text("walkable band (suggested y 520–630)",660,612,13,W1,"bold","ma")
p=wireframe("poi",24,ex)
zone_at(p,"poi","P2",640,300); zone_at(p,"poi","P3",40,330,centre=False); zone_at(p,"poi","P3",1176,330,centre=False)
P.append((p,"Zone diagram (px @1280×720)","P1 toast top-left; ☰ top-right. P2 and P3 float with the world but clamp to stay out of T1/T2/M. The walker's feet may pass behind T1/T2 (controls are translucent), but no prompt, chevron, or NPC talk target should sit there."))
save(HEAD+"02 · Sumikage Wood","Forest path POI (poi id: forest) · "+SUB,P,2,"02_sumikage_wood.png")
