"""A notebook-local widget interface. No public share link or running API."""
import html
import json
import math
import subprocess
import tempfile
from pathlib import Path
from scripts.pipeline import analyze_audio
from scripts.render_clip import render_clip
from scripts.edit_input import parse_edit


def create_app(upload, download, analyze=analyze_audio, render=render_clip):
    import ipywidgets as w
    from IPython.display import display, Audio, Video, clear_output
    state=dict(audio=None,bgm=None,project=None,video=None,busy=False)
    buttons=[]
    def button(label,action,style=''):
        b=w.Button(description=label,button_style=style,layout=w.Layout(width='auto'))
        buttons.append(b)
        def invoke(_):
            if state['busy']:return
            state['busy']=True
            for item in buttons:item.disabled=True
            with log:
                clear_output(wait=True)
                try:action()
                except Exception as error:print(f'処理できませんでした: {error}\n設定や素材を確認して、同じボタンを押してください。')
                finally:
                    state['busy']=False
                    for item in buttons:item.disabled=False
        b.on_click(invoke)
        return b
    log=w.Output()
    preview=w.Output()
    movie=w.Output()
    info=w.HTML('元音声を選択してください。')
    overview=w.HTML()
    editor=w.VBox()
    speaker_names=w.VBox()
    start=w.FloatText(description='開始（秒）',value=0)
    end=w.FloatText(description='終了（秒）',value=30)
    duration=w.HTML()
    title=w.Text(description='タイトル',layout=w.Layout(width='95%'))
    audio_format=w.Dropdown(description='動画サイズ',options=[('縦 9:16','vertical'),('正方形 1:1','square'),('横 16:9','landscape')])
    volume=w.FloatSlider(description='BGM音量',min=0,max=1,step=.01,value=.12)
    use_bgm=w.Checkbox(description='選択したBGMを使う',value=True)
    candidate=w.Dropdown(description='候補',options=[],layout=w.Layout(width='95%'))
    sort=w.Dropdown(description='並び順',options=[('おすすめ順','score'),('時刻順','time')])
    query=w.Text(description='候補を検索',placeholder='要約・字幕の言葉',layout=w.Layout(width='95%'))
    sample=w.Dropdown(description='解析範囲',options=[('全編（おすすめ）',0),('冒頭3分だけ試す',180)])
    count=w.IntSlider(description='候補数',min=5,max=10,value=10)
    people=w.BoundedIntText(description='出演人数',min=1,max=10,value=2)
    diarize=w.Checkbox(description='話者を自動推定する',value=True)
    topics=w.Checkbox(description='話題の区切りも使う',value=True)
    def refresh_info():
        project=state.get('project')
        scope=''
        if project:
            seconds=project.get('analysis',{}).get('test_seconds')
            scope=' ／ 解析範囲：'+('全編' if seconds==0 else f'冒頭{seconds}秒のみ' if seconds else '不明')
        info.value=f"元音声：{html.escape(state['audio'].name) if state['audio'] else '未選択'} ／ BGM：{html.escape(state['bgm'].name) if state['bgm'] else 'なし'}"+scope
    def choose_audio():
        if state['project'] and not reanalyze.value:
            raise ValueError('先に作業を保存し、「再解析を許可」にチェックしてから別の元音声を選んでください')
        paths=upload_one()
        state.update(audio=paths,project=None,video=None)
        candidate.options=[];editor.children=[];speaker_names.children=[];overview.value=''
        with preview:clear_output()
        with movie:clear_output()
        refresh_info();print('元音声を選びました。「解析する」を押してください。')
    def upload_one():
        data=upload()
        names=[Path(n) for n in data if Path(n).suffix.lower() in {'.mp3','.wav','.m4a','.ogg','.flac'}]
        if len(names)!=1:raise ValueError('音声ファイルを1本だけ選択してください')
        # Colab writes bytes to cwd; use our own unique directory to avoid name collisions.
        directory=Path(tempfile.mkdtemp(prefix='campus-upload-'))
        path=directory/names[0].name
        path.write_bytes(data[str(names[0])])
        return path
    def choose_bgm():
        state['bgm']=upload_one();refresh_info();print('BGMを選びました。解析のやり直しは不要です。')
    def remove_bgm():
        state['bgm']=None;refresh_info();print('BGMなしにしました。')
    def run_analysis():
        if not state['audio']:raise ValueError('先に元音声を選択してください')
        if state['project'] and not reanalyze.value:
            raise ValueError('すでに解析済みです。再解析すると編集を破棄します。「再解析を許可」にチェックしてください。')
        project=analyze(state['audio'],test_seconds=sample.value,speakers=people.value,use_speakers=diarize.value,use_topics=topics.value,count=count.value,report=print)
        state['project']=project;state['video']=None;reanalyze.value=False
        refresh_info();refresh_candidates();refresh_names();tabs.selected_index=1
        if not project['candidates']:
            start.value=project['segments'][0]['start'];end.value=min(project['segments'][-1]['end'],start.value+60)
            overview.value='30〜60秒の候補がないため、範囲を手動指定してください。';refresh_segments()
    reanalyze=w.Checkbox(description='再解析を許可（字幕・範囲の編集を破棄）',value=False)
    def refresh_segments(*_):
        duration.value=f'<b>選択時間：{end.value-start.value:.1f}秒</b>（おすすめ30〜60秒）'
        if not state['project']:return
        rows=[]
        for s in state['project']['segments']:
            if s['end']<=start.value or s['start']>=end.value:continue
            name=w.Text(value=s.get('speaker',''),description='話者名')
            text=w.Textarea(value=s['text'],description='字幕',layout=w.Layout(width='95%',height='80px'))
            name.observe(lambda change,segment=s:segment.update(speaker=change['new']),names='value')
            text.observe(lambda change,segment=s:segment.update(text=change['new']),names='value')
            rows.append(w.VBox([w.HTML(f"{s['start']:.1f}〜{s['end']:.1f}秒"),name,text]))
        editor.children=rows
    def refresh_names():
        if not state['project']:return
        rows=[]
        for name in dict.fromkeys(s.get('speaker','') for s in state['project']['segments']):
            if not name:continue
            field=w.Text(value=name,description=name)
            def rename(old=name,field=field):
                new=field.value.strip()
                if not new:raise ValueError('話者名を入力してください')
                for s in state['project']['segments']:
                    if s.get('speaker')==old:s['speaker']=new
                refresh_names();refresh_segments();print('話者名を変更しました。')
            rows.append(w.HBox([field,button('名前をまとめて変更',rename)]))
        speaker_names.children=rows
    def select_candidate(change):
        index=change['new']
        if index is None or not state['project']:return
        c=state['project']['candidates'][index]
        start.value=c['start'];end.value=c['end'];title.value=c.get('title','')
        reasons=c.get('reasons',[c.get('reason','理由の記録なし')])
        overview.value='<b>内容の要約（字幕の抜粋）</b><p>'+html.escape(c.get('summary','このデータには要約がありません'))+'</p><b>選出理由</b><ul>'+''.join('<li>'+html.escape(r)+'</li>' for r in reasons)+'</ul><small>要約・理由は解析時点の情報です。修正後も自動更新されません。</small>'
        refresh_segments()
    def refresh_candidates(*_):
        if not state['project']:return
        project=state['project'];indices=list(range(len(project['candidates'])))
        q=query.value.strip().lower()
        if q:
            indices=[i for i in indices if q in (' '.join(str(project['candidates'][i].get(k,'')) for k in ['title','summary','reason'])+' '+' '.join(s['text'] for s in project['segments'] if s['end']>project['candidates'][i]['start'] and s['start']<project['candidates'][i]['end'])).lower()]
        indices.sort(key=lambda i:project['candidates'][i]['start'] if sort.value=='time' else -project['candidates'][i].get('score',0))
        candidate.options=[(f"{project['candidates'][i]['start']/60:.1f}分〜 ／ {project['candidates'][i].get('title','候補')}",i) for i in indices]
        if indices:select_candidate(dict(new=indices[0]))
        else:overview.value='一致する候補がありません。検索を変えるか、範囲を手動指定してください。'
    def current_edit():
        if not state['project'] or not state['audio']:raise ValueError('先に解析または保存した作業の読み込みをしてください')
        project=state['project']
        edit=dict(version=1,audio_name=project['audio_name'],start=start.value,end=end.value,title=title.value,format=audio_format.value,bgm_volume=volume.value,segments=[s for s in project['segments'] if s['end']>start.value and s['start']<end.value])
        edit=parse_edit(json.dumps(edit),state['audio'].name)
        duration_audio=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(state['audio'])],check=True,capture_output=True,text=True).stdout)
        if end.value>duration_audio+.1:raise ValueError('選択範囲が元音声の長さを超えています')
        return edit
    def listen():
        edit=current_edit();a=max(0,edit['start']-5);length=edit['end']+5-a
        path=Path(tempfile.mkdtemp(prefix='campus-preview-'))/'preview.wav'
        subprocess.run(['ffmpeg','-y','-v','error','-ss',str(a),'-i',str(state['audio']),'-t',str(length),'-ar','16000','-ac','1',str(path)],check=True)
        with preview:clear_output();display(Audio(filename=str(path)))
        print('選択範囲の前後5秒を含む試聴です。')
    def make_video():
        edit=current_edit();state['video']=None
        with movie:clear_output()
        print('動画を作成しています。完了するまでお待ちください。')
        path=render(state['audio'],edit,state['bgm'] if use_bgm.value else None)
        state['video']=Path(path)
        state['video_edit']=json.dumps(edit,ensure_ascii=False)
        state['video_bgm']=str(state['bgm']) if use_bgm.value else None
        with movie:display(Video(filename=str(path),embed=True,width=300))
        print('完成しました。「完成MP4を保存」を押してください。')
    def save_video():
        if not state['video']:raise ValueError('先に「動画を作る」を押してください')
        if json.dumps(current_edit(),ensure_ascii=False)!=state.get('video_edit') or (str(state['bgm']) if use_bgm.value else None)!=state.get('video_bgm'):
            raise ValueError('編集内容やBGMが変わっています。「動画を作る」で作り直してから保存してください')
        download(str(state['video']))
    def save_session():
        edit=current_edit()
        path=Path(tempfile.mkdtemp(prefix='campus-session-'))/'campus-voice-session.json'
        path.write_text(json.dumps(dict(kind='campus-voice-session',version=1,project=state['project'],selection=edit),ensure_ascii=False,indent=2))
        download(str(path));print('作業を保存しました。次回は元音声とこのJSONを読み込めます。')
    def restore_session():
        if not state['audio']:raise ValueError('先に元音声を選んでください')
        uploaded=upload()
        if len(uploaded)!=1:raise ValueError('作業JSONを1つ選択してください')
        data=json.loads(next(iter(uploaded.values())))
        if data.get('kind')!='campus-voice-session':raise ValueError('「作業を保存」で取得したJSONを選択してください')
        project=data['project'];saved=data['selection']
        parse_edit(json.dumps(saved),state['audio'].name)
        if project.get('audio_name')!=state['audio'].name or not isinstance(project.get('segments'),list) or not isinstance(project.get('candidates'),list):raise ValueError('作業JSONか元音声が一致しません')
        state['project']=project;state['video']=None
        refresh_candidates();refresh_names()
        start.value=saved['start'];end.value=saved['end'];title.value=saved.get('title','');volume.value=saved.get('bgm_volume',.12);audio_format.value=saved['format']
        refresh_info();refresh_segments();tabs.selected_index=1;print('作業を再開しました。解析のやり直しは不要です。')
    candidate.observe(select_candidate,names='value')
    query.observe(refresh_candidates,names='value');sort.observe(refresh_candidates,names='value')
    start.observe(refresh_segments,names='value');end.observe(refresh_segments,names='value')
    tabs=w.Tab(children=[
        w.VBox([w.HTML('<h3>1. 音声を選んで解析</h3><p>元のラジオ音声を選び「解析する」を押します。全編は時間がかかります。</p>'),button('元音声を選ぶ',choose_audio),info,w.HBox([button('BGMを選ぶ（任意）',choose_bgm),button('BGMなしにする',remove_bgm)]),sample,people,diarize,topics,count,reanalyze,button('解析する',run_analysis,'primary'),button('保存した作業を読み込む',restore_session)]),
        w.VBox([w.HTML('<h3>2. 候補を確認して編集</h3><p>候補を選び、前後を試聴。字幕・話者名・範囲を修正します。変更はこの画面内で保持されます。</p>'),query,sort,candidate,overview,w.HBox([start,end]),duration,title,button('前後を試聴',listen),preview,w.HTML('<b>話者名をまとめて設定</b>'),speaker_names,editor,button('作業を保存（次回再開用）',save_session)]),
        w.VBox([w.HTML('<h3>3. 動画を作って保存</h3><p>現在の選択範囲と字幕で作ります。2本目は「候補と編集」へ戻って選び直してください。</p>'),audio_format,volume,use_bgm,button('動画を作る',make_video,'success'),movie,button('完成MP4を保存',save_video),button('作業を保存（次回再開用）',save_session)])
    ])
    for i,label in enumerate(['素材と解析','候補と編集','動画と保存']):tabs.set_title(i,label)
    app=w.VBox([w.HTML('<h2>Campus Voice</h2><p>①素材と解析 → ②候補と編集 → ③動画と保存</p><p>終了前に「作業を保存」。Colabの接続が切れると未保存の作業は消えることがあります。</p>'),tabs,w.HTML('<b>進行状況・メッセージ</b>'),log])
    return app


def launch_colab_app():
    print('② 起動準備：Colabの表示機能を読み込んでいます。', flush=True)
    from google.colab import files, output
    from IPython.display import display, HTML
    import ipywidgets as w
    from importlib.metadata import version
    if w.__version__ != version('ipywidgets'):
        raise RuntimeError('古い表示ライブラリがメモリに残っています。「ランタイム → セッションを再起動」の後、②だけ実行してください。')
    print(f'表示ライブラリ: ipywidgets {w.__version__}', flush=True)
    output.enable_custom_widget_manager()
    display(HTML('<p><b>操作画面を表示しています。</b>下にタブが出ない場合は出力欄を展開し、ノートブックを再読み込みしてください。それでも出ない場合は、このメッセージと②の出力を送ってください。</p>'))
    app=create_app(files.upload,files.download)
    status=w.HTML('最初に「表示確認」を押してください。')
    check=w.Button(description='表示確認',button_style='info')
    def confirm(_):
        status.value='✓ 操作できます。下の「元音声を選ぶ」から始めてください。'
    check.on_click(confirm)
    display(w.VBox([w.HBox([check,status]),app]))
    print('② 起動処理が完了しました。上の「表示確認」を押してください。', flush=True)
    return app
