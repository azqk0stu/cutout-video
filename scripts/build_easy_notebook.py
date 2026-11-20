"""Bundle a button-only Colab notebook without requiring GitHub runtime fetches."""
import json
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[1]
modules=['candidates','speakers','edit_input','render_clip','pipeline','colab_app']
# Reuse the existing static editor, with no user content bundled in Git.
legacy=json.loads((root/'notebooks/campus_voice.ipynb').read_text())
portable=next(c for c in legacy['cells'] if 'portable-editor' in c.get('metadata',{}).get('tags',[]))
tree=ast.parse(''.join(portable['source']))
editor_html=next(node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('<!doctype'))
source=['PORTABLE_EDITOR_HTML = '+repr(editor_html)]
for module in modules:
    text=(root/'scripts'/f'{module}.py').read_text()
    text='\n'.join(line for line in text.splitlines() if not line.startswith('from scripts.'))
    source.append(text)
source.append('campus_app = launch_colab_app()\n')

def md(text):return dict(cell_type='markdown',metadata={},source=text.splitlines(True))
def code(text,tag):return dict(cell_type='code',metadata={'tags':[tag],'cellView':'form'},execution_count=None,outputs=[],source=text.splitlines(True))
nb=dict(nbformat=4,nbformat_minor=5,metadata={'colab':{'name':'Campus Voice — かんたん操作画面'},'kernelspec':{'display_name':'Python 3','name':'python3'},'language_info':{'name':'python'}},cells=[
    md('# Campus Voice — かんたん操作画面\n\n無料のColab内で、音声解析と動画生成はこのColabで、候補確認・試聴・字幕編集は前の編集画面で行います。編集結果はコピー＆貼り付けで戻します。\n\n**最初だけ①を実行 → セッションを再起動 → ②を実行してください。** 画面が出たら、セルではなくボタンを使います。\n\nGPU推奨：「ランタイム → ランタイムのタイプを変更 → T4 GPU」。無料枠の割当や処理時間は保証されません。音声はColabへアップロードされます。共有用の公開URLは作りません。'),
    code('#@title ① 最初の準備（完了後にセッションを再起動）\n'+(root/'scripts/colab_setup.py').read_text()+'\nsetup_colab()\n','setup'),
    md('### ② 操作画面を開く\n①の後に「ランタイム → セッションを再起動」を行い、このセルの▶を1回押してください。起動後は音声解析 → 編集画面HTMLを保存してPCで開く → 編集結果を貼り付け → 動画生成の順に操作します。\n\n**編集途中に②を再実行すると新しい画面になり、作業が引き継がれません。** 終了前に「作業を保存」と「完成MP4を保存」を押してください。再接続後は、元音声と保存した作業JSONを読み込めば再解析せず続けられます。'),
    code('#@title ② 操作画面を開く（起動後は下のボタンで操作）\n'+'\n\n'.join(source),'app'),
    md('### よくある困りごと\n- ボタンが出ない：②の「起動準備」等の文字が表示されるか確認してください。出力が折りたたまれていたら展開し、再起動後に②を実行してください。Colabからウィジェット表示の許可を求められたら確認してください。\n- 解析が長い：全編は時間がかかります。進行状況欄を確認してください。最初の確認だけなら解析範囲を「冒頭3分」にできます。\n- HF Hubの未認証の警告：ダウンロードが進んでいれば待って構いません。\n- 話者名が違う：「候補と編集」で名前を直してください。自動推定は同時発話・短い相づち等で誤ることがあります。\n- 候補の要約は字幕の抜粋です。内容と範囲は必ず試聴して確認してください。\n- Colabが切れた：①②で起動し直し、元音声→保存した作業の順に読み込みます。BGMは別途選び直します。\n- データの削除：手元の保存ファイルを削除し、Colabは「接続を解除して削除」で一時データを削除できます。Driveへの自動保存はしません。')])
(root/'notebooks/campus_voice_easy.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=2)+'\n')
print('Built notebooks/campus_voice_easy.ipynb')
