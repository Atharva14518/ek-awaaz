"""Native portrait re-edit, not an unreadable crop of the widescreen video."""
from pathlib import Path
import argparse
import json
import subprocess

from PIL import Image, ImageDraw

from render_v2 import ROOT, OUT, FINAL, PAPER, INK, CORAL, MUTED, txt, wave, ease, mask_for, font
from finish_v2 import timestamp

SIZE=(1080,1920)


def run(args):
    subprocess.run([str(a) for a in args],check=True)


def frame(index,t,source=None):
    dark=index in (0,3)
    im=Image.new('RGB',SIZE,INK if dark else PAPER)
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((72,94,116,138),radius=14,fill=CORAL)
    d.arc((81,102,107,128),180,360,fill=PAPER,width=3)
    d.rounded_rectangle((79,116,85,130),radius=2,fill=PAPER)
    d.rounded_rectangle((104,116,110,130),radius=2,fill=PAPER)
    txt(im,'EK AWAAZ',140,98,size=30,color=PAPER if dark else INK,weight='semibold')
    if dark:
        p=ease(t/.65)
        txt(im,'One voice.',72,470+40*(1-p),size=105,color=PAPER,weight='semibold',reveal=p)
        txt(im,'Many calls.' if index==3 else 'Every next\nstep.',72,620+40*(1-p),size=98,color=CORAL,weight='semibold',reveal=p)
        txt(im,'Built with Bolna' if index==3 else 'One calm conversation.',77,1030,size=35,color='#C6BDB4')
        txt(im,'Symphony Buildathon' if index==3 else 'A clearer path to action.',77,1090,size=30,color='#C6BDB4')
        wave(d,540,1430,t,width=770,height=210,color=CORAL)
        txt(im,'VOICE-FIRST EMERGENCY ASSISTANT',77,1615,size=23,color='#C6BDB4')
    else:
        txt(im,'The conversation.' if index==1 else 'The understanding.',72,240,size=56,weight='semibold')
        txt(im,'ACTUAL APP · SIMULATED SCENARIO',76,340,size=22,color=CORAL)
        w,h=source.size
        x=(1080-w)//2
        d.rounded_rectangle((x-5,430-5,x+w+5,430+h+5),radius=28,fill='#E4DACF')
        im.paste(source,(x,430),mask_for(w,h))
        txt(im,'Listen / Understand' if index==1 else 'Confirm / Coordinate',76,1580,size=37,color=CORAL)
        txt(im,'One conversation. Every next step visible.',76,1660,size=25,color=MUTED)
    d.line((72,1854,1008,1854),fill='#443B33' if dark else '#E7DFD6',width=2)
    d.line((72,1854,72+936*([0,4,9,14][index]+t)/20,1854),fill=CORAL,width=3)
    return im


