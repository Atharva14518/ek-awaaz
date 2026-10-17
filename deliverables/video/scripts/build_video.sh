#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"
RAW="$ROOT/raw"
FRAMES="$ROOT/frames"
FONTS="$ROOT/fonts"
SCENES="$ROOT/scenes"
FINAL="$ROOT/final"
AUDIO="$ROOT/audio"

mkdir -p "$SCENES" "$FINAL"

encode=( -an -r 30 -c:v libx264 -preset veryfast -crf 17 -pix_fmt yuv420p -movflags +faststart )
label_font="$FONTS/Poppins-SemiBold.ttf"

ffmpeg -hide_banner -loglevel error \
  -loop 1 -t 3 -i "$FRAMES/hook-card.png" \
  -ss 1 -t 12 -i "$RAW/accident-live.mov" \
  -filter_complex "[0:v]fps=30,format=yuv420p,fade=t=out:st=2.7:d=0.3:color=black[h];[1:v]crop=2600:1462:0:420,scale=1920:1080,fps=30,setsar=1,fade=t=in:st=0:d=0.3,drawbox=x=64:y=64:w=342:h=60:color=0x1F1B16@0.92:t=fill,drawtext=fontfile='$label_font':text='LIVE  •  HINGLISH':fontcolor=white:fontsize=25:x=94:y=80[l];[h][l]concat=n=2:v=1:a=0[v]" \
  -map "[v]" -t 15 "${encode[@]}" -y "$SCENES/00-hook.mp4"

ffmpeg -hide_banner -loglevel error \
  -loop 1 -i "$FRAMES/problem-card.png" \
  -vf "zoompan=z='min(zoom+0.00005,1.03)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=600:s=1920x1080:fps=30,fade=t=in:st=0:d=0.25:color=0xFBF7F2,fade=t=out:st=19.75:d=0.25:color=0xFBF7F2" \
  -t 20 "${encode[@]}" -y "$SCENES/01-problem.mp4"

ffmpeg -hide_banner -loglevel error \
  -i "$RAW/home.mov" \
  -vf "crop=3420:1924:0:80,scale=1920:1080,setpts=1.5*PTS,fps=30,tpad=stop_mode=clone:stop_duration=1,drawbox=x=655:y=920:w=610:h=70:color=0x352B22@0.94:t=fill,drawtext=fontfile='$label_font':text='CALL   •   LISTEN   •   COORDINATE':fontcolor=white:fontsize=27:x=714:y=940,fade=t=in:st=0:d=0.25:color=0xFBF7F2,fade=t=out:st=14.75:d=0.25:color=0xFBF7F2" \
  -t 15 "${encode[@]}" -y "$SCENES/02-solution.mp4"

ffmpeg -hide_banner -loglevel error \
  -ss 0 -t 15 -i "$RAW/accident-live.mov" \
  -ss 8 -t 15 -i "$RAW/accident-live.mov" \
  -ss 18 -t 15 -i "$RAW/accident-live.mov" \
  -filter_complex "[0:v]crop=2600:1462:0:420,scale=1920:1080,fps=30,setsar=1,drawbox=x=64:y=64:w=374:h=60:color=0x1F1B16@0.92:t=fill,drawtext=fontfile='$label_font':text='01  LIVE TRANSCRIPT':fontcolor=white:fontsize=25:x=92:y=80,fade=t=in:st=0:d=0.25:color=0xFBF7F2,fade=t=out:st=14.75:d=0.25:color=0xFBF7F2[a];[1:v]crop=2600:1462:410:420,scale=1920:1080,fps=30,setsar=1,drawbox=x=64:y=64:w=392:h=60:color=0x3D6A8F@0.94:t=fill,drawtext=fontfile='$label_font':text='02  DETAILS EXTRACTED':fontcolor=white:fontsize=25:x=92:y=80,fade=t=in:st=0:d=0.25:color=0xFBF7F2,fade=t=out:st=14.75:d=0.25:color=0xFBF7F2[b];[2:v]crop=2600:1462:820:420,scale=1920:1080,fps=30,setsar=1,drawbox=x=64:y=64:w=438:h=60:color=0x5B8C6B@0.94:t=fill,drawtext=fontfile='$label_font':text='03  CONFIRMED FIRST':fontcolor=white:fontsize=25:x=92:y=80,fade=t=in:st=0:d=0.25:color=0xFBF7F2,fade=t=out:st=14.75:d=0.25:color=0xFBF7F2[c];[a][b][c]concat=n=3:v=1:a=0[v]" \
  -map "[v]" -t 45 "${encode[@]}" -y "$SCENES/03-live-demo.mp4"

