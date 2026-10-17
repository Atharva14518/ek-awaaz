"""Premium editorial motion around genuine Ek Awaaz screen recordings.

No UI is recreated: app panels are cropped from the original recordings.
Run with the isolated .voice-env Python. Outputs stay separate from version one.
"""
from __future__ import annotations

import argparse
import concurrent.futures
from functools import lru_cache
import json
import math
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'v2'
FINAL = ROOT / 'final'
W, H, FPS = 1920, 1080, 30
PAPER, INK, CORAL = '#FBF7F2', '#1F1B16', '#E4572E'
SAGE, BLUE, AMBER, MUTED = '#5B8C6B', '#3D6A8F', '#F2A541', '#736B62'
SCENES = [
    dict(start=0, duration=10, kind='hook', title='One voice.\nEvery next step.', chapter='THE IDEA'),
    dict(start=10, duration=10, kind='problem', title='Less pressure.\nMore coordination.', chapter='MEET EK AWAAZ'),
    dict(start=20, duration=11, kind='home', title='A calmer place to start.', chapter='THE ACTUAL APP',
         source='home.mov', seek=0, span=9, crop=(430, 480, 2540, 1120), box=(96, 226, 1728, 752)),
    dict(start=31, duration=6, kind='flow', title='From voice to action.', chapter='THE WORKFLOW'),
    dict(start=37, duration=20, kind='live', title='A conversation, not a form.', chapter='01 / LISTEN',
         source='accident-live.mov', seek=0, span=20, crop=(210, 640, 2060, 1240), box=(96, 226, 1250, 752),
         side=['Natural Hinglish', 'Details highlighted', 'One shared picture'], note='ACTUAL APP RECORDING\nSimulated road-accident scenario'),
    dict(start=57, duration=18, kind='detail', title='Details become understanding.', chapter='02 / UNDERSTAND',
         source='accident-live.mov', seek=9, span=18, crop=(1335, 640, 945, 1310), box=(130, 226, 544, 752),
         side=['Incident type + severity', 'People + injuries', 'Location corrections'], note='FOLLOW THE INCIDENT CARD\nThe latest details replace old guesses.'),
    dict(start=75, duration=12, kind='confirm', title='Confirm first. Then coordinate.', chapter='03 / CONFIRM',
         source='accident-live.mov', seek=17, span=12, crop=(1335, 640, 1880, 1320), box=(96, 226, 1076, 752),
         side=['Incident understood', 'Location confirmed', 'Next steps unlocked'], note='A VISIBLE CHECKPOINT\nFollow the confirmation on the timeline.'),
    dict(start=87, duration=9, kind='parallel', title='One conversation. Two roles.', chapter='04 / COORDINATE'),
    dict(start=96, duration=16, kind='dispatch', title='Every handoff, visible.', chapter='PARALLEL COORDINATION',
         source='accident-live.mov', seek=17, span=12, crop=(1335, 640, 1880, 1320), box=(96, 226, 1076, 752),
         side=['Demo ambulance', 'Family outreach', 'Location link'], note='SIMULATED OUTREACH\nNo real emergency services contacted.'),
    dict(start=112, duration=15, kind='silent', title='When speaking is not an option.', chapter='SILENT MODE',
         source='silent-live.mov', seek=4, span=15, crop=(205, 640, 2080, 1500), box=(96, 226, 1044, 752),
         side=['Discreet prompts', 'Yes / no responses', 'Keypad interaction'], note='A QUIETER INTERACTION\nKeep the next step clear.'),
    dict(start=127, duration=16, kind='report', title='A clear record of every step.', chapter='THE INCIDENT REPORT',
         source='report.mov', seek=0, span=11, crop=(580, 520, 2260, 1610), box=(96, 226, 1056, 752),
         side=['Incident summary', 'Timestamped actions', 'Prototype demonstration'], note='DEMO MODE ONLY\nNot a live emergency response.'),
    dict(start=143, duration=7, kind='close', title='One voice.\nMany calls.', chapter='EK AWAAZ'),
]


def run(args):
    subprocess.run([str(x) for x in args], check=True)


def ease(x):
    x = max(0., min(1., x))
    return 1 - (1-x)**3


@lru_cache(maxsize=100)
def font(size, weight='medium'):
    name={'regular':'Regular','medium':'Medium','semibold':'SemiBold'}[weight]
    return ImageFont.truetype(str(ROOT / 'fonts' / f'Poppins-{name}.ttf'), size)


