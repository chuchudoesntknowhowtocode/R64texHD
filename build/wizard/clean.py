from PIL import Image
import numpy as np, scipy.ndimage as nd
from scipy.cluster.vq import kmeans2
np.random.seed(3)
def prep(name,h,erode):
    a=np.array(Image.open(f'raw_{name}.png')).astype(float)
    m=a[...,3]>0
    if name in 'CF':
        lab,n=nd.label(m); sz=nd.sum(m,lab,range(1,n+1)); m=lab==1+np.argmax(sz)
    if name=='R':
        m=nd.binary_fill_holes(nd.binary_closing(m,iterations=6))
    m=nd.binary_erosion(m,iterations=erode)
    # strip light, desaturated fringe pixels on the silhouette edge
    edge=m&~nd.binary_erosion(m,iterations=2)
    rgb=a[...,:3]; sat=rgb.max(2)-rgb.min(2); br=rgb.mean(2)
    m&=~(edge&(br>150)&(sat<40))
    _,idx=nd.distance_transform_edt(~m,return_indices=True)
    rgb=rgb[idx[0],idx[1]]
    ys,xs=np.nonzero(m); rgb=rgb[ys.min():ys.max()+1,xs.min():xs.max()+1]; m=m[ys.min():ys.max()+1,xs.min():xs.max()+1]
    w=round(m.shape[1]*h/m.shape[0])
    rs=np.array(Image.fromarray(rgb.astype(np.uint8)).resize((w,h),Image.BOX)).astype(float)
    ms=np.array(Image.fromarray((m*255).astype(np.uint8)).resize((w,h),Image.BOX))>120
    return rs,ms
k=66/306
spec={'A':k,'C':k,'E':k,'F':k}
sprites={}
for n in 'CEF': im=Image.open(f'raw_{n}.png'); sprites[n]=prep(n,round(im.height*k),3)
sprites['R']=prep('R',66,8)
allpx=np.concatenate([s[0][s[1]] for s in sprites.values()])
pal,_=kmeans2(allpx,18,minit='++',seed=3)
OUT=np.array([10,14,42.])
for n,(rgb,m) in sprites.items():
    d=((rgb[...,None,:]-pal[None,None])**2).sum(-1); q=pal[d.argmin(-1)]
    # outline: 1px dark ring around silhouette
    ring=nd.binary_dilation(m)&~m
    out=np.zeros(m.shape+(4,))
    out[m,:3]=q[m]; out[m,3]=255
    # pad for outline
    H,W=m.shape; o=np.zeros((H+2,W+2,4)); o[1:-1,1:-1]=out
    mm=np.zeros((H+2,W+2),bool); mm[1:-1,1:-1]=m
    ring=nd.binary_dilation(mm)&~mm
    o[ring,:3]=OUT; o[ring,3]=255
    Image.fromarray(o.astype(np.uint8)).save(f'px_{n}.png')
pv=Image.new('RGBA',(400,90),(25,15,40,255)); x=4
for n in 'RECF':
    s=Image.open(f'px_{n}.png'); pv.alpha_composite(s,(x,88-s.height)); x+=s.width+12
pv.resize((1600,360),Image.NEAREST).save('px_preview.png')