ffmpeg -hide_banner -loglevel error \
  -ss 17 -t 16 -i "$RAW/accident-live.mov" \
  -vf "crop=2600:1462:820:420,scale=1920:1080,setpts=1.25*PTS,fps=30,setsar=1,drawbox=x=64:y=64:w=520:h=60:color=0xE4572E@0.94:t=fill,drawtext=fontfile='$label_font':text='SECOND AGENT  •  PARALLEL ACTION':fontcolor=white:fontsize=25:x=92:y=80,drawbox=x=82:y=895:w=315:h=58:color=white@0.94:t=fill,drawtext=fontfile='$label_font':text='DEMO AMBULANCE':fontcolor=0x1F1B16:fontsize=21:x=112:y=912,drawbox=x=419:y=895:w=220:h=58:color=white@0.94:t=fill,drawtext=fontfile='$label_font':text='FAMILY':fontcolor=0x1F1B16:fontsize=21:x=469:y=912,drawbox=x=661:y=895:w=315:h=58:color=white@0.94:t=fill,drawtext=fontfile='$label_font':text='LOCATION LINK':fontcolor=0x1F1B16:fontsize=21:x=704:y=912,fade=t=in:st=0:d=0.25:color=0xFBF7F2,fade=t=out:st=19.75:d=0.25:color=0xFBF7F2" \
  -t 20 "${encode[@]}" -y "$SCENES/04-dispatcher.mp4"

ffmpeg -hide_banner -loglevel error \
  -ss 4 -t 15 -i "$RAW/silent-live.mov" \
  -vf "crop=3000:1688:210:300,scale=1920:1080,fps=30,setsar=1,drawbox=x=64:y=64:w=520:h=60:color=0x352B22@0.94:t=fill,drawtext=fontfile='$label_font':text='SILENT MODE  •  1 YES  •  2 NO':fontcolor=white:fontsize=25:x=92:y=80,fade=t=in:st=0:d=0.25:color=0xFBF7F2,fade=t=out:st=14.75:d=0.25:color=0xFBF7F2" \
  -t 15 "${encode[@]}" -y "$SCENES/05-silent-mode.mp4"

ffmpeg -hide_banner -loglevel error \
  -i "$RAW/report.mov" \
  -vf "crop=2600:1462:410:260,scale=1920:1080,setpts=1.25*PTS,fps=30,tpad=stop_mode=clone:stop_duration=1,setsar=1,drawbox=x=64:y=64:w=450:h=60:color=0x5B8C6B@0.94:t=fill,drawtext=fontfile='$label_font':text='TIMESTAMPED INCIDENT REPORT':fontcolor=white:fontsize=25:x=92:y=80,drawbox=x=1330:y=900:w=500:h=64:color=0x352B22@0.95:t=fill,drawtext=fontfile='$label_font':text='DEMO MODE  •  TEST NUMBERS ONLY':fontcolor=white:fontsize=22:x=1370:y=919,fade=t=in:st=0:d=0.25:color=0xFBF7F2,fade=t=out:st=14.75:d=0.25:color=0xFBF7F2" \
  -t 15 "${encode[@]}" -y "$SCENES/06-report.mp4"

ffmpeg -hide_banner -loglevel error \
  -loop 1 -i "$FRAMES/close-card.png" \
  -vf "zoompan=z='min(zoom+0.00008,1.012)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=150:s=1920x1080:fps=30,fade=t=in:st=0:d=0.3:color=0xFBF7F2,fade=t=out:st=4.7:d=0.3:color=0xFBF7F2" \
  -t 5 "${encode[@]}" -y "$SCENES/07-close.mp4"

ffmpeg -hide_banner -loglevel error \
  -f concat -safe 0 -i "$ROOT/scripts/scenes.txt" \
  -c copy -movflags +faststart -y "$FINAL/ek-awaaz-visual.mp4"

