from common import *
N=WORLD_NODES
PATHS=[("start","forest",[(360,520),(430,340)]),("forest","town",[(700,300),(800,520)]),("town","locked",[(1040,420),(1020,250)])]
def path_pts(a,b,c): return [N[a],c[0],c[1],N[b]]
def screen_bg(p,bold=True):
    # folding screen leaves
    for i in range(6):
        x=i*1280/6
        if i%2: p.wash([(x,0),(x+1280/6,0),(x+1280/6,720),(x,720)],SHADE,110,1)
        p.line([(x,0),(x,720)],1.5,W3,160)
    p.wash([(0,250),(200,120),(420,230),(560,90),(760,200),(980,60),(1280,180),(1280,0),(0,0)],W3,90,20)
    p.stroke([(-20,260),(180,130),(330,210),(520,80),(700,190)],46,W1,200,dry=0.5)
    p.stroke([(760,190),(980,50),(1150,130),(1300,90)],38,W2,190,dry=0.55)
    p.stroke([(0,640),(260,560),(520,640),(820,560),(1300,620)],60,W2,130,dry=0.6)  # river sweep
    p.wash([(0,330),(1280,280),(1280,360),(0,400)],PAPER,160,26)  # mist band
    # forest mass, town mass
    for k in range(7): p.stroke([(470+k*26,420),(480+k*26,300-(k%3)*20)],14,INK,200,dry=0.4)
    p.blob(930,470,120,40,W1,120,12)
    p.stroke([(860,440),(930,405),(1000,440)],12,INK,220); p.stroke([(900,470),(950,445),(990,468)],9,INK,200)
    p.blob(1110,210,70,60,W3,120,6)
def draw_paths(p):
    for a,b,c in PATHS:
        pts=catmull(path_pts(a,b,c),14)
        for i in range(0,len(pts)-1,3): p.dots([pts[i]],3.2,W1 if b!="locked" else W3)
def nodes(p,labels=True):
    for k,(x,y) in N.items():
        if k=="forest": p.ellipse(x,y,22,22,4,INK); p.seal(x+20,y-20,14,False)
        elif k=="town": p.ellipse(x,y,22,22,4,INK); p.blob(x+22,y-22,7,9,RED,240,1)
        elif k=="locked": p.ellipse(x,y,20,20,3,W3,200,arc=(20,300)); p.blob(x,y,12,12,INK,150,3)
        else: p.ellipse(x,y,16,16,3,INK)
        if labels: p.text({"start":"trailhead (name TBD, story)","forest":"Sumikage Wood","town":"Hanshi","locked":"locked (Blot)"}[k],x,y+34,13,INK,"serifb","ma",bg=(250,247,240,200))
def token(p,x,y):
    p.blob(x,y+4,16,5,INK,90,3)
    p.stroke([(x,y),(x-2,y-30),(x,y-58)],12,INK,240,taper=(0.4,0.3))
    p.stroke([(x+2,y-52),(x+22,y-46)],5,RED,240,dry=0)
P=[]
p=Panel(PW,seed=11); screen_bg(p); draw_paths(p); nodes(p)
p.callout("six-leaf folding screen, fold lines = parallax-free seams",213,40,330,30,12)
p.callout("mist band drifts 6 px/s",640,320,760,350,12)
P.append((p,"Composition (world-bg 2560×1440)","Bold abstract strokes only: ridges, river sweep, mist band. Forest = vertical bamboo slashes, town = two roof strokes. Nodes use data/world.json positions. Red only on POI nodes (seal on Sumikage Wood, lantern dot on Hanshi). Almost no line detail."))
p=Panel(PW,seed=12); screen_bg(p); draw_paths(p); nodes(p,False)
tx,ty=760,395; token(p,tx,ty); p.arrow((690,330),(745,380),RED,2.5,12,curve=0.1)
zones(p,"world",["W1","W2"],red=("W2",)); p.text("Sumikage Wood → Hanshi",80,86,18,INK,"serifb")
p.text("Enter Hanshi  [A]",640,646,22,INK,"serifb","mm"); reserved(p)
P.append((p,"In play: token travelling","Party token (ink stroke with Itsuki's red cord) slides along the path bezier, ~260 px/s, slight bob. Location plate W1 swaps name mid-path. Node prompt W2 appears on arrival. ☰ and touch zones always reserved."))
p=Panel(PW,seed=13)
items=[("start",170,"start node\nplain ink ring"),("forest",490,"POI node (Sumikage)\nring + red seal"),("town",810,"POI node (Hanshi)\nring + lantern dot"),("locked",1110,"locked node\nbroken grey ring + Blot")]
for k,x,cap in items:
    y=300; s=3
    if k=="forest": p.ellipse(x,y,66,66,12,INK); p.seal(x+60,y-60,44,True)
    elif k=="town": p.ellipse(x,y,66,66,12,INK); p.blob(x+64,y-64,20,26,RED,240,2)
    elif k=="locked": p.ellipse(x,y,60,60,8,W3,220,arc=(20,300)); p.blob(x,y,36,34,INK,150,6)
    else: p.ellipse(x,y,48,48,9,INK)
    for j,ln in enumerate(cap.split("\n")): p.text(ln,x,410+j*30,15,INK,"bold","ma")
token(p,150,640); p.text("party token 48×64, anchor feet",190,600,15,INK,"bold")
for i in range(12): p.dots([(560+i*40,600+math.sin(i/2)*14)],5,W1)
p.text("path = dry-brush dots, 40px spacing; locked leg in wash 3",560,650,14,W1)
P.append((p,"Node + token designs (in screen px)","Hover/arrival: node ring thickens 1.2x over 150ms, red element pulses 0.8Hz. Locked node never pulses. Token idles with a 2px bob at 1Hz."))
P.append((wireframe("world",14,lambda p:(nodes(p,False),draw_paths(p))),"Zone diagram (px @1280×720)","W1 location plate, W2 node prompt between the touch zones, ☰ and T1/T2 reserved. Keep node positions out of T1/T2/M rects: current data nodes all clear (lowest node y=470 is at x=230: inside T1's x span but above y=496, keep it ≥ 24px clear)."))
save(HEAD+"01 · World map","Shirofuda (folding-screen view) · "+SUB,P,2,"01_world_map.png")
