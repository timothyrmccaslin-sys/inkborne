import numpy as np, os
from PIL import Image
from scipy import ndimage as ndi
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); O=R+'/out'; PV=O+'/preview'
W,H=3200,1440
def comp(p):
    far=Image.open(f"{O}/{p}-far.png").convert('RGBA')
    m=np.exp(-((np.arange(H)[:,None]-H*0.62)/(H*0.08))**2)*0.4*np.ones((1,W))
    mist=Image.new('RGBA',(W,H),(236,230,216,0)); mist.putalpha(Image.fromarray((m*255).astype(np.uint8)))
    out=Image.alpha_composite(far,mist)
    out=Image.alpha_composite(out,Image.open(f"{O}/{p}-mid.png"))
    out=Image.alpha_composite(out,Image.open(f"{O}/{p}-near.png")).convert('RGB')
    out.resize((1600,720),Image.LANCZOS).save(f"{PV}/{p}-preview-wide-720.jpg",quality=88)
    out.crop((0,0,2560,1440)).resize((1280,720),Image.LANCZOS).save(f"{PV}/{p}-preview-720.jpg",quality=88)
    out.crop((640,0,3200,1440)).resize((1280,720),Image.LANCZOS).save(f"{PV}/{p}-preview-scrolled-720.jpg",quality=88)
for p in ['poi-forest','poi-town']: comp(p)
for n in ['poi-forest-mid','poi-forest-near','poi-town-mid','poi-town-near']:
    im=Image.open(f"{O}/{n}.png"); c=np.indices((H//40,W//40)).sum(0)%2
    bg=np.kron(c,np.ones((40,40)))[:H,:W]*60+150
    Image.alpha_composite(Image.fromarray(np.dstack([bg]*3).astype(np.uint8)).convert('RGBA'),im).convert('RGB').resize((1600,720)).save(f"{PV}/{n}-alphacheck.jpg",quality=85)
Image.open(f"{O}/battle-forest.png").resize((1280,720),Image.LANCZOS).save(f"{PV}/battle-forest-720.jpg",quality=88)
print('previews ok')
