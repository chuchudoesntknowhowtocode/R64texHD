import os
from PIL import Image, ImageOps
import numpy as np, scipy.ndimage as nd, math, random
random.seed(7)
S=2; FPS=30; N=84
bg1=Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'assets','app_idle.png')).convert('RGB')
BG=bg1.resize((bg1.width*S,bg1.height*S),Image.NEAREST).convert('RGBA')
FW,FH=BG.size
FLOOR=372; SAFE_TOP=216; PIPE_X=172; QUIT_X=1484
def largest(img):
    a=np.array(img); m=a[...,3]>0; lab,n=nd.label(m)
    if n>1:
        sz=nd.sum(m,lab,range(1,n+1)); a[...,3]=np.where(lab==1+np.argmax(sz),a[...,3],0)
    im=Image.fromarray(a); return im.crop(im.getbbox())
def scale(img,h):
    w=round(img.width*h/img.height); r=img.resize((w,h),Image.LANCZOS)
    a=np.array(r); a[...,3]=np.where(a[...,3]>110,255,0); return Image.fromarray(a)
def U(im): return im.resize((im.width*S,im.height*S),Image.NEAREST)
P1={n:Image.open(f'px_{n}.png') for n in 'RECF'}
P1['Cf']=ImageOps.mirror(P1['C']); P1['Ff']=ImageOps.mirror(P1['F'])
P={n:U(v) for n,v in P1.items()}
def shear(img,amt):  # lean top toward the left by amt px per px height
    w,h=img.size; ext=int(abs(amt)*h)+2
    out=img.transform((w+ext,h),Image.AFFINE,(1,amt,-ext if amt<0 else 0,0,1,0),Image.NEAREST)
    # amt>0 : x_src = x + amt*y -> top shifts right... we want head left (forward): bottom row unchanged
    return out
def lean(img,deg):
    a=math.tan(math.radians(deg)); w,h=img.size; ext=int(a*h)+2
    # top shifted left by a*h, bottom fixed
    return img.transform((w+ext,h),Image.AFFINE,(1,-a,-a*h,0,1,0),Image.NEAREST) if False else \
           img.transform((w+ext,h),Image.AFFINE,(1,a,-ext,0,1,0),Image.NEAREST).crop((0,0,w+ext,h))
def stride_swap(img,frac=0.30):
    a=np.array(img).copy(); h,w=a.shape[:2]; t=int(h*(1-frac))
    low=a[t:].copy(); cols=np.nonzero(low[...,3].any(0))[0]; c0,c1=cols.min(),cols.max()
    seg=low[:,c0:c1+1][:,::-1]; low[:]=0; low[:,c0:c1+1]=seg; a[t:]=low
    return Image.fromarray(a)
def squash(img,sy,sx=1.0):
    return img.resize((max(1,round(img.width*sx)),max(1,round(img.height*sy))),Image.NEAREST)
runA=U(lean(P1['Cf'],14)); runB=U(lean(stride_swap(P1['Cf']),14))
runA2=U(lean(squash(P1['Cf'],0.95,1.04),16)); runB2=U(lean(squash(stride_swap(P1['Cf']),0.95,1.04),16))
RUN=[runA,runA2,runB,runB2]
CYAN=(30,225,255); WHITE=(235,250,255); LBLUE=(110,190,255); NAVY=(20,40,110); PINK=(230,90,170)
def px(layer,x,y,s,c,a=255):
    x=int(x);y=int(y)
    if s<=0: return
    blk=Image.new('RGBA',(s,s),c+(int(max(0,min(255,a))),))
    layer.alpha_composite(blk,(max(0,min(FW-s,x)),max(0,min(FH-s,y))))
def place(fr,img,cx,bottom,alpha=1.0,tint=None,clip=True):
    im=img
    if tint is not None:
        a=np.array(im).astype(float); a[...,:3]=a[...,:3]*(1-tint[1])+np.array(tint[0])*tint[1]
        a[...,3]*=alpha; im=Image.fromarray(a.clip(0,255).astype(np.uint8))
    elif alpha<1:
        a=np.array(im); a[...,3]=(a[...,3]*alpha).astype(np.uint8); im=Image.fromarray(a)
    x=int(round(cx-im.width/2)); y=int(round(bottom-im.height))
    if clip and x<PIPE_X:
        cut=PIPE_X-x
        if cut>=im.width: return
        im=im.crop((cut,0,im.width,im.height)); x=PIPE_X
    fr.alpha_composite(im,(x,y))
