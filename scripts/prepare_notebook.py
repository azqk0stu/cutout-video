"""Embed the current static editor into the Colab notebook for a no-deploy trial."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
path = root / 'notebooks/campus_voice.ipynb'
nb = json.loads(path.read_text())
html = (root / 'web/index.html').read_text()
css = (root / 'web/style.css').read_text()
model = (root / 'web/model.js').read_text().replace('export function', 'function')
app = (root / 'web/app.js').read_text().replace("import {validateProject,exportEdit} from './model.js';", '')
html = html.replace('<link rel="stylesheet" href="style.css">', '<style>'+css+'</style>')
html = html.replace('<script type="module" src="app.js"></script>', '<script type="module">'+model+'\n'+app+'</script>')
portable_source = '# 解析後に、解析結果入りの編集画面を出力する準備です。\nfrom pathlib import Path\nfrom google.colab import files\nimport json\nEDITOR_HTML = '+repr(html)+'\n'
portable_source += r'''def save_editor(project):
    payload = json.dumps(project, ensure_ascii=False).replace("<", "\\u003c")
    embedded = '<script type="application/json" id="embeddedProject">'+payload+'</script>'
    result = EDITOR_HTML.replace('<script type="module">', embedded+'<script type="module">', 1)
    Path("campus-voice-editor.html").write_text(result, encoding="utf-8")
    files.download("campus-voice-editor.html")
print("準備完了。候補作成後に、解析結果入りのHTMLがダウンロードされます。")
'''
cell = {'cell_type':'code','metadata':{'tags':['portable-editor']},'execution_count':None,'outputs':[], 'source': portable_source.splitlines(True)}
nb['cells'] = [c for c in nb['cells'] if 'portable-editor' not in c.get('metadata',{}).get('tags',[])]
nb['cells'].insert(2,cell)
# Keep the ranking implementation executable without repository downloads in Colab.
algorithm = (root / 'scripts/candidates.py').read_text()
for candidate_cell in nb['cells']:
    if 'candidate-ranking' in candidate_cell.get('metadata', {}).get('tags', []):
        source = ''.join(candidate_cell['source'])
        marker = '# 候補だけ再計算する場合は、このセルから実行します。'
        source = source[source.index(marker):]
        candidate_cell['source'] = (algorithm + '\n' + source).splitlines(True)
for speaker_cell in nb['cells']:
    if 'speaker-diarization' in speaker_cell.get('metadata', {}).get('tags', []):
        source = ''.join(speaker_cell['source'])
        marker = '# 話者を自動で推定します。'
        source = source[source.index(marker):]
        speaker_cell['source'] = ((root / 'scripts/speakers.py').read_text() + '\n' + source).splitlines(True)
for edit_cell in nb['cells']:
    if 'edit-input' in edit_cell.get('metadata', {}).get('tags', []):
        source = ''.join(edit_cell['source'])
        marker = '# 編集データを読み込む（'
        source = source[source.index(marker):]
        edit_cell['source'] = ((root / 'scripts/edit_input.py').read_text() + '\n' + source).splitlines(True)
path.write_text(json.dumps(nb, ensure_ascii=False, indent=2)+'\n')

# Keep the beginner-facing notebook synchronized with shared modules.
import runpy
runpy.run_path(str(root / 'scripts/build_easy_notebook.py'))
runpy.run_path(str(root / 'scripts/build_live_notebook.py'))