@lru_cache(maxsize=512)
def text_layer(text, size=32, color=INK, weight='medium', width=1800):
    f = font(size, weight)
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split():
            trial = (line + ' ' + word).strip()
            if f.getlength(trial) > width and line:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    lh = int(size * 1.42)
    tw = min(width + 10, int(max(f.getlength(line) for line in lines)) + 12)
    layer = Image.new('RGBA', (max(1, tw), lh * len(lines) + 12))
    draw = ImageDraw.Draw(layer)
    for i, line in enumerate(lines):
        draw.text((0, i * lh), line, font=f, fill=color, stroke_width=0)
    return layer


def txt(im, text, x, y, size=32, color=INK, weight='medium', width=1800, reveal=1):
    layer = text_layer(text, size, color, weight, width)
    if reveal < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel('A').point(lambda a: int(a * reveal)))
    im.paste(layer, (int(x), int(y)), layer)


def appear(im, text, x, y, t, delay=0, **kwargs):
    p = ease((t-delay)/.7)
    if p:
        txt(im, text, x, y+35*(1-p), reveal=p, **kwargs)


def wave(draw, cx, cy, t, width=330, height=130, color=CORAL):
    for k in range(19):
        amp = .15 + .85 * abs(math.sin(k*.66 + t*3.8) * math.cos(k*.31-t*1.3))
        h = 16 + height*amp
        x = cx-width/2 + k*width/18
        draw.rounded_rectangle((x-5, cy-h/2, x+5, cy+h/2), radius=5, fill=color)


def line_progress(draw, points, progress, color=CORAL, width=4):
    lengths = [math.dist(a,b) for a,b in zip(points, points[1:])]
    remain = sum(lengths) * max(0, min(1, progress))
    for a,b,length in zip(points, points[1:], lengths):
        f = min(1, remain / length) if length else 1
        if f <= 0:
            break
        end = (a[0]+(b[0]-a[0])*f, a[1]+(b[1]-a[1])*f)
        draw.line([a,end], fill=color, width=width)
        remain -= length


def base(scene, dark=False):
    im = Image.new('RGB', (W,H), INK if dark else PAPER)
    d = ImageDraw.Draw(im)
    accent = CORAL
    d.rounded_rectangle((96,69,136,109),radius=13,fill=accent)
    d.arc((105,77,127,99),180,360,fill=PAPER,width=3)
    d.rounded_rectangle((103,88,108,100),radius=2,fill=PAPER)
    d.rounded_rectangle((124,88,129,100),radius=2,fill=PAPER)
    txt(im,'EK AWAAZ',153,69,size=24,color=PAPER if dark else INK,weight='semibold')
    label = scene['chapter']
    layer = text_layer(label,21,'#C6BDB4' if dark else MUTED)
    im.paste(layer,(W-96-layer.width,72),layer)
    if not dark:
        txt(im,scene['title'],96,133,size=52,weight='semibold')
    d.line((96,1037,1824,1037),fill='#443B33' if dark else '#E7DFD6',width=2)
    return im


def footer(im, scene, t):
    d=ImageDraw.Draw(im)
    prog=(scene['start']+min(t,scene['duration']))/150
    d.line((96,1037,96+1728*prog,1037),fill=CORAL,width=3)


