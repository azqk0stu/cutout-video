"""HTML notebook output with native Colab callbacks; no external API endpoint."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
page=(root/'web/index.html').read_text()
page=page.replace('<link rel="stylesheet" href="style.css">','<style>'+(root/'web/style.css').read_text()+'</style>')
app=(root/'web/model.js').read_text().replace('export function','function')+'\n'+(root/'web/app.js').read_text().replace("import {validateProject,exportEdit} from './model.js';",'')
page=page.replace('<script type="module" src="app.js"></script>','<script type="module">'+app+'\n'+(root/'web/colab_bridge.js').read_text()+'</script>')
controls='''<section><h2>Colabとの一時接続</h2><p>この画面はColab内で動作します。公開サーバーは使用しません。切断前に作業全体を保存してください。</p>
<label>解析範囲<select id="liveSeconds"><option value="0">全編</option><option value="180">冒頭3分だけ</option></select></label>
<label>出演人数<input id="liveSpeakers" type="number" min="1" max="10" value="2"></label>
<label>候補数<input id="liveCount" type="number" min="5" max="10" value="10"></label>
<label><input id="liveDiarize" type="checkbox" checked>話者を推定</label><label><input id="liveTopics" type="checkbox" checked>話題の区切りも使う</label>
<label><input id="liveBgm" type="checkbox">最初に選択したBGMを動画に使う</label><button id="liveAnalyze" data-live>解析する</button><pre id="liveStatus" role="status">接続を確認しています…</pre></section>'''
page=page.replace('<main>','<main>'+controls)
page=page.replace('<input id="audioFile"','<input hidden id="audioFile"')
page=page.replace('試聴用の元音声（サーバーへ送信しません）','試聴音声はColabから取得します（音声の再選択は不要）')
page=page.replace('<button id="download">','<button id="liveRender" data-live>この内容で動画を作る</button><div id="liveResult"></div><p>BGMはColab起動時に選択したものを使えます。</p><button id="download">')
modules=['candidates','speakers','edit_input','render_clip','pipeline','html_bridge']
source=[]
for module in modules:
 text=(root/'scripts'/f'{module}.py').read_text()
 source.append('\n'.join(line for line in text.splitlines() if not line.startswith('from scripts.')))
source.append('LIVE_HTML = '+repr(page)+'\ncampus_bridge = launch_html_editor(LIVE_HTML)\n')
def md(s):return dict(cell_type='markdown',metadata={},source=s.splitlines(True))
def code(s):return dict(cell_type='code',metadata={'cellView':'form'},execution_count=None,outputs=[],source=s.splitlines(True))
nb=dict(nbformat=4,nbformat_minor=5,metadata={'colab':{'name':'Campus Voice — HTML接続版'},'kernelspec':{'display_name':'Python 3','name':'python3'}},cells=[
 md('# Campus Voice — HTML接続版\n①準備→セッション再起動→②起動して元音声を選択。その後は表示されたHTML画面で解析・試聴・編集・動画生成を操作します。ipywidgetsや公開トンネルは使いません。\n\n別タブの外部サイトへ接続する方式ではありません。無料Colabのノートブック内でHTMLを表示します。実Colabでの通し操作は未検証です。終了前は作業全体を保存してください。'),
 code('#@title ① 準備（完了後にセッション再起動）\n'+(root/'scripts/colab_setup.py').read_text()+'\nsetup_colab()\n'),
 code('#@title ② 元音声を選びHTML画面を開く\n'+'\n\n'.join(source))])
(root/'notebooks/campus_voice_live.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=2)+'\n')
(root.parent/'campus-voice-live.html').write_text(page)
print('Built HTML connection notebook')
