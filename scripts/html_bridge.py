"""Notebook-local HTML callbacks. No HTTP server, tunnel or public endpoint."""
import base64
import json
import math
import subprocess
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from scripts.pipeline import analyze_audio
from scripts.render_clip import render_clip
from scripts.edit_input import parse_edit


class HtmlBridge:
    def __init__(self,audio,bgm=None,analyze=analyze_audio,render=render_clip):
        self.audio=Path(audio);self.bgm=bgm;self.analyze=analyze;self.render=render
        self.pool=ThreadPoolExecutor(max_workers=1)
        self.lock=threading.Lock();self.job=None;self.project=None

    def call(self,action,data=None):
        data=data or {}
        try:
            with self.lock:
                return dict(ok=True,**self._call(action,data))
        except Exception as error:
            return dict(ok=False,error=str(error))

    def _call(self,action,data):
        if action=='hello':return dict(audio_name=self.audio.name,bgm=bool(self.bgm))
        if action in ('analyze','render','preview'):
            if self.job and not self.job['future'].done():raise ValueError('前の処理が実行中です。完了までお待ちください')
            if action=='analyze':
                seconds=data.get('seconds',0);speakers=data.get('speakers',2);count=data.get('count',10)
                if seconds not in (0,180) or type(speakers)!=int or not 1<=speakers<=10 or type(count)!=int or not 5<=count<=10:raise ValueError('解析設定が不正です')
                def task():
                    project=self.analyze(self.audio,test_seconds=seconds,speakers=speakers,count=count,use_speakers=bool(data.get('diarize',True)),use_topics=bool(data.get('topics',True)),report=report)
                    self.project=project
                    return dict(project=project)
            elif action=='render':
                edit=parse_edit(json.dumps(data.get('edit')),self.audio.name)
                def task():
                    duration=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(self.audio)],capture_output=True,text=True,check=True).stdout)
                    if edit['end']>duration+.1:raise ValueError('編集範囲が元音声の長さを超えています')
                    report('動画を生成しています。')
                    return self.artifact(self.render(self.audio,edit,self.bgm if data.get('bgm',True) else None),'video/mp4')
            else:
                a,b=data.get('start'),data.get('end')
                if any(type(v) not in (int,float) or not math.isfinite(v) for v in (a,b)) or not 0<=a<b or b-a>620:raise ValueError('試聴範囲が不正です')
                def task():
                    report('試聴音声を準備しています。')
                    path=Path(tempfile.mkdtemp(prefix='campus-listen-'))/'preview.wav'
                    subprocess.run(['ffmpeg','-y','-v','error','-ss',str(a),'-i',str(self.audio),'-t',str(b-a),'-ar','16000','-ac','1',str(path)],check=True,capture_output=True)
                    return self.artifact(path,'audio/wav')
            messages=[]
            def report(message):
                messages.append(str(message));del messages[:-20]
            job_id=uuid.uuid4().hex
            self.job=dict(id=job_id,messages=messages,future=self.pool.submit(task))
            return dict(job=job_id)
        if action in ('status','chunk'):
            job=self.job
            if not job or data.get('job')!=job['id']:raise ValueError('処理が見つかりません。再接続・再実行してください')
            future=job['future']
            if action=='status':
                return dict(done=future.done(),messages=list(job['messages']),result=future.result() if future.done() else None)
            if not future.done():raise ValueError('まだ生成中です')
            result=future.result()
            if 'path' not in result:raise ValueError('ダウンロード対象がありません')
            offset=data.get('offset',0)
            if type(offset)!=int or offset<0 or offset>result['size']:raise ValueError('読み込み位置が不正です')
            with Path(result['path']).open('rb') as handle:
                handle.seek(offset);chunk=handle.read(512*1024)
            return dict(data=base64.b64encode(chunk).decode(),next=offset+len(chunk),done=offset+len(chunk)>=result['size'])
        raise ValueError('未知の操作です')

    @staticmethod
    def artifact(path,mime):
        path=Path(path)
        return dict(path=str(path),name=path.name,size=path.stat().st_size,mime=mime)


def launch_html_editor(page):
    from google.colab import files,output
    from IPython.display import display,HTML,JSON
    print('元音声1本と任意のBGM1本を選択してください。選択後、HTML画面が表示されます。',flush=True)
    uploaded=files.upload()
    names=[name for name in uploaded if Path(name).suffix.lower() in {'.mp3','.wav','.m4a','.ogg','.flac'}]
    if not 1<=len(names)<=2:raise ValueError('元音声1本と、必要ならBGM1本を選択してください')
    source_name=names[0];bgm_name=None
    if len(names)==2:
        for index,name in enumerate(names,1):print(f'{index}: {name}')
        choice=input('元のラジオ音声の番号（1か2）: ').strip()
        if choice not in ('1','2'):raise ValueError('1か2を入力してください')
        source_name=names[int(choice)-1];bgm_name=names[2-int(choice)]
    directory=Path(tempfile.mkdtemp(prefix='campus-source-'));audio=directory/Path(source_name).name
    audio.write_bytes(uploaded[source_name])
    bgm=None
    if bgm_name:
        bgm=directory/Path(bgm_name).name;bgm.write_bytes(uploaded[bgm_name])
    del uploaded
    bridge=HtmlBridge(audio,bgm)
    callback='campus_'+uuid.uuid4().hex
    output.register_callback(callback,lambda action,data:JSON(bridge.call(action,data)))
    display(HTML(page.replace('__CAMPUS_CALLBACK__',callback)))
    print('この下のHTML画面で操作してください。切断後は起動し直しと元音声の選択が必要です。',flush=True)
    return bridge
