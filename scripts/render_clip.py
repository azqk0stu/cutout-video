"""Shared FFmpeg renderer for the button-based Colab interface."""
import math
import subprocess
import tempfile
from pathlib import Path


def render_clip(audio_path, edit, bgm=None):
    audio_path = Path(audio_path).resolve()
    bgm = str(Path(bgm).resolve()) if bgm else None
    work = Path(tempfile.mkdtemp(prefix='campus-clip-'))
    start,end=float(edit['start']),float(edit['end']); duration=end-start
    assert math.isfinite(duration) and 0<duration<=600
    size={'vertical':(1080,1920),'square':(1080,1080),'landscape':(1920,1080)}[edit['format']]
    def stamp(t):
        cs=max(0,round(t*100)); h,cs=divmod(cs,360000); m,cs=divmod(cs,6000); s,cs=divmod(cs,100)
        return f'{h}:{m:02}:{s:02}.{cs:02}'
    def safe_text(t):
        return str(t).replace('\\','').replace('{','').replace('}','').replace('\n',r'\N').replace('\r','')
    w,h=size
    header=f"""[Script Info]
    ScriptType: v4.00+
    PlayResX: {w}
    PlayResY: {h}
    WrapStyle: 0
    [V4+ Styles]
    Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    Style: Default,Noto Sans CJK JP,56,&H00FFFFFF,&H00FFFFFF,&H00203930,&H00203930,0,0,0,0,100,100,0,0,1,3,0,5,80,80,60,1
    [Events]
    Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    """
    lines=[]
    for s in edit['segments']:
        a=max(start,float(s['start'])); b=min(end,float(s['end']))
        if b<=a: continue
        text=(str(s.get('speaker',''))+'：' if s.get('speaker') else '')+str(s['text'])
        lines.append(f'Dialogue: 0,{stamp(a-start)},{stamp(b-start)},Default,,0,0,0,,{safe_text(text)}')
    (work / 'captions.ass').write_text(header+'\n'.join(lines),encoding='utf-8')
    cmd=['ffmpeg','-y','-f','lavfi','-i',f'color=c=0x173e35:s={w}x{h}:r=30:d={duration}', '-ss',str(start),'-t',str(duration),'-i',str(audio_path)]
    if bgm:
        volume=float(edit.get('bgm_volume',0.12)); assert 0<=volume<=1
        cmd+=['-stream_loop','-1','-i',bgm,'-filter_complex',f'[2:a]volume={volume},afade=t=in:d=1,afade=t=out:st={max(0,duration-1)}:d=1[bg];[1:a][bg]amix=inputs=2:duration=first:normalize=0[a]','-map','0:v','-map','[a]']
    else: cmd+=['-map','0:v','-map','1:a']
    cmd+=['-vf','ass=captions.ass','-t',str(duration),'-c:v','libx264','-preset','fast','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart','clip.mp4']
    subprocess.run(cmd,check=True,cwd=work,capture_output=True)
    return work / 'clip.mp4'