def reveal(img,prog):
    a=np.array(img).copy(); h=a.shape[0]; line=int(h*prog)
    out=a.copy(); out[line:,:,3]=0
    for r in range(max(0,line-10),min(h,line+1)):
        if r<h:
            row=out[r].copy(); m=row[:,3]>0
            row[m,:3]=(row[m,:3]*0.3+np.array(WHITE)*0.7).astype(np.uint8)
            sh=random.randint(-6,6); out[r]=np.roll(row,sh,axis=0)
    return Image.fromarray(out)
APP_CX=1395  # appear spot, left of Quit
# precomputed sparkles
spark=[(random.uniform(0,6.28),random.uniform(60,150),random.uniform(-50,30),random.choice([CYAN,WHITE,LBLUE]),random.choice([2,4,4,6])) for _ in range(46)]
dust=[]; trail=[]
run_x0=APP_CX; run_x1=PIPE_X+60
for f in range(N):
    t=f/FPS; fr=BG.copy(); fx=Image.new('RGBA',(FW,FH),(0,0,0,0)); top=Image.new('RGBA',(FW,FH),(0,0,0,0))
    wiz=None; cx=APP_CX; bottom=FLOOR
    # ---- 1. magic summon f4-20
    if 4<=f<=22:
        p=(f-4)/16
        # floor rune ring
        rx=70*min(1,p*2.2); ry=12*min(1,p*2.2)
        for i in range(28):
            ang=i/28*6.28+f*0.25
            px(fx,cx+rx*math.cos(ang),FLOOR-4+ry*math.sin(ang),4,CYAN if i%3 else WHITE,220*(1-max(0,p-0.8)*4))
        # spiralling sparkles converging
        for (a0,r0,h0,c,s) in spark:
            r=r0*max(0,1-p)**1.3; ang=a0+p*7
            px(fx,cx+r*math.cos(ang),FLOOR-60+h0*(1-p)+r*0.25*math.sin(ang),s,c,255*min(1,p*3))
    # soft fade-in beam (f5-26), stays below the upper panels
    if 5<=f<=26:
        if f<=13: lvl=((f-5)/8)**1.5
        elif f<=19: lvl=1.0
        else: lvl=1-((f-19)/7)
        BTOP=SAFE_TOP+8; Hh=FLOOR-BTOP
        for yy in range(BTOP,FLOOR,4):
            v=(FLOOR-yy)/Hh                      # 0 at floor .. 1 at top
            g=(1-v)**1.4*lvl
            g*=0.85+0.15*math.sin(yy*0.12-f*0.9)  # gentle upward shimmer
            for w,c,amax in((84,LBLUE,70),(52,CYAN,120),(18,WHITE,170)):
                ww=int(w*(0.7+0.3*lvl))//4*4
                top.alpha_composite(Image.new('RGBA',(ww,4),c+(int(amax*g),)),(cx-ww//2,yy))
        for i in range(10):                     # motes drifting up inside the beam
            ph_=((f*6+i*23)%Hh)
            px(top,cx-28+(i*29)%56,FLOOR-ph_,4,WHITE if i%2 else CYAN,220*lvl*(1-ph_/Hh))
    if 13<=f<=15:  # flash
        a=[150,230,110][f-13]; rr=[30,52,70][f-13]
        for dy in range(-rr,rr+1,4):
            for dx in range(-rr,rr+1,4):
                dd=abs(dx)+abs(dy)*0.6
                if dd<=rr: px(top,cx+dx,FLOOR-75+dy,4,WHITE if dd<rr*0.5 else CYAN,a*(1-dd/rr*0.8))
    # ---- 2. materialise levitating f12-24, descend f24-29
    if 12<=f<=29:
        lift=26 if f<=24 else int(26*(1-((f-24)/5)**2))
        bob=int(3*math.sin(f*0.9)) if f<=24 else 0
        img=reveal(P['E'],min(1,(f-12)/9)) if f<21 else P['E']
        wiz=(img,cx,FLOOR-lift+bob)
        for i in range(5):  # levitation drips
            yy=FLOOR-lift+6+((f*7+i*9)%26); xx=cx-30+i*15
            px(fx,xx,yy,4,CYAN if i%2 else LBLUE,200-((f*7+i*9)%26)*7)
    # ---- 3. land f30-33 (front pose, squash)
    if 30<=f<=33:
        sq=[0.88,0.94,1.0,1.0][f-30]
        wiz=(U(squash(P1['R'],sq,2-sq)),cx,FLOOR)
        if f<=31:
            for i in range(6):
                d=(f-29)*14+i*3
                px(fx,cx-40-d,FLOOR-4-i%3*4,4,(200,170,210),180); px(fx,cx+40+d,FLOOR-4-i%3*4,4,(200,170,210),180)
    # ---- 4. turn + crouch anticipation f34-39
    if 34<=f<=39:
        img=P1['Ff'] if f>=36 else P1['Cf']
        if f>=36: img=squash(img,[0.92,0.86,0.84,0.86][f-36],1.05)
        img=U(img)
        wiz=(img,cx+ (0 if f<38 else 6),FLOOR)
    # ---- 5. sprint f40-69
    if 40<=f<=69:
        u=(f-40)/29
        cx=run_x0-(run_x0-run_x1)*(u**1.6*0.35+u*0.65)
        ph=(f-40)%4; img=RUN[ph]; b=FLOOR-(4 if ph in(1,3) else 0)
        trail.append((img,cx,b)); trail=trail[-7:]
        ghosts=trail[:-1][::-2][:3]
        for j,(ti,tx,tb) in enumerate(ghosts):
            place(fr,ti,tx,tb,alpha=[0.45,0.28,0.14][j],tint=([60,200,255],1.0))
        wiz=(img,cx,b)
        if f==40:
            for i in range(14): dust.append([cx+30,FLOOR-random.randint(2,20),random.uniform(4,14),random.uniform(-3,0),12])
        if ph in(0,2): dust.append([cx+25,FLOOR-6,random.uniform(2,6),random.uniform(-2,0),9])
        # speed lines
        for i in range(7):
            yy=FLOOR-120+i*17+ (f*5+i*13)%7; ln=60+((i*37+f*11)%70)
            xs=cx+40+((i*23+f*19)%60)
            top.alpha_composite(Image.new('RGBA',(int(ln),2),WHITE+(110,)),(int(xs),int(yy)))
    # ---- 6. dive f70-74
    if 70<=f<=75:
        d=f-70; img=U(P1['Ff'].rotate(18+d*6,expand=True,resample=Image.NEAREST))
        cx=run_x1-14-d*30; wiz=(img,cx,FLOOR-4+d*2)
    # dust particles
    nd_=[]
    for p_ in dust:
        p_[0]+=p_[2]; p_[1]+=p_[3]; p_[4]-=1
        if p_[4]>0:
            px(fx,p_[0],p_[1],4,(205,165,215),p_[4]*20); nd_.append(p_)
    dust=nd_
    fr.alpha_composite(fx)
    if wiz: place(fr,*wiz)
    # pipe bounce + puff f75+
    if f>=75:
        k=f-75; off=[4,8,6,2,0,0,0,0,0,0][min(k,9)]
        if off:
            pipe=BG.crop((20,230,PIPE_X+6,392)); fr.alpha_composite(Image.new('RGBA',pipe.size,(22,13,30,255)),(20,230)); fr.alpha_composite(pipe,(20,230-off))
        for i in range(10):
            ang=-1.2+i*0.27; r=10+k*9
            px(top,PIPE_X+8+r*math.cos(ang)*1.0,300+r*math.sin(ang)*0.9,4,[CYAN,WHITE,LBLUE][i%3],255-k*28)
    fr.alpha_composite(top)
    fr.paste(BG.crop((0,0,FW,SAFE_TOP)),(0,0))  # never draw over the panels
    fr.convert('RGB').save(f'f{f:03d}.png')
print('done')
