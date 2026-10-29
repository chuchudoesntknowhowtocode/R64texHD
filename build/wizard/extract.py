import os
from PIL import Image
import numpy as np, scipy.ndimage as nd
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'assets','pose_sheets')+'/'
S1=D+'ff88068b-image.png'; S2=D+'2cf01425-image.png'; S3=D+'1125234e-image.png'
boxes={'A':(S2,(15,25,245,335)),'B':(S2,(45,340,400,642)),'C':(S2,(440,345,720,642)),
'D':(S2,(120,700,335,985)),'E':(S2,(465,680,705,985)),'F':(S1,(70,160,340,478)),
'G':(S1,(480,140,690,478)),'H':(S1,(55,550,320,990)),'I':(S1,(375,600,735,990)),'R':(S3,(0,0,1086,1448))}
def cut(path,box):
    im=np.array(Image.open(path).convert('RGB').crop(box)).astype(int)
    mx,mn=im.max(2),im.min(2); br=im.mean(2)
    if path==S3: bg=(mx-mn<=16)&(br>205)
    else: bg=(mx-mn<=13)&(br>88)&(br<190)
    fg=~bg
    fg=nd.binary_opening(fg,iterations=2)
    lab,n=nd.label(fg); sizes=nd.sum(fg,lab,range(1,n+1))
    keep=np.isin(lab,1+np.nonzero(sizes>400)[0])
    keep=nd.binary_closing(keep,iterations=1)
    rgba=np.dstack([im,keep*255]).astype(np.uint8)
    img=Image.fromarray(rgba,'RGBA'); return img.crop(img.getbbox())
out={}
for k,(p,b) in boxes.items():
    s=cut(p,b); s.save(f'raw_{k}.png'); out[k]=s; print(k,s.size)
# preview on app bg colour
W=sum(s.width for s in out.values())//2+200
pv=Image.new('RGBA',(1700,800),(25,15,40,255)); x=0;y=0
for k,s in out.items():
    t=s if k!='R' else s.resize((s.width*300//s.height,300))
    if x+t.width>1700: x=0;y+=400
    pv.alpha_composite(t,(x,y)); x+=t.width+10
pv.save('preview.png')
