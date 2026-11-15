"""Rough sumi-e storyboard drawing kit (PIL). Helen / storyboard, Tabula Rasa demo."""
import math, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PAPER=(236,230,216); SHADE=(217,208,188); INK=(27,24,19); W1=(59,55,48); W2=(109,103,91); W3=(163,156,140)
RED=(179,38,30); GALE=(95,138,106); EMBER=(194,69,45); STONE=(122,106,82)
LW, LH = 1280, 720  # logical screen (SPEC v1 section 1)

FS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FSB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FSER="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSERB="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
_fc={}
def font(sz,kind="sans"):
    k=(sz,kind)
    if k not in _fc:
        _fc[k]=ImageFont.truetype({"sans":FS,"bold":FSB,"serif":FSER,"serifb":FSERB}[kind],max(6,int(sz)))
    return _fc[k]

def paper(w,h,seed=0):
    rnd=random.Random(seed)
    im=Image.new("RGBA",(w,h),PAPER+(255,))
    n=Image.effect_noise((max(1,w//3),max(1,h//3)),18).resize((w,h)).filter(ImageFilter.GaussianBlur(1.2))
    tint=Image.new("RGBA",(w,h),SHADE+(255,)); mask=n.point(lambda v:int(max(0,v-128)*0.5))
    im.paste(tint,(0,0),mask)
    return im

def catmull(pts,n=10):
    if len(pts)<3: 
        out=[];(x0,y0),(x1,y1)=pts[0],pts[-1]
        for i in range(n+1): t=i/n; out.append((x0+(x1-x0)*t,y0+(y1-y0)*t))
        return out
    P=[pts[0]]+list(pts)+[pts[-1]]; out=[]
    for i in range(1,len(P)-2):
        p0,p1,p2,p3=P[i-1],P[i],P[i+1],P[i+2]
        for j in range(n):
            t=j/n;t2=t*t;t3=t2*t
            out.append(tuple(0.5*((2*p1[k])+(-p0[k]+p2[k])*t+(2*p0[k]-5*p1[k]+4*p2[k]-p3[k])*t2+(-p0[k]+3*p1[k]-3*p2[k]+p3[k])*t3) for k in (0,1)))
    out.append(pts[-1]); return out

class Panel:
    """A 16:9 frame drawn in logical coords (default 1280x720) scaled to pw px wide."""
    def __init__(self,pw,lw=LW,lh=LH,seed=1):
        self.s=pw/lw; self.lw,self.lh=lw,lh
        self.w,self.h=int(pw),int(round(lh*self.s))
        self.im=paper(self.w,self.h,seed); self.rnd=random.Random(seed)
    def P(self,x,y): return (x*self.s,y*self.s)
    def _layer(self): return Image.new("RGBA",(self.w,self.h),(0,0,0,0))
    def comp(self,layer,blur=0):
        if blur: layer=layer.filter(ImageFilter.GaussianBlur(blur*self.s))
        self.im.alpha_composite(layer)
    # --- brush ---
    def stroke(self,pts,w=8,col=INK,a=235,taper=(0.35,0.25),dry=0.25,jit=1.2,blur=0.6):
        r=self.rnd; L=self._layer(); d=ImageDraw.Draw(L)
        path=catmull([self.P(*p) for p in pts],12); n=len(path)
        if n<2: return
        left=[];right=[]
        for i,(x,y) in enumerate(path):
            t=i/(n-1)
            a0,b0=path[max(0,i-1)],path[min(n-1,i+1)]
            dx,dy=b0[0]-a0[0],b0[1]-a0[1]; ln=math.hypot(dx,dy) or 1
            nx,ny=-dy/ln,dx/ln
            k=1.0
            if t<taper[0]: k=0.25+0.75*(t/taper[0])**0.6
            if t>1-taper[1]: k=min(k,0.15+0.85*((1-t)/taper[1])**0.8)
            ww=w*self.s*k*(1+r.uniform(-0.12,0.12))/2
            jx,jy=r.uniform(-jit,jit)*self.s,r.uniform(-jit,jit)*self.s
            left.append((x+nx*ww+jx,y+ny*ww+jy)); right.append((x-nx*ww+jx,y-ny*ww+jy))
        d.polygon(left+right[::-1],fill=col+(a,))
        # dry-brush streaks: paper showing through
        if dry>0 and w*self.s>3:
            for _ in range(int(3+w*dry)):
                off=r.uniform(-0.4,0.4); st=r.uniform(0.3,0.95)
                seg=[(path[i][0]*(1)+0,path[i][1]) for i in range(int(n*st),n)]
                if len(seg)<2: continue
                sp=[]
                for i,(x,y) in enumerate(seg):
                    j=int(n*st)+i; a0,b0=path[max(0,j-1)],path[min(n-1,j+1)]
                    dx,dy=b0[0]-a0[0],b0[1]-a0[1]; ln=math.hypot(dx,dy) or 1
                    sp.append((x-dy/ln*w*self.s*off,y+dx/ln*w*self.s*off))
                d.line(sp,fill=PAPER+(int(150*dry+60),),width=max(1,int(w*self.s*0.08)))
        self.comp(L,blur)
    def line(self,pts,w=2,col=INK,a=230): self.stroke(pts,w,col,a,taper=(0.1,0.1),dry=0,jit=0.6,blur=0.3)
    def wash(self,pts,col=W2,a=90,blur=10):
        L=self._layer(); ImageDraw.Draw(L).polygon([self.P(*p) for p in pts],fill=col+(a,)); self.comp(L,blur)
    def blob(self,cx,cy,rx,ry,col=W2,a=90,blur=8,rough=0.18,n=24):
        r=self.rnd; pts=[]
        for i in range(n):
            t=2*math.pi*i/n; k=1+r.uniform(-rough,rough)
            pts.append((cx+math.cos(t)*rx*k,cy+math.sin(t)*ry*k))
        self.wash(pts,col,a,blur)
    def ellipse(self,cx,cy,rx,ry,w=3,col=INK,a=230,fill=None,arc=(0,360)):
        n=40; a0,a1=[math.radians(v) for v in arc]
        pts=[(cx+math.cos(a0+(a1-a0)*i/n)*rx,cy+math.sin(a0+(a1-a0)*i/n)*ry) for i in range(n+1)]
        if fill: self.wash(pts,fill[0],fill[1],1)
        self.stroke(pts,w,col,a,taper=(0.08,0.15),dry=0.1,jit=0.8,blur=0.4)
    def dots(self,pts,r=3,col=INK,a=220):
        L=self._layer(); d=ImageDraw.Draw(L)
        for (x,y) in pts:
            X,Y=self.P(x,y); R=r*self.s; d.ellipse([X-R,Y-R,X+R,Y+R],fill=col+(a,))
        self.comp(L,0.4)
    def splat(self,cx,cy,rad,col=INK,a=220,n=14):
        r=self.rnd; self.blob(cx,cy,rad*0.6,rad*0.5,col,a,1.5,0.35)
        self.dots([(cx+math.cos(t)*rad*r.uniform(0.7,1.5),cy+math.sin(t)*rad*r.uniform(0.6,1.3)) for t in [r.uniform(0,6.28) for _ in range(n)]],r=rad*0.06,col=col,a=a)
    # --- UI ---
    def rect(self,x,y,w,h,col=INK,a=255,width=2,dash=None,fill=None):
        L=self._layer(); d=ImageDraw.Draw(L); X0,Y0=self.P(x,y); X1,Y1=self.P(x+w,y+h)
        if fill: d.rectangle([X0,Y0,X1,Y1],fill=fill)
        if dash:
            on,off=dash
            for (ax,ay,bx,by) in [(X0,Y0,X1,Y0),(X1,Y0,X1,Y1),(X1,Y1,X0,Y1),(X0,Y1,X0,Y0)]:
                ln=math.hypot(bx-ax,by-ay); k=0
                while k<ln:
                    e=min(k+on,ln); d.line([(ax+(bx-ax)*k/ln,ay+(by-ay)*k/ln),(ax+(bx-ax)*e/ln,ay+(by-ay)*e/ln)],fill=col+(a,),width=width); k+=on+off
        else: d.rectangle([X0,Y0,X1,Y1],outline=col+(a,),width=width)
        self.comp(L)
    def zone(self,code,label,x,y,w,h,red=False,fill=True,tag="tl",fs=12):
        col=RED if red else INK
        self.rect(x,y,w,h,col,235,2,(7,4),fill=(255,255,255,70) if fill else None)
        txt=f"{code} {label}" if label else code
        self.tag(txt,x,y,w,h,col,tag,fs)
    def tag(self,txt,x,y,w,h,col=INK,where="tl",fs=12):
        L=self._layer(); d=ImageDraw.Draw(L); f=font(fs,"bold"); X,Y=self.P(x,y); X1,Y1=self.P(x+w,y+h)
        tw,th=d.textbbox((0,0),txt,font=f)[2:]
        if where=="tl": px,py=X+3,Y+3
        elif where=="bl": px,py=X+3,Y1-th-6
        elif where=="above": px,py=X,Y-th-6
        elif where=="below": px,py=X,Y1+2
        else: px,py=X1-tw-7,Y+3
        d.rectangle([px-2,py-1,px+tw+3,py+th+3],fill=(250,247,240,225)); d.text((px,py),txt,font=f,fill=col+(255,))
        self.im.alpha_composite(L)
    def text(self,txt,x,y,fs=14,col=INK,kind="sans",anchor="la",a=255,bg=None):
        L=self._layer(); d=ImageDraw.Draw(L); X,Y=self.P(x,y); f=font(fs,kind)
        if bg:
            bb=d.textbbox((X,Y),txt,font=f,anchor=anchor); d.rectangle([bb[0]-3,bb[1]-2,bb[2]+3,bb[3]+2],fill=bg)
        d.text((X,Y),txt,font=f,fill=col+(a,),anchor=anchor); self.im.alpha_composite(L)
    def arrow(self,a,b,col=INK,w=2,head=14,a_=230,curve=0):
        mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2
        dx,dy=b[0]-a[0],b[1]-a[1]; m=(mx-dy*curve,my+dx*curve)
        pts=catmull([a,m,b],10); self.line(pts,w,col,a_)
        (px,py),(qx,qy)=pts[-3],pts[-1]; ang=math.atan2(qy-py,qx-px)
        for s in (-1,1):
            self.line([(qx,qy),(qx-head*math.cos(ang+s*0.45),qy-head*math.sin(ang+s*0.45))],w,col,a_)
    def seal(self,cx,cy,sz,glyph=True,a=235,rot=0):
        r=self.rnd; L=self._layer(); d=ImageDraw.Draw(L); X,Y=self.P(cx,cy); S=sz*self.s/2
        pts=[]
        for (ux,uy) in [(-1,-1),(1,-1),(1,1),(-1,1)]:
            c,s_=math.cos(rot),math.sin(rot); pts.append((X+(ux*c-uy*s_)*S*r.uniform(0.95,1.05),Y+(ux*s_+uy*c)*S*r.uniform(0.95,1.05)))
        d.polygon(pts,fill=RED+(a,))
        if glyph:
            g=S*0.55; lw=max(1,int(S*0.12))
            for seg in [[(-g,-g*0.6),(g,-g*0.6)],[(0,-g),(0,g)],[(-g*0.7,g*0.2),(g*0.7,g*0.2)],[(-g*0.6,g),(g*0.6,g*0.75)]]:
                d.line([(X+p[0],Y+p[1]) for p in seg],fill=PAPER+(230,),width=lw)
        # speckle wear
        for _ in range(int(S*1.5)):
            px,py=X+r.uniform(-S,S),Y+r.uniform(-S,S); d.point((px,py),fill=PAPER+(200,))
        self.comp(L,0.3)
    def bar(self,x,y,w,h,frac,col=RED,bgcol=W3):
        self.rect(x,y,w,h,INK,200,1,fill=bgcol+(90,))
        if frac>0: self.stroke([(x+2,y+h/2),(x+2+(w-4)*frac,y+h/2)],h*0.9,col,230,taper=(0.02,0.08),dry=0.15,jit=0.3,blur=0.3)
    def callout(self,txt,x,y,tx,ty,fs=12,col=INK):
        self.arrow((tx,ty),(x,y),col,1.6,10)
        self.text(txt,tx,ty,fs,col,"bold",anchor="lm" if tx>=x else "rm",bg=(250,247,240,215))
    def frame(self):
        d=ImageDraw.Draw(self.im); d.rectangle([0,0,self.w-1,self.h-1],outline=INK+(255,),width=3)

# ---------- figures (feet anchor x,y; h = standing height in logical px) ----------
def fig_itsuki(p,x,y,h=200,face=1,pose="idle",tint=None):
    f=face; hy=y-h
    p.blob(x,y+4,h*0.22,h*0.04,W2,70,4)
    # hair trail + red cord
    p.stroke([(x-f*h*0.02,hy+h*0.08),(x-f*h*0.14,hy+h*0.2),(x-f*h*0.2,hy+h*0.36)],h*0.05,INK,220)
    p.stroke([(x-f*h*0.06,hy+h*0.13),(x-f*h*0.1,hy+h*0.16)],h*0.025,RED,240,dry=0)
    p.blob(x,hy+h*0.07,h*0.055,h*0.065,INK,235,1,0.1)
    # kimono body wash
    p.wash([(x-h*0.1,hy+h*0.16),(x+h*0.1,hy+h*0.16),(x+h*0.14,hy+h*0.62),(x-h*0.15,hy+h*0.62)],W2,150,2)
    p.stroke([(x,hy+h*0.15),(x+f*h*0.01,hy+h*0.4),(x,hy+h*0.6)],h*0.05,INK,200)
    p.stroke([(x-f*h*0.1,hy+h*0.2),(x-f*h*0.18,hy+h*0.34),(x-f*h*0.22,hy+h*0.4)],h*0.04,W1,210)  # torn sleeve
    # legs
    st=0.16 if pose!="idle" else 0.1
    p.stroke([(x,hy+h*0.6),(x-f*h*st,y)],h*0.05,INK); p.stroke([(x,hy+h*0.6),(x+f*h*st*1.2,y)],h*0.05,INK)
    # katana
    if pose=="strike":
        p.stroke([(x+f*h*0.05,hy+h*0.3),(x+f*h*0.55,hy+h*0.05)],h*0.022,INK,240,taper=(0.05,0.4))
        p.stroke([(x+f*h*0.1,hy+h*0.32),(x+f*h*0.7,hy+h*0.02),(x+f*h*0.9,hy+h*0.15)],h*0.02,W2,120,dry=0.4) # ink trail
    else:
        p.stroke([(x+f*h*0.06,hy+h*0.38),(x+f*h*0.42,hy+h*0.7)],h*0.022,INK,240,taper=(0.05,0.4))
    p.stroke([(x+f*h*0.04,hy+h*0.22),(x+f*h*0.07,hy+h*0.38)],h*0.035,INK,220)  # arm
    p.dots([(x+f*h*0.07,hy+h*0.39)],h*0.018,W3,255)  # wrapped palm
def fig_benika(p,x,y,h=170,face=1,pose="idle"):
    f=face; hy=y-h
    p.blob(x,y+4,h*0.2,h*0.04,W2,70,4)
    p.blob(x,hy+h*0.09,h*0.08,h*0.08,INK,235,1,0.12)
    p.stroke([(x-h*0.08,hy+h*0.08),(x-h*0.07,hy+h*0.2)],h*0.04,INK)
    p.rect(x+f*h*0.03,hy+h*0.02,h*0.035,h*0.06,INK,255,1,fill=(250,250,245,255))  # paper charm
    p.ellipse(x,hy+h*0.32,h*0.12,h*0.13,2.2,W1,220)  # white top outline
    p.wash([(x-h*0.13,hy+h*0.43),(x+h*0.13,hy+h*0.43),(x+h*0.2,y-h*0.02),(x-h*0.2,y-h*0.02)],RED,215,1.5)  # vermilion hakama
    p.stroke([(x-h*0.13,hy+h*0.43),(x-h*0.2,y)],2.4,INK,200,dry=0); p.stroke([(x+h*0.13,hy+h*0.43),(x+h*0.2,y)],2.4,INK,200,dry=0)
    bx=x+f*h*0.25
    p.stroke([(bx,hy-h*0.05),(bx+f*h*0.1,hy+h*0.4),(bx,y-h*0.05)],h*0.03,INK,240,taper=(0.1,0.1))
    p.line([(bx,hy-h*0.05),(bx-f*(h*0.12 if pose=="draw" else 0),hy+h*0.4),(bx,y-h*0.05)],1.2,W1,200)
    for k in (0.1,0.2): p.rect(bx+f*h*0.05,hy+h*k,h*0.03,h*0.08,W1,220,1,fill=(250,250,245,230))
def fig_gonzo(p,x,y,h=230,face=1,pose="idle"):
    f=face; hy=y-h
    p.blob(x,y+4,h*0.28,h*0.045,W2,80,4)
    p.blob(x,hy+h*0.45,h*0.24,h*0.3,W1,215,3,0.12)
    p.ellipse(x+f*h*0.02,hy+h*0.08,h*0.075,h*0.075,3,INK,240,fill=(PAPER,255))
    p.stroke([(x+f*h*0.05,hy+h*0.13),(x+f*h*0.08,hy+h*0.24),(x+f*h*0.03,hy+h*0.28)],h*0.06,W2,230)  # beard
    p.dots([(x+math.cos(t)*h*0.12,hy+h*0.25+math.sin(t)*h*0.08) for t in [0.2+i*0.35 for i in range(8)]],h*0.022,INK,255)
    p.stroke([(x-h*0.13,hy+h*0.72),(x-h*0.18,y)],h*0.08,INK); p.stroke([(x+h*0.13,hy+h*0.72),(x+h*0.2,y)],h*0.08,INK)
    sx=x+f*h*0.3
    if pose=="guard": p.stroke([(x-f*h*0.15,hy+h*0.2),(x+f*h*0.35,hy+h*0.55)],h*0.04,INK,240)
    else: p.stroke([(sx,hy-h*0.02),(sx+f*h*0.02,y)],h*0.035,INK,240,taper=(0.05,0.05))
    for k in (0.15,0.5): p.line([(sx-6,hy+h*k),(sx+8,hy+h*k)],3,W3)
def fig_blotling(p,x,y,s=1.0,eye=True):
    p.blob(x,y-18*s,46*s,24*s,INK,230,2,0.25)
    for dx in (-30,-5,22): p.stroke([(x+dx*s,y-6*s),(x+dx*s+3,y+10*s)],6*s,INK,210)
    if eye:
        p.ellipse(x-6*s,y-24*s,11*s,8*s,2,PAPER,255,fill=(PAPER,255)); p.dots([(x-9*s,y-24*s)],4*s,INK)
def fig_lantern(p,x,y,s=1.0,flame=0.3):
    cy=y-110*s
    p.blob(x,y-30*s,30*s,12*s,W2,90,10)
    p.stroke([(x,y-40*s),(x-14*s,y-70*s),(x+6*s,y-90*s)],8*s,W2,120,dry=0.5)
    p.ellipse(x,cy,34*s,44*s,2.5,INK,230,fill=(PAPER,200))
    for k in (-0.5,0,0.5): p.line([(x-34*s*math.sqrt(1-k*k),cy+k*44*s),(x+34*s*math.sqrt(1-k*k),cy+k*44*s)],1.4,W2)
    p.line([(x+10*s,cy+30*s),(x+24*s,cy+48*s)],2,INK)  # tear
    p.blob(x,cy+6*s,10*s,15*s,W3,200,2); p.blob(x,cy+12*s,5*s,6*s,RED,int(255*flame)+40,1.5)
def fig_ronin(p,x,y,h=240,face=-1,pose="idle"):
    f=face; hy=y-h
    p.blob(x,y+4,h*0.25,h*0.04,INK,90,5)
    p.stroke([(x,hy+h*0.02),(x+f*h*0.04,hy+h*0.12)],h*0.09,INK,235,dry=0.5)  # wet face stroke
    p.wash([(x-h*0.18,hy+h*0.18),(x+h*0.18,hy+h*0.18),(x+h*0.15,hy+h*0.6),(x-h*0.12,hy+h*0.6)],INK,190,2)
    p.wash([(x-h*0.1,hy+h*0.6),(x+h*0.18,hy+h*0.6),(x+h*0.24,y),(x-h*0.2,y)],W1,170,2)
    # half-unwritten side: broken dashed outline
    for k in range(6):
        yy=hy+h*(0.2+k*0.13); p.line([(x-f*h*0.28,yy),(x-f*h*0.3,yy+h*0.06)],2,W2,200)
    p.dots([(x-f*h*0.25+p.rnd.uniform(-10,10),hy+h*p.rnd.uniform(0.2,0.9)) for _ in range(14)],2.2,W2)
    blade=[(x+f*h*0.12,hy+h*0.35),(x+f*h*0.5,hy+h*(0.2 if pose=="attack" else 0.55))]
    p.stroke(blade,h*0.025,INK,240,taper=(0.05,0.3))
    for t in (0.5,0.8): 
        bx=blade[0][0]+(blade[1][0]-blade[0][0])*t; by=blade[0][1]+(blade[1][1]-blade[0][1])*t
        p.stroke([(bx,by),(bx+2,by+22)],4,INK,200)
def wings(p,x,y,h,tint=GALE,open_=1.0,a=1.0):
    """Gale Crane Inkwing wings behind a figure; open_ 0..1"""
    sy=y-h*0.72
    for side in (-1,1):
        span=h*(0.35+0.85*open_)
        tip=(x+side*span,sy-h*(0.15+0.45*open_)); mid=(x+side*span*0.55,sy-h*0.35*open_)
        p.wash([(x+side*h*0.04,sy),mid,tip,(x+side*span*0.85,sy+h*0.15),(x+side*span*0.5,sy+h*0.35),(x+side*h*0.1,sy+h*0.3)],tint,int(70*a),4)
        for k in range(7):
            t=k/6; bx=x+side*(h*0.05+span*0.8*t); by=sy-h*0.3*open_*math.sin(t*2.6)
            p.stroke([(bx,by),(bx+side*h*0.06,by+h*(0.25+0.2*(1-t)))],h*0.035,INK,int(200*a),dry=0.5)
        p.stroke([(x+side*h*0.05,sy),mid,tip],h*0.04,INK,int(235*a),taper=(0.05,0.5),dry=0.3)

# ---------- board assembly ----------
def wrap(txt,f,maxw,d):
    out=[]
    for para in txt.split("\n"):
        words=para.split(); cur=""
        for wd in words:
            t=(cur+" "+wd).strip()
            if d.textlength(t,font=f)<=maxw: cur=t
            else: out.append(cur); cur=wd
        out.append(cur)
    return out

def board(title,subtitle,panels,cols,out,pw=768,cap_h=150,seed=7):
    """panels: list of (Panel, heading, caption)"""
    M=36; rows=math.ceil(len(panels)/cols); ph=panels[0][0].h
    W=M+cols*(pw+M); H=150+rows*(ph+cap_h+M)+40
    B=paper(W,H,seed); d=ImageDraw.Draw(B)
    d.text((M,28),title,font=font(46,"serifb"),fill=INK)
    d.text((M,92),subtitle,font=font(19,"serif"),fill=W1)
    # header seal
    sp=Panel(110,110,110,seed); sp.im=Image.new("RGBA",(110,110),(0,0,0,0)); sp.seal(55,55,84,True,240,0.05)
    B.alpha_composite(sp.im,(W-M-110,22))
    d.text((W-M-130,70),"Helen · storyboard v1",font=font(15,"sans"),fill=W2,anchor="rm")
    d.line([(M,135),(W-M-150,135)],fill=INK,width=3)
    for i,(p,head,cap) in enumerate(panels):
        r,c=divmod(i,cols); x=M+c*(pw+M); y=150+r*(ph+cap_h+M)
        p.frame(); B.alpha_composite(p.im,(x,y))
        # number badge
        d.rectangle([x,y,x+46,y+38],fill=INK); d.text((x+23,y+19),str(i+1),font=font(22,"bold"),fill=PAPER,anchor="mm")
        d.text((x,y+ph+10),head,font=font(21,"serifb"),fill=INK)
        fy=y+ph+40; f=font(16,"sans")
        for ln in wrap(cap,f,pw,d)[:6]:
            d.text((x,fy),ln,font=f,fill=W1); fy+=21
    d.text((M,H-30),"Rough layout thumbnails, not final art. Zones use the logical 1280×720 screen from SPEC v1.1; px values in LAYOUT_NOTES.md. Red = meaningful accent only.",font=font(15,"sans"),fill=W2)
    B.convert("RGB").save(out,optimize=True); return out