def graphic(scene,t):
    kind=scene['kind']
    dark=kind in ('hook','parallel','close')
    im=base(scene,dark)
    d=ImageDraw.Draw(im)
    if kind == 'hook':
        appear(im,'One voice.',96,300,t,size=108,color=PAPER,weight='semibold')
        appear(im,'Every next step.',96,442,t,.7,size=90,color=CORAL,weight='semibold')
        appear(im,'When every second matters.',102,627,t,1.5,size=30,color='#C6BDB4')
        for k in range(3):
            r=110+60*k+9*math.sin(t*1.4-k)
            d.ellipse((1500-r,508-r,1500+r,508+r),outline='#42362C',width=2)
        wave(d,1500,508,t,width=300,height=190)
        appear(im,'A VOICE-FIRST EMERGENCY ASSISTANT',102,850,t,2,size=22,color='#C6BDB4')
    elif kind == 'problem':
        appear(im,'The caller speaks.',106,328,t,.1,size=68,weight='semibold')
        appear(im,'The system coordinates.',106,432,t,.65,size=61,color=CORAL,weight='semibold')
        appear(im,'One calm conversation.\nA clearer path to the next step.',110,590,t,1.3,size=30,color=MUTED)
        labels=['CALLER','LISTENER','COORDINATION']
        for k,label in enumerate(labels):
            p=ease((t-.4-k*.6)/.7)
            y=280+k*186+30*(1-p)
            if k:
                line_progress(d,[(1480,y-64),(1480,y-4)],ease((t-k*.6)/.6),color=CORAL)
            if p:
                d.rounded_rectangle((1230,y,1730,y+118),radius=24,fill='white',outline='#E7DFD6',width=2)
                txt(im,label,1270,y+36,size=25,color=CORAL if k==2 else INK,reveal=p)
                d.ellipse((1660,y+47,1684,y+71),fill=[BLUE,SAGE,CORAL][k])
    elif kind == 'flow':
        names=['Listen','Understand','Confirm','Coordinate']
        subs=['Natural speech','Structured details','Clear checkpoint','Visible next steps']
        colors=[CORAL,BLUE,SAGE,AMBER]
        for k in range(4):
            x=96+k*444
            p=ease((t-.25-k*.45)/.7)
            if k<3:
                line_progress(d,[(x+390,548),(x+438,548)],ease((t-1-k*.45)/.5),color=colors[k])
            if p:
                y=360+50*(1-p)
                d.rounded_rectangle((x,y,x+396,y+340),radius=28,fill='white',outline='#E7DFD6',width=2)
                txt(im,f'0{k+1}',x+34,y+38,size=27,color=colors[k],reveal=p)
                txt(im,names[k],x+34,y+125,size=35,weight='semibold',reveal=p)
                txt(im,subs[k],x+34,y+205,size=22,color=MUTED,reveal=p)
        appear(im,'One conversation. A visible, connected workflow.',100,818,t,2,size=30,color=MUTED)
    elif kind == 'parallel':
        appear(im,scene['title'],96,160,t,size=63,color=PAPER,weight='semibold')
        # Two simultaneous routes describe architecture, not fabricated app status.
        nodes=[(96,425,490,690,'CALLER','One conversation',CORAL),
               (700,300,1170,530,'LISTENER','Stay with the caller',SAGE),
               (700,645,1170,875,'DISPATCHER','Coordinate next steps',BLUE)]
        for k,(x,y,x2,y2,title,sub,c) in enumerate(nodes):
            p=ease((t-.4-k*.5)/.6)
            if p:
                d.rounded_rectangle((x,y+20*(1-p),x2,y2+20*(1-p)),radius=28,fill='#302820',outline='#574637',width=2)
                txt(im,title,x+38,y+37,size=26,color=c,reveal=p)
                txt(im,sub,x+38,y+102,size=26,color=PAPER,reveal=p)
        for y in [415,760]:
            path=[(490,557),(592,557),(592,y),(700,y)]
            line_progress(d,path,ease((t-1)/1),color=CORAL,width=4)
        for k,(label,c) in enumerate([('Demo ambulance',CORAL),('Family',SAGE),('Location link',BLUE)]):
            yy=605+k*103
            p=ease((t-2.0-k*.3)/.6)
            line_progress(d,[(1170,760),(1230,760),(1230,yy+38),(1320,yy+38)],p,color=c,width=3)
            if p:
                d.rounded_rectangle((1320,yy,1824,yy+76),radius=20,fill='#302820')
                txt(im,label,1354,yy+20,size=24,color=PAPER,reveal=p)
        wave(d,1510,408,t,width=320,height=90,color=SAGE)
        appear(im,'WORKFLOW EXPLAINER • SIMULATED OUTREACH IN THIS DEMO',100,923,t,2.5,size=21,color='#C6BDB4')
    elif kind == 'close':
        appear(im,'One voice.',96,300,t,.1,size=112,color=PAPER,weight='semibold')
        appear(im,'Many calls.',96,445,t,.65,size=112,color=CORAL,weight='semibold')
        appear(im,'Built with Bolna · Symphony Buildathon',103,684,t,1.3,size=29,color='#C6BDB4')
        wave(d,1500,506,t,width=320,height=210,color=CORAL)
        appear(im,'EK AWAAZ',103,851,t,1.8,size=25,color=PAPER)
    footer(im,scene,t)
    return im


@lru_cache(maxsize=24)
def mask_for(w,h):
    mask=Image.new('L',(w,h))
    ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=22,fill=255)
    return mask


