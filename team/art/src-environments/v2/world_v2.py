# world-bg v2: keep gestural mountains + sun from gen_world_v4, paint sea/river/forest procedurally at 2560x1440.
import numpy as np, cv2, os
from PIL import Image, ImageFilter, ImageDraw
from scipy import ndimage as ndi
import process_v2 as P   # helpers only when imported with no world arg
import worldgeo
D=os.path.dirname(os.path.abspath(__file__)); OUT=P.OUT; PV=P.PV
W,H=2560,1440; PAPER,INK,VER=P.PAPER,P.INK,P.VER
def ss(x,a,b): t=((x-a)/(b-a)).clip(0,1); return t*t*(3-2*t)
g=np.asarray(Image.open(f"{D}/gen_world_v4.jpg").convert('RGB').resize((W,H),Image.LANCZOS).filter(ImageFilter.UnsharpMask(2,60,2))).astype(float)
Lm=g.mean(-1); pw=np.percentile(Lm,90)
k=2.5  # 1024-preview coords -> 2560
keep=np.zeros((H,W),bool)
for x0,y0,x1,y1 in [(0,40,410,280),(330,0,650,140),(740,15,1024,245),(380,385,850,576)]:
    keep[int(y0*k):int(y1*k),int(x0*k):int(x1*k)]=True
river=[(1712,0),(1740,250),(1830,470),(2030,670)]
coast=[(2030,670),(2060,960),(2120,1200),(2180,1440)]
band=np.zeros((H,W),np.uint8)
cv2.polylines(band,[np.array(river)],False,1,90); cv2.polylines(band,[np.array(coast)],False,1,90)
sea=np.zeros((H,W),np.uint8); cv2.fillPoly(sea,[np.array(coast+[(W,H),(W,520),(2030,520)])],1)
yy_=np.arange(H)[:,None]*np.ones((1,W))
keep&=~(band>0)&~((sea>0)&(yy_>640))
keep[930:1110,1985:2045]=False
keep=ndi.gaussian_filter(keep.astype(float),10)
keep*=1-ss(np.arange(W)[None,:]*1.0,1990,2090)*ss(yy_,900,1000)
sunm=ndi.binary_dilation(P.redmask(g),iterations=3)
alpha=(((pw-Lm-8)/(pw-INK.mean()-8)).clip(0,1))**0.85*keep
alpha=ndi.gaussian_filter(alpha,0.5)
inkcol=P.to_palette(g,red=False)
# --- paper base with faint fibre mottling
base=np.ones((H,W,3))*PAPER*(1+0.018*(P.noise(H,W,160,4,1)[...,None]-0.5))
def wash(mask_t,tone_rgb):  # mask_t 0..1
    global base; base=base*(1-mask_t[...,None])+tone_rgb*mask_t[...,None]
W3=np.array([0xa3,0x9c,0x8c],float); W2=np.array([0x6d,0x67,0x5b],float); W1=np.array([0x3b,0x37,0x30],float)
# sea: pale wash, wet pooled rim along coast, mottled
dsea=ndi.distance_transform_edt(sea)
yy=np.arange(H)[:,None]*np.ones((1,W)); topf=ss(yy+220*(P.noise(H,W,140,3,8)-0.5),620,860)
seat=(sea>0)*(0.36+0.16*P.noise(H,W,120,4,7))*ss(dsea,0,25)*(1-0.5*ss(dsea,80,600))*topf
rim=(sea>0)*np.exp(-((dsea-12)/16.0)**2)*0.30*topf
wash(seat.clip(0,1),W3); wash(rim.clip(0,1),W2)
# dry-brush stroke helper: per-pixel (t, cross) coords from the nearest centreline sample
def brush(pts,w0,w1,tone,dry=0.35,seed=0,n=None):
    r=np.random.default_rng(seed); pts=np.array(pts,float)
    t=np.linspace(0,1,len(pts)); tt=np.linspace(0,1,600)
    xs=ndi.gaussian_filter1d(np.interp(tt,t,pts[:,0]),12,mode='nearest'); ys=ndi.gaussian_filter1d(np.interp(tt,t,pts[:,1]),12,mode='nearest')
    dx=np.gradient(xs); dy=np.gradient(ys); nl=np.hypot(dx,dy)+1e-6; nx,ny=-dy/nl,dx/nl
    x0,x1=int(max(0,xs.min()-w0-20)),int(min(W,xs.max()+w0+20)); y0,y1=int(max(0,ys.min()-w0-20)),int(min(H,ys.max()+w0+20))
    h,w=y1-y0,x1-x0; idx=-np.ones((h,w),int)
    for i in range(600):
        xi,yi=int(xs[i])-x0,int(ys[i])-y0
        if 0<=xi<w and 0<=yi<h: idx[yi,xi]=i
    dist,(iy,ix)=ndi.distance_transform_edt(idx<0,return_indices=True)
    I=idx[iy,ix]; T=tt[I]
    yy,xx=np.mgrid[y0:y1,x0:x1]
    cross=(xx-xs[I])*nx[I]+(yy-ys[I])*ny[I]
    half=(w0+(w1-w0)*T)/2
    # pressure: taper in at start, out at end
    half=half*np.clip(np.minimum(T/0.06,1),0.3,1)*np.clip((1-T)/0.10,0.15,1)
    edgeN=P.noise(h,w,6,2,seed+1)
    tx_,ty_=dx/nl,dy/nl
    along=(xx-xs[I])*tx_[I]+(yy-ys[I])*ty_[I]
    s_=cross/np.maximum(half,1)
    body=(np.abs(s_)<1+0.25*(edgeN-0.5))&(np.abs(along)<4)
    # bristles: high-freq 1D noise across the stroke, stretched along it
    bq=np.random.default_rng(seed+2).random(400); bq=ndi.gaussian_filter1d(bq,0.7)
    bi=((s_+1.3)/2.6*399).clip(0,399).astype(int); bris=(bq[bi]-bq.min())/(np.ptp(bq)+1e-6)
    along=P.noise(1,600,40,3,seed+3)[0][I]
    dryness=dry*(0.25+1.1*T**1.5)+0.25*(along-0.5)
    bris=0.6*bris+0.4*P.noise(h,w,3,1,seed+6)
    m=body*np.clip((bris-dryness)*3.2+0.75,0,1)
    m*=0.75+0.25*P.noise(h,w,25,2,seed+4)
    m=ndi.gaussian_filter(m,0.8)
    full=np.zeros((H,W)); full[y0:y1,x0:x1]=m
    return (full*tone).clip(0,1)
