from battle_kit import *
# encounter sumikage_c (data/enemies.json): blotling, hollow_lantern, blotling
BL1,BL2,LAN=(1000,470),(1150,455),S["lantern"]
ORD=["Benika","Itsuki","lantern","blot","blot","Gonzō"]  # spd 20, 17, 15, 12, 12, 10
def foes3(p,flame=0.5,b1=True,lan=True,b2=True,split=False):
    if lan: fig_lantern(p,*LAN,1.0,flame)
    if b1 and not split: fig_blotling(p,*BL1,1.0)
    if split:
        fig_blotling(p,BL1[0]-40,BL1[1],0.5); fig_blotling(p,BL1[0]+40,BL1[1]+6,0.5)
    if b2: fig_blotling(p,*BL2,1.0)
def stdb(p,cur,ink,act,hp=(214,177,288)):
    turn_order(p,ORD,cur); hud(p,ink,hp,act=act); reserved(p,False)
LAN_HIT=(LAN[0],LAN[1]-110)
P=[]
# 1 intro + Benika's menu
p=Panel(PW,seed=81); bg(p); party(p); foes3(p)
for x in (BL1[0],BL2[0]): p.stroke([(x,0),(x+2,200),(x,BL1[1]-40)],8,INK,120,dry=0.6)
menu(p,["Brushstroke","Unfurl","Still Water","Items","Flee"],0,dim=("Unfurl",),title="Benika")
target_plate(p,"Hollow Lantern",1.0); p.stroke([(LAN[0],LAN[1]-185),(LAN[0]-10,LAN[1]-200),(LAN[0]+10,LAN[1]-200),(LAN[0],LAN[1]-185)],8,RED,240,dry=0)
p.callout("two Blotlings drip down strands",BL2[0],BL2[1]-60,1100,560-200,12)
stdb(p,0,(85,30,20),1)
P.append((p,"1 · Standard encounter: intro + Benika's turn","Encounter sumikage_c: Blotling, Hollow Lantern, Blotling. Enemies ink in 0.4 s apart (Blotlings drip down, Lantern drifts in on smoke); no name banner for a standard fight. Benika is fastest (spd 20) so she opens. Unfurl stays greyed: nobody is at 100."))
# 2 Brushstroke chain: Three Prayer Slips on the Lantern
p=Panel(PW,seed=82); bg(p); party(p,bpose="draw"); foes3(p,flame=0.35)
for k in range(3): p.stroke([(420,300-k*6),(LAN_HIT[0]-80,LAN_HIT[1]+10-k*8)],2.5,INK,150-k*30,dry=0)
p.rect(LAN_HIT[0]-110,LAN_HIT[1]+2,16,26,W1,220,1,fill=(250,247,240,240))  # prayer slip in flight
ring(p,*LAN_HIT,1.0,clean=True); pips(p,["clean","clean","clean"],cx=LAN_HIT[0],y=LAN_HIT[1]+130)
x,y,w,h=zr("battle","B8"); p.seal(x+w/2-40,y+h/2+40,110,True,235,0.1)
dmg(p,LAN_HIT[0]+110,LAN_HIT[1]-10,"96",True,26)
p.arrow((1150,262),(LAN_HIT[0]+60,LAN_HIT[1]+40),W1,1.6,10); p.text("ring overlaps B3:",1236,270,12,INK,"bold","ra",bg=(250,247,240,215)); p.text("banner waits until it clears",1236,298,12,INK,"bold","ra",bg=(250,247,240,215))
stdb(p,0,(85,65,20),1)
P.append((p,"2 · Brushstroke Chain: Three Prayer Slips (all Clean → Seal)","Benika fires from her spot (archer, no dash). Rings close on the Lantern's flame at 760 / 560 / 520 ms; each Clean Line pins a prayer slip. Fully Clean chain = red Seal stamp at B8. Her ink 30→65. The Lantern's high hit point overlaps B3, so the Form-name banner shows after the ring, not during."))
# 3 enemy turn
p=Panel(PW,seed=83); bg(p); party(p,gpose="guard"); foes3(p,flame=0.25)
p.wash([(LAN[0]-40,LAN_HIT[1]+20),(560,300),(330,330),(320,280),(560,250)],W2,90,12)
p.text("Dimming Curse",470,250,13,INK,"bold","mm",bg=(250,247,240,215)); p.text("(grey smoke on Benika, ACC↓)",470,278,12,INK,"bold","mm",bg=(250,247,240,215))
p.splat(660,430,40,INK,220,16); p.stroke([(BL1[0]-50,BL1[1]-30),(860,380),(690,430)],8,INK,160,dry=0.6)
p.text("Ink Splash",800,520,13,INK,"bold","mm",bg=(250,247,240,215)); dmg(p,615,300,"18",False,22)
banner(p,"Dimming Curse",fs=20)
turn_order(p,ORD,2); hud(p,(85,65,24),(214,177,270),act=2); reserved(p,False)
p.arrow((790,330),(650,400),W1,1.6,10); p.text("Gonzō in Still Water:",800,320,12,INK,"bold","la",bg=(250,247,240,215)); p.text("half damage, +6 ink",800,346,12,INK,"bold","la",bg=(250,247,240,215))
P.append((p,"3 · Enemy turn: Lantern curses, Blotling splashes","Hollow Lantern's Dimming Curse drifts grey smoke onto Benika (accuracy down, icon on her card). A Blotling flings an Ink Splash at Gonzō, who is guarding (Still Water). Ink rises from damage but no one reaches 100, so there is no Unfurl in this fight."))
# 4 victory
p=Panel(PW,seed=84); bg(p,120)
fig_blotling(p,BL2[0]-30,BL2[1],0.45); fig_blotling(p,BL2[0]+30,BL2[1]+4,0.4)
p.arrow((1180,410),(BL2[0],BL2[1]-24),W1,1.6,10); p.text("Blotling splits,",1236,360,12,INK,"bold","ra",bg=(250,247,240,215)); p.text("then washes away",1236,386,12,INK,"bold","ra",bg=(250,247,240,215))
fig_benika(p,500,560,170,1); fig_itsuki(p,640,560,200,1); fig_gonzo(p,800,560,230,1)
x,y,w,h=zr("battle","B9"); p.rect(x,y,w,h,INK,235,2,fill=(250,247,240,240)); p.seal(x+w-30,y+30,44,True)
p.text("Victory",x+w/2,y+40,30,INK,"serifb","mm")
for i,l in enumerate(["mon   +44  (12 + 20 + 12)","Ink kept   Itsuki 85 · Benika 65 · Gonzō 40","Itsuki nearly full for the boss"]): p.text(l,x+40,y+100+i*48,16,INK,"serif","lm")
p.text("[A] continue",x+w/2,y+h-26,14,W1,"bold","mm")
hud(p,(85,65,40),(214,177,270)); reserved(p,False)
P.append((p,"4 · Finish + results (no Unfurl)","Gonzō's Temple Bell (820 / 640 ms) lands hard on the last Blotling: it splits into two small blots that wash out to blank paper. Results panel B9 as in board 06; ink carries over (persists between battles), which sets up the boss showcase."))
save(HEAD+"06b · Standard battle","Encounter sumikage_c: party vs Blotling, Hollow Lantern, Blotling · no Unfurl · logical 1280×720 (SPEC v1.1)",P,2,"06b_battle_standard.png")