def ui_frame(scene,source,t,background):
    im=background.copy()
    d=ImageDraw.Draw(im)
    x,y,w,h=scene['box']
    # Subtle 1.5% push; the source remains a real screen recording.
    zoom=1+.015*ease(t/scene['duration'])
    sw,sh=source.size
    cutw,cuth=int(sw/zoom),int(sh/zoom)
    source=source.crop(((sw-cutw)//2,(sh-cuth)//2,(sw+cutw)//2,(sh+cuth)//2)).resize((w,h),Image.Resampling.BILINEAR)
    d.rounded_rectangle((x-5,y-5,x+w+5,y+h+5),radius=26,fill='#E9E0D5')
    im.paste(source,(x,y),mask_for(w,h))
    if scene['kind']=='home':
        footer(im,scene,t)
        return im
    sx=1430 if scene['kind']=='live' else 796 if scene['kind']=='detail' else 1264
    width=W-sx-100
    appear(im,'WHAT TO NOTICE',sx,258,t,.4,size=20,color=CORAL)
    for k,label in enumerate(scene['side']):
        p=ease((t-1.0-k*2.2)/.8)
        yy=340+k*144+22*(1-p)
        if p:
            c=[CORAL,BLUE,SAGE][k]
            d.ellipse((sx,yy+13,sx+33,yy+46),fill=c)
            txt(im,f'{k+1}',sx+10,yy+14,size=17,color='white',reveal=p)
            txt(im,label,sx+54,yy,size=30 if width<500 else 35,width=width-54,weight='medium',reveal=p)
            line_progress(d,[(sx+54,yy+103),(sx+width,yy+103)],p,color='#E2D8CD',width=2)
    note=scene['note'].split('\n')
    appear(im,note[0],sx,825,t,2,size=18,color=CORAL,width=width)
    appear(im,note[1],sx,866,t,2.3,size=23,color=MUTED,width=width)
    footer(im,scene,t)
    return im


def source_pipe(scene,duration):
    x,y,w,h=scene['crop']
    _,_,dw,dh=scene['box']
    # Fill the matte viewport with a centred crop, never stretching app typography.
    vf=f'crop={w}:{h}:{x}:{y},setpts={duration/scene["span"]}*(PTS-STARTPTS),fps={FPS},scale={dw}:{dh}:force_original_aspect_ratio=increase,crop={dw}:{dh},setsar=1,tpad=stop_mode=clone:stop_duration=1'
    args=['ffmpeg','-hide_banner','-loglevel','error','-threads','2','-ss',str(scene['seek']),'-t',str(scene['span']),'-i',str(ROOT/'raw'/scene['source']),'-vf',vf,'-t',str(duration),'-an','-pix_fmt','rgb24','-f','rawvideo','-']
    return subprocess.Popen(args,stdout=subprocess.PIPE)


def render_scene(index):
    scene=SCENES[index]
    duration=scene['duration']+(.5 if index<len(SCENES)-1 else 0)
    target=OUT/f'scene-{index:02d}.mp4'
    if target.exists() and target.stat().st_mtime >= Path(__file__).stat().st_mtime:
        print(f'Cached scene {index:02d}',flush=True)
        return
    encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],stdin=subprocess.PIPE)
    decoder=source_pipe(scene,duration) if 'source' in scene else None
    background=base(scene)
    last=None
    try:
        for frame in range(round(duration*FPS)):
            t=frame/FPS
            if decoder:
                dw,dh=scene['box'][2:]
                data=decoder.stdout.read(dw*dh*3)
                if len(data)==dw*dh*3:
                    last=Image.frombytes('RGB',(dw,dh),data)
                if last is None:
                    raise RuntimeError('Could not decode source')
                im=ui_frame(scene,last,t,background)
            else:
                im=graphic(scene,t)
            encoder.stdin.write(im.tobytes())
            if frame==round(min(4,duration/2)*FPS):
                im.save(OUT/f'preview-{index:02d}.jpg',quality=88)
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError('Video encoding failed')
    finally:
        if decoder:
            decoder.stdout.close()
            decoder.terminate()
            decoder.wait()
    print(f'Rendered {index:02d}: {scene["kind"]}',flush=True)


def transition_join():
    # Pairwise joins keep memory bounded: xfade does not hold twelve HD decoders.
    current=OUT/'scene-00.mp4'
    styles=['smoothleft','fade','smoothup','fade','smoothleft','fade','smoothup','fade','smoothleft','fade','fade']
    for i in range(1,len(SCENES)):
        target=OUT/f'joined-{i:02d}.mp4'
        newest_source=max(current.stat().st_mtime,(OUT/f'scene-{i:02d}.mp4').stat().st_mtime)
        if not target.exists() or target.stat().st_mtime < newest_source:
            run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',current,'-i',OUT/f'scene-{i:02d}.mp4',
                 '-filter_complex',f'[0:v]settb=AVTB,setpts=PTS-STARTPTS[a];[1:v]settb=AVTB,setpts=PTS-STARTPTS[b];[a][b]xfade=transition={styles[i-1]}:duration=0.5:offset={SCENES[i]["start"]}[v]',
                 '-map','[v]','-an','-c:v','libx264','-preset','veryfast','-threads','4','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',target])
        current=target
        print(f'Transition {i:02d} joined',flush=True)
    return current


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenes',action='store_true')
    parser.add_argument('--join',action='store_true')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.scenes:
        with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
            list(pool.map(render_scene,range(len(SCENES))))
    if args.join:
        transition_join()


if __name__=='__main__':
    main()
