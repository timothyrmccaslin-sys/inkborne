# v2.1: hide the town-mid stitch seam behind a solid pine; tile A becomes fully opaque right of the trunk.
import numpy as np, os
from PIL import Image, ImageFilter
from scipy import ndimage as ndi
import process_v2 as P
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D); WK=ROOT+'/work'; OUT=P.OUT
W,H,TW=3200,1440,1920
# --- pine: scale so shown-y 20..1000 (of 1024) maps to y 330..1060, trunk (shown x~190) at x~1380
pi=Image.open(f"{D}/gen_town_pine.jpg").convert('RGB')  # 864x1152
s=730/(980*1152/1024); pw,ph=int(864*s),int(1152*s)
pa=np.asarray(pi.resize((pw,ph),Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.2,40,2))).astype(float)
px0=int(1380-190*(864/768)*s); py0=int(330-20*(1152/1024)*s)
L=pa.mean(-1); Lp=np.percentile(L,95)
la=((Lp-L-6)/(Lp-P.INK.mean()-6)).clip(0,1)            # ink coverage
core=ndi.binary_opening(la>0.55,iterations=3)           # trunk, limbs, dense needle masses
core=ndi.binary_fill_holes(ndi.binary_closing(core,iterations=3))
pA=np.maximum(la,ndi.gaussian_filter(core.astype(float),1.0)).clip(0,1)
t=(L/Lp).clip(0,1)[...,None]
inside=P.INK+(P.PAPER-P.INK)*(t**1.15)                  # absolute ink->paper ramp (keeps bark highlights)
inkc=P.INK*(1+0.25*(1-la[...,None]))                    # dark ink for keyed edges/needles
cw=ndi.gaussian_filter(core.astype(float),1.0)[...,None]
prgb=(inside*cw+inkc*(1-cw))*(1+0.02*P.grain(*L.shape)[...,None])
PA=np.zeros((H,W)); PR=np.zeros((H,W,3))
ys,xs=slice(max(py0,0),min(py0+ph,H)),slice(px0,px0+pw)
PA[ys,xs]=pA[max(0,-py0):max(0,-py0)+(ys.stop-ys.start)]; PR[ys,xs]=prgb[max(0,-py0):max(0,-py0)+(ys.stop-ys.start)]
# --- per-row cut x for tile A: centre of the widest fully-opaque pine run in [1290,1480]
cut=np.full(H,1280)
solid=PA>0.97
for y in range(H):
    row=solid[y,1290:1480]
    if not row.any(): continue
    lab,n=ndi.label(row); 
    if n==0: continue
    sz=ndi.sum(row,lab,range(1,n+1)); k=int(np.argmax(sz))+1; idx=np.where(lab==k)[0]
    if sz[k-1]>=12: cut[y]=1290+int(idx.mean())
rows=np.arange(H); band=(rows>=330)&(rows<1066)
missing=band&(cut==1280)
print('rows in seam band without pine cover:',int(missing.sum()))
# fill gaps by interpolation from neighbouring covered rows
good=band&(cut>1280)
cut[band]=np.interp(rows[band],rows[good],cut[good]).astype(int)
cut[rows<330]=int(cut[good][0]); cut[rows>=1066]=int(cut[good][-1])
cut=ndi.uniform_filter1d(cut.astype(float),5).astype(int)
# --- re-stitch: A at 1280 (no left feather; removed left of cut), B2 at 0 with right feather, ground crossfade as before
def tile(n):
    im=Image.open(f"{D}/{n}").convert("RGB").resize((TW,H),Image.LANCZOS)
    return np.asarray(im.filter(ImageFilter.UnsharpMask(1.6,50,2))).astype(float)
def nw(a): p=np.percentile(a.reshape(-1,3),95,axis=0); return (a/p*255).clip(0,255)
def ramp(n,a,b): x=np.arange(n); return ((x-a)/(b-a)).clip(0,1)
A=nw(tile('tmid_a.jpg')); B=nw(tile('tmid_b.jpg'))
ca=np.full((H,W,3),255.0); cb=np.full((H,W,3),255.0); ca[:,1280:]=A; cb[:,:TW]=B
xx=np.arange(W)[None,:]
ma=(xx>=cut[:,None]).astype(float); ma=ndi.gaussian_filter(ma,(0,2))
fb=1-ramp(W,TW-180,TW); fb[TW:]=0
ca_cut=255-(255-ca)*ma[...,None]; cb_f=255-(255-cb)*fb[None,:,None]
mult=ca_cut*cb_f/255.0
gy=int(H*0.72); w=ramp(W,1280,1920)[None,:,None]
groundmix=np.where(xx[...,None]<1280,cb,np.where(xx[...,None]>=1920,ca,cb*(1-w)+ca*w))
g=ramp(H,gy-40,gy+40)[:,None,None]
stitched=mult*(1-g)+groundmix*g
Image.fromarray(stitched.clip(0,255).astype(np.uint8)).save(f"{WK}/town-mid.png")
# --- key + noren mark exactly as v2, then pine over at full alpha
rgb,Aa=P.keyed(stitched,ground_y=int(1440*0.74),fill_holes=True,silhouette=True,lighten=(int(1440*0.76),0.6))
Ls=stitched.mean(-1); Y=np.arange(H)[:,None]
zone=(xx>=1135)&(xx<cut[:,None]+8)&(Y<1040)&(Ls>232)&((xx>=1205)|(Y>=612))
zone=ndi.binary_closing(zone,iterations=4)
zone=ndi.binary_opening(zone,iterations=5)
zone&=ndi.binary_erosion(Ls>200,iterations=1)
zs=ndi.gaussian_filter(zone.astype(float),2.0)
Aa=Aa*(1-zs); rgb=np.where((zs>0.99)[...,None],P.PAPER,rgb)
mk=Image.open(f"{D}/prop-kobo-tsuru-mark.webp").convert('RGBA').resize((76,76),Image.LANCZOS)
mm=np.asarray(mk).astype(float)/255.0; ma_a=mm[...,3]*0.92
cx,cy=2433,836; sl=(slice(cy-38,cy+38),slice(cx-38,cx+38))
cloth=rgb[sl].mean(-1,keepdims=True); cl=(cloth/np.percentile(cloth,85)).clip(0.55,1.05)
mott=0.9+0.15*P.noise(76,76,10,2,77)[...,None]
red=(P.VER*cl*mott).clip(0,P.VER*1.06)
rgb[sl]=rgb[sl]*(1-ma_a[...,None])+red*ma_a[...,None]
rgb=rgb*(1-PA[...,None])+PR*PA[...,None]; Aa=np.maximum(Aa,PA)
P.save(rgb,'poi-town-mid',Aa)
print('cut range',cut[330:1066].min(),cut[330:1066].max(),'pine box',px0,py0,pw,ph)
