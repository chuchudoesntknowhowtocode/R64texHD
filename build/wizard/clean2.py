from PIL import Image
import numpy as np, scipy.ndimage as nd
from scipy.cluster.vq import vq
exec(open('clean.py').read().split("k=66/306")[0])   # reuse prep()
k=66/306
pal_src=[np.array(Image.open(f'px_{n}.png')) for n in 'RECF']
pal=np.unique(np.concatenate([p[p[...,3]>0][:,:3] for p in pal_src]),axis=0).astype(float)
OUT=np.array([10,14,42.])
def glowkill(name):
    a=np.array(Image.open(f'raw_{name}.png')).astype(int); h,w=a.shape[:2]
    rgb=a[...,:3]; sat=rgb.max(2)-rgb.min(2); br=rgb.mean(2)
    glow=(br>85)&(sat<95)&~((rgb[...,2]>200)&(rgb[...,0]<120))   # tinted checker but not saturated cyan core
    reg=np.zeros((h,w),bool)
    if name=='B': reg[:int(h*.42),int(w*.72):]=True; reg[int(h*.25):int(h*.6),:int(w*.2)]=True
    if name=='I': reg[:, :int(w*.33)]=True
    a[...,3]=np.where(reg&glow,0,a[...,3])
    m=a[...,3]>0; lab,n=nd.label(m); sz=nd.sum(m,lab,range(1,n+1)); m=lab==1+np.argmax(sz)
    a[...,3]=m*255; Image.fromarray(a.astype(np.uint8)).save(f'raw_{name}x.png')
glowkill('B'); glowkill('I')
for n in ['D','H']:
    a=np.array(Image.open(f'raw_{n}.png')); m=a[...,3]>0; lab,c=nd.label(m); sz=nd.sum(m,lab,range(1,c+1))
    a[...,3]=(lab==1+np.argmax(sz))*255; im=Image.fromarray(a); im.crop(im.getbbox()).save(f'raw_{n}x.png')
for n in ['Bx','Ix','Dx','Hx']:
    im=Image.open(f'raw_{n}.png'); im=im.crop(im.getbbox()); im.save(f'raw_{n}.png')
    rgb,m=prep(n,round(im.height*k),3)
    d=((rgb[...,None,:]-pal[None,None])**2).sum(-1); q=pal[d.argmin(-1)]
    H,W=m.shape; o=np.zeros((H+2,W+2,4)); mm=np.zeros((H+2,W+2),bool); mm[1:-1,1:-1]=m
    o[1:-1,1:-1][m,:3]=q[m]; o[mm,3]=255
    ring=nd.binary_dilation(mm)&~mm; o[ring,:3]=OUT; o[ring,3]=255
    Image.fromarray(o.astype(np.uint8)).save(f'px_{n[0]}.png')
pv=Image.new('RGBA',(420,100),(25,15,40,255)); x=4
for n in 'BIDH':
    s=Image.open(f'px_{n}.png'); pv.alpha_composite(s,(x,98-s.height)); x+=s.width+10
pv.resize((1680,400),Image.NEAREST).save('px_preview2.png')
