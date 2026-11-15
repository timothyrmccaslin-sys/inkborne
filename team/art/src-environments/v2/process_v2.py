# v2 post-process: stitched work/*.png + src gens -> SPEC keys. Run after stitch.py.
import numpy as np, os, json, sys, cv2
from PIL import Image, ImageFilter
from scipy import ndimage as ndi
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
WK=os.path.join(ROOT,'work'); OUT=os.path.join(ROOT,'out'); PV=os.path.join(OUT,'preview')
os.makedirs(PV,exist_ok=True)
PAPER=np.array([0xec,0xe6,0xd8],float); INK=np.array([0x1b,0x18,0x13],float); VER=np.array([0xb3,0x26,0x1e],float)
rng=np.random.default_rng(11)
def noise(h,w,scale,oct=4,seed=0):
    r=np.random.default_rng(seed); out=np.zeros((h,w)); amp=1; tot=0
    for o in range(oct):
        s=max(2,int(scale/(2**o))); g=r.random((h//s+2,w//s+2))
        g=cv2.resize(g,(w+2*s,h+2*s),interpolation=cv2.INTER_CUBIC)[s:s+h,s:s+w]
        out+=g*amp; tot+=amp; amp*=0.5
    return out/tot
def grain(h,w): 
    g=ndi.gaussian_filter(rng.normal(0,1,(h,w)),0.8); return g/ g.std()
def redmask(a):
    r,g,b=a[...,0],a[...,1],a[...,2]; return ((r-np.maximum(g,b))>55)&(r>110)
def to_palette(a,red=True):
    L=a.mean(-1); lo,hi=np.percentile(L,0.5),np.percentile(L,99.5)
    t=((L-lo)/max(hi-lo,1)).clip(0,1)[...,None]
    out=INK+(PAPER-INK)*t
    if red:
        rm=ndi.binary_dilation(redmask(a),iterations=2)
        s=ndi.gaussian_filter(rm.astype(float),1.2)[...,None]
        # vermilion with ink-wash variance: shading from luminance + low-freq mottling, never brighter than #b3261e*1.08
        h,w=L.shape; mott=0.88+0.2*noise(h,w,40,3,seed=5)[...,None]
        rl=(a[...,0]/max(np.percentile(a[...,0][rm],90),1) if rm.any() else 1)
        shade=np.clip(rl if np.isscalar(rl) else rl[...,None],0.35,1.0)
        ver=(VER*shade*mott).clip(0,VER*1.08)
        out=out*(1-s)+ver*s
    g=grain(*L.shape); out=out*(1+0.022*g[...,None])
    return out.clip(0,255)
def save(rgb,name,alpha=None):
    a8=rgb.clip(0,255).astype(np.uint8)
    im=Image.fromarray(np.dstack([a8,(alpha*255).clip(0,255).astype(np.uint8)]),"RGBA") if alpha is not None else Image.fromarray(a8,"RGB")
    im.save(f"{OUT}/{name}.png",optimize=True); im.save(f"{OUT}/{name}.webp",quality=90,method=6); return im
def keyed(a,ground_y=None,fill_holes=False,silhouette=False,lighten=None,solid_stalks=False):
    H,W=a.shape[:2]; L=a.mean(-1); Lp=np.percentile(L,92); Lk=INK.mean(); t0=10.0
    alpha=(((Lp-L-t0)/(Lp-Lk-t0)).clip(0,1))**0.8
    rm=ndi.binary_dilation(redmask(a),iterations=2)
    alpha=np.maximum(alpha,ndi.gaussian_filter(rm.astype(float),1.0))
    solid=np.zeros((H,W),bool)
    if solid_stalks:
        # bamboo: fill between left/right outline strokes of vertical stalks so the stalk body is opaque
        edge=alpha>0.22
        closed=ndi.binary_closing(edge,structure=np.ones((1,31)))
        closed=ndi.binary_opening(closed,structure=np.ones((61,1)))  # keep only tall vertical runs
        solid|=closed&(np.arange(H)[:,None]<(ground_y or H))
    if fill_holes:
        paper=alpha<0.15; lab,n=ndi.label(paper)
        border=set(np.unique(np.concatenate([lab[0],lab[:,0],lab[:,-1]])))-{0}
        solid|=paper&~np.isin(lab,list(border))
    if silhouette:
        strong=ndi.binary_opening(alpha>0.5,iterations=2)
        has=strong.any(0); top=np.where(has,strong.argmax(0),H)
        top=ndi.minimum_filter1d(top,25); top=ndi.uniform_filter1d(top.astype(float),9)
        solid|=(np.arange(H)[:,None]>=top[None,:]+6)
    sf=solid.astype(float)
    if ground_y is not None: sf=np.maximum(sf,((np.arange(H)-ground_y)/30.0).clip(0,1)[:,None]*np.ones((1,W)))
    sf=ndi.gaussian_filter(sf,1.5)
    pw=np.percentile(a.reshape(-1,3),92,axis=0)
    with np.errstate(divide='ignore',invalid='ignore'):
        col=((a-(1-alpha[...,None])*pw)/np.maximum(alpha[...,None],1e-3)).clip(0,255)
    ink=to_palette(col); papered=to_palette(a)
    if solid_stalks:  # stalk interiors get a light wash tone, not bare paper
        papered=np.where(solid[...,None]&(np.arange(H)[:,None,None]<(ground_y or H)),papered*0.93,papered)
    A=np.maximum(alpha,sf); w=(sf/np.maximum(A,1e-3))[...,None]
    rgb=ink*(1-w)+papered*w
    if lighten is not None:
        y0,k=lighten; f=((np.arange(H)-y0)/40.0).clip(0,1)[:,None,None]
        rgb=rgb*(1-f)+(PAPER+(rgb-PAPER)*k)*f
    m=A>0.06; lab,n=ndi.label(m); sz=ndi.sum(m,lab,range(n+1))
    A=np.where(np.isin(lab,np.where(sz<40)[0]),0,A); A[A<0.04]=0
    A=ndi.gaussian_filter(A,0.6); rgb[A<0.01]=PAPER
    return rgb,A
def seal(size,angle=0,crack=True,seed=1):
    """Cracked vermilion seal stamp: returns (rgba float, alpha) patch."""
    r=np.random.default_rng(seed); S=int(size*1.6); c=S//2
    yy,xx=np.mgrid[0:S,0:S]-c
    th=np.deg2rad(angle); u=xx*np.cos(th)+yy*np.sin(th); v=-xx*np.sin(th)+yy*np.cos(th)
    h=size/2; rough=noise(S,S,max(3,size//10),3,seed)*size*0.06
    box=(np.maximum(abs(u),abs(v))<h-rough)
    # carved glyph strokes (paper showing through), abstract not a real character
    g=np.zeros_like(box); k=size/10
    for (x0,y0,x1,y1) in [(-3,-3.4,3,-2.4),(-0.5,-3.4,0.5,3.4),(-3,-0.5,3,0.5),(-3,2.4,-1.2,3.4),(1.2,1.5,3,3.4),(-3,-3.4,-2,0)]:
        g|=(u>x0*k)&(u<x1*k)&(v>y0*k)&(v<y1*k)
    border=(np.maximum(abs(u),abs(v))<h*0.86)&(np.maximum(abs(u),abs(v))>h*0.78)
    m=box&~(g|border); m|=box&(np.maximum(abs(u),abs(v))>=h*0.86)
    # chipped corner
    m&=~((u>h*0.45)&(v<-h*0.45)&((u-v)>h*1.3))
    cr=np.zeros_like(m)
    if crack:
        pts=[(-h*1.0,-h*0.2)]
        for i in range(6): pts.append((pts[-1][0]+size*0.34,pts[-1][1]+r.uniform(-0.18,0.22)*size))
        img=np.zeros((S,S),np.uint8)
        P=[(int(c+p[0]*np.cos(-th)-p[1]*np.sin(-th)),int(c+p[0]*np.sin(-th)+p[1]*np.cos(-th))) for p in pts]
        cv2.polylines(img,[np.array(P)],False,255,max(1,size//26)); cr=img>0
    a=m.astype(float)*(0.82+0.18*noise(S,S,6,2,seed+3)); a[cr]=0
    a=ndi.gaussian_filter(a,0.7)
    col=VER*(0.85+0.2*noise(S,S,max(4,size//6),2,seed+9))[...,None]
    return col,a,cr
def paste(rgb,A,cx,cy,col,a,crackmask=None,inkcrack=True):
    S=a.shape[0]; x0,y0=cx-S//2,cy-S//2
    sl=(slice(y0,y0+S),slice(x0,x0+S))
    rgb[sl]=rgb[sl]*(1-a[...,None])+col*a[...,None]
    if A is not None: A[sl]=np.maximum(A[sl],a)
    if crackmask is not None and inkcrack:
        cm=ndi.gaussian_filter(crackmask.astype(float),0.6)[...,None]
        rgb[sl]=rgb[sl]*(1-0.8*cm)+INK*0.8*cm
        if A is not None: A[sl]=np.maximum(A[sl],cm[...,0]*0.9)

def load(p,size=None):
    im=Image.open(p).convert('RGB')
    if size: im=im.resize(size,Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.6,50,2))
    return np.asarray(im).astype(float)

which=(sys.argv[1:] or ['world','forest','town','battle']) if __name__=='__main__' else []
L={}
if 'forest' in which:
    far=to_palette(load(f"{WK}/forest-far.png"),red=False); L['poi-forest-far']=save(far,'poi-forest-far')
    rgb,A=keyed(load(f"{WK}/forest-mid.png"),ground_y=int(1440*0.80),solid_stalks=True)
    for (cx,cy,s,ang,sd) in [(1500,900,46,-3,2),(2515,1062,54,-12,4)]:
        col,a,cr=seal(s,ang,seed=sd); paste(rgb,A,cx,cy,col,a,cr)
    L['poi-forest-mid']=save(rgb,'poi-forest-mid',A)
    rgb,A=keyed(load(f"{WK}/forest-near.png")); L['poi-forest-near']=save(rgb,'poi-forest-near',A)
if 'town' in which:
    far=to_palette(load(f"{WK}/town-far.png")); L['poi-town-far']=save(far,'poi-town-far')
    rgb,A=keyed(load(f"{WK}/town-mid.png"),ground_y=int(1440*0.74),fill_holes=True,silhouette=True,lighten=(int(1440*0.76),0.6))
    # Kobo Tsuru shop mark (Luc's prop) on the noren: multiply onto the cloth, red pulled to #b3261e
    mk=Image.open(f"{D}/prop-kobo-tsuru-mark.webp").convert('RGBA').resize((76,76),Image.LANCZOS)
    ma=np.asarray(mk).astype(float)/255.0; ma_a=ma[...,3]*0.92
    cx,cy=2433,836; x0,y0=cx-38,cy-38; sl=(slice(y0,y0+76),slice(x0,x0+76))
    cloth=rgb[sl].mean(-1,keepdims=True); cl=(cloth/np.percentile(cloth,85)).clip(0.55,1.05)
    mott=0.9+0.15*noise(76,76,10,2,77)[...,None]
    red=(VER*cl*mott).clip(0,VER*1.06)
    rgb[sl]=rgb[sl]*(1-ma_a[...,None])+red*ma_a[...,None]
    L['poi-town-mid']=save(rgb,'poi-town-mid',A)
    rgb,A=keyed(load(f"{WK}/town-near.png")); L['poi-town-near']=save(rgb,'poi-town-near',A)
if 'battle' in which:
    a=load(f"{D}/gen_battle.jpg",(2560,1440)); b=to_palette(a)
    # hairline red crack running down from the left seal-stone's seal (~805,738)
    img=np.zeros((1440,2560),np.uint8); pts=[(812,712)]
    r=np.random.default_rng(3)
    for i in range(9): pts.append((pts[-1][0]+int(r.integers(-9,10)),pts[-1][1]+int(r.integers(14,24))))
    cv2.polylines(img,[np.array(pts)],False,255,2)
    br=[(pts[4][0],pts[4][1]),(pts[4][0]+22,pts[4][1]+18),(pts[4][0]+30,pts[4][1]+40)]
    cv2.polylines(img,[np.array(br)],False,255,1)
    m=ndi.gaussian_filter((img>0).astype(float),0.7)[...,None]
    b=b*(1-0.85*m)+VER*0.8*0.85*m
    save(b,'battle-forest')
if 'world' in which:
    import worldgeo
    a=load(f"{D}/gen_world_v2.jpg"); h,w=a.shape[:2]
    Lm=a.mean(-1); paper_c=np.median(a[Lm>200],axis=0)
    mask=np.zeros((h,w),np.uint8)
    mask[:6,:]=1; mask[-6:,:]=1; mask[:,:6]=1; mask[:,-6:]=1          # frame
    for xs in (320,640,960):                                           # generated panel seams (x in 1280 space)
        col=Lm[:,xs-12:xs+12].mean(0); x=xs-12+int(np.argmin(col)); mask[:,x-4:x+5]=1
    # grey placeholder ovals -> paper
    ov=np.zeros((h,w),np.uint8)
    cv2.ellipse(ov,(566,250),(142,58),0,0,360,1,-1); cv2.ellipse(ov,(642,469),(128,56),0,0,360,1,-1)
    ov=ov.astype(bool)&(Lm<215)&(Lm>90); ov=ndi.binary_dilation(ov,iterations=5)
    a8=a.clip(0,255).astype(np.uint8)
    a8=cv2.inpaint(a8,(mask>0).astype(np.uint8)*255,5,cv2.INPAINT_TELEA)
    a=a8.astype(float); a[ov]=paper_c
    a=np.asarray(Image.fromarray(a.clip(0,255).astype(np.uint8)).resize((2560,1440),Image.LANCZOS).filter(ImageFilter.UnsharpMask(2,60,2))).astype(float)
    base=to_palette(a)
    H,W=1440,2560
    # distance to paths + nodes
    pm=np.zeros((H,W),np.uint8)
    for p in worldgeo.curves(400): cv2.polylines(pm,[p.astype(np.int32)],False,1,3)
    dpath=ndi.distance_transform_edt(pm==0)
    nm=np.zeros((H,W),np.uint8)
    for (x,y) in worldgeo.N.values(): cv2.circle(nm,(int(x),int(y)),4,1,-1)
    dnode=ndi.distance_transform_edt(nm==0)
    def ss(x,a,b): t=((x-a)/(b-a)).clip(0,1); return t*t*(3-2*t)
    keep=np.minimum(ss(dpath,60,150),ss(dnode,110,210))  # 0 = cleared to paper
    # forest tonal smudges: wet-ink bleed blobs (no trees), darker wet edge
    def smudge(cx,cy,rx,ry,tone,seed):
        n=noise(H,W,90,4,seed); yy,xx=np.mgrid[0:H,0:W]
        d=np.sqrt(((xx-cx)/rx)**2+((yy-cy)/ry)**2)
        f=(1-d)+0.55*(n-0.5)
        core=ss(f,0.0,0.35)
        edge=np.exp(-((f-0.03)/0.04)**2)*0.35    # pooled-ink rim
        t=(core*0.75+edge)*(0.85+0.3*noise(H,W,30,3,seed+1))
        return (t*tone).clip(0,1)
    sm=np.maximum(smudge(1150,470,340,120,0.55,21),smudge(1280,950,300,105,0.48,22))
    sm=np.maximum(sm,smudge(560,610,180,70,0.35,23))
    sm*=keep
    wash=np.array([0x6d,0x67,0x5b],float)
    base=base*(1-sm[...,None])+wash*sm[...,None]
    # clear corridors (soft) - pull everything except the sun toward paper
    sun=ndi.binary_dilation(redmask(base),iterations=4)
    k=np.where(sun,1.0,0.25+0.75*keep)[...,None]
    base=PAPER+(base-PAPER)*k
    # Hanshi: small ink mark below the town node (three tiny roof strokes)
    tx,ty=[int(v) for v in worldgeo.N['hollowbell']]
    mk=np.zeros((H,W),np.uint8)
    for dx,dy,s in [(-34,52,14),(0,46,17),(32,54,12)]:
        cv2.polylines(mk,[np.array([(tx+dx-s,ty+dy+s//2),(tx+dx,ty+dy-s//3),(tx+dx+s,ty+dy+s//2)])],False,1,4)
    cv2.line(mk,(tx-52,ty+70),(tx+50,ty+72),1,3)
    mkf=ndi.gaussian_filter(mk.astype(float),0.9)[...,None]
    base=base*(1-0.85*mkf)+INK*0.85*mkf
    # faint 6-panel byobu seams + alternating panel tone, faded near nodes
    shade=np.ones((H,W))
    for i in range(6):
        x0,x1=W*i//6,W*(i+1)//6; shade[:,x0:x1]*=1+(0.012 if i%2 else -0.008)
    seam=np.zeros((H,W))
    for i in range(1,6):
        x=W*i//6; seam[:,x-1:x+1]=1; seam[:,x+1:x+3]=0.35
    seam=ndi.gaussian_filter(seam,0.6)*ss(dnode,40,120)
    base=base*shade[...,None]*(1-0.10*seam[...,None])
    save(base,'world-bg')
    Image.open(f"{OUT}/world-bg.png").resize((1920,1080),Image.LANCZOS).save(f"{OUT}/world-bg@1080.png",optimize=True)
    # debug overlay with nodes/paths for review
    dbg=Image.open(f"{OUT}/world-bg.png").convert('RGB'); from PIL import ImageDraw; dd=ImageDraw.Draw(dbg)
    for p in worldgeo.curves(): dd.line([tuple(q) for q in p],fill=(180,40,30),width=4)
    for x,y in worldgeo.N.values(): dd.ellipse([x-18,y-18,x+18,y+18],outline=(180,40,30),width=5)
    dbg.resize((1280,720),Image.LANCZOS).save(f"{PV}/world-bg-nodes-overlay-720.jpg",quality=88)
    Image.open(f"{OUT}/world-bg.png").resize((1280,720),Image.LANCZOS).save(f"{PV}/world-bg-720.jpg",quality=88)
print('ok',which)
