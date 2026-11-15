# v2 step 1: upscale 4:3 tiles (1152x864 -> 1920x1440) and stitch to 3200x1440 RGB "paper" canvases.
import numpy as np, os
from PIL import Image, ImageFilter
D=os.path.dirname(os.path.abspath(__file__)); B=os.path.join(D,'..','work'); os.makedirs(B,exist_ok=True)
W,H,TW=3200,1440,1920
def tile(n):
    im=Image.open(f"{D}/{n}").convert("RGB").resize((TW,H),Image.LANCZOS)
    return np.asarray(im.filter(ImageFilter.UnsharpMask(1.6,50,2))).astype(float)
def norm_white(a):  # paper -> 255 so multiply works
    p=np.percentile(a.reshape(-1,3),95,axis=0); return (a/p*255).clip(0,255)
def ramp(n,a,b):  # 0 at a ->1 at b
    x=np.arange(n); return ((x-a)/(b-a)).clip(0,1)
def stitch_far(l,r,ol,orr):
    L,R=tile(l),tile(r); out=np.zeros((H,W,3))
    out[:,:TW]=L; w=ramp(W,1280,1920)[None,:,None]
    Rf=np.zeros((H,W,3)); Rf[:,1280:]=R
    # match R tone to L in overlap
    m=(L[:,1280:].mean((0,1))/R[:,:640].mean((0,1))); Rf*=m
    out=out*(1-w)+Rf*w; out[:,1920:]=Rf[:,1920:]; return out
def stitch_alpha(l,r,offL,offR,ground_y,feather=180):
    L,R=norm_white(tile(l)),norm_white(tile(r))
    cl=np.full((H,W,3),255.0); cr=np.full((H,W,3),255.0)
    cl[:,offL:offL+TW]=L; cr[:,offR:offR+TW]=R
    # feather inner edges to white
    def fe(off):
        f=np.ones(W)
        if off>0: f=np.minimum(f,ramp(W,off,off+feather))
        if off+TW<W: f=np.minimum(f,1-ramp(W,off+TW-feather,off+TW))
        f[:off]=0; f[off+TW:]=0; return f
    fl,fr=fe(offL),fe(offR)
    cl=255-(255-cl)*fl[None,:,None]; cr=255-(255-cr)*fr[None,:,None]
    mult=cl*cr/255.0
    # ground band: linear crossfade across overlap instead of multiply
    o0,o1=max(offL,offR),min(offL,offR)+TW
    w=ramp(W,o0,o1)[None,:,None]
    left_is_L = offL<offR
    A_,B_=(cl,cr) if left_is_L else (cr,cl)
    Lg=np.where(np.arange(W)[None,:,None]<o0,A_,0); 
    cross=np.where(np.arange(W)[None,:,None]<o0,A_,np.where(np.arange(W)[None,:,None]>=o1,B_,
          (255-(255-A_)/np.maximum(1-ramp(W,o1-feather,o1)[None,:,None]*0+1,1))*(1-w)+B_*w))
    # undo the feathering for the ground crossfade: use raw tiles there
    rawA=np.full((H,W,3),255.0); rawB=np.full((H,W,3),255.0)
    (rawA[:,offL:offL+TW],rawB[:,offR:offR+TW])=(L,R) if left_is_L else (R,L)
    if not left_is_L: rawA[:]=255; rawB[:]=255; rawA[:,offR:offR+TW]=R; rawB[:,offL:offL+TW]=L
    gx=np.arange(W)[None,:,None]
    groundmix=np.where(gx<o0,rawA,np.where(gx>=o1,rawB,rawA*(1-w)+rawB*w))
    gy=ramp(H,ground_y-40,ground_y+40)[:,None,None]
    return mult*(1-gy)+groundmix*gy
def save(a,n): Image.fromarray(a.clip(0,255).astype(np.uint8)).save(f"{B}/{n}.png")
save(stitch_far('ffar_a.jpg','ffar_b.jpg',0,1280),'forest-far')
save(stitch_far('tfar_a.jpg','tfar_b.jpg',0,1280),'town-far')
save(stitch_alpha('fmid_a.jpg','fmid_b.jpg',0,1280,int(H*0.76)),'forest-mid')
save(stitch_alpha('tmid_a.jpg','tmid_b.jpg',1280,0,int(H*0.72)),'town-mid')
save(stitch_alpha('fnear_a.jpg','fnear_b.jpg',0,1280,H+100),'forest-near')
save(stitch_alpha('tnear_a.jpg','tnear_b.jpg',0,1280,H+100),'town-near')
print('stitched')