ffmpeg -hide_banner -loglevel error \
  -i "$FINAL/ek-awaaz-visual.mp4" \
  -i "$AUDIO/original-ambient-bed.wav" \
  -i "$AUDIO/phone-ring.wav" \
  -i "$AUDIO/narration-01.aiff" \
  -i "$AUDIO/narration-02.aiff" \
  -i "$AUDIO/narration-03.aiff" \
  -i "$AUDIO/narration-04.aiff" \
  -i "$AUDIO/narration-05.aiff" \
  -i "$AUDIO/narration-06.aiff" \
  -i "$AUDIO/narration-07.aiff" \
  -i "$AUDIO/narration-08.aiff" \
  -i "$AUDIO/ui-chime.wav" \
  -filter_complex "[1:a]volume=.82[bed];[2:a]volume=.72[ring];[3:a]highpass=f=85,loudnorm=I=-18:TP=-2:LRA=7,adelay=2300:all=1[n1];[4:a]highpass=f=85,loudnorm=I=-18:TP=-2:LRA=7,adelay=16300:all=1[n2];[5:a]highpass=f=85,loudnorm=I=-18:TP=-2:LRA=7,adelay=35800:all=1[n3];[6:a]highpass=f=85,loudnorm=I=-18:TP=-2:LRA=7,adelay=51000:all=1[n4];[7:a]highpass=f=85,loudnorm=I=-18:TP=-2:LRA=7,adelay=96000:all=1[n5];[8:a]highpass=f=85,loudnorm=I=-18:TP=-2:LRA=7,adelay=116000:all=1[n6];[9:a]highpass=f=85,loudnorm=I=-18:TP=-2:LRA=7,adelay=131000:all=1[n7];[10:a]highpass=f=85,loudnorm=I=-18:TP=-2:LRA=7,adelay=144000:all=1[n8];[n1][n2][n3][n4][n5][n6][n7][n8]amix=inputs=8:duration=longest:normalize=0[voice];[voice]asplit=2[voiceout][side];[bed][side]sidechaincompress=threshold=.018:ratio=8:attack=20:release=650[ducked];[11:a]asplit=6[c1][c2][c3][c4][c5][c6];[c1]adelay=55500:all=1[c1d];[c2]adelay=61000:all=1[c2d];[c3]adelay=67000:all=1[c3d];[c4]adelay=101000:all=1[c4d];[c5]adelay=105000:all=1[c5d];[c6]adelay=120000:all=1[c6d];[ducked][voiceout][ring][c1d][c2d][c3d][c4d][c5d][c6d]amix=inputs=9:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=10[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 256k -t 150 -movflags +faststart -y "$FINAL/ek-awaaz-demo-clean.mp4"

ffmpeg -hide_banner -loglevel error \
  -i "$FINAL/ek-awaaz-demo-clean.mp4" \
  -vf "subtitles='$FINAL/ek-awaaz-demo.srt':fontsdir='$FONTS':force_style='FontName=Poppins Medium,FontSize=13,PrimaryColour=&H00FFFFFF,BackColour=&H801F1B16,OutlineColour=&H801F1B16,BorderStyle=3,Outline=4,Shadow=0,Alignment=2,MarginL=30,MarginR=30,MarginV=20'" \
  -c:v libx264 -preset medium -crf 18 -c:a copy -movflags +faststart -y "$FINAL/ek-awaaz-demo-2m30.mp4"

ffmpeg -hide_banner -loglevel error \
  -loop 1 -t 6 -i "$FRAMES/portrait-hook.png" \
  -ss 8 -t 8 -i "$RAW/accident-live.mov" \
  -loop 1 -t 6 -i "$FRAMES/portrait-close.png" \
  -i "$FINAL/ek-awaaz-demo-clean.mp4" \
  -filter_complex "[0:v]fps=30,format=yuv420p,fade=t=out:st=5.75:d=0.25:color=0xFBF7F2[v0];[1:v]split=2[topin][bottomin];[topin]crop=1520:1000:0:520,scale=960:632[top];[bottomin]crop=1520:1000:950:520,scale=960:632[bottom];color=c=0xFBF7F2:s=1080x1920:r=30:d=8[canvas];[canvas]drawtext=fontfile='$label_font':text='LIVE TRANSCRIPT':fontcolor=0xE4572E:fontsize=28:x=60:y=68,drawtext=fontfile='$label_font':text='INCIDENT CARD':fontcolor=0x3D6A8F:fontsize=28:x=60:y=900[labels];[labels][top]overlay=60:135[mid];[mid][bottom]overlay=60:970,drawbox=x=60:y=1690:w=960:h=92:color=0x352B22@0.96:t=fill,drawtext=fontfile='$label_font':text='CONFIRMED BEFORE ACTION':fontcolor=white:fontsize=30:x=285:y=1718,fade=t=in:st=0:d=0.25:color=0xFBF7F2,fade=t=out:st=7.75:d=0.25:color=0xFBF7F2[v1];[2:v]fps=30,format=yuv420p,fade=t=in:st=0:d=0.25:color=0xFBF7F2[v2];[v0][v1][v2]concat=n=3:v=1:a=0[v];[3:a]atrim=0:6,asetpts=PTS-STARTPTS[a0];[3:a]atrim=56:64,asetpts=PTS-STARTPTS[a1];[3:a]atrim=144:150,asetpts=PTS-STARTPTS[a2];[a0][a1][a2]concat=n=3:v=0:a=1[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 192k -movflags +faststart -y "$FINAL/ek-awaaz-social-vertical-20s.mp4"
