# Post-process generated ink art into SPEC v1 environment assets (2560x1440, sRGB).
import numpy as np, os
from PIL import Image, ImageFilter
from scipy import ndimage as ndi
W,H=2560,1440
D=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.dirname(D)
PAPER=np.array([0xec,0xe6,0xd8],float); INK=np.array([0x1b,0x18,0x13],float)
rng=np.random.default_rng(7)

def load(n):
    im=Image.open(f"{D}/{n}").convert("RGB").resize((W,H),Image.LANCZOS)
    im=im.filter(ImageFilter.UnsharpMask(radius=2,percent=60,threshold=2))
    return np.asarray(im).astype(float)

def grain():
    g=rng.normal(0,1,(H//2,W//2)); g=ndi.gaussian_filter(g,1.0)
    g=np.asarray(Image.fromarray(((g*40)+128).clip(0,255).astype(np.uint8)).resize((W,H),Image.BICUBIC)).astype(float)
    return (g-128)/128.0
G=grain()

def redmask(a):
    r,g,b=a[...,0],a[...,1],a[...,2]
    return ((r-np.maximum(g,b))>40)

def to_palette(a):
    """Map greys onto SPEC paper/ink ramp; keep vermilion pixels, desaturate everything else."""
    L=a.mean(-1)
    lo,hi=np.percentile(L,0.5),np.percentile(L,99.5)
    t=((L-lo)/max(hi-lo,1)).clip(0,1)[...,None]
    grey=INK+(PAPER-INK)*t
    rm=ndi.binary_dilation(redmask(a),iterations=2)
    s=ndi.gaussian_filter(rm.astype(float),1.2)[...,None]
    # pull reds toward SPEC vermilion #b3261e, keep shading
    ver=np.array([0xb3,0x26,0x1e],float)*(0.55+0.6*t)
    out=grey*(1-s)+ver.clip(0,255)*s
    out=out*(1+0.025*G[...,None])
    return out.clip(0,255), rm

def save(arr,name,alpha=None):
    a8=arr.clip(0,255).astype(np.uint8)
    if alpha is not None:
        im=Image.fromarray(np.dstack([a8,(alpha*255).clip(0,255).astype(np.uint8)]),"RGBA")
    else: im=Image.fromarray(a8,"RGB")
    im.save(f"{OUT}/{name}.png",optimize=True)
    im.save(f"{OUT}/{name}.webp",quality=90,method=6)
    return im

def opaque(src,name):
    out,_=to_palette(load(src)); return save(out,name)

def keyed(src,name,ground_y=None,fill_holes=False):
    a=load(src); L=a.mean(-1)
    Lp=np.percentile(L,92)  # paper level (layers are mostly paper)
    Lk=INK.mean()
    t0=10.0
    alpha=((Lp-L-t0)/(Lp-Lk-t0)).clip(0,1)
    alpha=alpha**0.8
    rm=ndi.binary_dilation(redmask(a),iterations=2)
    alpha=np.maximum(alpha,ndi.gaussian_filter(rm.astype(float),1.0))
    solid=np.zeros((H,W),bool)
    if fill_holes:
        # paper regions not connected to the sky/border stay opaque (house walls, noren, etc.)
        paper=alpha<0.15
        lab,n=ndi.label(paper)
        border=set(np.unique(np.concatenate([lab[0],lab[:,0],lab[:,-1]])))-{0}
        enclosed=paper&~np.isin(lab,list(border))
        sizes=ndi.sum(enclosed,lab,range(n+1))
        solid|=enclosed
    if ground_y is not None:
        ramp=((np.arange(H)-ground_y)/30.0).clip(0,1)[:,None]
        solid_f=np.maximum(solid.astype(float),ramp*np.ones((1,W)))
    else: solid_f=solid.astype(float)
    solid_f=ndi.gaussian_filter(solid_f,1.5)
    # unmix ink colour against paper white
    pw=np.percentile(a.reshape(-1,3),92,axis=0)
    with np.errstate(divide='ignore',invalid='ignore'):
        col=(a-(1-alpha[...,None])*pw)/np.maximum(alpha[...,None],1e-3)
    col=col.clip(0,255)
    ink,_=to_palette(col)
    # opaque-fill regions: paper tint of the original pixels
    papered,_=to_palette(a)
    A=np.maximum(alpha,solid_f)
    w=(solid_f/np.maximum(A,1e-3))[...,None]
    rgb=ink*(1-w)+papered*w
    # despeckle: kill tiny isolated faint blobs
    m=A>0.06; lab,n=ndi.label(m); sz=ndi.sum(m,lab,range(n+1))
    A=np.where(np.isin(lab,np.where(sz<40)[0]),0,A); A[A<0.04]=0
    A=ndi.gaussian_filter(A,0.6)
    rgb[A<0.01]=PAPER  # clean colour under fully transparent px
    return save(rgb,name,A)

layers={}
layers['world-bg']=opaque('gen_world.jpg','world-bg')
Image.open(f"{OUT}/world-bg.png").resize((1920,1080),Image.LANCZOS).save(f"{OUT}/world-bg@1080.png",optimize=True)
layers['poi-forest-far']=opaque('gen_forest_far.jpg','poi-forest-far')
layers['poi-forest-mid']=keyed('gen_forest_mid.jpg','poi-forest-mid',ground_y=int(H*0.775))
layers['poi-forest-near']=keyed('gen_forest_near.jpg','poi-forest-near')
layers['poi-town-far']=opaque('gen_town_far.jpg','poi-town-far')
layers['poi-town-mid']=keyed('gen_town_mid.jpg','poi-town-mid',ground_y=int(H*0.735),fill_holes=True)
layers['poi-town-near']=keyed('gen_town_near.jpg','poi-town-near')
layers['battle-forest']=opaque('gen_battle.jpg','battle-forest')

def comp(prefix):
    base=layers[prefix+'-far'].convert('RGBA')
    mist=Image.new('RGBA',(W,H),(236,230,216,0))
    m=np.zeros((H,W)); yy=np.arange(H)[:,None]
    m=(np.exp(-((yy-H*0.62)/(H*0.08))**2)*0.45)*np.ones((1,W))
    m*=0.7+0.3*ndi.gaussian_filter(rng.random((H//8,W//8)),3).repeat(8,0).repeat(8,1)/0.5
    mist.putalpha(Image.fromarray((m.clip(0,1)*255).astype(np.uint8)))
    out=Image.alpha_composite(base,mist)          # FX slot A: far->mid
    out=Image.alpha_composite(out,layers[prefix+'-mid'])
    out=Image.alpha_composite(out,layers[prefix+'-near'])
    out.convert('RGB').save(f"{OUT}/preview/{prefix}-preview.png",optimize=True)
    out.convert('RGB').resize((1280,720),Image.LANCZOS).save(f"{OUT}/preview/{prefix}-preview-720.jpg",quality=88)
comp('poi-forest'); comp('poi-town')
# alpha check sheets: layers over a checker so transparency is visible
def checker(name):
    im=layers[name]; c=np.indices((H//40,W//40)).sum(0)%2
    bg=np.kron(c,np.ones((40,40)))[:H,:W]*60+150
    bgim=Image.fromarray(np.dstack([bg]*3).astype(np.uint8)).convert('RGBA')
    Image.alpha_composite(bgim,im).convert('RGB').resize((1280,720)).save(f"{OUT}/preview/{name}-alphacheck.jpg",quality=85)
for n in ['poi-forest-mid','poi-forest-near','poi-town-mid','poi-town-near']: checker(n)
Image.open(f"{OUT}/world-bg.png").resize((1280,720),Image.LANCZOS).save(f"{OUT}/preview/world-bg-720.jpg",quality=88)
Image.open(f"{OUT}/battle-forest.png").resize((1280,720),Image.LANCZOS).save(f"{OUT}/preview/battle-forest-720.jpg",quality=88)
print("done")
