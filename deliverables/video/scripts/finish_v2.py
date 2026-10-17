"""Align neural narration, captions and subtle original transition sound design."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import subprocess
import wave

import numpy as np

from render_v2 import OUT, ROOT, FINAL, SCENES, font


def run(args):
    subprocess.run([str(a) for a in args],check=True)


def timestamp(seconds,ass=False):
    units=100 if ass else 1000
    n=round(seconds*units)
    h,n=divmod(n,3600*units)
    m,n=divmod(n,60*units)
    s,n=divmod(n,units)
    return f'{h}:{m:02}:{s:02}.{n:02}' if ass else f'{h:02}:{m:02}:{s:02},{n:03}'


def captions(manifest):
    cues=[]
    for part in manifest:
        words=[]
        cursor=0
        for word in part['words']:
            token=word['text']
            match=re.search(re.escape(token),part['text'][cursor:],flags=re.I)
            if match:
                a=cursor+match.start(); b=cursor+match.end()
                while b<len(part['text']) and part['text'][b] in ',.!?:;':
                    b+=1
                token=part['text'][a:b]
                cursor=b
            words.append(dict(text=token,start=part['start']+word['offset']/1e7/part['speed'],end=part['start']+(word['offset']+word['duration'])/1e7/part['speed']))
        group=[]
        for i,w in enumerate(words):
            group.append(w)
            text=' '.join(x['text'] for x in group)
            pause=(words[i+1]['start']-w['end']) if i+1<len(words) else 0
            if len(group)>=7 or len(text)>=58 or (len(group)>=2 and (text[-1] in '.?!' or pause>.32)) or i==len(words)-1:
                cues.append(dict(start=group[0]['start'],end=min(part['end'],group[-1]['end']+.16),text=text))
                group=[]
    for a,b in zip(cues,cues[1:]):
        a['end']=min(a['end'],b['start']-.025)
    srt='\n\n'.join(f'{i+1}\n{timestamp(c["start"])} --> {timestamp(c["end"])}\n{c["text"]}' for i,c in enumerate(cues))+'\n'
    (FINAL/'ek-awaaz-demo-v2.srt').write_text(srt)
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Poppins Medium,40,&H00FFFFFF,&H00FFFFFF,&H00161B1F,&H00161B1F,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Pill,Poppins Medium,28,&H10161B1F,&H10161B1F,&H10161B1F,&H10161B1F,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events=[]
    for c in cues:
        start,end=timestamp(c['start'],True),timestamp(c['end'],True)
        width=math.ceil(font(28).getlength(c['text']))+48
        x=(1920-width)//2
        r=13; h=49; w=width
        shape=f'm {r} 0 l {w-r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h-r} b {w} {h} {w} {h} {w-r} {h} l {r} {h} b 0 {h} 0 {h} 0 {h-r} l 0 {r} b 0 0 0 0 {r} 0'
        events.append(f'Dialogue: 0,{start},{end},Pill,,0,0,0,,{{\\an7\\pos({x},983)\\p1\\fad(70,70)}}{shape}')
        events.append(f'Dialogue: 1,{start},{end},Caption,,0,0,0,,{{\\an5\\pos(960,1007)\\fad(70,70)}}{c["text"]}')
    (OUT/'captions.ass').write_text(header+'\n'.join(events)+'\n')
    (OUT/'caption-cues.json').write_text(json.dumps(cues,indent=2))
    return cues


def transition_audio():
    rate=48000
    track=np.zeros((rate*150,2),dtype=np.float32)
    rng=np.random.default_rng(27)
    for i,scene in enumerate(SCENES[1:]):
        duration=.55
        t=np.arange(int(duration*rate))/rate
        noise=rng.normal(0,1,len(t))
        noise=np.convolve(noise,np.ones(18)/18,mode='same')
        envelope=np.sin(np.pi*t/duration)**2
        airy=noise*envelope*.065
        tone=np.sin(2*np.pi*(392 if i%2 else 523.25)*t)*np.exp(-t*15)*.022
        sound=airy+tone
        start=int((scene['start']-.12)*rate)
        track[start:start+len(t),0]+=sound*.8
        track[start:start+len(t),1]+=sound
    with wave.open(str(OUT/'transitions.wav'),'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(rate)
        f.writeframes((np.clip(track,-1,1)*32767).astype('<i2').tobytes())


def main():
    manifest=json.loads((OUT/'voice'/'manifest.json').read_text())
    for p in manifest:
        # Ignore the service's long trailing silence; preserve natural prosody.
        last=p['words'][-1]
        p['trim']=(last['offset']+last['duration'])/1e7+.18
        p['speed']=max(1,p['trim']/(p['end']-p['start']-.04))
        assert p['speed']<=1.12, f'Rewrite rather than rush segment {p["index"]}'
    cues=captions(manifest)
    transition_audio()
    args=['ffmpeg','-hide_banner','-loglevel','error','-y']
    for p in manifest:
        args+=['-i',p['audio']]
    args+=['-i',ROOT/'audio'/'original-ambient-bed.wav','-i',OUT/'transitions.wav']
    filters=[]
    for i,p in enumerate(manifest):
        filters.append(f'[{i}:a]atrim=0:{p["trim"]},asetpts=PTS-STARTPTS,atempo={p["speed"]},highpass=f=80,loudnorm=I=-17:TP=-2:LRA=8,afade=t=in:d=0.015,adelay={round(p["start"]*1000)}:all=1[n{i}]')
    filters.append(''.join(f'[n{i}]' for i in range(12))+'amix=inputs=12:duration=longest:normalize=0,apad=whole_dur=150,asplit=2[voice][side]')
    filters.append('[12:a]loudnorm=I=-30:TP=-8:LRA=6[bed]')
    filters.append('[bed][side]sidechaincompress=threshold=.035:ratio=4:attack=30:release=450[duck]')
    filters.append('[voice][duck][13:a]amix=inputs=3:duration=longest:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9,afade=t=out:st=149.5:d=0.5[a]')
    args+=['-filter_complex',';'.join(filters),'-map','[a]','-t','150','-ar','48000','-ac','2','-c:a','pcm_s16le',OUT/'mix.wav']
    run(args)
    (OUT/'mix-manifest.json').write_text(json.dumps(manifest,indent=2))
    print(f'Audio mixed; {len(cues)} speech-aligned captions',flush=True)
    video=OUT/'joined-11.mp4'
    if not video.exists():
        print('Visual assembly pending; run again after render_v2 --join',flush=True)
        return
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',video,'-i',OUT/'mix.wav','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','256k','-t','150','-movflags','+faststart',FINAL/'ek-awaaz-demo-v2-clean.mp4'])
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',FINAL/'ek-awaaz-demo-v2-clean.mp4','-vf',f"ass='{OUT/'captions.ass'}':fontsdir='{ROOT/'fonts'}'",'-c:v','libx264','-preset','medium','-threads','4','-crf','18','-c:a','copy','-movflags','+faststart',FINAL/'ek-awaaz-demo-v2.mp4'])
    print('Finished narrated, captioned 2:30 video',flush=True)


if __name__=='__main__':
    main()