rv=brush(river,100,60,0.9,dry=0.40,seed=3); wash(rv,W1)
cs=brush(coast,46,26,0.85,dry=0.35,seed=5); wash(cs,INK)
# a few dry wave strokes in the sea
for i,(x,y,l) in enumerate([(2230,1010,300),(2300,1250,240)]):
    wv=brush([(x,y),(x+l*0.35,y-26),(x+l*0.7,y-8),(x+l,y-30)],22,10,0.6,dry=0.5,seed=40+i); wash(wv,W2)
# forest bleeds lower-left (tonal, no trees)
def smudge(cx,cy,rx,ry,tone,seed):
    n=P.noise(H,W,90,4,seed); yy,xx=np.mgrid[0:H,0:W]
    d=np.sqrt(((xx-cx)/rx)**2+((yy-cy)/ry)**2); f=(1-d)+0.55*(n-0.5)
    core=ss(f,0.0,0.4); edge=np.exp(-((f-0.03)/0.045)**2)*0.4
    return ((core*0.7+edge)*(0.85+0.3*P.noise(H,W,30,3,seed+1))*tone).clip(0,1)
sm=np.maximum.reduce([smudge(420,1250,470,230,0.60,21),smudge(760,1080,320,140,0.48,22),smudge(160,1060,200,120,0.40,23)])
wash(sm,W2)
# mountains on top
base=base*(1-alpha[...,None])+inkcol*alpha[...,None]
# sun (from gen, palette vermilion with wash variance)
sun=P.redmask(g); sunsoft=ndi.gaussian_filter(ndi.binary_dilation(sun,iterations=1).astype(float),1.2)
mott=0.9+0.16*P.noise(H,W,30,3,9)
base=base*(1-sunsoft[...,None])+(VER*mott[...,None])*sunsoft[...,None]
# corridor clearing around world.json paths + nodes
pm=np.zeros((H,W),np.uint8)
for p in worldgeo.curves(400): cv2.polylines(pm,[p.astype(np.int32)],False,1,3)
dpath=ndi.distance_transform_edt(pm==0)
nm=np.zeros((H,W),np.uint8)
for (x,y) in worldgeo.N.values(): cv2.circle(nm,(int(x),int(y)),4,1,-1)
dnode=ndi.distance_transform_edt(nm==0)
kp=np.minimum(ss(dpath,50,140),ss(dnode,100,200))
kk=np.where(ndi.binary_dilation(sun,iterations=6),1.0,0.22+0.78*kp)[...,None]
base=PAPER+(base-PAPER)*kk
# Hanshi: small ink mark just below the town node
tx,ty=[int(v) for v in worldgeo.N['hanshi']]
mk=np.zeros((H,W),np.uint8)
for dx,dy,s in [(-30,58,13),(2,52,16),(32,60,11)]:
    cv2.polylines(mk,[np.array([(tx+dx-s,ty+dy+s//2),(tx+dx,ty+dy-s//3),(tx+dx+s,ty+dy+s//2)])],False,1,4)
cv2.line(mk,(tx-48,ty+76),(tx+46,ty+78),1,3)
mkf=ndi.gaussian_filter(mk.astype(float),0.9)[...,None]; base=base*(1-0.85*mkf)+INK*0.85*mkf
# faint 6-panel byobu seams + alternating panel tone, faded near nodes
shade=np.ones((H,W))
for i in range(6): shade[:,W*i//6:W*(i+1)//6]*=1+(0.012 if i%2 else -0.008)
seam=np.zeros((H,W))
for i in range(1,6): x=W*i//6; seam[:,x-1:x+1]=1; seam[:,x+1:x+3]=0.35
seam=ndi.gaussian_filter(seam,0.6)*ss(dnode,40,120)
base=base*shade[...,None]*(1-0.10*seam[...,None])
base=base*(1+0.02*P.grain(H,W)[...,None])
P.save(base,'world-bg')
Image.open(f"{OUT}/world-bg.png").resize((1920,1080),Image.LANCZOS).save(f"{OUT}/world-bg@1080.png",optimize=True)
Image.open(f"{OUT}/world-bg.png").resize((1280,720),Image.LANCZOS).save(f"{PV}/world-bg-720.jpg",quality=88)
dbg=Image.open(f"{OUT}/world-bg.png").convert('RGB'); dd=ImageDraw.Draw(dbg)
for p in worldgeo.curves(): dd.line([tuple(q) for q in p],fill=(120,120,120),width=5)
for x,y in worldgeo.N.values(): dd.ellipse([x-20,y-20,x+20,y+20],fill=(179,38,30))
dbg.resize((1280,720),Image.LANCZOS).save(f"{PV}/world-bg-nodes-overlay-720.jpg",quality=88)
print('world ok')
