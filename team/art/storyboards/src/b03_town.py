from common import *
def house(p,x,w,h,base=560,a=1.0):
    p.wash([(x,base),(x,base-h),(x+w,base-h),(x+w,base)],PAPER,230,1)
    p.rect(x,base-h,w,h,W1,int(220*a),2)
    for k in range(1,4): p.line([(x+w*k/4,base-h),(x+w*k/4,base)],1.2,W2,int(170*a))
    p.line([(x,base-h*0.5),(x+w,base-h*0.5)],1.2,W2,int(170*a))
    p.stroke([(x-30,base-h+6),(x+w/2,base-h-50),(x+w+30,base-h+6)],16,INK,int(230*a),dry=0.4)
def lantern(p,x,y,s=1.0,glow=True):
    p.line([(x,y-40*s),(x,y-22*s)],1.5,INK)
    p.blob(x,y,12*s,17*s,RED,235,1.5,0.08)
    if glow: p.blob(x,y,30*s,34*s,RED,40,12)
    p.line([(x-9*s,y-15*s),(x+9*s,y-15*s)],2,INK); p.line([(x-9*s,y+15*s),(x+9*s,y+15*s)],2,INK)
def street(p):
    p.wash([(0,0),(1280,0),(1280,720),(0,720)],SHADE,50,1)
    p.stroke([(0,250),(300,190),(700,230),(1000,140),(1280,180)],40,W3,120,dry=0.6)  # far hills
    house(p,40,220,190); house(p,330,280,210)
    # shop Kōbō Tsuru noren
    for k in range(4): p.wash([(380+k*46,360),(420+k*46,360),(418+k*46,420),(382+k*46,416)],INK,200,1)
    p.seal(470,330,28,True,230)
    house(p,700,200,170)
    # stair + shrine
    for k in range(7): p.line([(980+k*26,560-k*30),(1060+k*26,560-k*30)],3,W1)
    p.stroke([(1150,330),(1150,200)],10,RED,230,dry=0); p.stroke([(1240,330),(1240,200)],10,RED,230,dry=0)
    p.stroke([(1120,205),(1195,190),(1272,205)],14,RED,240,dry=0.2); p.stroke([(1135,232),(1260,232)],7,RED,230,dry=0)
    p.wash([(0,560),(1280,560),(1280,720),(0,720)],W3,90,6)
    p.stroke([(0,600),(1280,600)],3,W2,120,dry=0.7)
    for x in (300,640,940): p.line([(x-100,300),(x,320),(x+100,300)],1.2,INK,180)
    for x in (230,300,610,680,880): lantern(p,x,330+((x//10)%3)*6)
def npc(p,x,y,h=110,kind="villager"):
    if kind=="tsuru":
        p.blob(x,y-h*0.55,h*0.18,h*0.38,W1,220,2); p.ellipse(x,y-h*0.92,h*0.08,h*0.08,2.5,INK,240,fill=(W3,255))
        p.stroke([(x+h*0.08,y-h*0.6),(x+h*0.2,y)],3,INK)  # cane
    elif kind=="child":
        p.blob(x,y-h*0.3,h*0.12,h*0.22,W2,210,2); p.blob(x,y-h*0.6,h*0.08,h*0.08,INK,240,1)
    else:
        p.blob(x,y-h*0.45,h*0.14,h*0.36,W2,210,2); p.blob(x,y-h*0.88,h*0.07,h*0.08,INK,240,1)
        p.stroke([(x-h*0.25,y-h*0.98),(x,y-h*1.08),(x+h*0.25,y-h*0.98)],5,INK)  # straw hat
P=[]
p=Panel(PW,seed=31); street(p)
p.callout("Kōbō Tsuru: noren curtain + red shop seal",470,390,560,470,12)
p.callout("Benika's shrine at the top of the stair (red torii)",1190,250,1100,90,12)
p.callout("lantern string (the street's red rhythm)",610,330,520,260,12)
P.append((p,"Layout: one wide street (poi-town, 2560 wide)","Paper-walled houses, Kōbō Tsuru shop at left of centre, stair and red torii to the shrine at right. Red only on lanterns, shop seal, torii. Street floor y≈560–640."))
p=Panel(PW,seed=32); street(p); fig_itsuki(p,560,620,128)
npc(p,500,575,96,"tsuru"); npc(p,860,600,104); p.stroke([(870,520),(885,380)],3,INK,230,dry=0); npc(p,960,610,70,"child")
p.callout("Old Hotaru relights a lantern (pole)",885,380,1000,440,12)
p.callout("lanterns sway ±3° @0.5Hz, flame flicker",680,335,780,250,12)
p.callout("paper windows glow (slow 4s pulse)",260,470,330,430,12)
p.callout("child loops a 3s run",960,560,1010,500,12)
zones(p,"poi",["P1"]); p.text("Hanshi",84,86,22,INK,"serifb"); reserved(p)
P.append((p,"In play: ambient town","Grandmother Tsuru waits under her noren; Old Hotaru (lamplighter, canon) relights a greying lantern with his pole; a child runs the street. Wood footsteps (step-wood). Lantern flames and window glow are the motion; keep NPCs out of the lower 25% corners."))
p=Panel(PW,seed=33); street(p); fig_itsuki(p,470,620,128); npc(p,520,575,96,"tsuru")
prompt(p,470,450,"Enter Kōbō Tsuru  [A]")
prompt(p,1000,380,"Climb to the shrine  [A]")
zone_at(p,"poi","P3",40,330,centre=False); p.stroke([(80,350),(58,362),(80,374)],6,INK)
p.text("← to Sumikage / map",40,410,14,INK,"bold",bg=(250,247,240,215))
p.callout("shop trigger = noren rect",440,410,640,300,12)
reserved(p)
P.append((p,"Triggers + exits","Shop door (shop trigger), shrine stair (dialogue trigger: Benika's scene, board 04), NPC talk targets. West exit back to Sumikage Wood / the world map. Prompts P2 clamp out of T1/T2/☰."))
def ex(p):
    p.wash([(0,560),(1280,560),(1280,640),(0,640)],W3,90,6); p.text("street floor y 560–640",660,612,13,W1,"bold","ma")
p=wireframe("poi",34,ex); zone_at(p,"poi","P2",470,330); zone_at(p,"poi","P2",1040,300); zone_at(p,"poi","P3",40,330,centre=False)
P.append((p,"Zone diagram (px @1280×720)","Same POI zone set as Sumikage Wood. The shrine stair rises toward the ☰ corner: stop the climb prompt below y=120 so it never touches the menu rect."))
save(HEAD+"03 · Hanshi","Town POI (poi id: town) · "+SUB,P,2,"03_hanshi.png")