def render(index):
    duration=[4.4,5.4,5.4,6][index]
    target=OUT/f'portrait-{index}.mp4'
    encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r','30','-i','-','-an','-c:v','libx264','-preset','veryfast','-threads','2','-crf','18','-pix_fmt','yuv420p',str(target)],stdin=subprocess.PIPE)
    decoder=None
    if index in (1,2):
        w,h=(936,1072) if index==1 else (774,1072)
        crop='1100:1260:225:640' if index==1 else '945:1310:1335:640'
        decoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-ss',str(8 if index==1 else 14),'-i',str(ROOT/'raw'/'accident-live.mov'),'-vf',f'crop={crop},scale={w}:{h},fps=30','-t',str(duration),'-an','-pix_fmt','rgb24','-f','rawvideo','-'],stdout=subprocess.PIPE)
    for n in range(round(duration*30)):
        source=None
        if decoder:
            data=decoder.stdout.read(w*h*3)
            source=Image.frombytes('RGB',(w,h),data)
        im=frame(index,n/30,source)
        encoder.stdin.write(im.tobytes())
        if n==90:
            im.save(OUT/f'portrait-preview-{index}.jpg',quality=90)
    encoder.stdin.close()
    assert encoder.wait()==0
    if decoder:
        decoder.stdout.close(); decoder.terminate(); decoder.wait()
    print('Portrait scene',index,'rendered',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--finish-only',action='store_true')
    args=parser.parse_args()
    if not args.finish_only:
        for i in range(4):
            render(i)
    current=OUT/'portrait-0.mp4'
    for i in range(1,4):
        target=OUT/f'portrait-joined-{i}.mp4'
        if not args.finish_only:
            run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',current,'-i',OUT/f'portrait-{i}.mp4','-filter_complex',f'[0:v]settb=AVTB[a];[1:v]settb=AVTB[b];[a][b]xfade=transition={"smoothleft" if i<3 else "fade"}:duration=0.4:offset={[0,4,9,14][i]}[v]','-map','[v]','-an','-c:v','libx264','-preset','veryfast','-threads','3','-crf','18','-pix_fmt','yuv420p',target])
        current=target
    manifest=json.loads((OUT/'mix-manifest.json').read_text())
    selected=[(manifest[0],.6,1.),(manifest[3],8.7,1.08),(manifest[11],14.1,1.02)]
    args=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',current]
    for p,_,_ in selected:
        args+=['-i',p['audio']]
    args+=['-i',ROOT/'audio'/'original-ambient-bed.wav']
    filters=[]
    cues=[]
    fullcues=json.loads((OUT/'caption-cues.json').read_text())
    for i,(p,start,speed) in enumerate(selected):
        filters.append(f'[{i+1}:a]atrim=0:{p["trim"]},asetpts=PTS-STARTPTS,atempo={speed},loudnorm=I=-17:TP=-2:LRA=8,adelay={round(start*1000)}:all=1[a{i}]')
        for c in fullcues:
            if c['start']>=p['start'] and c['end']<=p['end']:
                cues.append(dict(start=start+(c['start']-p['start'])*p['speed']/speed,end=min(19.97,start+(c['end']-p['start'])*p['speed']/speed),text=c['text']))
    filters.append('[4:a]atrim=0:20,loudnorm=I=-33:TP=-8:LRA=6,afade=t=in:d=0.5,afade=t=out:st=19:d=1[bed]')
    filters.append('[a0][a1][a2][bed]amix=inputs=4:duration=longest:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9,afade=t=out:st=19.8:d=0.2[a]')
    args+=['-filter_complex',';'.join(filters),'-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-t','20','-movflags','+faststart',OUT/'portrait-clean.mp4']
    run(args)
    srt='\n\n'.join(f'{i+1}\n{timestamp(c["start"])} --> {timestamp(c["end"])}\n{c["text"]}' for i,c in enumerate(cues))+'\n'
    (FINAL/'ek-awaaz-social-v2.srt').write_text(srt)
    header=(OUT/'captions.ass').read_text().split('[Events]')[0]
    header=header.replace('PlayResX: 1920','PlayResX: 1080').replace('PlayResY: 1080','PlayResY: 1920').replace('Caption,Poppins Medium,40,','Caption,Poppins Medium,48,')
    events=[]
    for c in cues:
        start,end=timestamp(c['start'],True),timestamp(c['end'],True)
        w=int(font(34).getlength(c['text']))+50
        assert w<1000, 'Portrait caption needs wrapping'
        x=(1080-w)//2
        shape=f'm 15 0 l {w-15} 0 b {w} 0 {w} 0 {w} 15 l {w} 50 b {w} 65 {w} 65 {w-15} 65 l 15 65 b 0 65 0 65 0 50 l 0 15 b 0 0 0 0 15 0'
        events.append(f'Dialogue: 0,{start},{end},Pill,,0,0,0,,{{\\an7\\pos({x},1775)\\p1\\fad(70,70)}}{shape}')
        events.append(f'Dialogue: 1,{start},{end},Caption,,0,0,0,,{{\\an5\\pos(540,1807)\\fad(70,70)}}{c["text"]}')
    (OUT/'portrait-captions.ass').write_text(header+'[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'+'\n'.join(events)+'\n')
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',OUT/'portrait-clean.mp4','-vf',f"ass='{OUT/'portrait-captions.ass'}':fontsdir='{ROOT/'fonts'}'",'-c:v','libx264','-preset','medium','-threads','4','-crf','18','-c:a','copy','-movflags','+faststart',FINAL/'ek-awaaz-social-v2.mp4'])
    # A matching thumbnail from the real incident view and the new title treatment.
    cover=Image.new('RGB',(1920,1080),INK)
    live=Image.open(OUT/'preview-06.jpg').crop((96,226,1172,978)).resize((1076,752))
    cover.paste(live,(800,200),mask_for(1076,752))
    d=ImageDraw.Draw(cover)
    d.rounded_rectangle((48,80,980,1000),radius=34,fill=PAPER)
    txt(cover,'EK AWAAZ',104,140,size=35,color=CORAL,weight='semibold')
    txt(cover,'One voice.',100,320,size=100,weight='semibold')
    txt(cover,'Many calls.',100,455,size=100,color=CORAL,weight='semibold')
    txt(cover,'Voice-first emergency\ncoordination.',105,650,size=38,color=MUTED)
    txt(cover,'ACTUAL APP · DEMO WALKTHROUGH',105,872,size=25,color=CORAL)
    cover.resize((1280,720),Image.Resampling.LANCZOS).save(FINAL/'ek-awaaz-thumbnail-v2.png')
    print('Portrait video and revised thumbnail complete',flush=True)


if __name__=='__main__':
    main()
